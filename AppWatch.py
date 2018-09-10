"""
Simple WatchDog for Windows applications with email or Slack notifications.
Delete .cfg file and run script to create example configuration.
"""

import os.path
from sys import stdout
from time import sleep
import datetime
from threading import Thread
from subprocess import Popen, PIPE, CREATE_NEW_CONSOLE
from logging.handlers import RotatingFileHandler
import logging
import configparser
import requests, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from json import dumps
import re
import shutil


taskList = []
jobList = []
sendedMail = []
diskUsage = 0

def configWrite():
    with open("AppWatch.cfg", "w") as configFile:
        config.write(configFile)

# load config
try:
    config = open('AppWatch.cfg', encoding = 'utf-8')
except IOError:
    with open("AppWatch.cfg", 'tw', encoding = 'utf-8') as configFile: # Создаём конфиг если его нет
        config = configparser.RawConfigParser()
        config.add_section("server")
        config.set("server", "# This Server info",'')
        config.set("server","localName","Pantsu Server")
        config.set("server","localIp","0.0.0.0")
        config.set("server","# Notification service.  mailer or Slack","")
        config.set("server","Notify","mailer")

        config.add_section("Slack")
        config.set("Slack","URL","YOUR_WEBHOOK_URL_HERE")

        config.add_section("mailer")
        config.set("mailer","userMail","user@pantsumail.ru")
        config.set("mailer", "server", "smtp.pantsumail.ru")
        config.set("mailer","Port","587")
        config.set("mailer", "#465 maybe not work")
        config.set("mailer", "user",'username')
        config.set("mailer","password","0000")
        config.set("mailer", "FromHeader", "Pantsu Alarm <user@pantsumail.ru>")
        config.add_section("taskList")
        config.set("taskList", "Active", "0")
        config.set("taskList", "1", "diskUsage")
        config.set("taskList", "2", "MyApp")
        config.set("taskList", "3", "MyHttpServer")
        config.add_section("diskUsage")
        config.set("diskUsage", "Path", "C:\\")
        config.set("diskUsage", "Warning", "30")
        config.set("diskUsage", "Critical", "10")
        config.set("diskUsage", "# Лимит свободного места в ГБ", "")
        config.add_section("MyApp")
        config.set("MyApp", "url", "https://myHost.ru")
        config.set("MyApp", "Path", "C:\Autonomy\MyApp")
        config.set("MyApp", "Exe", "MyApp.exe")
        config.set("MyApp", "# Keys for starting exe", "")
        config.set("MyApp", "ExeKey", "/247 /hidegui")
        config.set("MyApp", "# If set, replace <exe> param", "")
        config.set("MyApp", "startApp", "")
        config.add_section("MyHttpServer")
        config.set("MyHttpServer", "url", "http://127.0.1.1:7252")
        config.set("MyHttpServer", "Path", "C:\path")
        config.set("MyHttpServer", "Exe", "MyServer.exe")
        config.set("MyHttpServer", "ExeKey", "")
        config.set("MyHttpServer", "startApp", "C:\path\StartMyServer.bat")
        config.add_section("logging")
        config.set("logging", "Enable", "True")
        config.set("logging", "LogLevel", "Normal")
        config.set("logging", "# Full or Normal", '')
        config.set("logging", "LogMaxSizeKbs", "10240")
        config.set("logging", "logmaxfiles", "5")
        configWrite()
        raise SystemExit(1)
finally:
    config = configparser.RawConfigParser()
    config.read("AppWatch.cfg")

# Check logging
Level = logging.INFO
logSize = 10240
logCount = 5
try:
    if config.getboolean("logging","enable") == False:
        Level = 0
    else:
        LogLevel = str(config.get("logging","loglevel")).lower()
        if LogLevel == "full":
            Level = logging.DEBUG
        else:
            pass
            # backupCount
        logSize = config.getint("logging", "logmaxsizekbs")
        logCount = config.getint("logging", "logmaxfiles")
except Exception as e:
    print("WARNING: Проверьте параметры logging. Err:",str(e))
    raise SystemExit(1)


# create logger
logFile = 'AppWatch.log'
log_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s',
                                      datefmt = '%Y-%m-%d %H:%M:%S')
myHandler = RotatingFileHandler(logFile, maxBytes = logSize * 1024, backupCount = logCount, delay = 0)
myHandler.setFormatter(log_formatter)
log = logging.getLogger('root')
log.setLevel(int(Level))
log.addHandler(myHandler)

cons_log = logging.getLogger('root')
cons_log.setLevel(int(Level))
consoleHandler = logging.StreamHandler(stdout)
consoleHandler.setFormatter(log_formatter)
cons_log.addHandler(consoleHandler)

