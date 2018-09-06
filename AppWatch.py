import os.path
from sys import stdout
from time import sleep
import datetime
from threading import Thread
from subprocess import Popen, PIPE, CREATE_NEW_CONSOLE
from logging.handlers import RotatingFileHandler
import logging
import configparser
import urllib.request
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re
import shutil


TaskList=[]
JobList=[]
SendedMail=[]
DiskUsage=0

def ConfigWrite():
    with open("AppWatch.cfg", "w") as ConfigFile:
        Config.write(ConfigFile)

# Загружаем конфиг
try:
    Config = open('AppWatch.cfg', encoding='utf-8')
except IOError:
    with open("AppWatch.cfg", 'tw', encoding='utf-8') as ConfigFile: # Создаём конфиг если его нет
        Config = configparser.RawConfigParser()
        Config.add_section("Server")
        Config.set("Server", "# Сведения о машине",'')
        Config.set("Server","LocalName","Pantsu Server")
        Config.set("Server","LocalIP","0.0.0.0")
        Config.add_section("Mailer")
        Config.set("Mailer", "# Параметры почты",'')
        Config.set("Mailer","UserMail","user@pantsumail.ru")
        Config.set("Mailer", "Server", "smtp.pantsumail.ru")
        Config.set("Mailer","Port","587")
        Config.set("Mailer", "#465 порт может не работать")
        Config.set("Mailer", "user",'username')
        Config.set("Mailer","password","0000")
        Config.set("Mailer", "FromHeader", "Pantsu Alarm <user@pantsumail.ru>")
        Config.add_section("TaskList")
        Config.set("TaskList", "Active", "0")
        Config.set("TaskList", "1", "DiskUsage")
        Config.set("TaskList", "2", "Videologger")
        Config.set("TaskList", "3", "MyHttpServer")
        Config.add_section("DiskUsage")
        Config.set("DiskUsage", "Path", "C:\\")
        Config.set("DiskUsage", "Warning", "30")
        Config.set("DiskUsage", "Critical", "10")
        Config.set("DiskUsage", "# Лимит свободного места в ГБ", "")
        Config.add_section("Videologger")
        Config.set("Videologger", "Port", "15081")
        Config.set("Videologger", "Path", "C:\Autonomy\Videologger")
        Config.set("Videologger", "Exe", "Videologger.exe")
        Config.set("Videologger", "# Параметры с котороми запускать Exe", "")
        Config.set("Videologger", "ExeKey", "/247 /hidegui")
        Config.set("Videologger", "# Если задано, то запустит его вместо Exe", "")
        Config.set("Videologger", "StartApp", "")
        Config.add_section("MyHttpServer")
        Config.set("MyHttpServer", "Port", "7252")
        Config.set("MyHttpServer", "Path", "C:\path")
        Config.set("MyHttpServer", "Exe", "MyServer.exe")
        Config.set("MyHttpServer", "ExeKey", "")
        Config.set("MyHttpServer", "StartApp", "C:\path\StartMyServer.bat")
        Config.add_section("Logging")
        Config.set("Logging", "Enable", "True")
        Config.set("Logging", "LogLevel", "Normal")
        Config.set("Logging", "# Full или Normal", '')
        Config.set("Logging", "LogMaxSizeKbs", "10240")
        Config.set("Logging", "logmaxfiles", "5")
        ConfigWrite()
finally:
    Config = configparser.RawConfigParser()
    Config.read("AppWatch.cfg")

# Проверяем журналирование
Level = logging.INFO
LogSize=10240
LogCount=5
try:
    Logging=str(Config.get("Logging","enable")).lower()
    if Logging=="false":
        Level=0
    elif Logging == "true":
        LogLevel=str(Config.get("Logging","loglevel")).lower()
        if LogLevel=="full":
            Level=logging.DEBUG
        else:
            pass
            # backupCount
        LogSize = Config.getint("Logging", "logmaxsizekbs")
        LogCount=Config.getint("Logging", "logmaxfiles")
    else:
        pass
except Exception as e:
    print("WARNING: Проверьте параметры Logging. Err:",str(e))

# Создаём журнал
logFile = 'AppWatch.log'
log_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s',
                                      datefmt='%Y-%m-%d %H:%M:%S')
my_handler = RotatingFileHandler(logFile, maxBytes=LogSize * 1024,
                                 backupCount=LogCount, delay=0)
my_handler.setFormatter(log_formatter)
app_log = logging.getLogger('root')
app_log.setLevel(int(Level))
app_log.addHandler(my_handler)

cons_log = logging.getLogger('root')
cons_log.setLevel(int(Level))
consoleHandler = logging.StreamHandler(stdout)
consoleHandler.setFormatter(log_formatter)
cons_log.addHandler(consoleHandler)

