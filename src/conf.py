from __init__ import (
    sout,
    re,
    sys, os,
    sleep,
    PLATFORM,
    traceback,
    configparser,
    logging,
    RotatingFileHandler,
    homeDir)
    
from types import FunctionType


cfgFileName = "AppWatch.cfg"
default = {
    "notify": {
        "type": "email",
        "; email or slack": "",
        "resendTimeoutM": "30",
        "; This Server info": "",
        "onlyChanges": "false",
        "; send only if task status is changed": "",
        "localName": "Pantsu Server",
        "localIp": "0.0.0.0",
        "useProxy": "false"
    },
    "proxy": {
        "https": 'host:port',
        "http": 'host:port'
    },
    "service": {
        "name": "AppWatchSvc",
        "displayName": "AppWatch Service",
        "description": "WatchDog for Windows/Linux apps"
    },
    "tasklist": {
        "intervalCheckMin": "10",
        "active": "4",
        "; will do all": "",
        "1": "disk_c",
        "2": "app_log",
        "3": "my_app",
        "4": "my_http_server"
    },
    "disk_c": {
        "; Free space limit in GB": "",
        "disk": "C:\\",
        "warning": "30",
        "critical": "10"
    },
    "app_log": {
        "file": "c:\\app\\events.log",
        "templates": "event1; event2",
        "; list of events what appWatch must looking in file": "",
    },
    "my_app": {
        "alwaysWork": "false",
        "; not check if process not running": "",
        "doRestart": "true",
        "; if false - will only notify": "",
        "timeForRestartingSec": "20",
        "; time for waiting to check again": "",
        "checkUrl" : "False",
        "exe": "my_app.exe",
        "; What watching for": "",
        "whatStart": "exe",
        "; exe|command|service": "",
        "exePath": "c:\\apps\\my_app",
        "exeKey": "/247 /hidegui",
        "; Keys for starting exe": "",
        "command": "c:\\app\\start.bat -fast",
        "; if whatStart=command": "",
        "service": "appDeamon",
        "; if whatStart=service": "",
        "workDir": "D:\\my_app\\tmp",
        "; used to identify process if workDir != exePAth": "",
    },
    "my_http_server": {
        "alwaysWork": "true",
        "; start process if not running": "",
        "doRestart": "true",
        "timeForRestartingSec": "30",
        "checkUrl" : "True",
        "url": "http://127.0.1.1:7252/uptime",
        "; must return status 200": "",
        "timeForResponse": "30",
        "; not required. Default is 10": "",
        "exe": "MyServer.exe",
        "exePath": "c:\\apps\\Mmy_http_server",
        "whatStart": "service",
        "service": "HttpServer-srv"
    },
    "logging": {
        "Enable": "True",
        "Loglevel": "Normal",
        "; Normal or Full": "",
        "LogMaxSizeKbs": "10240",
        "logMaxFiles": "5"
    }
}
cfg = {
    "notify": {
        'proxy': None,
        "tmpl": {}
    },
    "tasks": {"jobList": {}, "diskTask": {}, "logTask": {}}
}


class FakeMatch:
    def __init__(self, match):
        self.match = match

    def group(self, name):
        return self.match.group(name).lower()


class FakeRe:
    def __init__(self, regex):
        self.regex = regex

    def match(self, text):
        m = self.regex.match(text)
        if m:
            return FakeMatch(m)


def lowcase_sections(parser: configparser.RawConfigParser) -> configparser.RawConfigParser:
    parser.SECTCRE = FakeRe(re.compile(r"\[ *(?P<header>[^]]+?) *]"))
    return parser


def create_dirs(paths: iter) -> None:
    for i in paths:
        if not os.path.exists(i):
            try:
                os.makedirs(i)
            except Exception as e:
                raise Exception(f'Fail to create dir {i}: {e}')


