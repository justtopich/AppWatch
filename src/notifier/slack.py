####################################
#
# AppWatch
# Connector to Slack service
#
####################################

from json import dumps
import requests
from conf import configparser, log


class Notify:
    def __init__(self, name: str):
        log.info("lucky-slacky v1.1")
        self.name = name
        self.cfg = {}
        self.defaultCfg = {"url": "YOUR_WEBHOOK_URL_HERE"}

    def load_config(self, config: configparser, proxy:dict = None) -> dict:
        self.cfg['proxy'] = proxy

        try:
            self.cfg["url"] = config.get(self.name, "url")
            log.info(f"Slack using WEBHOOK {self.cfg['url']}")
        except Exception as e:
            e = f"Bad {self.name} configuration: {e}"
            log.error(e)
            raise Exception(e)

        return self.cfg

    def send_notify(self, app:str, event:str, body:str) -> bool:
        try:
            data = dumps({"text": body})
            headers = {"Content-type" : "application/json", 'Content-Length': len(body)}

            res = requests.post(self.cfg['url'], data, headers, timeout=10, proxies=self.cfg['proxy'])
            if res.status_code != 200:
                raise Exception("Server return status %s" % res.status_code)

            log.info(f"Отчёт отправлен.")
            return True

        except Exception as e:
            log.error("Не могу отправить отчёт в Slack  %s" % e)
            return False
