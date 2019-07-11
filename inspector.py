"""
Simple WatchDog for Windows applications with email or Slack notifications.
Delete .cfg file and run script to create example configuration.
"""

from time import sleep
import datetime as dtime
from threading import Thread
from subprocess import Popen, PIPE, CREATE_NEW_CONSOLE, DEVNULL
import requests, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from json import dumps
from __init__ import __version__
import signal, shutil
import traceback


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
        conv = Popen('taskList /svc /fi "IMAGENAME eq ' + exe + '" /nh', shell=True, encoding='cp866',
                     stdout=PIPE, stderr=PIPE, stdin=DEVNULL)
        stdout = str(conv.communicate())
        result = stdout.split()[0].split("\\n")[-1]
        return result.lower() == exe


    def restart(data,restartTime):
        status = 0
        failList[app]['attemp'] += 1
        try:
            Popen('TASKKILL /f /im ' + exe, shell=True, stdout=PIPE, stderr=PIPE)
            n = 0
            while is_alive(exe) is True:
                sleep(1)
                n += 1
                if n>100: raise Exception(f"Не удалось убить процесс {app} : {exe}")
        except Exception as e:
            data = 'Не удалось перезапустить процесс: %s\n' % e
            log.error(data)
            status = 2

        if status == 0:
            log.debug(f"Запуск приложения {exe}")
            try:
                os.system('START cmd /c "' + startApp + '" ' + exeKey)  # исп. другой метод
                log.info("Начат перезапуск " + app)

                # проверка что он снова не упал
                sleep(restartTime)
                if is_alive(exe) is True:
                    data += ' выполнена успешно.\n'
                    failList[app]['isAlive'] = False
                    failList[app]['attemp'] -= 1
                else:
                    raise Exception('он упал сразу после запуска')

            except Exception as e:
                data = "Не удалось перезапусть процесс: %s (%s): %s\n" % (exe, startApp, e)
                log.error(data)

        return data


    log.debug("process_inspector started")
    for job in jobList:
        failList[job[0]] = {'isAlive' : False,
                            "attemp" : 0,
                            "send_time" : None}
    while True:
        try:
            for job in jobList:
                app = job[0]
                url = str(job[1])        
                exe = job[2].lower()
                exeKey = job[3]
                path = job[4]
                startApp = job[5].lower()
                doRestart = job[6]
                alwaysWork = job[7]
                restartTime = job[8]
                status = 0
                body = ''
                if startApp == "":
                    startApp = path + exe

                isAlive = is_alive(exe)

                if isAlive is True:
                    log.debug("Найден процесс " + app +" Запрос статуса.")
                    try:
                        res = requests.get(url, timeout = 10)
                        if res.status_code!=200:
                            raise Exception("Server return status %s" %res.status_code)
                        log.info("Процесс " + app + " работает.")
                        if failList[app]['isAlive'] is False:
                            continue
                        else:
                            failList[app]['isAlive'] = False
                            data = "Процесс %s одумался и вернулся к работе!" % app
                            resend = True

                    except Exception as e:
                        status = 1
                        data = "Процесс %s не отвечает или вернул не верный статус %s" % (app, e)
                        log.warning(data)
                        body = f'Капитан! На сервере {localName} взбунтовал процесс {app}!\nIP адрес сервера: {localIp}\n'
                        failList[app]['isAlive'] = True

                    if status != 0 and doRestart is True:
                        data = restart(data, restartTime)
                        body += data

                    sendTime = failList[app]['send_time']
                    send_notify(app, body, sendTime)

                elif isAlive is False and alwaysWork is True:
                    body = f'Капитан! На сервере {localName} отсутсвует процесс {app}!\nIP адрес сервера: {localIp}\n'
                    log.warning(f"Отсутсвует обязательный процесс {app}. Попытка запуска")
                    data = restart('Попытка перезапуска', restartTime)
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
            app = job[0]
            path = job[4]
            log.debug("Проверка лицензии " + app)
            try:
                LicLog = open(path+'license.log', encoding = 'utf-8')
                text = LicLog.read()
                LicLog.close()
                if 'LICENSE: Error' in text or 'No license found' in text:
                    log.error("Ошибка лицензии " + app)
                    with open(path + 'uid/uid.dat', encoding = 'utf-8') as uidDat:
                        uid = uidDat.read()
                    body = 'Капитан! На корабле ' + localName + " произошёл бунт против лицензии, возглавляемый пиратом " \
                        + app + '!\nIP адрес сервера: ' + localIp + '\nUID лицензии: ' + uid
                    send_notify(app,body)
                    break
                else:
                    pass
                log.debug("Корректная лицензия " + app)
            except Exception as e:
                if e.errno == 2:
                    log.warning("Не найден журнал лицензии " + app)
                else:
                    log.error("Ошибка чтения журнала лицензии %s: %s" % (app, e))
        sleep(intervalCheckMin*2)

def disk_inspector():
    log.debug("disk_inspector started")
    while True:
        free = round(shutil.disk_usage(pathUsage).free / 1073741824, 2)
        if free < critFree:
            log.error("Критически мало места! Осталось всего: " + str(free))
            app = 'critFree'
            body = 'Капитан! На корабле ' + localName + " закончилась провизия" + '!\nIP адрес сервера: ' + localIp \
                + '\nСвободно места : ' + str(free)
            send_notify(app, body)
        elif free < diskWarn:
            log.warning("Заканчивается место. Свободно на диске: %s GB" %free)
            app = 'diskWarn'
            body = 'Капитан! На корабле ' + localName + " заканчивается провизия" + '!\nIP адрес сервера: ' + localIp \
                + '\nСвободно на диске : %s GB' %free
            send_notify(app, body)
        elif free > diskWarn:
            log.info("Свободно места %s GB. До лимита ещё: %s GB" % (free, round(free-diskWarn,2)))
        sleep(intervalCheckMin)

if __name__ != "__main__":
    from conf import *

    resendTime = dtime.timedelta(minutes=resendTime)
    global failList
    failList={}

    if diskUsage == 1:
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
        while True: sleep(10)
