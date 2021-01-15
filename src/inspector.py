from AppWatch import (
    sout,
    platform,
    os, sys,
    dtime,
    sleep,
    shutil,
    signal,
    Thread,
    traceback,
    requests,
    psutil,
    notification,
    __version__,
    dataDir)
from conf import cfg, log, notify, templater

if platform == 'nt':
    import win32serviceutil


def new_toast(title: str, msg: str):
    if platform != "nt":
        return
    if len(msg) > 255:
        msg = msg[:256]

    try:
        notification.notify(
            title=title,
            message=msg,
            app_name='AppWatch',
            app_icon=f'{dataDir}notifier/chat_ava.ico',
            timeout=10
        )
    except Exception as e:
        log.error(f"Fail to show windows notification: {e}")


def shutdown_me(signum, frame, appServerSvc=None):
    # ловит ctrl-C. Останавливает модули в нужном порядке
    log.warning('Stopping...')

    if appServerSvc:
        appServerSvc.daemon.exit()

    log.info("Shutdown is successful")
    os._exit(0)


def send_notify(taskName: str, event: str, body: str):
    try:
        # decorator?
        now = dtime.datetime.now()
        if taskName not in sendedNotify:
            sendedNotify[taskName] = {}
        if event not in sendedNotify[taskName]:
            sendedNotify[taskName][event] = {"dtm": now, "body": body}
        else:
            delta = now - sendedNotify[taskName][event]['dtm']
            if delta < resendTime:
                log.info(f"Reject report of an event {event}: is already sent.")
                return

            if cfg['notify']['onlyChanges'] and sendedNotify[taskName][event]['body'] == body:
                log.info(f"Reject report of an event {event}: is not changed from last sent")
                return

        log.debug(f"New report of an event {taskName}: {event}")
        if not notify.send_notify(taskName, event, body):
            del sendedNotify[taskName][event]

    except Exception as e:
        log.error(f"Fail send notify: {e}")
        del sendedNotify[taskName][event]


