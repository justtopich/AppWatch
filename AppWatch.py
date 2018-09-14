####################################
#
# AppWatch. 20180910
#
# Создание\удаление windows службы. Обработка ключей консоли.
# Запуск через службу\консоль.
#
####################################

import socket
import win32event
import win32service
import win32serviceutil
import servicemanager
from conf import *
from __init__ import __version__

svcParams = get_svc_params()
# devmod = True

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
        import inspector
        while rc != win32event.WAIT_OBJECT_0:
            time.sleep(1)
            rc = win32event.WaitForSingleObject(self.hWaitStop, 4000)
        inspector.shutdown_me(1, '')

if __name__ == "__main__":
    if devmod == True:
        print('!#RUNING IN DEVELOPER MODE')
        sys.argv.append('run') # only debug mode
        log.setLevel(int(logging.DEBUG))
    try:
        if len(sys.argv) == 1:
            servicemanager.Initialize()
            servicemanager.PrepareToHostSingle(AppServerSvc)
            servicemanager.StartServiceCtrlDispatcher()
        else:
            if 'install' in sys.argv or 'remove' in sys.argv or 'update' in sys.argv:
                win32serviceutil.HandleCommandLine(AppServerSvc)
            elif 'help' in sys.argv:
                raise Exception('Show help')
            elif 'run' in sys.argv:
                import inspector
            else:
                raise Exception('Show help')

    except Exception as e:
        print(e)
        with open(homeDir+'error.txt','w') as file:
            file.write(str(e))
        print('\nUsage: '+os.path.basename(sys.argv[0])+' [options]\n'
              'Options:\n'
              ' run : запуск через консоль\n'
              ' install : установка службы windows\n'
              ' remove : удалить службу windows\n'
              ' update: обновить службу windows\n')
        time.sleep(2)