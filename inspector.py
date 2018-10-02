"""
Simple WatchDog for Windows applications with email or Slack notifications.
Delete .cfg file and run script to create example configuration.
"""

from time import sleep
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

def send_notify(app,body):
    if app in sendedMail:
        log.info("Отчёт по событию " + app + " уже был отправлен.")
        return

    sendedMail.append(app)  # чтобы не спамить на почту
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
    def proc_run(app):
        # можно использовать | find
        conv = Popen('taskList /svc /fi "IMAGENAME eq ' + exe + '" /nh', shell=True, encoding='cp866',
                     stdout=PIPE, stderr=PIPE, stdin=DEVNULL)
        stdout = str(conv.communicate())
        result = stdout.split()[0].split("\\n")[-1]
        return result == exe


    log.debug("process_inspector started")
    while True:
        try:
            for job in jobList:
                app = job[0]
                url = str(job[1])        
                exe = job[2].lower()
                exeKey = job[3]
                path = job[4]
                launchApp = job[5].lower()
                launch = job[6]
                status = 0     
                if launchApp == "" or launchApp == 'none':
                    launchApp = path + exe
                
                if proc_run(app)==True:
                    log.debug("Найден процесс " + app +" Запрос статуса.")
                    try:
                        res = requests.get(url, timeout = 10)
                        if res.status_code!=200:
                            raise Exception("Server return status %s" %res.status_code)
                        log.info("Процесс " + app + " работает.")
                        continue
                    except Exception as e:
                        status = 1
                        data = "Процесс %s не отвечает или вернул не верный статус %s" % (app, e)
                        log.warning(data)
                        body = 'Капитан! На корабле %s взбунтовал матрос %s!\nIP адрес сервера: %s\n' \
                               % (localName, localIp, app)

                    if status != 0 and launch is True:
                        status = 0
                        try:
                            Popen('TASKKILL /f /im ' + exe, shell=True, stdout=PIPE, stderr=PIPE)
                            while proc_run(app)==True:
                                sleep(1)
                        except Exception as e:
                            data = 'Не удалось перезапустить процесс: %s\n' %e
                            log.error(data)
                            status = 2

                        if status == 0:
                            log.debug("Запуск приложения %s (%s)" % (exe, launchApp))
                            try:
                                os.system('START cmd /c "' + launchApp + '" ' + exeKey)  # исп. другой метод
                                log.info("Успешный перезапуск " + app)
                                data += '\nНо он был успешно перезапущен\n'
                            except Exception as e:
                                data = "Не удалось перезапусть процесс: %s (%s): %s\n" % (exe, launchApp, e)
                                log.error(data)

                        body += data
                    send_notify(app, body)
            sleep(intervalCheckMin)
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

    if diskUsage == 1:
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
