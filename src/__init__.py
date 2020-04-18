import datetime as dtime
import os, sys
import socket
import servicemanager
import traceback
import signal
import shutil
import json
from time import sleep
from threading import Thread
from subprocess import Popen, PIPE, DEVNULL
import configparser, logging
from logging.handlers import RotatingFileHandler

# need for email connector
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import re


import win32event
import win32service
import win32serviceutil

# import pystray
import requests
from plyer import notification

__version__ = "2020.04.18.397"
# Windows запускает модули exe из папки пользователя
# Папка должна определяться только исполняемым файлом
keys = os.path.split(os.path.abspath(os.path.join(os.curdir, __file__)))
appName = keys[1][:keys[1].find('.')].lower()
homeDir = sys.argv[0][:sys.argv[0].replace('\\', '/').rfind('/')+1]

if hasattr(sys, "_MEIPASS"):
    dataDir = sys._MEIPASS + '/'
else:
    dataDir = './'

__all__ = [
    'dtime', 'os', 'sys', 'socket', 'servicemanager', 'traceback', 'signal',
    'shutil', 'sleep', 'Thread', 'Popen', 'PIPE', 'DEVNULL', 'configparser', 'json',
    'logging', 'RotatingFileHandler', 'MIMEText', 'MIMEMultipart', 'smtplib', 're',

    'win32event', 'win32service', 'win32serviceutil', 'requests', 'notification',

    '__version__', 'homeDir', 'dataDir', 'appName'
]