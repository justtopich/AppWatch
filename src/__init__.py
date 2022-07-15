import datetime as dtime
import os, sys
import socket
import traceback
import signal
import shutil
import json
from time import sleep
from threading import Thread
from subprocess import Popen, PIPE, DEVNULL
import configparser
import logging
from logging.handlers import RotatingFileHandler
# need for email connector
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import re

import psutil
import requests
# from plyer import notification


__version__ = "2022.07.14.18"


def sout(msg, clr='white'):
    """
    :param clr: colors available: white|green|sun|violet|breeze|red
    """
    colors = {
        'white': '\x1b[37m',
        'green': '\x1b[0;30;32m',
        'sun': '\033[93m',
        'violet': '\x1b[0;30;35m',
        'breeze': '\x1b[0;30;36m',
        'red': '\x1b[0;30;31m'}

    print(f"{colors[clr]}{msg}\x1b[0m")

notification = None

if hasattr(sys, "_MEIPASS"):
    dataDir = sys._MEIPASS + '/'  # pylint: disable=no-member
else:
    dataDir = './'

keys = os.path.split(os.path.abspath(os.path.join(os.curdir, __file__)))
appName = sys.argv[0][sys.argv[0].replace('\\', '/').rfind('/') + 1:]
homeDir = os.path.realpath(os.path.dirname(sys.argv[0])).replace('\\', '/', -1) + '/'

# import os,sys
# print("CWD: "+os.getcwd())
# print("Script: "+sys.argv[0])
# print(".EXE: "+os.path.dirname(sys.executable))
# print("Script dir: "+ os.path.realpath(os.path.dirname(sys.argv[0])))
# pathname, scriptname = os.path.split(sys.argv[0])
# print("Relative script dir: "+pathname)
# print("Script dir: "+ os.path.abspath(pathname))

if not os.path.exists(homeDir):
    homeDir = sys.argv[0][:sys.argv[0].replace('\\', '/').rfind('/')+1]
if not os.path.exists(homeDir+appName):
    appName = keys[1][:keys[1].find('.')].lower()

unixSvcFile = """
[Unit]
Description = {{desc}}
After = network.target

[Service]
Type = simple
ExecStart = {{exe}} deamon
TimeoutStartSec = 0
PIDFile = {{pid}}

[Install]
WantedBy=multi-user.target
"""


__all__ = [
    'dtime', 'os', 'sys', 'socket', 'unixSvcFile', 'traceback', 'signal',
    'shutil', 'sleep', 'Thread', 'Popen', 'PIPE', 'DEVNULL', 'configparser', 'json',
    'logging', 'RotatingFileHandler', 'MIMEText', 'MIMEMultipart', 'smtplib', 're',

    'requests', 'psutil', 'notification',

    '__version__', 'homeDir', 'dataDir', 'appName', 'sout']


if os.name == "nt":
    import win32event
    import win32service
    import win32serviceutil
    import servicemanager
    from windowstoast import Toast as notification

    __all__.extend([
        'win32event',
        'win32service',
        'win32serviceutil',
        'servicemanager'])
    PLATFORM = 'nt'
else:
    from deamonizer import Daemonize

    __all__.append('Daemonize')
    PLATFORM = 'posix'

__all__.append('PLATFORM')
