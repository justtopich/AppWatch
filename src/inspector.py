import datetime as dtime
from time import sleep
from threading import Thread
from subprocess import Popen, PIPE, DEVNULL
import signal, shutil, os, sys
import traceback

import requests

from __init__ import __version__
from conf import cfg, log, notify, templater


localName = cfg['notify']['localName']
localIp = cfg['notify']['localIp']
intervalCheckMin = cfg['tasks']['intervalCheckMin']
sendedNotify = {}


# ловит ctrl-C. Останавливает модули в нужном порядке
def shutdown_me(signum, frame):
    log.warning('Получена команда завершения работы')
    os._exit(1)

def send_notify(app, event, body):
    try:
        # decorator?
        now = dtime.datetime.now()
        if app not in sendedNotify: sendedNotify[app] = {}
        if event not in sendedNotify[app]:
            sendedNotify[app][event] = now
        else:
            delta = now - sendedNotify[app][event]
            if delta < resendTime:
                log.info(f"Отчёт по событию {event} уже был отправлен.")
                return

        log.debug(f"Создание отчёта по событию {app}: {event}")
        if not notify.send_notify(app, event, body):
            del sendedNotify[app][event]

    except Exception as e:
        log.error(f"Fail send notify: {e}")
        del sendedNotify[app][event]

def process_inspector():
    def is_alive(exe):
        # можно использовать | find
        conv = Popen(f'taskList /svc /fi "IMAGENAME eq {exe}" /nh', shell=True, encoding='cp866',
                     stdout=PIPE, stderr=PIPE, stdin=DEVNULL)
        stdout = str(conv.communicate())
        result = stdout.split()[0].split("\\n")[-1]
        return result.lower() == exe

    def restart(data, job, isDead=False):
        status = 0
        failList[app]['attemp'] += 1
        if not isDead:
            try:
                Popen(f'TASKKILL /f /im {exe}', shell=True, stdout=PIPE, stderr=PIPE)
                n = 0
                while is_alive(exe):
                    sleep(1)
                    n += 1
                    if n > 100: raise Exception(f"Не удалось убить процесс {app} : {exe}")
            except Exception as e:
                data = f'Не удалось перезапустить процесс: {e}\n'
                log.error(data)
                status = 2

        if status == 0:
            log.debug(f"Запуск приложения {exe}")
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
                    data = f"Не удалось перезапусть процессня: {exe} ({app}): {e}\n"
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
                    data += ' выполнена успешно.\n'
                    failList[app]['isAlive'] = False
                    failList[app]['attemp'] -= 1
                    log.info(data)
                else:
                    data = f"Не удалось перезапусть {app}: он вновь падает\n"
                    log.error(data)
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
                    log.debug(f"Найден процесс {app}. Запрос статуса.")
                    try:
                        res = requests.get(url, timeout=10)
                        if res.status_code != 200:
                            raise Exception(f"Server return status {res.status_code}")

                        log.debug(f"процесс {app} работает.")

                        if not failList[app]['isAlive']:
                            continue
                        else:
                            failList[app]['isAlive'] = False
                            data = templater.tmpl_fill(selfName, 'alive')
                    except Exception as e:
                        status = 1
                        data = f"Процесс {app} не отвечает или вернул не верный статус: {e}"
                        log.warning(data)
                        body = templater.tmpl_fill(selfName, "badAnswer")
                        failList[app]['isAlive'] = True

                    if status != 0 and doRestart:
                        data = restart(data, job)
                        body += data

                    send_notify(selfName, "badAnswer", body)
                elif not isAlive and alwaysWork:
                    body = templater.tmpl_fill(selfName, 'notFound')
                    log.warning(f"Отсутсвует обязательный процесс {app}. Попытка запуска")
                    data = restart('Попытка перезапуска', job, isDead=True)
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

                    send_notify(selfName, 'error', body)
                    break
                else:
                    pass
                log.debug(f"Корректная лицензия {app}")

            except Exception as e:
                if e.errno == 2:
                    log.warning(f"Не найден журнал лицензии {app}")
                else:
                    log.error("Ошибка чтения журнала лицензии %s: %s" % (app, e))

        sleep(intervalCheckMin*2)

def disk_inspector():
    log.debug("disk_inspector started")
    selfName = 'disk_inspector'
    critFree = cfg['tasks']['diskTask']['critFree']
    diskUsage = cfg['tasks']['diskTask']['diskUsage']
    diskWarn = cfg['tasks']['diskTask']['diskWarn']
    templater.extend_legend(selfName, {"critFree": critFree, "diskUsage": diskUsage, "diskWarn": diskWarn, "diskFree": 0 })

    while True:
        diskFree = round(shutil.disk_usage(diskUsage).free / 1073741824, 2)
        templater.legendTmpl[selfName]["diskFree"] = diskFree
        if diskFree < critFree:
            log.error(f"Критически мало места! Осталось всего: {diskFree}")
            event = 'critFree'
            body = templater.tmpl_fill(selfName, event)
            send_notify(selfName, event, body)
        elif diskFree < diskWarn:
            log.warning(f"Заканчивается место. Свободно на диске: {diskFree}GB")
            event = 'diskWarn'
            body = templater.tmpl_fill(selfName, event)
            send_notify(selfName, event, body)
        elif diskFree > diskWarn:
            log.info("Свободно места %s GB. До лимита ещё: %s GB" % (diskFree, round(diskFree - diskWarn,2)))

        #TODO maybe use custom timer
        sleep(intervalCheckMin)

if __name__ != "__main__":
    resendTime = dtime.timedelta(minutes=cfg['notify']['resendTime'])

    if 'diskTask' in cfg['tasks']:
        ht3 = Thread(target=disk_inspector, name='disk_inspector')
        ht3.start()

    if 'jobList' in cfg['tasks']:
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
