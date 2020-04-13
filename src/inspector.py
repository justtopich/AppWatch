import datetime as dtime
from time import sleep
from threading import Thread
from subprocess import Popen, PIPE, DEVNULL
import signal, shutil, os, sys
import traceback
# import six

import requests
# from win10toast import ToastNotifier
from plyer import notification
import pystray

from __init__ import __version__
from conf import cfg, log, notify, templater, homeDir, dataDir


localName = cfg['notify']['localName']
localIp = cfg['notify']['localIp']
intervalCheckMin = cfg['tasks']['intervalCheckMin']
sendedNotify = {}
# toaster = ToastNotifier()

def new_toast(title: str, msg: str):
    try:
        # toaster.show_toast("AppWatch", msg=msg, duration=20, threaded=False, icon_path=None)
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
        a = sendedNotify
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
                target = f"{path}{exe} {job['exeKey']}"
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
                path = job['path']
                doRestart = job['doRestart']
                alwaysWork = job['alwaysWork']
                restartTime = job['restartTime']
                status = 0
                body = ''

                isAlive = is_alive(exe)
                if isAlive:
                    log.debug(f"Found {app}. Check http status")
                    try:
                        res = requests.get(url, timeout=10)
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

                    send_notify(selfName, "badAnswer", body)
                elif not isAlive and alwaysWork:
                    body = templater.tmpl_fill(selfName, 'notFound').replace("{{app}}", app, -1)
                    data = f"Отсутсвует обязательныое приложение {app}. Предпринята попытка запуска\n"
                    log.warning(data)
                    new_toast(f'Запуск {app}', data)

                    data += restart(job, isDead=True)
                    body += data
                    send_notify(selfName, 'notFound', body)

            sleep(intervalCheckMin)
        except Exception as e:
            e = traceback.format_exc()
            log.error(str(e))
            break

def license_inspector():
    log.debug("license_inspector started")
    selfName = 'license_inspector'
    while True:
        log.info("Проверка лицензий")
        for job in jobList.values():
            app = job['task']
            path = job['path']
            log.debug(f"Проверка лицензии {app}")
            try:
                with open(path+'license.log', encoding='utf-8') as LicLog:
                    text = LicLog.read()

                if 'LICENSE: Error' in text or 'No license found' in text:
                    log.error(f"Ошибка лицензии {app}")
                    with open(path + 'uid/uid.dat', encoding='utf-8') as uidDat:
                        uid = uidDat.read()

                    body = templater.tmpl_fill(selfName, 'error')
                    body = body.replace('{{uid}}', uid).replace('{{app}}', app)

                    new_toast(app, 'Ошибка лицензии')
                    send_notify(selfName, 'error', body)
                    break
                else:
                    pass

            except Exception as e:
                if e.errno == 2:
                    log.warning(f"Не найден журнал лицензии {app}")
                else:
                    log.error("Ошибка чтения журнала лицензии %s: %s" % (app, e))
        sleep(intervalCheckMin*2)

def disk_inspector():
    def fill_tmpl(event: str) -> str:
        body = templater.tmpl_fill(selfName, event)
        body = body.replace('{{critFree}}', str(critFree), -1)
        body = body.replace('{{diskUsage}}', diskUsage, -1)
        body = body.replace('{{diskFree}}', str(diskFree), -1)
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
                    log.info("Свободно места %s GB. До лимита ещё: %s GB" % (diskFree, round(diskFree - diskWarn,2)))

            except Exception as e:
                log.critical(f'disk_inspector: {traceback.format_exc()}')
                raise SystemExit(1)

        # TODO maybe use custom timer
        sleep(intervalCheckMin)

# def tray_icon():
#     image = Image.open(f'{dataDir}notifier/chat_ava.ico')
#     icon = pystray.Icon("name", image, "title")
#     icon.run()

if __name__ != "__main__":
    resendTime = dtime.timedelta(minutes=cfg['notify']['resendTime'])

    # ht = Thread(target=tray_icon, name='tray_icon')
    # ht.start()

    if cfg['tasks']['diskTask'] != {}:
        ht3 = Thread(target=disk_inspector, name='disk_inspector')
        ht3.start()

    if cfg['tasks']['jobList'] != {}:
        jobList = cfg['tasks']['jobList']
        ht1 = Thread(target=process_inspector, name='process_inspector')
        ht1.start()
        ht2 = Thread(target=license_inspector, name='license_inspector')
        ht2.start()

    log.info("AppWatch started. Version " + __version__)

    if 'run' in sys.argv:
        signal.signal(signal.SIGTERM, shutdown_me)
        signal.signal(signal.SIGINT, shutdown_me)
        input()
        while True:
            input('Use Ctrl+C to stop me\n')