def get_svc_params() -> list:
    try:
        return [
            config.get("service", "Name"),
            config.get("service", "DisplayName"),
            config.get("service", "Description")]
    except Exception as e:
        e = f"incorrect parameters in [Service]: {e}"
        if 'log' in locals():
            log.error(e)
        else:
            print(e)
        sleep(3)
        raise SystemExit(1)


def open_config() -> configparser.RawConfigParser:
    try:
        open(f"{homeDir}{cfgFileName}", encoding='utf-8')
    except IOError:
        open(f"{homeDir}{cfgFileName}", 'tw', encoding='utf-8')

    config = configparser.RawConfigParser(allow_no_value=True)
    config = lowcase_sections(config)

    try:
        config.read(f"{homeDir}{cfgFileName}")
    except Exception as e:
        print(f"Fail to read configuration file: {e}")
        sleep(3)
        raise SystemExit(1)
    return config


def write_section(section: str, params: dict) -> bool:
    try:
        with open(f'{homeDir}{cfgFileName}', "a") as configFile:
            configFile.write(f"\n[{section}]\n")
            for k, v in params.items():
                configFile.write(f"{k} = {v}\n")

        return True
    except Exception as e:
        print(f"Can't write to {cfgFileName}: {e}")
        return False


def check_base_sections(config: configparser.RawConfigParser):
    edited = False
    try:
        for i in ['service', 'logging', "notify", 'tasklist']:
            try:
                if not config.has_section(i):
                    print(f"ERROR: no section {i}")
                    edited = write_section(i, default[i])

                    if i == 'tasklist':
                        for taskName in ["disk_c", "app_log", "my_app", "my_http_server"]:
                            write_section(taskName, default[taskName])

            except Exception as e:
                print(e)
                continue

        if edited:
            print("WARNING: created new sections in config file. Restart me to apply them")
            sleep(3)
            raise SystemExit(1)
    except Exception as e:
        print(f"ERROR: Fail to create configuration file: {e}")
        sleep(3)
        raise SystemExit(1)


def create_logger(config: configparser.RawConfigParser) -> (logging.Logger, logging.Logger, logging.StreamHandler):
    level = logging.INFO
    logSize = 10240
    logCount = 5
    try:
        if not config.getboolean("logging", "enable"):
            level = 0
        else:
            logLevel = config.get("logging", "loglevel").lower()
            if logLevel == "full":
                level = logging.DEBUG

            logSize = config.getint("logging", "logmaxsizekbs")
            logCount = config.getint("logging", "logmaxfiles")
    except Exception as e:
        print("WARNING: Check parameters for Logging.", str(e))
        sleep(3)
        raise SystemExit(1)

    log_formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    my_handler = RotatingFileHandler(
        f"{homeDir}logs/AppWatch.log",
        maxBytes=logSize * 1024,
        backupCount=logCount,
        encoding='utf-8')
    my_handler.setFormatter(log_formatter)

    console = logging.StreamHandler(stream=sys.stdout)  # вывод в основной поток
    console.setFormatter(log_formatter)
    console.setLevel(level)
    # logging.getLogger('root').addHandler(console)

    log = logging.getLogger('AppWatch')
    log.addHandler(my_handler)
    log.setLevel(level)
    log.addHandler(console)

    # disable requests logging
    logging.getLogger('urllib3.connectionpool').setLevel(logging.CRITICAL)

    return log, console