def process_inspector():
    def get_pid(exe: str, exePath: str, workDir: str=None) -> int:
        # if give workDir, will check only it

        for p in psutil.process_iter(["name", 'exe', 'cwd']):
            # if 'calc1' in p.info['name']:
                # sout(f"{p.pid} | {p.info['name']} | {p.info['cwd']} | {p.info['exe']}", 'violet' )

            if exe == p.info['name'].lower():
                if workDir:
                    if not p.info['cwd'].endswith('/'):
                        p.info['cwd'] = f"{p.info['cwd']}/"

                    if workDir.lower() == p.info['cwd'].replace('\\', '/', -1).lower():
                        return p.pid
                else:
                    if platform == 'nt':
                        exePath = f"{exePath}{exe}"
                    else:
                        exePath = exePath[:-1]

                    if exePath.lower() == p.info['exe'].replace('\\', '/', -1).lower():
                        return p.pid

    def restart(job: dict, exePid: int=None, killRecursive: bool=False) -> str:
        data = ""
        status = 0
        failList[taskName]['attemp'] += 1
        if exePid:
            try:
                assert exePid != os.getpid(), "won't kill myself"
                parent = psutil.Process(exePid)
                children = parent.children(killRecursive)
                children.append(parent)

                # TODO try soft kill before hard
                for p in children:
                    try:
                        # p.send_signal(signal.SIGTERM)
                        p.kill()
                    except psutil.NoSuchProcess:
                        pass

                _, alive = psutil.wait_procs(children, timeout=60)
                if alive:
                    raise Exception(f"Fail to kill process {exe} (PID {exePid})")
            except Exception as e:
                data = f'Fail to restart process {exe}: {e}\n'
                log.error(data)
                status = 2

        if status == 0:
            log.debug(f"Launch application {taskName}")
            whatStart = job['whatStart']

            if whatStart == 'command':
                target = job['command']
            elif whatStart == 'exe':
                target = f"{job['exePath']}{exe} {job['exeKey']}"
            else:
                target = None

            if target:
                log.info(f"Starting {taskName}")
                try:
                    if platform == 'nt':
                        os.system(f"start cmd /c {target}")
                    else:
                        os.system(f"command {target} &")
                except Exception as e:
                    data = f"Fail to restart application: {exe} ({taskName}): {e}\n"
                    status = 3
            else:
                log.info(f"Starting service {job['service']}")
                try:
                    if platform == 'nt':
                        win32serviceutil.StartService(job['service'])
                    else:
                        os.system(f"systemctl start {job['service']}")

                except Exception as e:
                    e = traceback.format_exc()
                    log.error(str(e))
                    status = 3
                    data = f"Fail to start service: {job['service']} ({taskName}): {e}\n"

            # проверка что он снова не упал
            # TODO отсчёт времени падения после старта
            if status == 0:
                sleep(restartTime)
                if get_pid(exe, checkPath, workDir):
                    data += 'Successfully restarted application'
                    failList[taskName]['isAlive'] = False
                    failList[taskName]['attemp'] -= 1
                    log.info(data)
                else:
                    data += f'Fail to start {taskName}'
                    log.error(data)
            else:
                log.error(data)

        new_toast(taskName, data)
        return data

    sleep(3)
    selfName = "process_inspector"
    failList = {}
    for job in jobList:
        failList[job] = {'isAlive': False, "attemp": 0}

    while True:
        try:
            for job in jobList.values():
                taskName = job['task']
                exe = job['exe'].lower()
                checkPath = job['checkPath']
                exePath = job['exePath']
                workDir = job['workDir']
                doRestart = job['doRestart']
                alwaysWork = job['alwaysWork']
                restartTime = job['restartTime']
                respTime = job['respTime']
                status = 0
                body = ''

                log.info(f'Check app {taskName}')
                exePid = get_pid(exe, checkPath, workDir)

                if exePid and not job['checkUrl']:
                    log.debug(f"{taskName} is fine.")
                elif exePid and job['checkUrl']:
                    log.debug(f"Found {taskName}. Check http status")
                    try:
                        res = requests.get(job['url'], timeout=respTime)
                        if res.status_code != 200:
                            raise Exception(f"Server return status {res.status_code}")

                        log.debug(f"{taskName} is fine.")

                        if not failList[taskName]['isAlive']:
                            continue
                        else:
                            failList[taskName]['isAlive'] = False
                            data = templater.tmpl_fill(selfName, 'alive')
                    except Exception:
                        status = 1
                        data = f"{taskName} didn't respond or return wrong answer. Trying to restart application\n"
                        new_toast(f'Restarting {taskName}', data)
                        log.warning(data)

                        body = templater.tmpl_fill(selfName, "badAnswer").replace("{{taskName}}", taskName, -1)
                        failList[taskName]['isAlive'] = True

                    if status != 0 and doRestart:
                        data += restart(job, exePid)
                        body += data

                    send_notify(taskName, "badAnswer", body)
                elif not exePid and alwaysWork:
                    body = templater.tmpl_fill(selfName, 'notFound').replace("{{taskName}}", taskName, -1)
                    data = f"Not found required application {taskName}. Trying to restart\n"
                    log.warning(data)
                    new_toast(f'Starting {taskName}', data)

                    data += restart(job, exePid)
                    body += data
                    send_notify(taskName, 'notFound', body)

            sleep(intervalCheckMin)
        except Exception:
            e = traceback.format_exc()
            log.critical(str(e))
            break


