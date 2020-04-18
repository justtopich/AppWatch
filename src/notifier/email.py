####################################
#
# AppWatch
# Connector to email service
#
####################################

from AppWatch import (
    configparser,
    MIMEMultipart,
    MIMEText,
    smtplib,
    re)
from conf import log, templater


class Notify:
    def __init__(self, name: str):
        self.name = name
        self.cfg = {}
        self.defaultCfg = {
            "sendTo": "admin@pantsumail.ru",
            "server": "smtp.pantsumail.ru",
            "port": "587",
            "useSSL": "False",
            "// Try 587 if 465 not work": "",
            "user": "username",
            "password": "11111",
            "fromHeader": "Pantsu Alarm <bot@pantsumail.ru>"}

    def load_config(self, config: configparser, proxy:dict = None) -> dict:
        self.cfg['proxy'] = proxy
        try:
            self.cfg["sendTo"] = config.get(self.name, "sendTo")
            self.cfg["server"] = config.get(self.name, "server")
            self.cfg["port"] = config.getint(self.name, "port")
            self.cfg["useSSL"] = config.getboolean(self.name, "useSSL")
            self.cfg["user"] = config.get(self.name, "user")
            self.cfg["password"] = config.get(self.name, "password")
            self.cfg["fromHeader"] = config.get(self.name, "fromHeader")
            log.info("Адрес почты получателя " + self.cfg["sendTo"])
        except Exception as e:
            e = f"Bad {self.name} configuration: {e}"
            log.error(e)
            raise Exception(e)

        if re.findall(r'\w+@\w+.\w+', self.cfg["sendTo"]):
            log.debug(f'Адрес почты получателя {self.cfg["sendTo"]}')
        else:
            log.error("Неправильный адрес почты sendTo.")
            raise SystemExit(1)

        return self.cfg

    def send_notify(self, app:str, event:str, body:str) -> bool:
        try:
            # Формирует заголовок письма
            msg = MIMEMultipart('mixed')
            msg['Subject'] = templater.tmpl_fill(self.name, 'subject')
            msg['From'] = self.cfg['fromHeader']
            msg['To'] = self.cfg['sendTo']
            msg.attach(MIMEText(body))
        except Exception as e:
            log.error(str(e))

        log.debug(f"Соединение с почтовым сервером {self.cfg['server']}")
        try:
            if self.cfg["useSSL"]:
                s = smtplib.SMTP_SSL(host=self.cfg['server'], port=self.cfg['port'])
                s.ehlo()
                s.login(self.cfg['user'], self.cfg['password'])
                s.auth_plain()
            else:
                s = smtplib.SMTP(self.cfg['server'], self.cfg['port'])
                s.ehlo().starttls().ehlo().login(self.cfg['user'], self.cfg['password']) # Рукопожатие, обязательно

            log.debug(f"Отправка письма")
            s.sendmail(self.cfg["fromHeader"], self.cfg["sendTo"], msg.as_string())

            log.info(f"Письмо с отчётом {app} отправлено.")
            return True
        except Exception as e:
            if e.errno == 11004:
                log.error("Не могу соединиться с почтовым сервером.")
            else:
                log.error("Ошибка при отправлении письма: %s" % e)
            return False