def verify_config(config: configparser.RawConfigParser, log: logging.Logger) -> dict:
    def verify_notify():
        try:
            cfg["notify"]["localName"] = config.get("notify", "localName")
            cfg["notify"]["localIp"] = config.get("notify", "localIp")
            log.info("Local server is %s (%s)" % (cfg["notify"]["localIp"], cfg["notify"]["localName"]))
        except Exception as e:
            log.error(f"incorrect parameters in [notify]: {e}")
            sleep(3)
            raise SystemExit(1)

        try:
            cfg["notify"]["resendTime"] = config.getint("notify", "resendTimeoutM")
            cfg["notify"]["onlyChanges"] = config.getboolean("notify", "onlyChanges")
            cfg["notify"]["type"] = config.get("notify", "type").lower()
            if cfg["notify"]["type"].strip() == '':
                raise Exception(f'Wrong Notify type: {cfg["notify"]["type"]}')

            cfg["notify"]["useproxy"] = config.getboolean("notify", "useproxy")
            if cfg['notify']["useproxy"]:
                log.warning("Using proxy for notifier")

                if not config.has_section('proxy'):
                    if write_section('proxy', default['proxy']):
                        log.warning("created new sections in config file. Restart me to apply them")
                        sleep(3)
                        raise SystemExit(1)

                cfg['notify']['proxy'] = {'http': {}, 'https': {}}
                added = False
                for k in cfg['notify']['proxy']:
                    if config.has_option('proxy', k):
                        added = True
                        cfg['notify']['proxy'][k] = config.get('proxy', k)

                if not added:
                    raise Exception(f"Ebabled Proxy, but no one proxy added")

        except Exception as e:
            log.error("%s" % e)
            sleep(3)
            raise SystemExit(1)

    def verify_log_task(sec: str, parent: dict = None):
        try:
            if parent:
                if not parent['workDir']:
                    if not parent['exePath']:
                        raise Exception(f'not found parameter exePath in [{parent["task"]}]')
                    else:
                        path = parent['exePath']
                else:
                    path = parent['workDir']

                if not path.endswith('/'):
                    path = path + '/'

                cfg["tasks"]["logTask"][parent['task']] = tmp = {}
                tmp["file"] = config.get(sec, "file").replace('{{appDir}}', path)
            else:
                cfg["tasks"]["logTask"][sec] = tmp = {}
                tmp["file"] = config.get(sec, "file")

            tmp["tmpl"] = [i.strip() for i in config.get(sec, "templates").split(';')]
        except Exception as e:
            log.error(f"incorrect parameters in [{sec}]: {e}")
            sleep(3)
            raise SystemExit(1)

    def verify_scheduler() -> list:
        ls = []
        try:
            active = config.getint('tasklist', "active")
            cfg["tasks"]["intervalCheckMin"] = config.getint('tasklist', "intervalCheckMin") * 60
            log.info(f"Activated {active} tasks")

            if active <= 0:
                raise Exception('Schedule is enabled, but no one task is active')
            else:
                for n in range(1, active + 1):
                    taskName = config.get('tasklist', str(n))
                    if not config.has_section(taskName):
                        raise Exception(f'Not found task section {taskName}')
                    else:
                        ls.append(taskName)
            return ls
        except Exception as e:
            log.error(f"incorrect parameters in [tasklist]: {e}")
            sleep(3)
            raise SystemExit(1)

    def verify_tasks(taskList: list):
        for task in taskList:
            try:
                # disk tasks
                if config.has_option(task, 'disk'):
                    cfg["tasks"]["diskTask"][task] = tmp = {}
                    tmp["diskWarn"] = config.getint(task, "Warning")
                    tmp["critFree"] = config.getint(task, "Critical")
                    tmp["diskUsage"] = config.get(task, "disk")
                    log.info(f'monitoring disk space: {tmp["diskUsage"]}')
                    continue

                # log tasks
                if config.has_option(task, 'file'):
                    verify_log_task(task)
                    continue

                # process tasks
                jobListTmp = {}
                jobListTmp['task'] = task
                jobListTmp['exe'] = config.get(task, "exe")
                jobListTmp['doRestart'] = config.getboolean(task, "doRestart")
                jobListTmp['alwaysWork'] = config.getboolean(task, "alwaysWork")
                jobListTmp['restartTime'] = config.getint(task, "timeForRestartingSec")
                jobListTmp['whatStart'] = whatStart = config.get(task, "whatStart")

                if config.has_option(task, 'exePath'):
                    jobListTmp['exePath'] = config.get(task, "exePath").replace('\\', '/', -1)
                    if not jobListTmp['exePath'].endswith('/'):
                        jobListTmp['exePath'] = jobListTmp['exePath'] + '/'
                else:
                    jobListTmp['exePath'] = None

                if config.has_option(task, 'workdir'):
                    jobListTmp['workDir'] = config.get(task, "workdir").replace('\\', '/', -1)
                    if not jobListTmp['workDir'].endswith('/'):
                        jobListTmp['workDir'] = jobListTmp['workDir'] + '/'

                    jobListTmp['checkPath'] = jobListTmp['workDir']
                else:
                    jobListTmp['workDir'] = None
                    jobListTmp['checkPath'] = jobListTmp['exePath']

                if not config.has_option(task, 'exePath') and not config.has_option(task, 'workDir'):
                    raise Exception("set any parameter: exePath, workDir ")

                if config.has_option(task, 'timeForResponse'):
                    jobListTmp['respTime'] = config.getint(task, "timeForResponse")
                else:
                    jobListTmp['respTime'] = 10

                jobListTmp['checkUrl'] = config.getboolean(task, "checkUrl")
                if jobListTmp['checkUrl']:
                    jobListTmp['url'] = config.get(task, "url")

                if whatStart == 'exe':
                    if not config.has_option(task, 'exePath'):
                        raise Exception("Used whatStart=exe, but no parameter exePath")

                    if config.has_option(task, 'exeKey'):
                        jobListTmp['exeKey'] = config.get(task, "exeKey")
                    else:
                        jobListTmp['exeKey'] = ''
                elif whatStart == 'command':
                    jobListTmp['command'] = config.get(task, "command")
                elif whatStart == 'service':
                    jobListTmp['service'] = config.get(task, "service")
                else:
                    raise Exception('Wrong parameter whatStart. Allowed: exe, command, service')

                if config.has_option(task, 'logInspector'):
                    jobListTmp['logInspector'] = config.get(task, 'logInspector')
                    verify_log_task(jobListTmp['logInspector'], jobListTmp)

                cfg["tasks"]["jobList"][task] = jobListTmp
            except Exception as e:
                log.error(f"incorrect parameters in [{task}]: {e}")
                sleep(3)
                raise SystemExit(1)

    verify_notify()
    taskList = verify_scheduler()
    verify_tasks(taskList)
    return cfg