app_log.info("Application Management запущен")

# Время события
def LogTime():
    return str(datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S "))

# Проверяем задания
try:
    active = Config.getint('TaskList', "active")
    # print(LogTime()+"DEBUG: Задано "+str(active)+" заданий")
    app_log.info("Задано "+str(active)+" заданий")
except Exception:
    app_log.warning("Проверьте параметры TaskList")

if active<=0: #можно было бы и параметры проверить, но грамоздить ступеньки...
    app_log.info("Нет заданий для выполнения. Остановка приложения.")
    sleep(3)
    os._exit(1)
else:
    n=1
    while n<=active:
        try:
            Task=Config.get('TaskList', str(n))
            if not Config.has_section(Task):
                app_log.error("Задано несуществующее задание " + Task)
            else:
                TaskList.append(Task)
        except Exception:
            app_log.warning("В TaskList нет задания "+str(n))
        n=n+1

if 'DiskUsage' in TaskList:
    try:
        DiskWarn=int(Config.get('DiskUsage', "Warning"))
        CritFree=int(Config.get('DiskUsage', "Critical"))
        PathUsage=Config.get('DiskUsage', "path")
        PathUsage=PathUsage.replace('\\','/')+'/'
        app_log.info("Задан DiskUsage. Папка: " + str(PathUsage)+" Лимит: "+str(DiskWarn))
        DiskUsage=1
    except Exception as e:
        app_log.error("Задание "+Task+" отклонено. Проверьте параметры. Err: "+str(e))
    finally:
        TaskList.remove('DiskUsage')

#Проверка параметров и составлене списка заданий
for Task in TaskList:
    JobListTmp=[]
    try:
        JobListTmp.append(Task)
        JobListTmp.append(Config.getint(Task, "port"))
        JobListTmp.append(Config.get(Task, "Exe"))
        JobListTmp.append(Config.get(Task, "ExeKey"))
        Path=Config.get(Task, "path")
        Path=Path.replace('\\','/')+'/'
        JobListTmp.append(Path)
        StartApp=Config.get(Task, "StartApp")
        StartApp=StartApp.replace('\\','/')
        JobListTmp.append(StartApp)
        JobList.append(tuple(JobListTmp))
    except Exception as e:
        app_log.error("Задание "+Task+" отклонено. Проверьте параметры. Err: "+str(e))

# Проверка параметров почты
try:
    UserMail=(Config.get("Mailer", "UserMail"))
    ServerMail = (Config.get("Mailer", "Server"))
    PortMail = (Config.getint("Mailer", "Port"))
    Pechkin = (Config.get("Mailer", "user"))
    PassMail = (Config.get("Mailer", "password"))
    HeadMail = (Config.get("Mailer", "fromheader"))
    app_log.info("Адрес почты отправителя "+Pechkin)
except Exception as e:
    app_log.error("Проверьте параметры почты. Err: "+str(e))
check = re.findall(r'\w+@\w+.\w+', UserMail) ## проверяем правильность почты и убираем пробелы
if check:
    app_log.info("Адрес почты получателя "+UserMail)
else:
    app_log.error("Неправильный адрес почты UserMail.")

try:
    LocalName = (Config.get("Server", "LocalName"))
    app_log.info("Имя локальной машины: "+LocalName)
    LocalIP = (Config.get("Server", "LocalIP"))
    app_log.info("IP адрес локальной машины: "+LocalIP)
except Exception as e:
    app_log.error("Не указаны имя или IP адрес машины")

## Отправка почты
def Mailer (App,Body):
    if App in SendedMail:
        app_log.info("Отчёт по событию " + App + " уже был отправлен.")
        pass
    else:
        SendedMail.append(App)  # чтобы не спамить на почту

        app_log.debug("Создание отчёта по событию "+App)
        # Формируем заголовок письма
        msg = MIMEMultipart('mixed')
        msg['Subject'] = ('Inspecor Pantsu: Бунт на машинке '+LocalName)
        msg['From'] = HeadMail
        msg['To'] = UserMail

        # Формируем письмо

        msg.attach(Body)
        app_log.debug("Соединение с почтовым сервером "+ServerMail)
        try:
            s = smtplib.SMTP(ServerMail, PortMail)
            s.ehlo()    ## Рукопожатие, обязательно
            s.starttls()
            s.ehlo()
            s.login(Pechkin, PassMail)
            s.sendmail(HeadMail, UserMail, msg.as_string())
            app_log.info("Письмо с отчётом "+App+" отправлено.")
        except Exception as e:
            if e.errno==11004:
                app_log.error("Не могу соединиться с почтовым сервером.")
            else:
                app_log.error("Ошибка при отправлении письма. Err: "+str(e))
        sleep(1)

# Process Inspector
def Process_Inspector ():
    app_log.debug("Process_Inspector запущен")
    while True:
        for Job in JobList:
            App = Job[0]
            Port = str(Job[1])
            Exe = Job[2].lower()
            ExeKey=Job[3]
            Path = Job[4]
            LaunchApp=Job[5].lower()
            if LaunchApp == "" or LaunchApp=='none':
                LaunchApp = Path + Exe
            else:
                pass
            Launch = 0
            conv = Popen('TASKLIST /svc /fi "IMAGENAME eq '+Exe+'" /nh', # можно использовать | find
                                    shell=True, stdout=PIPE, stderr=PIPE)
            Stdout = str(conv.communicate())  ##Забираем вывод
            Result = Stdout.split()[0].split("\\n")[-1]
            if Result!=Exe:
                pass
            else:
                app_log.debug("Найден процесс " + App+" Запрос статуса.")
                try:
                    urllib.request.urlopen('http://127.0.0.1:'+Port + '/a=getstatus', timeout=10)
                    app_log.info("Процесс "+App+" работает.")
                except:
                    app_log.warning("Процесс "+App+" не отвечает. Завершение процесса.")
                    Popen('TASKKILL /f /im ' + Exe, shell=True, stdout=PIPE, stderr=PIPE)
                    Launch=1
                    sleep(2)
                if Launch==0:
                    pass
                else:
                    app_log.debug("Запуск приложения "+App+" ("+LaunchApp+")")
                    try:
                        Popen(LaunchApp+' '+ExeKey, creationflags=CREATE_NEW_CONSOLE)
                        app_log.info("Приложение "+App+" запущено.")
                    except Exception as e:
                        if e.errno==8: # В случае запуска х32 в х64 среде - запускаем из самой среды ОС
                            os.system('START cmd /c "'+LaunchApp+'"')
                            app_log.info("Приложения " + App + " запущено.")
                        else:
                            app_log.error("Ошибка запуска приложения "+Exe+" ("+LaunchApp+")"+str(e))
        sleep(60)

# License Inspector
def License_Inspector():
    app_log.debug("License_Inspector запущен")
    while True:
        app_log.info("Проверка лицензий")
        for Job in JobList:
            App = Job[0]
            Path = Job[4]
            app_log.debug("Проверка лицензии " + App)
            try:
                LicLog=open(Path+'license.log', encoding='utf-8')
                text=LicLog.read()
                LicLog.close()
                if 'LICENSE: Error' in text or 'No license found' in text:
                    app_log.error("Ошибка лицензии " + App)
                    UidDat = open(Path + 'uid/uid.dat', encoding='utf-8')
                    Uid = UidDat.read()
                    UidDat.close()
                    Body = MIMEText(
                         'Капитан! На сервере ' + LocalName + " произошёл бунт против лицензии, возглавляемый пиратом " + App
                         + '!\nIP адрес сервера: ' + LocalIP
                         + '\nUID лицензии: ' + Uid)
                    Mailer(App,Body,)
                    break
                else:
                    pass
                app_log.debug("Корректная лицензия " + App)
            except Exception as e:
                if e.errno==2:
                    app_log.warning("Не найден журнал лицензии " + App)
                else:
                    app_log.error("Ошибка чтения журнала лицензии " + App+". Err: "+str(e))
        sleep(1800)

# Проверка свободного места
def Disk_Inspector():
    app_log.debug("Disk_Inspector запущен")
    while True:
        Free = round(shutil.disk_usage(PathUsage).free / 1073741824, 2)
        if Free < CritFree:
            app_log.error("Критически мало места! Осталось всего: " + str(Free))
            App='CritFree'
            Body = MIMEText(
                'Капитан! На корабле ' + LocalName + " закончилась провизия"
                + '!\nIP адрес сервера: ' + LocalIP
                + '\nСвободно места : ' + str(Free))
            Mailer(App, Body,)
        elif Free < DiskWarn:
            app_log.warning("Заканчивается место. Свободно лишь: "+str(Free))
            App = 'DiskWarn'
            Body = MIMEText(
                'Капитан! На корабле ' + LocalName + " заканчивается провизия"
                + '!\nIP адрес сервера: ' + LocalIP
                + '\nСвободно лишь : ' + str(Free))
            Mailer(App, Body, )
        elif Free > DiskWarn:
            app_log.info("Свободно места "+str(Free)+". До лимита ещё: "+str(round(Free-DiskWarn,2)))
        sleep(3600)

if DiskUsage==1:
    ht3=Thread(target=Disk_Inspector, name='Disk_Inspector')
    ht3.start()

if len(JobList)!=0:
    ht1 = Thread(target=Process_Inspector, name='Process_Inspector')
    ht1.start()
    ht2 = Thread(target=License_Inspector, name='License_Inspector')
    ht2.start()
