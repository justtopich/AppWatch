"""
Simple WatchDog for Windows applications with email or Slack notifications.
Delete .cfg file and run script to create example configuration.
"""

from time import sleep
import datetime as dtime
from threading import Thread
from subprocess import Popen, PIPE, CREATE_NEW_CONSOLE, DEVNULL, run
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from json import dumps
import signal, shutil
import traceback

import requests, smtplib

from __init__ import __version__


# ловит ctrl-C. Останавливает модули в нужном порядке
def shutdown_me(signum, frame):
    log.warning('Получена команда завершения работы')
    os._exit(1)

def send_notify(app,body, sendTime=None):
    global failList
    now = dtime.datetime.now()
    if sendTime is None:
        failList[app]['send_time'] = now
    else:
        delta = now - sendTime
        if delta < resendTime:
            log.info("Отчёт по событию " + app + " уже был отправлен.")
            return

    if noify == 'email':
        log.debug("Создание отчёта по событию " + app)
        try:
            # Формируем заголовок письма
            msg = MIMEMultipart('mixed')
            msg['Subject'] = ('Inspecor Pantsu: Бунт на машинке ' + localName)
            msg['From'] = headMail
            msg['To'] = userMail

                # Формируем письмо
            msg.attach(MIMEText(body))
        except Exception as e:
            log.error(str(e))
        log.debug("Соединение с почтовым сервером " + serverMail)
        try:
            s = smtplib.SMTP(serverMail, portMail)
            ## Рукопожатие, обязательно
            s.ehlo().starttls().ehlo().login(pechkin, passMail)
            s.sendmail(headMail, userMail, msg.as_string())
            log.info("Письмо с отчётом " + app + " отправлено.")
        except Exception as e:
            if e.errno == 11004:
                log.error("Не могу соединиться с почтовым сервером.")
            else:
                log.error("Ошибка при отправлении письма: %s" % e)
        sleep(1)

    else:
        log.info("Отправка отчёта по событию " + app)
        try:
            data = dumps({"text": body})
            headers={"Content-type" : "application/json", 'Content-Length': len(body)}
            res = requests.post(slackUrl, data, headers, timeout = 10)
            if res.status_code != 200:
                raise Exception("Server return status %s" % res.status_code)
            log.info("Отчёт о " + app + " отправлен.")
        except Exception as e:
            log.error("Не могу отправить отчёт в Slack  %s" % e)

def process_inspector ():
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
        if isDead is False:
            try:
                Popen(f'TASKKILL /f /im {exe}', shell=True, stdout=PIPE, stderr=PIPE)
                n = 0
                while is_alive(exe) is True:
                    sleep(1)
                    n += 1
                    if n > 100: raise Exception(f"Не удалось убить процессня {app} : {exe}")
            except Exception as e:
                data = 'Не удалось перезапустить процессня: %s\n' % e
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
                log.info("Начат запуск " + app)
                try:
                    os.system(f"start cmd /c {target}")
                except Exception as e:
                    data = f"Не удалось перезапусть процессня: {exe} ({app}): {e}\n"
                    status = 3
                    log.error(data)
            else:
                log.info("Начат запуск службы " + job['service'])
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
                if is_alive(exe) is True:
                    data += ' выполнена успешно.\n'
                    failList[app]['isAlive'] = False
                    failList[app]['attemp'] -= 1
                    log.info(data)
                else:
                    data = f"Не удалось перезапусть {app}: он вновь падает\n"
                    log.error(data)
        return data

    log.debug("process_inspector started")
    for job in jobList:
        failList[job['task']] = {
            'isAlive' : False,
            "attemp" : 0,
            "send_time" : None}

    while True:
        try:
            #TODO или всё забрать или убрать лишние
            for job in jobList:
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
                if isAlive is True:
                    log.debug(f"Найден процесс {app} Запрос статуса.")
                    try:
                        res = requests.get(url, timeout = 10)
                        if res.status_code != 200:
                            raise Exception("Server return status %s" %res.status_code)

                        log.info(f"процесс {app} работает.")

                        if failList[app]['isAlive'] is False:
                            continue
                        else:
                            failList[app]['isAlive'] = False
                            data = "процессня %s одумался и вернулся к работе ня!" % app
                            # resend = True
                    except Exception as e:
                        status = 1
                        data = f"Процессня {app} не отвечает или вернул не верный статус ня: {e}"
                        log.warning(data)
                        body = f'Сенпай! Под котацу {localName} уснул {app}!\nIP адрес котацу: {localIp}\n'
                        failList[app]['isAlive'] = True

                    if status != 0 and doRestart is True:
                        data = restart(data, job)
                        body += data

                    sendTime = failList[app]['send_time']
                    send_notify(app, body, sendTime)

                elif isAlive is False and alwaysWork is True:
                    body = f'Сенпай! Под котацу {localName} не найден процессня {app}!\nIP адрес котацу: {localIp}\n'
                    log.warning(f"Отсутсвует обязательный процесс {app}. Попытка запуска")
                    data = restart('Попытка перезапуска', job, isDead=True)
                    body += data
                    sendTime = failList[app]['send_time']
                    send_notify(app, body, sendTime)

            sleep(intervalCheckMin)
            # sleep(10)
        except Exception as e:
            e = traceback.format_exc()
            log.error(str(e))
            break

