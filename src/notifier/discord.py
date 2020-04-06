####################################
#
# AppWatch
# Connector to Discord service
#
####################################

from json import dumps
import requests
from conf import configparser, log, templater


class Notify:
    def __init__(self, name: str):
        log.info("Discord connector v1.0")
        self.name = name
        self.cfg = {}
        self.defaultCfg = {"url": "YOUR_WEBHOOK_URL_HERE"}

    def load_config(self, config: configparser) -> dict:
        try:
            self.cfg["url"] = config.get(self.name, "url")
        except Exception as e:
            e = f"Bad {self.name} configuration: {e}"
            log.error(e)
            raise Exception(e)

        try:
            r = requests.get(self.cfg["url"])
            if r.status_code != 200:
                raise ConnectionError

            j = r.json()
            self.cfg['token'] = j['token']
            self.cfg['name'] = j['name']
            log.info(f"Connected to Discord webhook: {self.cfg['name']}")

        except ConnectionError:
            e = "Bad answer from Discord. Check WEBHOOK URL"
        except KeyError:
            e = "WEBHOOK doesn't return token"

        if 'token' not in self.cfg:
            e = f"Fail with discord connection: {e}"
            log.error(e)
            raise Exception(e)

        return self.cfg

    def send_notify(self, app:str, event:str, body:str) -> bool:
        try:
            data = {"username": "AppWatch", "content": body}
            res = requests.post(self.cfg['url'], json=data,  timeout=10)

            if res.ok:
                log.info(f"Отчёт отправлен.")
                return True
            else:
                raise Exception("Server return status %s" % res.status_code)
        except Exception as e:
            log.error("Не могу отправить отчёт в Discord  %s" % e)
            return False