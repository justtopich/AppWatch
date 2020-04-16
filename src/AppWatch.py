from time import sleep
import os, sys
import socket
import servicemanager
import traceback

import win32event
import win32service
import win32serviceutil

from __init__ import __version__
from conf import get_svc_params, dataDir, homeDir


# Windows запускает модули exe из папки пользователя
# Папка должна определяться только исполняемым файлом
keys = os.path.split(os.path.abspath(os.path.join(os.curdir, __file__)))
# homeDir = sys.argv[0][:sys.argv[0].replace('\\', '/').rfind('/')+1]
appName = keys[1][:keys[1].find('.')].lower()
svcParams = get_svc_params()
del keys

devMode = False
# devMode = True
# sys.argv.append('run')


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
                    f.write(f"{traceback.format_exc()}")
                os._exit(42)

            while rc != win32event.WAIT_OBJECT_0:
                sleep(1)
                rc = win32event.WaitForSingleObject(self.hWaitStop, 4000)

            inspector.shutdown_me(1, '')
    return AppServerSvc

if __name__ == "__main__":
    try:
        if len(sys.argv) == 1 and not devMode:
            if homeDir.endswith('system32/'):
                homeDir = os.path.dirname(sys.executable) + '/' # Server 2012 != Win 10

            AppServerSvc = svc_init()
            servicemanager.Initialize()
            servicemanager.PrepareToHostSingle(AppServerSvc)
            servicemanager.StartServiceCtrlDispatcher()
        else:
            if 'install' in sys.argv or 'remove' in sys.argv or 'update' in sys.argv:
                from conf import homeDir, config
                AppServerSvc = svc_init()
                win32serviceutil.HandleCommandLine(AppServerSvc)

            elif 'doc' in sys.argv:
                from shutil import copy2
                print('Export documentation to ./docs')

                try:
                    os.mkdir(f'{homeDir}docs')
                except:
                    pass

                for i in os.listdir(f'{dataDir}docs'):
                    copy2(f'{dataDir}docs/{i}', f'{homeDir}docs/{i}')

            elif 'help' in sys.argv:
                raise Exception('Show help')
            elif 'run' in sys.argv:
                from conf import cfg, log

                if devMode:
                    print('\n!#RUNNING IN DEVELOPER MODE\n')
                    log.setLevel(10)
                import inspector

            else:
                raise Exception('Show help')

    except Exception as e:
        e = traceback.format_exc()
        print(e)
        with open(homeDir+'error.txt','w') as file:
            file.write(str(e))

        print(f'\nUsage: {os.path.basename(sys.argv[0])} [options]\n'
              'Options:\n'
              ' run : start me\n'
              ' doc : get documentation\n'
              ' install : install as windows service\n'
              ' remove : delete windows service\n'
              ' update: update windows service\n')
        sleep(2)
