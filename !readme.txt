Python 3.6.6

Simple WatchDog for Windows applications with email or Slack notifications.
It's not starting apps, but it will force restart apps if they are freezing.

Delete .cfg file and run script to create example configuration.

Create task [diskUsage] to watch disk free space.
Create custom task to monitor you application:
	exe - procces name, that must be running. If it in procces list, script will check 
	status
	url - using for http request to checking status. It must be 200 to pass control.
	path - where exe running from. It use for restarting app. Not required
	exeKey - you can setting keys for starting exe. Not required.
	startApp - set executable file(maybe start.bat) for custom starting app or another 
	actions. Not required

AppWatch also monitoring license status of applications. Just searching string "error"
 in license.log in application path. It's ok if application doesn't have this file. 
 In this case you will see warning message. But if this file will be and contains 
 errors, AppWatch will send alert.

Alerts sending once for each application. To reset alerts you must restart AppWatch.

В отличии от Videologger_helper.ps1 не надо разрешать выполнение скриптов PowerShell,
 перезапускает программы быстрее, способен контролировать любые НТТР сервера. Так же 
проверяет лицензии компонентов Autonomy и в случае выявления ошибок отправляет 
уведомления на почту. Чтобы не спамить на почту, по каждой ошибке отправляется по
 одному письму. После исправления ошибок необходимо перезапустить скрипт. 
Для каждой программы можно задать параметры запуска или же указать иную программу
 (Например, если программа должна запускаться через скрипт). При первом запуске 
 будет создан файл настроек с примерами.

TODO
 - add checkStatus & checkProcces. Вариативность проверки статуса, либо процесса,
 либо всего вместе.
 - указывать рабочую папку при старте процесса


История
[build20190710]
* Мог не видить процесс если в его названии были буквы в верхнем регистре
* Падение при старте если было активно только задание по слежке за диском

[build20181009]
* в прошлой версии перепутал местами в отчёте ip и название сервера
+ Теперь если процесс сам поднялся, то пришлёт отчёт об этом.

[build20181002]
* исправлен запуск приложений при работе как служба
* изменён порядок нумерации заданий  - начиная с 0

[build20180913]
* исправлена папка записи логов при запуске через службы
* приложение не стартовало.
* Запуск зомби процессов было лишь на x32 ОС
+ doRestart - если указать False, то пришлёт лишь уведомление без перезапуска app


[build20180910]
Перенёс часть наработок из ASKID Connector:
+ Можно использовать exe файл чтобы запускать как службу или так.
* Изменена структура проекта. Раньше было всё одним файлом.
+ Добавлен параметр intervalMin
+ Поддержка '#', ';', '//' для комментариев в конфиге
+ Создание только несуществующих секций в конфиге. Раньше просто проверял на наличие 
  файла конфига.


[old]
V2.1 Проверка лицензии – теперь отчёт шлётся не только при Error, но и если в журнале
  встречается «No license found», т.к. это надпись имеет уровень info (даже не warning!)
V2.0 Добавил проверку свободного места. Нужно указать папку, предупредительный и 
  критический размер свободного места.
