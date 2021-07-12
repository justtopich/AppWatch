from logging import Logger
from typing import Tuple
import os
from datetime import datetime, timedelta


def handler(log: Logger, task: str, event: str, message: str) -> Tuple[bool, str]:
    maxDays = timedelta(days=20)
    logDir = '/var/log'

    for i in os.listdir(logDir):
        if i.startswith('messages'):

            logLife = datetime.now() - datetime.fromtimestamp(os.path.getmtime(f'{logDir}/{i}'))
            if logLife >= maxDays:
                os.remove(f'{logDir}/{i}')
                text = f'deleted log {logDir}/{i}'

                log.info(text)
                message += f"\n{text}"

    return True, message
