import configparser, logging
from logging.handlers import RotatingFileHandler
import re, sys, time, os


homeDir = sys.argv[0][:sys.argv[0].replace('\\', '/').rfind('/')+1]

# Загружает конфиг
try:
    config = open(homeDir+'AppWatch.cfg', encoding='utf-8')
except IOError:
    open(homeDir+'AppWatch.cfg', 'tw', encoding='utf-8')

config = configparser.RawConfigParser(comment_prefixes=('#', ';', '//'), allow_no_value=True)
try:
    config.read(homeDir+'AppWatch.cfg')
except Exception as e:
    print("Error to read configuration file:", str(e))
    time.sleep(3)
    raise SystemExit(1)

def writeSection(section, params):
    def lowcaseMe(val):
        return val.lower()

    def configWrite():
        with open(homeDir + 'AppWatch.cfg', "w") as configFile:
            config.write(configFile)

    config.optionxform = str  # позволяет записать параметр сохранив регистр
    config.add_section(section)
    for val in params:
        config.set(section, val, params[val])
    config.optionxform = lowcaseMe  # возращаем предопределённый метод назад
    configWrite()
    return 1

# пример конфига
default={
    "server" : {
        "// This Server info": "",
        "localName": "Pantsu Server",
        "localIp": "0.0.0.0",
        "Notify": "mailer",
        "// Notification service.  mailer or Slack": ""
    },
    "service": {
        "name": "AppWatchSvc",
        "displayName": "AppWatch Service",
        "description": "WatchDog for Windows apps"
    },
    "slack" : {
        "url": "YOUR_WEBHOOK_URL_HERE",
    },
    "mailer" : {
        "userMail": "admin@pantsumail.ru",
        "server": "localhost",
        "port": "587",
        "// Try 587 if 465 not work": "",
        "user": "username",
        "password": "11111",
        "fromHeader": "Pantsu Alarm <bot@pantsumail.ru>"
    },
    "taskList" : {
        "intervalMin": "10",
        "active": "1",
        "1": "diskUsage",
        "2": "MyApp;",
        "3": "MyHttpServer"
    },
    "diskUsage" : {
        "// Free space limit in GB": "",
        "path": "C:\\",
        "warning": "30",
        "critical": "10"
    },
    "myApp" : {
        "url": "https://myHost.ru",
        "path": "C:\Apps\MyApp",
        "exe": "myApp.exe",
        "exeKey": "/247 /hidegui",
        "// Keys for starting exe": "",
        "startApp": "",
        "// If not set, will start <exe> param": ""
    },
    "myHttpServer" : {
        "url": "http://127.0.1.1:7252",
        "path": "C:\path",
        "exe": "MyServer.exe",
        "exeKey": "",
        "startApp": "C:\path\StartMyServer.bat"
    },
    "logging" : {
        "Enable" : "True",
        "Loglevel" : "Normal",
        "// Normal or Full" : "",
        "LogMaxSizeKbs" : "10240",
        "logMaxFiles" : "5"
    }
}

# Создаёт секции если их нет
try:
    used=0
    for i in ['server', 'service', 'slack', 'mailer', 'taskList', 'logging']:
        if not config.has_section(i):
            used=writeSection(i,default[i])
            if i == 'taskList':
                used = writeSection('diskUsage', default['diskUsage'])
                used = writeSection('myApp', default['myApp'])
                used = writeSection('myHttpServer', default['myHttpServer'])

    if used==1:
        print("WARNING: Были созданы новые секции в файле конфигурации. "
              "Для их действия запустите коннектор заново.")
        time.sleep(3)
        raise SystemExit(1)
except Exception as e:
    print("ERROR: Не удалось создать файл конфигурации", str(e))
    time.sleep(3)
    raise SystemExit(1)

taskList = jobList = sendedMail = []
diskUsage = 0