def log_time():
    return str(datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S "))

# check general settings
try:
    localName = (config.get("server", "localName"))
    localIp = (config.get("server", "localIp"))
    noify = (config.get("server", "notify"))
    log.info("Local server is %s (%s)" %(localIp,localName))
except Exception as e:
    log.error("%s" %e)
    raise SystemExit(1)

# check if tasks
try:
    active = config.getint('taskList', "active")
    # print(log_time()+"DEBUG: Задано "+str(active)+" заданий")
    log.info("Задано "+str(active)+" заданий")
    if active <= 0:  # можно было бы и параметры проверить, но грамоздить ступеньки...
        log.error("Нет заданий для выполнения. Остановка приложения.")
        raise SystemExit(1)
    else:
        n = 1
        while n <= active:
            try:
                task = config.get('taskList', str(n))
                if not config.has_section(task):
                    log.error("Задано несуществующее задание " + task)
                else:
                    taskList.append(task)
            except:
                log.warning("В taskList нет задания %s" % n)
                raise SystemExit(1)
            n = n + 1
except Exception as e:
    log.warning("Проверьте параметры снкции taskList: %e" %e)
    raise SystemExit(1)

# check tasks settings and create tasks list
for task in taskList:
    if task=='diskUsage':
        try:
            diskWarn = int(config.get('diskUsage', "Warning"))
            critFree = int(config.get('diskUsage', "Critical"))
            pathUsage = config.get('diskUsage', "path")
            pathUsage = pathUsage.replace('\\', '/') + '/'
            log.info("Задан diskUsage. Папка: %s. Лимит: %s" % (pathUsage, diskWarn))
            diskUsage = 1
        except Exception as e:
            log.error("Проверьте параметры: %s" % e)
        continue

    jobListTmp = []
    try:
        jobListTmp.append(task)
        jobListTmp.append(config.get(task, "url"))
        jobListTmp.append(config.get(task, "Exe"))
        jobListTmp.append(config.get(task, "ExeKey"))
        path = config.get(task, "path")
        path = path.replace('\\','/')+'/'
        jobListTmp.append(path)
        startApp = config.get(task, "startApp")
        startApp = startApp.replace('\\','/')
        jobListTmp.append(startApp)
        jobList.append(tuple(jobListTmp))
    except Exception as e:
        log.error("Задание "+task+" отклонено. Проверьте параметры: %s" %e)
        raise SystemExit(1)


# check mailer settings
if noify=='mailer':
    try:
        userMail = (config.get("mailer", "userMail"))
        serverMail = (config.get("mailer", "server"))
        portMail = (config.getint("mailer", "Port"))
        pechkin = (config.get("mailer", "user"))
        passMail = (config.get("mailer", "password"))
        headMail = (config.get("mailer", "fromheader"))
        log.debug("Адрес почты отправителя "+pechkin)
    except Exception as e:
        log.error("Проверьте параметры почты: %s" %e)
        raise SystemExit(1)
    check = re.findall(r'\w+@\w+.\w+', userMail) ## проверяем правильность почты и убираем пробелы
    if check:
        log.debug("Адрес почты получателя "+userMail)
    else:
        log.error("Неправильный адрес почты userMail.")
        raise SystemExit(1)

elif noify=='slack':
    try:
        slackUrl=config.get("slack", "url")
        log.info("Using Slack services")
    except:
        log.error('Bad notify URL')
        raise SystemExit(1)
else:
    log.error("use <mailer> or <slack> for noify")
    raise SystemExit(1)

def send_notify(app,body):
    if app in sendedMail:
        log.info("Отчёт по событию " + app + " уже был отправлен.")
        return

    sendedMail.append(app)  # чтобы не спамить на почту
    if noify=='mailer':
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
        data = dumps({"text": body})
        headers={"Content-type" : "application/json", 'Content-Length': len(body)}
        try:
            res = requests.post(slackUrl, data, headers, timeout = 10)
            if res.status_code!=200:
                raise Exception("Server return status %s" %res.status_code)
            log.info("Отчёт о " + app + " отправлен.")
        except Exception as e:
            log.error("Не могу отправить отчёт в Slack  %s" %e)


def process_inspector ():
    log.debug("process_inspector started")
    while True:
        for job in jobList:
            app = job[0]
            url = str(job[1])
            exe = job[2].lower()
            exeKey = job[3]
            path = job[4]
            launchApp = job[5].lower()
            if launchApp == "" or launchApp == 'none':
                launchApp = path + exe

            # launch = 0
            # можно использовать | find
            conv = Popen('taskList /svc /fi "IMAGENAME eq '+ exe +'" /nh', shell = True, stdout = PIPE, stderr = PIPE)
            stdout = str(conv.communicate())
            if stdout.split()[0].split("\\n")[-1].lower() != exe:
                pass
            else:
                log.debug("Найден процесс " + app +" Запрос статуса.")
                try:
                    res = requests.get(url, timeout = 10)
                    if res.status_code!=200:
                        raise Exception("Server return status %s" %res.status_code)
                    log.info("Процесс " + app + " работает.")
                except Exception as e:
                    log.warning("Процесс %s не отвечает или вернул не верный статус %s" % ( app, e))
                    body = 'Капитан! На корабле ' + localName + " взбунтовал матрос " + app \
                         + '!\nIP адрес сервера: ' + localIp
                    send_notify(app, body)
                    # Popen('TASKKILL /f /im ' + exe, shell = True, stdout = PIPE, stderr = PIPE)
                    # launch = 1
                    # sleep(2)
                # if launch == 0:
                #     pass
                # else:
                #     log.debug("Запуск приложения %s (%s)" % (exe, launchApp))
                #     try:
                #         Popen(launchApp + ' ' + exeKey, creationflags = CREATE_NEW_CONSOLE)
                #         log.info("Приложение " + app + " запущено.")
                #     except Exception as e:
                #         if e.errno == 8: # В случае запуска х32 в х64 среде - запускаем из самой среды ОС
                #             os.system('START cmd /c "'+launchApp+'"')
                #             log.info("Приложения " + app + " запущено.")
                #         else:
                #             log.error("Ошибка запуска приложения %s (%s): %s" % (exe, launchApp, e))
        sleep(60*30)

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
        sleep(1800)

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
            log.info("Свободно места %s. До лимита ещё: %s" % (free, round(free-diskWarn,2)))
        sleep(3600)

if diskUsage == 1:
    ht3 = Thread(target = disk_inspector, name = 'disk_inspector')
    ht3.start()

if len(jobList) != 0:
    ht1 = Thread(target = process_inspector, name = 'process_inspector')
    ht1.start()
    ht2 = Thread(target = license_inspector, name = 'license_inspector')
    ht2.start()

log.info("AppWatch started")
