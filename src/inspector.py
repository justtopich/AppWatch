from AppWatch import (
    os, sys,
    dtime,
    sleep,
    shutil,
    signal,
    Thread,
    Popen, PIPE, DEVNULL,
    traceback,
    requests,
    notification,
    __version__,
    homeDir, dataDir)
from conf import cfg, log, notify, templater


def new_toast(title: str, msg: str):
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

# ловит ctrl-C. Останавливает модули в нужном порядке
def shutdown_me(signum, frame):
    log.warning('Получена команда завершения работы')
    os._exit(1)

def send_notify(taskName, event, body):
    try:
        # decorator?
        now = dtime.datetime.now()
        if taskName not in sendedNotify: sendedNotify[taskName] = {}
        if event not in sendedNotify[taskName]:
            sendedNotify[taskName][event] = now
        else:
            delta = now - sendedNotify[taskName][event]
            if delta < resendTime:
                log.info(f"Отчёт по событию {event} уже был отправлен.")
                return

        log.debug(f"Создание отчёта по событию {taskName}: {event}")
        if not notify.send_notify(taskName, event, body):
            del sendedNotify[taskName][event]

    except Exception as e:
        log.error(f"Fail send notify: {e}")
        del sendedNotify[taskName][event]

def process_inspector():
    def is_alive(exe):
        # можно использовать | find
        conv = Popen(f'taskList /svc /fi "IMAGENAME eq {exe}" /nh', shell=True, encoding='cp866',
                     stdout=PIPE, stderr=PIPE, stdin=DEVNULL)
        stdout = str(conv.communicate())
        result = stdout.split()[0].split("\\n")[-1]
        return result.lower() == exe

    def restart(job, isDead=False):
        data = ""
        status = 0
        failList[app]['attemp'] += 1
        if not isDead:
            try:
                Popen(f'TASKKILL /f /im {exe}', shell=True, stdout=PIPE, stderr=PIPE)
                n = 0
                while is_alive(exe):
                    sleep(1)
                    n += 1
                    if n > 100: raise Exception(f"Не удалось убить процесс {app}: {exe}")
            except Exception as e:
                data = f'Не удалось перезапустить процесс: {e}\n'
                log.error(data)
                status = 2

        if status == 0:
            log.debug(f"Запуск приложения {app}")
            whatStart = job['whatStart']
            if whatStart == 'script':
                 target = job['script']
            elif whatStart == 'exe':
                target = f"{job['path']}{exe} {job['exeKey']}"
            else:
                target = ''

            if target != '':
                log.info(f"Начат запуск {app}")
                try:
                    os.system(f"start cmd /c {target}")
                except Exception as e:
                    data = f"Не удалось перезапусть процесс: {exe} ({app}): {e}\n"
                    status = 3
                    log.error(data)
            else:
                log.info(f"Начат запуск службы {job['service']}")
                try:
                    # hSCManager = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_CONNECT)
                    # handle = win32service.OpenService(hSCManager, jobListTmp['service'], win32service.SERVICE_ALL_ACCESS)
                    # win32service.StartService(handle, None)
                    # win32service.CloseServiceHandle(handle)
                    p = Popen(f"net start {job['service']}", shell=True, encoding='cp866',
                              stdout=PIPE, stderr=PIPE, stdin=DEVNULL)
                    stdout, stderr = p.communicate()
                    if stdout:
                        for line in stdout.split('\n'):
                            line.replace('\n\n', '')
                            if line != '':
                                log.info(line)
                    if stderr:
                        for line in stderr.split('\n'):
                            line.replace('\n\n', '')
                            if line != '':
                                log.error(line)

                except Exception as e:
                    log.error(str(e))
                    e = traceback.format_exc()
                    status = 3
                    data = f"Не удалось перезапусть службу: {job['service']} ({app}): {e}\n"
                    log.error(data)

            # проверка что он снова не упал
            #TODO отсчёт времени падения после старта
            if status == 0:
                sleep(restartTime)
                if is_alive(exe):
                    data += 'Перезапуск приложения выполнено успешно.\n'
                    failList[app]['isAlive'] = False
                    failList[app]['attemp'] -= 1
                    log.info(data)
                else:
                    data = f"Не удалось перезапусть {app}: он вновь падает\n"
                    log.error(data)

        new_toast(app, data)
        return data

    log.debug("process_inspector started")
    selfName = "process_inspector"
    failList = {}
    for job in jobList:
        failList[job] = {'isAlive' : False, "attemp" : 0}

    while True:
        try:
            #TODO или всё забрать или убрать лишние
            for job in jobList.values():
                app = job['task']
                url = job['url']
                exe = job['exe'].lower()
                doRestart = job['doRestart']
                alwaysWork = job['alwaysWork']
                restartTime = job['restartTime']
                respTime = job['respTime']
                status = 0
                body = ''

                log.info(f'Check app {app}')
                isAlive = is_alive(exe)
                if isAlive:
                    log.debug(f"Found {app}. Check http status")
                    try:
                        res = requests.get(url, timeout=respTime)
                        if res.status_code != 200:
                            raise Exception(f"Server return status {res.status_code}")

                        log.debug(f"{app} is fine.")

                        if not failList[app]['isAlive']:
                            continue
                        else:
                            failList[app]['isAlive'] = False
                            data = templater.tmpl_fill(selfName, 'alive')
                    except Exception as e:
                        status = 1
                        data = f"{app} не отвечает или вернул не верный статус. Предпринята попытка перезапуска\n"
                        new_toast(f'Презапуск {app}', data)
                        log.warning(data)

                        body = templater.tmpl_fill(selfName, "badAnswer").replace("{{app}}", app, -1)
                        failList[app]['isAlive'] = True

                    if status != 0 and doRestart:
                        data += restart(job)
                        body += data

                    send_notify(app, "badAnswer", body)
                elif not isAlive and alwaysWork:
                    body = templater.tmpl_fill(selfName, 'notFound').replace("{{app}}", app, -1)
                    data = f"Отсутсвует обязательныое приложение {app}. Предпринята попытка запуска\n"
                    log.warning(data)
                    new_toast(f'Запуск {app}', data)

                    data += restart(job, isDead=True)
                    body += data
                    send_notify(app, 'notFound', body)

            sleep(intervalCheckMin)
        except Exception as e:
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
                    #TODO open if file is changed
                    with open(logFile, encoding='utf-8') as f:
                        cnt = f.read()

                    for tmpl in templates:
                        tmpl = templater.get_tmpl(selfName, tmpl)
                        if tmpl in cnt:
                            log.error(f"Ошибка лицензии {taskName}")
                            body = templater.tmpl_fill(selfName, 'error').replace('{{app}}', taskName, -1)

                            new_toast(taskName, 'Ошибка лицензии')
                            send_notify(taskName, 'error', body)

                except FileNotFoundError:
                    log.error(f"Не найден журнал лицензии {taskName}")
                except Exception as e:
                    log.error(f"Ошибка проверки журнала лицензии {taskName}: {e}")

            sleep(intervalCheckMin*2)
        except Exception as e:
            e = traceback.format_exc()
            log.critical(str(e))
            break