class Templater:
    def __init__(self, log: logging.Logger):
        self.legendTmpl = {
            'main': {
                "break": "\n",
                "localName": cfg['notify']['localName'],
                "localIp": cfg['notify']['localIp']
            }
        }
        self._tmpl = {}
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
                if s not in self._tmpl:
                    self._tmpl[s] = {}
                for p, v in config2.items(s):
                    self._tmpl[s][p] = v

            if len(self._tmpl) == 0:
                raise Exception("templates.cfg is empty")

        except Exception as e:
            print("Error to read configuration file:", str(traceback.format_exc()))
            sleep(3)
            raise SystemExit(1)

    def extend_legend(self, section: str, tmpl: dict):
        for newP, v in tmpl.items():
            if isinstance(v, dict):
                raise Exception(f"Trying add multiple levels dict")

            for oldApp in self.legendTmpl.values():
                for oldP in oldApp:
                    if newP.lower() == oldP.lower():
                        raise Exception(f"Templater legend already have {newP} for module {oldApp}")

        self.legendTmpl[section] = tmpl.copy()

    def tmpl_fill(self, section: str, name: str) -> str:
        try:
            body = self._tmpl[section][name.lower()]
            for sec in self.legendTmpl.values():
                for k, v in sec.items():
                    body = body.replace("{{%s}}" % k, str(v), -1)
            return body
        except KeyError:
            raise Exception(f'[{section}]{name} not found in templates')
        except Exception as e:
            raise Exception(f'Fail to get template [{section}]{name}: {e}')

    def get_tmpl(self, section: str, name: str) -> str:
        try:
            return self._tmpl[section][name]
        except KeyError:
            raise Exception(f'[{section}]{name} not found in templates')
        except Exception as e:
            raise Exception(f'Fail to get template [{section}]{name}: {e}')


