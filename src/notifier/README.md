# AppWatch: Создание коннектора

AppWatch использует коннекторы к различным сервисам для отправки оповещений, например email, slack, discord.

Здесь описано как создать и подключить свой коннектор к любым другим сервисам.



### Структура коннектора

Минимальная реализация:

```python
import requests
from conf import configparser, log, templater

class Notify:
    def __init__(self, name: str):
        self.name = name
        self.cfg = {}
        self.defaultCfg = {"myParameter": "myValue"}

​	def load_config(self, config: configparser, proxy: dict=None) -> dict:
		self.cfg['proxy'] = proxy
    
		try:
			self.cfg["myParameter"] = config.get(self.name, "myParameter")
		except Exception as e:
            log.warning(f"{e}. Будет использовано значение по умолчанию")
			self.cfg["myParameter"] = self.defaultCfg["myParameter"]
		return self.cfg

	def send_notify(self, app:str, event:str, body:str) -> bool:
		try:
            msg = templater.tmpl_fill(self.name, 'myTemplate')
			print(msg)
			print(f"Датчик {app} зарегестрировал событие {event}.")
			print(f"Текст события: {body}")
			requests.get('someURL', proxies=self.cfg['proxy'])
            return True
        except Exception as e:
            log.error(f"Не удалось отправить оповещение: {e}")
            return False
            
```

Коннектор использует объекты:

- configparser - парсер конфига  через который досутпны все парамтеры **AppWatch.cfg** 
- log - логер который пишет события в **AppWatch.log**
- templater - работа с шаблонами из **templates.cfg**

Коннектор должен содеражть класс **Notify**, имеющий обязательные методы **load_config** и **send_notify** и атрибуты **cfg** и **defaultCfg**.



#### Notify: атрибуты

###### self.name

Собственное имя коннектора. Оно используется для обращении к конфигу и шаблонам. AppWatch передаёт имя файла коннектора без расширения.

###### self.cfg

Собственные настройки коннектора, которые он будет использовать для своей работы. 

###### self.defaultCfg

Настройки коннектора которые будут записаны в **AppWatch.cfg** в случае их отсутсвия.



#### Notify: методы

###### load_config(self, config: configparser, proxy: dict=None)

Чтение параметров. Ваши параметры хранятся в секции, которая имеет тоже название что и коннектор. Коннектор должен вернуть свой актуальный конфиг в виде словаря.

**proxy** является словарём, содержащий адреса прокси серверов:

`{"https": "host:port", "http": "host:port"}`

Если в **AppWatch.cfg**  парметр **[notify]useproxy=False** то proxy будет None.



###### send_notify(self, app:str, event:str, body:str)

Обработка оповещения. Коннектор должен вернуть **True** или **False** в зависимости от успеха обработки. Подтверждение требуется для исключения многократной отправки повторного оповещения по одному событию за короткое время. Если вернуть False, то AppWatch вскоре попытается ещё раз отправить оповещение.

- *app* - Название модуля, из которого пришло событие. Например, это может быть process_inspector, license_inspector или disk_inspector.
- *event* - тип события. Например, diskWarn.
- *body* - текст оповещения.



### templater 

Вы можете использовать templater для хранения и наполнения своих шаблонов. Например, коннектор email использует его для создания темы письма. Этот шаблон выглядит так:

`Subject = "Inspector Pantsu: Бунт на машинке {{localName}}"`



#### templater: методы

###### tmpl_fill(self, appName: str, event: str)

Наполнение шаблона. **appName** и **event** указывают какой шаблон нужно использовать. Шаблон берётся из **templates.cfg** где каждая секция отвечает за конкретный модуль. Если вы хотите использовать свой шаблон, то в **appName** укажите название своего коннектора.

###### extend_legend(self, appName: str, tmpl: dict)

Добавление переменных для подстановки в шаблоны. Добавленные переменные templater будет подставляться во все шаблоны.

```extend_legend("MyConnector", {"var": "someStr"})```



### Подключение

Коннектор должен располагаться в папке **notifier**. В **AppWatch.cfg** в параметре **[notify]type** укажите свой коннектор.

Для шаблонов в **templates.cfg** создайте секцию с названием своего коннектора.