def disk_inspector():
    def fill_tmpl(event: str) -> str:
        body = templater.tmpl_fill(selfName, event)
        body = body.replace('{{critFree}}', str(critFree), -1)
        body = body.replace('{{diskFree}}', str(diskFree), -1)
        body = body.replace('{{diskUsage}}', diskUsage, -1)
        return body.replace('{{diskWarn}}', str(diskWarn), -1)


    log.debug("disk_inspector started")
    selfName = 'disk_inspector'

    while True:
        for name, task in cfg['tasks']['diskTask'].items():
            critFree = task['critFree']
            diskUsage = task['diskUsage']
            diskWarn = task['diskWarn']

            try:
                diskFree = round(shutil.disk_usage(diskUsage).free / 1073741824, 2)
                if diskFree < critFree:
                    log.error(f"Критически мало места! Осталось всего: {diskFree}")
                    event = 'critFree'
                    body = fill_tmpl(event)

                    new_toast(diskUsage, f"Критически мало места! Осталось всего: {diskFree}")
                    send_notify(name, event, body)
                elif diskFree < diskWarn:
                    log.warning(f"Заканчивается место. Свободно на диске: {diskFree}GB")
                    event = 'diskWarn'
                    body = fill_tmpl(event)

                    new_toast(diskUsage, f"Заканчивается место. Свободно на диске: {diskFree}GB")
                    send_notify(name, event, body)
                elif diskFree > diskWarn:
                    log.info(f"Свободно места {diskFree} GB")

            except Exception as e:
                log.critical(f'disk_inspector: {traceback.format_exc()}')
                raise SystemExit(1)

        # TODO maybe use custom timer
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

    log.info("AppWatch started. Version " + __version__)

    if 'run' in sys.argv:
        signal.signal(signal.SIGTERM, shutdown_me)
        signal.signal(signal.SIGINT, shutdown_me)
        input()
        while True:
            input('Use Ctrl+C to stop me\n')