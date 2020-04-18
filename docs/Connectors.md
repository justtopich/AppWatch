# AppWatch: Создание коннектора

AppWatch использует коннекторы к различным сервисам для отправки оповещений, например email, slack, discord. Коннекторы находятся в папке **notifier** и представляют из себя python файлы. При запуске AppWatch импортирует файл, указанный в типе оповещения **[notify]type**.

Здесь описано как создать и подключить свой коннектор к любым другим сервисам.



### Структура коннектора

Пример реализации:

```python
from AppWatch import requests, traceback, configparser
from conf import log, templater

class Notify:
    def __init__(self, name: str):
        self.name = name
        self.cfg = {}
        self.defaultCfg = {"myParam": "myValue"}

    def load_config(self, config: configparser, proxy: dict=None) -> dict:
        self.cfg['proxy'] = proxy
        try:
            self.cfg["myParam"] = config.get(self.name, "myParam")
        except Exception as e:
            log.warning(f"{e}. Using default value")
            self.cfg["myParam"] = self.defaultCfg["myParam"]
        return self.cfg

    def send_notify(self, taskName:str, event:str, body:str) -> bool:
        print(f"Task {taskName} have new event {event}.")
        try:
            msg = templater.tmpl_fill(self.name, 'myTemplate')
            print(msg)
            requests.get('someURL', proxies=self.cfg['proxy'])
            return True
        except Exception as e:
            log.error(f"Fail to send report: {e}")
            return False
```

В своих коннекторах можно использовать библиотеки которые уже использует **AppWatch**. Их список перечислен в ```__init__.py```. Дополнительно из модуля **conf** можете импортировать:

- log - логер который пишет события в **AppWatch.log**
- templater - работа с шаблонами из **templates.cfg**

Коннектор должен содержать класс **Notify**, имеющий обязательные методы **load_config** и **send_notify** и атрибуты **cfg** , **defaultCfg**, **name**.



#### Notify: атрибуты

###### self.name

Собственное имя коннектора. Оно используется для обращения к конфигу и шаблонам. AppWatch передаёт имя файла коннектора без расширения.

###### self.cfg

Собственные настройки коннектора, которые он будет использовать для своей работы. 

###### self.defaultCfg

Настройки коннектора которые будут записаны в **AppWatch.cfg** в случае их отсутствия.



#### Notify: методы

###### load_config(self, config: configparser, proxy: dict=None)

Чтение параметров. **Config** предоставляет доступ к вашим параметрам из **AppWatch.cfg**. Ваши параметры хранятся в секции, которая имеет тоже название что и коннектор. Коннектор должен вернуть свой актуальный конфиг в виде словаря.

**proxy** является словарём, содержащий адреса прокси серверов:

`{"https": "host:port", "http": "host:port"}`

Если в **AppWatch.cfg**  параметр **[notify]useproxy=False** то proxy будет *None*.



###### send_notify(self, taskName:str, event:str, body:str)

Обработка оповещения. Коннектор должен вернуть **True** или **False** в зависимости от успеха обработки. Подтверждение требуется для исключения многократной отправки повторного оповещения по одному событию за короткое время. Если вернуть False, то AppWatch вскоре попытается ещё раз отправить оповещение.

- *taskName* - Название задания, с которым произошло событие.
- *event* - тип события. Например, diskWarn.
- *body* - текст оповещения.



### Templater 

Вы можете использовать templater для хранения и наполнения своих шаблонов. Например, коннектор email использует его для создания темы письма. Этот шаблон выглядит так:

`Subject = "Inspector Pantsu: Бунт на машинке {{localName}}"`



#### Templater: методы

###### tmpl_fill(section:str, name:str)

Наполнение шаблона. **section** и **name** указывают какой шаблон нужно использовать. Шаблон берётся из **templates.cfg** где каждая секция отвечает за конкретный модуль. Если вы хотите использовать свой шаблон, то в **appName** укажите название своего коннектора.

###### extend_legend(section:str, tmpl: dict)

Добавление переменных для подстановки в шаблоны. Добавленные переменные templater будет подставляться во все шаблоны.

```extend_legend("MyConnector", {"var": "someStr"})```

###### get_tmpl(section:str, name:str)

Получить шаблон из **templates.cfg**.



### Подключение

Коннектор должен располагаться в папке **notifier**. В AppWatch.cfg в параметре **[notify]type** укажите свой коннектор.

Для использования шаблонов в **templates.cfg** создайте секцию с названием своего коннектора.