def license_inspector():
    log.debug("license_inspector started")
    while True:
        log.info("Проверка лицензий")
        for job in jobList:
            app = job['task']
            path = job['path']
            log.debug(f"Проверка лицензии {app}")
            try:
                LicLog = open(path+'license.log', encoding = 'utf-8')
                text = LicLog.read()
                LicLog.close()
                if 'LICENSE: Error' in text or 'No license found' in text:
                    log.error(f"Ошибка лицензии {app}")
                    with open(path + 'uid/uid.dat', encoding = 'utf-8') as uidDat:
                        uid = uidDat.read()
                    body = f"Сенпай! Под котацу {localName} процессня {app} отверг присягу лицензии!\n" \
                           f"IP адрес котацу: {localIp}\nUID лицензии: {uid}"
                    send_notify(app,body)
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
    while True:
        free = round(shutil.disk_usage(diskUsage).free / 1073741824, 2)
        if free < critFree:
            log.error(f"Критически мало места! Осталось всего: {free}")
            app = 'critFree'
            body = f"Сенпай! Под котацу {localName} уже нет места!\n" \
                   f"IP адрес сервера: {localIp}\n" \
                   f"Свободно места на диске {diskUsage} : {free}GB"
            send_notify(app, body)
        elif free < diskWarn:
            log.warning(f"Заканчивается место. Свободно на диске: {free}GB")
            app = 'diskWarn'
            body = f"Сенпай! Под котацу {localName} становиться тесновато!\n" \
                   f"IP адрес сервера: {localIp}\n" \
                   f"Свободно места на диске {diskUsage} : {free}GB"
            send_notify(app, body)
        elif free > diskWarn:
            log.info("Свободно места %s GB. До лимита ещё: %s GB" % (free, round(free - diskWarn,2)))
        sleep(intervalCheckMin)

if __name__ != "__main__":
    #TODO убрать *
    from conf import *
    from __main__ import win32serviceutil, win32service

    resendTime = dtime.timedelta(minutes=resendTime)
    global failList
    failList={}

    if diskTask is True:
        failList['diskWarn'] = {'send_time' : None}
        ht3 = Thread(target = disk_inspector, name = 'disk_inspector')
        ht3.start()
    if len(jobList) != 0:
        ht1 = Thread(target = process_inspector, name = 'process_inspector')
        ht1.start()
        ht2 = Thread(target = license_inspector, name = 'license_inspector')
        ht2.start()

    log.info("AppWatch started. Version " + __version__)

    if 'run' in sys.argv:
        signal.signal(signal.SIGTERM, shutdown_me)
        signal.signal(signal.SIGINT, shutdown_me)
        input()
        while True:
            input('Use Ctrl+C to stop me\n')
