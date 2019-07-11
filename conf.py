import configparser, logging
from logging.handlers import RotatingFileHandler
import re, sys, time, os


homeDir = sys.argv[0][:sys.argv[0].replace('\\', '/').rfind('/')+1]
devmod = False

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
default={
    "server" : {
        "// This Server info": "",
        "localName": "Pantsu Server",
        "localIp": "0.0.0.0",
        "Notify": "email",
        "resendTimeoutM": "30",
        "// Notification service.  email or Slack": ""
    },
    "service": {
        "name": "AppWatchSvc",
        "displayName": "AppWatch Service",
        "description": "WatchDog for Windows apps"
    },
    "slack" : {
        "url": "YOUR_WEBHOOK_URL_HERE",
    },
    "email" : {
        "userMail": "admin@pantsumail.ru",
        "server": "smtp.pantsumail.ru",
        "port": "587",
        "// Try 587 if 465 not work": "",
        "user": "username",
        "password": "11111",
        "fromHeader": "Pantsu Alarm <bot@pantsumail.ru>"
    },
    "taskList" : {
        "intervalCheckMin": "10",
        "active": "1",
        "1": "diskUsage",
        "2": "MyApp",
        "3": "MyHttpServer"
    },
    "diskUsage" : {
        "// Free space limit in GB": "",
        "path": "C:\\",
        "warning": "30",
        "critical": "10"
    },
    "myApp" : {
        "alwaysWork": "false",
        "doRestart": "true",
        "timeForRestarting": "5",
        "// false will only notify": "",
        "url": "https://myHost.ru",
        "path": "C:\Apps\MyApp",
        "exe": "myApp.exe",
        "// What must be running": "",
        "exeKey": "/247 /hidegui",
        "// Keys for starting exe": "",
        "startApp": "",
        "// If not set, will start <exe> param": ""
    },
    "myHttpServer" : {
        "alwaysWork": "true",
        "doRestart": "true",
        "timeForRestarting": "10",
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

# пример конфига

# Создаёт секции если их нет. Потом в рекурсию загнать можно
try:
    used=0
    for i in ['server', 'service', 'slack', 'email', 'taskList', 'logging']:
        try:
            if not config.has_section(i):
                print('Create new section [%s]' %i)
                used=writeSection(i,default[i])
                if i == 'taskList':
                    for y in ['diskUsage','myApp','myHttpServer']:
                        try:
                            used = writeSection(y, default[y])
                        except Exception as e:
                            print(e)
                            continue
        except Exception as e:
            print(e)
            continue


    if used==1:
        print("WARNING: Были созданы новые секции в файле конфигурации "
              "Для их действия запустите коннектор заново.")
        time.sleep(3)
        raise SystemExit(1)
except Exception as e:
    print("ERROR: Не удалось создать файл конфигурации", str(e))
    time.sleep(3)
    raise SystemExit(1)

taskList = []
jobList = []
diskUsage = 0

# Check logging
level = 20
logSize = 10240
logCount = 5
try:
    if config.getboolean("logging", "enable") == False:
        level = 0
    else:
        Loglevel = config.get("logging", "loglevel").lower()
        if Loglevel == "full":
            level = 10
        else:
            pass
            # backupCount
        logSize = config.getint("logging", "logmaxsizekbs")
        logCount = config.getint("logging", "logmaxfiles")
except Exception as e:
    print("WARNING: Проверьте параметры logging. Err:", str(e))
    raise SystemExit(1)

# create logger
logFile = homeDir+'AppWatch.log'
log_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s',
                                      datefmt = '%Y-%m-%d %H:%M:%S')
myHandler = RotatingFileHandler(logFile, maxBytes = logSize * 1024, backupCount = logCount, delay = 0)
myHandler.setFormatter(log_formatter)
log = logging.getLogger('root')
log.setLevel(level)
log.addHandler(myHandler)

cons_log = logging.getLogger('root')
cons_log.setLevel(level)
consoleHandler = logging.StreamHandler(sys.stdout)
consoleHandler.setFormatter(log_formatter)
cons_log.addHandler(consoleHandler)
log.warning(str(level))

# check general settings
try:
    localName = config.get("server", "localName")
    localIp = config.get("server", "localIp")
    noify = config.get("server", "notify").lower()
    resendTime = config.getint("server", "resendTimeoutM")
    log.info("Local server is %s (%s)" %(localIp,localName))
except Exception as e:
    log.error("%s" % e)
    raise SystemExit(1)

# check tasks
try:
    active = config.getint('taskList', "active")
    intervalCheckMin = config.getint('taskList', "intervalCheckMin") * 60
    log.info("Задано %s заданий" % active)
    if active <= 0:  # можно было бы и параметры проверить, но грамоздить ступеньки...
        log.error("Нет заданий для выполнения. Остановка приложения.")
        raise SystemExit(1)
    else:
        n = 0
        while n < active:
            try:
                task = config.get('taskList', str(n))
                if not config.has_section(task):
                    log.error("Задано несуществующее задание " + task)
                else:
                    taskList.append(task)
            except:
                log.warning("В taskList нет задания %s" % n)
                raise SystemExit(1)
            n += 1
except Exception as e:
    log.warning("Проверьте параметры снкции taskList: %s" % e)
    raise SystemExit(1)

# check tasks settings and create tasks list
for task in taskList:
    if task == 'diskUsage':
        try:
            diskWarn = config.getint('diskUsage', "Warning")
            critFree = config.getint('diskUsage', "Critical")
            pathUsage = config.get('diskUsage', "path")
            pathUsage = pathUsage.replace('\\', '/') + '/'
            log.info("Задан diskUsage. Папка: %s. Лимит: %s GB" % (pathUsage, diskWarn))
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
        jobListTmp.append(config.get(task, "path").replace('\\', '/') + '/')
        jobListTmp.append(config.get(task, "startApp").replace('\\', '/'))
        jobListTmp.append(config.getboolean(task, "doRestart"))
        jobListTmp.append(config.getboolean(task, "alwaysWork"))
        jobListTmp.append(config.getint(task, "timeForRestarting"))
        jobList.append(tuple(jobListTmp))
    except Exception as e:
        log.error("Задание " + task + " отклонено. Проверьте параметры: %s" % e)
        raise SystemExit(1)

# check email settings
if noify == 'email':
    try:
        userMail = config.get("email", "userMail")
        serverMail = config.get("email", "server")
        portMail = config.getint("email", "Port")
        pechkin = config.get("email", "user")
        passMail = config.get("email", "password")
        headMail = config.get("email", "fromheader")
        log.debug("Адрес почты отправителя " + pechkin)
    except Exception as e:
        log.error("Проверьте параметры почты: %s" % e)
        raise SystemExit(1)
    # проверяем правильность почты и убираем пробелы

    if re.findall(r'\w+@\w+.\w+', userMail):
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
    log.error("use <email> or <slack> for Notify parameter")
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

del i, level, task, logFile, logSize, logCount, default
