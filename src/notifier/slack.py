####################################
#
# AppWatch. Connector to Slack service
#
####################################

from AppWatch import requests, json
from conf import configparser, log


__version__ = '1.1.1'


class Notify:
    def __init__(self, name: str):
        log.info(f"lucky-slacky v{__version__}")
        self.name = name
        self.cfg = {}
        self.defaultCfg = {"url": "YOUR_WEBHOOK_URL_HERE"}

    def load_config(self, config: configparser, proxy:dict = None) -> dict:
        self.cfg['proxy'] = proxy
        log.info(f"Connecting to {self.name} webhook")

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
            data = json.dumps({"text": body})
            headers = {"Content-type" : "application/json", 'Content-Length': len(body)}

            res = requests.post(self.cfg['url'], data, headers, timeout=10, proxies=self.cfg['proxy'])
            if res.status_code != 200:
                raise Exception("Server return status %s" % res.status_code)

            log.info(f"Report sent")
            return True

        except Exception as e:
            log.error("Fail sent report by Slack  %s" % e)
            return False