# Check logging
level = logging.INFO
logSize = 10240
logCount = 5
try:
    if config.getboolean("logging", "enable") == False:
        level = 0
    else:
        Loglevel = str(config.get("logging", "loglevel")).lower()
        if Loglevel == "full":
            level = logging.DEBUG
        else:
            pass
            # backupCount
        logSize = config.getint("logging", "logmaxsizekbs")
        logCount = config.getint("logging", "logmaxfiles")
except Exception as e:
    print("WARNING: Проверьте параметры logging. Err:", str(e))
    raise SystemExit(1)


# create logger
logFile = 'AppWatch.log'
log_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s',
                                      datefmt = '%Y-%m-%d %H:%M:%S')
myHandler = RotatingFileHandler(logFile, maxBytes = logSize * 1024, backupCount = logCount, delay = 0)
myHandler.setFormatter(log_formatter)
log = logging.getLogger('root')
log.setLevel(int(level))
log.addHandler(myHandler)

cons_log = logging.getLogger('root')
cons_log.setLevel(int(level))
consoleHandler = logging.StreamHandler(sys.stdout)
consoleHandler.setFormatter(log_formatter)
cons_log.addHandler(consoleHandler)

# check general settings
try:
    localName = (config.get("server", "localName"))
    localIp = (config.get("server", "localIp"))
    noify = (config.get("server", "notify"))
    log.info("Local server is %s (%s)" %(localIp,localName))
except Exception as e:
    log.error("%s" % e)
    raise SystemExit(1)

# check tasks
try:
    active = config.getint('taskList', "active")
    intervalMin = config.getint('taskList', "intervalmin") * 60
    log.info("Задано %s заданий" % active)
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
    log.warning("Проверьте параметры снкции taskList: %s" % e)
    raise SystemExit(1)

# check tasks settings and create tasks list
for task in taskList:
    if task == 'diskUsage':
        try:
            diskWarn = int(config.get('diskUsage', "Warning"))
            critFree = int(config.get('diskUsage', "Critical"))
            pathUsage = config.get('diskUsage', "path")
            pathUsage = pathUsage.replace('\\', '/') + '/'
            log.info("Задан diskUsage. Папка: %s. Лимит: %s GB" % (pathUsage, diskWarn))
            diskUsage = 1
            taskList.remove('diskUsage')
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
        path = path.replace('\\', '/') + '/'
        jobListTmp.append(path)
        startApp = config.get(task, "startApp")
        startApp = startApp.replace('\\', '/')
        jobListTmp.append(startApp)
        jobList.append(tuple(jobListTmp))
    except Exception as e:
        log.error("Задание " + task + " отклонено. Проверьте параметры: %s" % e)
        raise SystemExit(1)

# check mailer settings
if noify == 'mailer':
    try:
        userMail = (config.get("mailer", "userMail"))
        serverMail = (config.get("mailer", "server"))
        portMail = (config.getint("mailer", "Port"))
        pechkin = (config.get("mailer", "user"))
        passMail = (config.get("mailer", "password"))
        headMail = (config.get("mailer", "fromheader"))
        log.debug("Адрес почты отправителя " + pechkin)
    except Exception as e:
        log.error("Проверьте параметры почты: %s" % e)
        raise SystemExit(1)
    check = re.findall(r'\w+@\w+.\w+', userMail) # проверяем правильность почты и убираем пробелы
    if check:
        log.debug("Адрес почты получателя " + userMail)
    else:
        log.error("Неправильный адрес почты userMail.")
        raise SystemExit(1)

elif noify == 'slack':
    try:
        slackUrl=config.get("slack", "url")
        log.info("Using Slack services")
    except:
        log.error('Bad notify URL')
        raise SystemExit(1)
else:
    log.error("use <mailer> or <slack> for noify")
    raise SystemExit(1)


# сбор параметров для службы windows
def get_svc_params():
    try:
        return [config.get("service", "name"),
                config.get("service", "displayName"),
                config.get("service", "description")
                ]
    except Exception as e:
        log.error("Неправильно заданы параметры [service]: " + str(e))
        time.sleep(3)
        raise SystemExit(1)

del i, level, task, check, logFile, logSize, logCount, default