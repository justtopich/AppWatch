from __init__ import *
from conf import get_svc_params, log


devMode = False
# devMode = True
# sys.argv.append('run')


def log_error(msg):
    with open(f"{homeDir}error.txt", 'a', encoding='utf-8') as f:
        f.write(str(msg)+'\r')
        f.write('\n')
    sleep(1)


def svc_init():
    if PLATFORM == 'nt':
        class WinServerSvc(win32serviceutil.ServiceFramework):
            def __init__(self, args):
                svcParams = get_svc_params()
                self._svc_name_ = svcParams[0]
                self._svc_display_name_ = svcParams[1]
                self._svc_description_ = svcParams[2]

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

                    while rc != win32event.WAIT_OBJECT_0:
                        sleep(1)
                        rc = win32event.WaitForSingleObject(self.hWaitStop, 4000)

                    inspector.shutdown_me(78, '')
                except Exception as e:
                    with open(f"{homeDir}error.txt", 'w') as f:
                        f.write(f"{traceback.format_exc()}")
                    os._exit(42)

        Svc = WinServerSvc
    else:
        class UnixServerSvc:
            def __init__(self):
                self.pid = f"{homeDir}appWatch.pid"
                self.daemon = Daemonize(
                    app='AppWatch',
                    pid=self.pid,
                    action=self.app_wrapper,
                    foreground=True,
                    logger=log)
                self.daemon.sigterm = self.sigterm

            def sigterm(self, signum, frame):
                """
                remapping exit method
                """
                from inspector import shutdown_me

                try:
                    shutdown_me(signum, frame, self)
                except Exception as e:
                    log_error(f"Fail shutdown_me: {e}")

            @staticmethod
            def app_wrapper():
                import inspector

            def SvcDoRun(self):
                self.daemon.start()

        Svc = UnixServerSvc
    svcParams = get_svc_params()
    Svc._svc_name_ = svcParams[0]
    Svc._svc_display_name_ = svcParams[1]
    Svc._svc_description_ = svcParams[2]
    return Svc


if __name__ == "__main__":
    try:
        if len(sys.argv) == 1 and not devMode:
            if PLATFORM != 'nt':
                raise Exception('Show help')

            if homeDir.endswith('system32/'):
                homeDir = os.path.dirname(sys.executable) + '/'  # Server 2012 != Win 10

            AppServerSvc = svc_init()
            servicemanager.Initialize()
            servicemanager.PrepareToHostSingle(AppServerSvc)
            servicemanager.StartServiceCtrlDispatcher()
        else:
            if 'install' in sys.argv or 'remove' in sys.argv:
                AppServerSvc = svc_init()

                if PLATFORM == 'nt':
                    win32serviceutil.HandleCommandLine(AppServerSvc)
                else:
                    appServerSvc = AppServerSvc()

                    if 'install' in sys.argv:
                        if not os.path.exists("/etc/systemd/system/"):
                            raise FileNotFoundError("Not found services path: /etc/systemd/system/")

                        unixSvcFile = unixSvcFile.replace('{{desc}}', appServerSvc._svc_description_)
                        unixSvcFile = unixSvcFile.replace('{{exe}}', f"{homeDir}{appName}")
                        unixSvcFile = unixSvcFile.replace('{{pid}}', f"{homeDir}appWatch.pid")

                        try:
                            with open(f'/etc/systemd/system/{appServerSvc._svc_name_}.service', 'w') as f:
                                f.write(unixSvcFile)
                            sout(f"Created {appServerSvc._svc_name_}.service", 'green')
                            sout(f"May need to disabled SELinux", 'sun')
                        except Exception as e:
                            sout(f"Error: creating service file: {e}", 'red')

                        try:
                            os.system(f"systemctl enable {appServerSvc._svc_name_}.service")
                            os.system("systemctl daemon-reload")
                        except Exception as e:
                            print(f"Error: register service: {e}")
                    else:
                        try:
                            os.remove(f'/etc/systemd/system/{appServerSvc._svc_name_}.service')
                            os.system("systemctl daemon-reload")
                            sout(f"Deleted {appServerSvc._svc_name_}.service", 'green')
                        except FileNotFoundError:
                            print(f"Service {appServerSvc._svc_name_}.service not installed")
                        except Exception as e:
                            sout(f"Can't remove {appServerSvc._svc_name_}.service: {e}", 'red')

            elif 'doc' in sys.argv:
                print('Export documentation to ./docs')
                try:
                    os.mkdir(f'{homeDir}docs')
                except Exception as e:
                    print(f"Fail to export docs: {e}")

                for i in os.listdir(f'{dataDir}docs'):
                    shutil.copy2(f'{dataDir}docs/{i}', f'{homeDir}docs/{i}')

            elif 'help' in sys.argv:
                raise Exception('Show help')
            elif 'run' in sys.argv:
                from conf import cfg, log, console

                if devMode:
                    print('\n!#RUNNING IN DEVELOPER MODE\n')
                    log.setLevel(10)
                    console.setLevel(10)
                import inspector

            elif 'deamon' in sys.argv and PLATFORM != 'nt':
                AppServerSvc = svc_init()
                appServerSvc = AppServerSvc()
                appServerSvc.SvcDoRun()
            else:
                raise Exception('Show help')

    except Exception as e:
        e = traceback.format_exc()
        print(e)
        log_error(str(e))

        print(f'\nUsage: {os.path.basename(sys.argv[0])} [options]\n'
              'Options:\n'
              ' run: start me\n'
              ' doc: get documentation\n'
              ' install: install as service\n'
              ' remove: delete service\n')
        sleep(2)
