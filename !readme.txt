Simple WatchDog for Windows applications with email or Slack notifications.
It's not starting apps, but it will force restart apps if they are freezing.

Delete .cfg file and run script to create example configuration.

Create task [diskUsage] to watch disk free space.
Create custom task to monitor you application:
	exe - procces name, that must be running. If it in procces list, script will check status
	url - using for http request to checking status. It must be 200 to pass control.
	path - where exe running from. It use for restarting app. Not required
	exeKey - you can setting keys for starting exe. Not required.
	startApp - set executable file(maybe start.bat) for castom starting app or another actions. Not required

AppWatch also monitoring license status of applications. Just searching string "error" in license.log in application path. It's ok if application doesn't have this file. In this case you will see warning message. But if it have and contains errors, AppWatch will send alert.

Alerts sending once for each application. To reset alerts you must restart AppWatch.
