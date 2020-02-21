import configparser, logging
from logging.handlers import RotatingFileHandler
import re, sys, time, os


homeDir = sys.argv[0][:sys.argv[0].replace('\\', '/').rfind('/')+1]
devmod = False

# пример конфига
default={
    "server" : {
        "// This Server info": "",
        "localName": "Pantsu Server",
        "localIp": "0.0.0.0",
        "Notify": "email",
        "// email or slack": "",
        "resendTimeoutM": "30",
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
        "active": "3",
        "// will do all": "",
        "1": "diskUsage",
        "2": "myApp",
        "3": "myHttpServer"
    },
    "diskUsage" : {
        "// Free space limit in GB": "",
        "disk": "C:\\",
        "warning": "30",
        "critical": "10"
    },
    "myApp" : {
        "alwaysWork": "false",
        "// not check if proccess not running": "",
        "doRestart": "true",
        "// if run and bad check": "if false will only notify",
        "timeForRestartingSec": "20",
        "url": "https://myHost.ru",
        "// must return status 200": "",
        "exe": "myApp.exe",
        "// What watching for": "",
        "whatStart": "exe",
        "// exe|script|service": "",
        "path": "C:\Apps\MyApp",
        "exeKey": "/247 /hidegui",
        "// Keys for starting exe": "",
        "script": "c:\\app\\start.bat",
        "// if whatStart=script": "",
        "service": "appDeamon",
        "// windows service name": ""
    },
    "myHttpServer" : {
        "alwaysWork": "true",
        "// start process if not running": "",
        "doRestart": "true",
        "timeForRestartingSec": "30",
        "url": "http://127.0.1.1:7252/uptime",
        "exe": "MyServer.exe",
        "whatStart": "service",
        "path": "",
        "exeKey": "",
        "script": "",
        "service": "HttpServer-srv"
    },
    "logging" : {
        "Enable" : "True",
        "Loglevel" : "Normal",
        "// Normal or Full" : "",
        "LogMaxSizeKbs" : "10240",
        "logMaxFiles" : "5"
    }
}

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

# Создаёт секции если их нет. 
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
diskTask = False

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
log_formatter = logging.Formatter(
                                        '%(asctime)s %(levelname)s: %(message)s',
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
                task = config.get('taskList', str(n+1))
                if not config.has_section(task):
                    log.error("Задано несуществующее задание " + task)
                else:
                    taskList.append(task)
            except:
                log.warning(f"В taskList нет задания %{n+1}")
                raise SystemExit(1)
            n += 1
except Exception as e:
    log.warning(f"Проверьте параметры снкции taskList: {e}")
    raise SystemExit(1)

# check tasks settings and create tasks list
for task in taskList:
    if task == 'diskUsage':
        try:
            diskWarn = config.getint('diskUsage', "Warning")
            critFree = config.getint('diskUsage', "Critical")
            diskUsage = config.get('diskUsage', "disk")
            diskUsage = diskUsage.replace('\\', '/') + '/'
            log.info(f"Задан diskUsage. Папка: {diskUsage}. Лимит: {diskWarn} GB")
            diskTask = True
        except Exception as e:
            log.error(f"Проверьте параметры: {e}")
        continue

    jobListTmp = {}
    try:
        jobListTmp['task'] = task
        jobListTmp['url'] = config.get(task, "url")
        jobListTmp['exe'] = config.get(task, "Exe")
        jobListTmp['path'] = config.get(task, "path").replace('\\', '/') + '/'
        jobListTmp['doRestart'] = config.getboolean(task, "doRestart")
        jobListTmp['alwaysWork'] = config.getboolean(task, "alwaysWork")
        jobListTmp['restartTime'] = config.getint(task, "timeForRestartingSec")
        jobListTmp['whatStart'] = whatStart = config.get(task, "whatStart")

        if whatStart == 'exe':
            jobListTmp['exeKey'] = config.get(task, "exeKey")
        elif whatStart == 'script':
            jobListTmp['script'] = config.get(task, "script").replace('\\', '/')
        elif whatStart == 'service':
            jobListTmp['service'] = config.get(task, "service")
        else:
            log.error('Wrong parameter whatStart. Allowed: exe, script, service')

        jobList.append(jobListTmp)
    except Exception as e:
        log.error(f"Задание {task} отклонено. Проверьте параметры: {e}")
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
        log.error(f"Проверьте параметры почты: {e}")
        raise SystemExit(1)
    # проверяем правильность почты и убираем пробелы

    if re.findall(r'\w+@\w+.\w+', userMail):
        log.debug(f"Адрес почты получателя {userMail}")
    else:
        log.error("Неправильный адрес почты userMail.")
        raise SystemExit(1)

elif noify == 'slack':
    try:
        slackUrl = config.get("slack", "url")
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
        return [
            config.get("service", "name"),
            config.get("service", "displayName"),
            config.get("service", "description")]
    except Exception as e:
        log.error("Неправильно заданы параметры [service]: " + str(e))
        time.sleep(3)
        raise SystemExit(1)

del i, level, logFile, logSize, logCount, default
