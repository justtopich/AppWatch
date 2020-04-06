from time import sleep
import os, sys
import socket
import servicemanager
import traceback

import win32event
import win32service
import win32serviceutil

from __init__ import __version__
from conf import get_svc_params

# Windows запускает модули exe из папки пользователя
# Папка должна определяться только исполняемым файлом
keys = os.path.split(os.path.abspath(os.path.join(os.curdir, __file__)))
homeDir = keys[0].replace('\\', '/')+'/'
appName = keys[1][:keys[1].find('.')].lower()
del keys

devMode = False
# devMode = True
# sys.argv.append('run')

svcParams = get_svc_params()

def svc_init():
    class AppServerSvc(win32serviceutil.ServiceFramework):
        _svc_name_ = svcParams[0]
        _svc_display_name_ = svcParams[1]
        _svc_description_ = svcParams[2]

        def __init__(self, args):
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
            socket.setdefaulttimeout(60)

        def SvcStop(self):
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            win32event.SetEvent(self.hWaitStop)

        def SvcDoRun(self):
            rc = None
            try:
                import inspector
            except Exception as e:
                with open(homeDir+'error.txt', 'w') as f:
                    f.write(str(e))
                    os._exit(42)

            while rc != win32event.WAIT_OBJECT_0:
                time.sleep(1)
                rc = win32event.WaitForSingleObject(self.hWaitStop, 4000)
            inspector.shutdown_me(1, '')
    return AppServerSvc

if __name__ == "__main__":
    try:
        if len(sys.argv) == 1 and not devMode:
            if homeDir.endswith('system32/'):
                # Server 2012 != Win 10
                homeDir = os.path.dirname(sys.executable) + '/'

            from conf import cfg

            AppServerSvc = svc_init()
            servicemanager.Initialize()
            servicemanager.PrepareToHostSingle(AppServerSvc)
            servicemanager.StartServiceCtrlDispatcher()
        else:
            if 'install' in sys.argv or 'remove' in sys.argv or 'update' in sys.argv:
                from conf import homeDir, config, get_svc_params

                svcParams = get_svc_params()
                AppServerSvc = svc_init()
                win32serviceutil.HandleCommandLine(AppServerSvc)

            elif 'help' in sys.argv:
                raise Exception('Show help')
            elif 'run' in sys.argv:
                from conf import *

                svcParams = get_svc_params()
                if devMode:
                    print('\n!#RUNNING IN DEVELOPER MODE\n')
                    log.setLevel(10)
                import inspector
            else:
                raise Exception('Show help')

    except Exception as e:
        print(traceback.format_exc())
        with open(homeDir+'error.txt','w') as file:
            file.write(str(e))
        print(f'\nUsage: {os.path.basename(sys.argv[0])} [options]\n'
              'Options:\n'
              ' run : запуск через консоль\n'
              ' install : установка службы windows\n'
              ' remove : удалить службу windows\n'
              ' update: обновить службу windows\n')
        sleep(2)