def log_inspector():
    log.debug("log_inspector started")
    selfName = 'log_inspector'
    while True:
        try:
            for taskName, task in cfg['tasks']['logTask'].items():
                log.info(f"Check log {taskName}")
                logFile = task['file']
                templates = task['tmpl']

                try:
                    # TODO open if file is changed
                    with open(logFile, encoding='utf-8') as f:
                        cnt = f.read()

                    for tmplName in templates:
                        tmpl = templater.get_tmpl(selfName, tmplName)
                        if tmpl in cnt:
                            ev = f"Found log expression {taskName}: {tmplName}"
                            log.warning(ev)
                            body = templater.tmpl_fill(selfName, 'error').replace('{{taskName}}', taskName, -1)

                            new_toast('log_inspector', ev)
                            send_notify(taskName, 'error', body)

                except FileNotFoundError:
                    log.error(f"Not found log file {taskName}")
                except Exception as e:
                    log.error(f"Fail to parse log file {taskName}: {e}")

            sleep(intervalCheckMin * 2)
        except Exception:
            e = traceback.format_exc()
            log.critical(str(e))
            break


def disk_inspector():
    def fill_tmpl(event: str) -> str:
        body = templater.tmpl_fill(selfName, event)
        body = body.replace('{{critFree}}', str(critFree), -1)
        body = body.replace('{{diskFree}}', str(diskFree), -1)
        body = body.replace('{{diskUsage}}', diskUsage, -1)
        body = body.replace('{{taskName}}', taskName, -1)
        return body.replace('{{diskWarn}}', str(diskWarn), -1)

    log.debug("disk_inspector started")
    selfName = 'disk_inspector'

    while True:
        for taskName, task in cfg['tasks']['diskTask'].items():
            critFree = task['critFree']
            diskUsage = task['diskUsage']
            diskWarn = task['diskWarn']

            try:
                diskFree = round(shutil.disk_usage(diskUsage).free / 1073741824, 2)
                if diskFree < critFree:
                    log.error(f"Free disk space is critically small on {diskUsage}: {diskFree}")
                    event = 'critFree'
                    body = fill_tmpl(event)

                    new_toast(diskUsage, f"Free disk space is critically small: {diskFree}")
                    send_notify(taskName, event, body)
                elif diskFree < diskWarn:
                    log.warning(f"Free disk space is ends {diskUsage}: {diskFree}GB")
                    event = 'diskWarn'
                    body = fill_tmpl(event)

                    new_toast(diskUsage, f"Free disk space is ends: {diskFree}GB")
                    send_notify(taskName, event, body)
                elif diskFree > diskWarn:
                    log.info(f"disk {diskUsage}: {diskFree}GB free")

            except FileNotFoundError:
                log.error(f'disk_inspector: wrong path: {diskUsage}')
            except Exception as e:
                log.critical(f'disk_inspector: {traceback.format_exc()}')
                shutdown_me(9, 9)
        sleep(intervalCheckMin)

# def tray_icon():
#     image = Image.open(f'{dataDir}notifier/chat_ava.ico')
#     icon = pystray.Icon("name", image, "title")
#     icon.run()


if __name__ != '__main__':
    resendTime = dtime.timedelta(minutes=cfg['notify']['resendTime'])
    localName = cfg['notify']['localName']
    localIp = cfg['notify']['localIp']
    intervalCheckMin = cfg['tasks']['intervalCheckMin']
    sendedNotify = {}

    # ht = Thread(target=tray_icon, name='tray_icon')
    # ht.start()

    if cfg['tasks']['diskTask'] != {}:
        ht3 = Thread(target=disk_inspector, name='disk_inspector')
        ht3.start()

    if cfg['tasks']['logTask'] != {}:
        ht2 = Thread(target=log_inspector, name='log_inspector')
        ht2.start()

    if cfg['tasks']['jobList'] != {}:
        jobList = cfg['tasks']['jobList']
        ht1 = Thread(target=process_inspector, name='process_inspector')
        ht1.start()

    log.info(f"AppWatch started. Version {__version__}_{platform}")

    if 'run' in sys.argv:
        signal.signal(signal.SIGINT, shutdown_me)
        signal.signal(signal.SIGTERM, shutdown_me)
        if platform != 'nt':
            signal.signal(signal.SIGQUIT, shutdown_me)

        input()
        while True:
            input('Use Ctrl+C to stop me\n')
