[https://github.com/justtopich/AppWatch](https://github.com/justtopich/AppWatch)

------

## [build20210712]

### Features

* new `eventScript` parameter



## [build2021011511]

### Features

* Add parameter `[notify]onlyChanges`



## [build202101162]

### Fixed

* Ignoring `resendTimeoutM` parameter



## [build2021011511]

### Features

* Add parameter `[notify]onlyChanges`

### Improvements

* Rename template variable `{{app}}` -> `{{taskName}}`

  

## [build202101145]

### Improvements

* Extended logs if notifier loading is fail

  

## [build2021011264]

### Features

* Multiplatform: adapted code for working on Linux and Windows.
* New parameter **checkUrl** - flag for REST applications
* New parameter **workDir**- additional attribute to identify process

### Fixed

* When AppWatch add new section to cfg file he lost all comments
* Exception if activated only disk check type task. Has no effect on working.
* Exception from process_inspector have double logging
* Can raise exception if **templates.cfg** is empty. AppWatch didn't check this file on starting. Had error when trying to notify.

### Improvements

* Rename parameter `path` -> `exePath`
* Rename parameter `script` -> `command`
* Rename log_inspector variable `{{path}}` -> `{{appDir}}`
* Comments prefix is now only `;`  and `#`
* Builded with python 3.8. Require > 3.6

### Notes

  * Linux version working with posix and tested on Centos 8. 

    


## [build20200427]

- disk_inspector: log doesn't show *diskUsage*
- fix starting service whith space in name
- Не видел процесс если его имя длинее 25 символов
- Идентифицирует процесс не только по имени, но и по директории. AppWatch не мог опередилть кому принадлежит процесс, если они имели одинаковые имена и убивал один из них
- Change methods: killing process and starting services
- not showing windows notifications longer then 255 symbols



## [build20200418]

- start point: all libraries are available from main module AppWatch
- Notifiers now can use main module libraries
- Dynamically importing notifiers. Notifiers must be as python files

## [build20200417]

- Несколько заданий могут ссылаться на одно задание по разбору логов
- add parameter *timeForResponse*
- Templater have new method: *get_tmpl*

## [build20200416]

- add console key ***doc***. Now you can get documentation by console
- fix running if no one task is set
- fix not changing *diskFree* in templates
- remove license inspector.  Add log inspector

##  [build20200413]

* Добавлены оповещения в Windows. Пока только при запуске в консоли
* fix в шаблонах переменные заполнялись только по одному разу
* fix остановка сразу после старта когда запущен как служба
* Отслеживание свободного места нескольких дисков

##  [build20200409]

* В шаблоны добавлена переменная **break**
* Проверка на совпадение переменных при расширении легенды шаблонов
* Discord: add timeout for webhook connection
* Для оповещений теперь можно использовать прокси

##  [build20200406]

* Тексты оповещений теперь можно редактировать через шаблоны.
* Коннекторы к сервисам оповещения вынесены в отдельные модули **notifier**. Теперь можно можно написать свой коннектор и указать его для оповещения. Инструкция прилагается
* Добавлен коннектор к Discord


##  [build20190808]

* Наконец-то доделан запуск служб когда само приложение работает как служба.
* Раньше пытался убить процесс, даже если он не найден
* расширены комментарии в примере конфигурации
* Немного расширены данные в отчёте о диске

##   [build20190723]

* добавлена возможность запускать службы. Но нужны права админа
* имения конфига. 
	новый параметр **whatStart** - указывает как запускать приложение
	параметр appName переименован в **script**
	новый параметр **service**

##   [build20190718]

* исправлена работа в качестве сервиса. На 2012 сервере как сервис не работал
* изменение нумерации заданий. Теперь с 1

##   [build20190710]
* Мог не видеть процесс если в его названии были буквы в верхнем регистре
* Падение при старте когда активно только задание по слежке за диском

##   [build20181009]
* в прошлой версии перепутал местами в отчёте ip и название сервера
* Теперь если процесс сам поднялся, то пришлёт отчёт об этом.

##   [build20181002]
* исправлен запуск приложений при работе как служба
* изменён порядок нумерации заданий  - начиная с 0

##   [build20180913]
* исправлена папка записи логов при запуске через службы
* приложение не стартовало.
* Запуск зомби процессов было лишь на x32 ОС
* **doRestart** - если указать False, то пришлёт лишь уведомление без перезапуска app

##   [build20180910]
* Добавил **__build_pyInst.py** для сборки exe файла чтобы запускать как службу или так.
+ Добавлен параметр **intervalMin**
+ Поддержка `#`,`;`, `//` для комментариев в конфиге
+ Создание только несуществующих секций в конфиге. Раньше просто проверял на наличие 
  файла конфига.

##   [old]
V2.1 Проверка лицензии – теперь отчёт шлётся не только при Error, но и если в журнале
  встречается «No license found», т.к. это надпись имеет уровень info (даже не warning!)
V2.0 Добавил проверку свободного места. Нужно указать папку, предупредительный и 
  критический размер свободного места.