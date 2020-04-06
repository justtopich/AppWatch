import configparser, logging
from logging.handlers import RotatingFileHandler
import sys, time
import traceback

homeDir = sys.argv[0][:sys.argv[0].replace('\\', '/').rfind('/')+1]
cfg = {
    "notify": {
        "tmpl": {}
    },
    "tasks": {"jobList": {}}
}
default = {
    "notify" : {
        "type": "email",
        "// email or slack": "",
        "resendTimeoutM": "30",
        "// This Server info": "",
        "localName": "Pantsu Server",
        "localIp": "0.0.0.0",
    },
    "service": {
        "name": "AppWatchSvc",
        "displayName": "AppWatch Service",
        "description": "WatchDog for Windows apps"
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

# Загружает конфиг
def open_config() -> configparser.RawConfigParser:
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

    return config

def writeSection(section:str, params:dict) -> bool:
    def lowcaseMe(val:str) -> str:
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
    return True

# Создаёт секции если их нет.
def check_sections(config: configparser.RawConfigParser):
    try:
        edited = False
        for i in ['service', "notify", 'taskList', 'logging']:
            try:
                if not config.has_section(i):
                    print('Create new section [%s]' %i)
                    edited = writeSection(i,default[i])
                    if i == 'taskList':
                        for y in ['diskUsage','myApp','myHttpServer']:
                            try:
                                edited = writeSection(y, default[y])
                            except Exception as e:
                                print(e)
                                continue
            except Exception as e:
                print(e)
                continue

        if edited:
            print("WARNING: Были созданы новые секции в файле конфигурации "
                  "Для их действия запустите коннектор заново.")
            time.sleep(3)
            raise SystemExit(1)
    except Exception as e:
        print("ERROR: Не удалось создать файл конфигурации", str(e))
        time.sleep(3)
        raise SystemExit(1)

def create_logger(config: configparser.RawConfigParser) -> logging.Logger:
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

    return log

# check general settings
def validate(config: configparser.RawConfigParser, log: logging.Logger) -> dict:
    try:
        cfg["notify"]["localName"] = config.get("notify", "localName")
        cfg["notify"]["localIp"] = config.get("notify", "localIp")
        log.info("Local server is %s (%s)" % (cfg["notify"]["localIp"], cfg["notify"]["localName"]))
    except Exception as e:
        log.error("%s" % e)
        raise SystemExit(1)

    try:
        cfg["notify"]["resendTime"] = config.getint("notify", "resendTimeoutM")
        cfg["notify"]["type"] = config.get("notify", "type").lower()
        if cfg["notify"]["type"].strip() == '':
            raise Exception(f'Wrong Notify type: {cfg["notify"]["type"]}')
    except Exception as e:
        log.error("%s" % e)
        raise SystemExit(1)

    # check tasks
    taskList = []
    try:
        active = config.getint('taskList', "active")
        cfg["tasks"]["intervalCheckMin"] = config.getint('taskList', "intervalCheckMin") * 60
        log.info("Задано %s заданий" % active)
        if active <= 0:  # можно было бы и параметры проверить, но грамоздить ступеньки...
            log.error("Нет заданий для выполнения. Остановка приложения.")
            raise SystemExit(1)
        else:
            for n in range(active):
                try:
                    task = config.get('taskList', str(n+1))
                    if not config.has_section(task):
                        log.error("Задано несуществующее задание " + task)
                    else:
                        taskList.append(task)
                except:
                    log.warning(f"В taskList нет задания %{n+1}")
                    raise SystemExit(1)
    except Exception as e:
        log.warning(f"Проверьте параметры снкции taskList: {e}")
        raise SystemExit(1)

    # check tasks settings and create tasks list
    for task in taskList:
        if task == 'diskUsage':
            cfg["tasks"]["diskTask"] = {}
            try:
                cfg["tasks"]["diskTask"]["diskWarn"] = config.getint('diskUsage', "Warning")
                cfg["tasks"]["diskTask"]["critFree"] = config.getint('diskUsage', "Critical")
                cfg["tasks"]["diskTask"]["diskUsage"] = config.get('diskUsage', "disk").replace('\\', '/') + '/'
                log.info(f'Задан diskUsage. Папка: {cfg["tasks"]["diskTask"]["diskUsage"]}.'
                         f' Лимит: {cfg["tasks"]["diskTask"]["diskWarn"]} GB')

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

            cfg["tasks"]["jobList"][task] = jobListTmp
        except Exception as e:
            log.error(f"Задание {task} отклонено. Проверьте параметры: {e}")
            raise SystemExit(1)

    return cfg

class Templater:
    def __init__(self, log: logging.Logger):
        self.legendTmpl = {
            'main': {
                "localName": cfg['notify']['localName'],
                "localIp": cfg['notify']['localIp']
            }
        }
        self.tmpl = {}
        self.__load_templates(log)

    def __load_templates(self, log: logging.Logger):
        log.info(f"Load templates.cfg")
        try:
            _ = open(f"{homeDir}templates.cfg", encoding='utf-8')
        except IOError:
            open(f"{homeDir}templates.cfg", 'tw', encoding='utf-8')

        config2 = configparser.RawConfigParser(comment_prefixes=('#', ';', '//'), allow_no_value=True)
        try:
            config2.read(f"{homeDir}templates.cfg", encoding="utf-8")
            for s in config2.sections():
                if s not in self.tmpl:
                    self.tmpl[s] = {}
                for p, v in config2.items(s):
                    self.tmpl[s][p] = v
        except Exception as e:
            print("Error to read configuration file:", str(traceback.format_exc()))
            time.sleep(3)
            raise SystemExit(1)

    def extend_legend(self, appName: str, tmpl: dict):
        self.legendTmpl[appName] = tmpl.copy()

    def tmpl_fill(self, appName: str, event: str) -> str:
        body = self.tmpl[appName][event.lower()]
        for e in self.legendTmpl.values():
            for k, v in e.items():
                body = body.replace("{{%s}}" % k, str(v))
        return body

class Notify:
    def __init__(self, name: str):
        self.name = name
        self.cfg = cfg
        self.defaultCfg = {}

    def load_config(self, config: configparser) -> dict:
        return {}

    def send_notify(self, app:str, event:str, body:str) -> bool:
        return True

def load_notifier(cfg: dict, log: logging.Logger) -> Notify:
    try:
        name = cfg["notify"]["type"]
        if name != '':
            log.info(f'Load notifier {name}')
            import notifier.email
            import notifier.discord
            import notifier.slack
            notifier = getattr(__import__(f'notifier.{name}'), name)
            notify = notifier.Notify(name)

            # на случай упаковки в бинарник, но тогда нужно всю стандартную либу включать
            # dict_obj = {}
            # with open(f'notifier/{name}.py', encoding='utf-8') as src:
            #     scrCode = src.read()
            #
            # exec(scrCode, globals(), dict_obj)
            # notify = dict_obj['Notify'](name)

            try:
                if not config.has_section(name):
                    log.warning(f'Create new section {name}')
                    if writeSection(name, notify.defaultCfg):
                        print("WARNING: Были созданы новые секции в файле конфигурации "
                              "Для их действия запустите коннектор заново.")
                        time. sleep(3)
                        raise SystemExit(1)
            except Exception as e:
                log.error(f"Fail to load notify configuration: {e}")

            cfg["notify"][name] = notify.load_config(config)

        return notify
    except ImportError as e:
        log.error(f'Fail import notifier: {name}: {traceback.format_exc()}')
        raise SystemExit(1)
    except AttributeError as e:
        log.error(f'Wrong notifier: {e}')
        raise SystemExit(1)
    except Exception as e:
        log.error(f'Fail load notifier: {e}')
        raise SystemExit(1)

config = open_config()
check_sections(config)
log = create_logger(config)
cfg = validate(config, log)
templater = Templater(log)
notify = load_notifier(cfg, log)