class Notify:
    def __init__(self, name: str):
        self.name = name
        self.cfg = cfg
        self.defaultCfg = {}

    def load_config(self, config: configparser, proxy: dict = None) -> dict:
        return {}

    def send_notify(self, app: str, event: str, body: str) -> bool:
        return True


def load_notifier(cfg: dict, log: logging.Logger) -> Notify:
    try:
        name = cfg["notify"]["type"]
        if name != '':
            log.info(f'Load notifier {name}')
            # TODO import *
            # but now for pyInstaller need like
            # import notifier.email
            # import notifier.discord
            # import notifier.slack
            # notifier = getattr(__import__(f'notifier.{name}'), name)
            # notify = notifier.Notify(name)

            # на случай упаковки в бинарник, но тогда нужно всю стандартную либу включать
            # dict_obj = {}
            with open(f'{homeDir}notifier/{name}.py', encoding='utf-8') as src:
                scrCode = src.read()

            a = globals()
            # exec(scrCode, globals(), dict_obj)
            # notify = dict_obj['Notify'](name)
            exec(scrCode, globals(), globals())
            notify = a['Notify'](name)

            try:
                if not config.has_section(name):
                    log.warning(f'Create new section {name}')
                    if write_section(name, notify.defaultCfg):
                        log.warning("created new sections in config file. Restart me to apply them")
                        sleep(3)
                        raise SystemExit(1)
            except Exception as e:
                log.error(f"Fail to load notify configuration: {e}")

            cfg["notify"][name] = notify.load_config(config, cfg['notify']['proxy'])
        return notify
    except ImportError:
        log.error(f'Fail import notifier: {name}: {traceback.format_exc()}')
        raise SystemExit(1)
    except AttributeError as e:
        log.error(f'Wrong notifier: {e}')
        raise SystemExit(1)
    except Exception:
        log.error(f'Fail load notifier: {traceback.format_exc()}')
        raise SystemExit(1)


def load_event_scripts(cfg: dict) -> dict:
    def load_script(script: str) -> FunctionType:
        """
        Search scripts in path and compile for using in
        Factory module

        :return: module
        """
        fileName, ext = script.split('.')

        if ext != 'py':
            raise Exception(f"Wrong script extension {ext}")

        try:
            with open(f'{homeDir}scripts/{script}', encoding='utf-8') as src:
                scrCode = src.read()

            a = globals()
            exec(scrCode, globals(), globals())
            handler = a['handler']
            return handler

        except ModuleNotFoundError as e:
            raise Exception(f"No script {fileName}. Try to set full path.")
        except AttributeError as e:
            raise Exception(f'Wrong script: {e}')
        except Exception as e:
            raise Exception(f'Fail import script: {e}')

    for sec in ['diskTask', 'logTask', 'jobList']:
        for k, v in cfg['tasks'][sec].items():
            if config.has_option(k, 'eventScript'):
                scriptName = config.get(k, 'eventScript')
                log.info(f"loading script {scriptName} ({k})")
                v['eventScript'] = load_script(scriptName)
    return cfg


if __name__ != "__main__":
    try:
        create_dirs([f"{homeDir}{'logs'}"])
    except Exception as e:
        print(e)
        sleep(3)
        raise SystemExit(-1)

    config = open_config()
    check_base_sections(config)
    log, console = create_logger(config)
    cfg = verify_config(config, log)
    cfg = load_event_scripts(cfg)
    templater = Templater(log)
    notify = load_notifier(cfg, log)
