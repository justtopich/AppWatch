Python 3.6.6

Simple WatchDog for Windows applications with email or Slack notifications.
It will force restart apps if they are freezing.

Delete .cfg file and run script to create example configuration.

Create task [diskUsage] to watch disk free space.
Create custom task to monitor you application:
	exe - procces name, that must be running. If it in procces list, script will check status
	url - using for http request to checking status. It must be 200 to pass control.
	whatStart [exe, script, service] - what appWatch must starting
		path - where exe running from. It use for restarting app. Used if whatStart=exe
		exeKey - you can setting keys for starting exe. Not required. Used if whatStart=exe
		script - set executable file(maybe start.bat) for custom starting app or another. Used if whatStart=script
		service - service name. Used if whatStart=service. Administrative privileges required.

AppWatch also monitoring license status of applications. Just searching string "error"
 in license.log in application path. It's ok if application doesn't have this file. 
 In this case you will see warning message. But if this file will be and contains 
 errors, AppWatch will send alert.

Cпособен контролировать любые НТТР сервера. Так же 
проверяет лицензии компонентов и в случае выявления ошибок отправляет 
уведомления на почту. Чтобы не спамить на почту, по каждой ошибке отправляется по
 одному письму.
Для каждой программы можно задать параметры запуска или же указать иную программу
 (Например, если программа должна запускаться через скрипт). При первом запуске 
 будет создан файл настроек с примерами.
