# AppWatch

Оповещает о падении REST приложений и перезапускает их.
Возможности:

- Отслеживание свободного места на диске

- Выявление ошибок лицензий

- Отслеживание процессов приложений.

- Проверка отклика REST API приложений

- Запуск приложений или его служб или сторонних скриптов

- Оповещение на почту или в slak о событиях

  

## Предназначение

Позволяет автоматизировать проверку работы web-приложений. Если приложение упало или зависло (процесс активен, но не не отвечает на запросы HTTP), то попытается перезапустить зависший компонент и вышлет вам оповещение.

Для приложений, которые ведут журнал лицензии в **license.log**  можно дополнительно проверять его. Решение парсит данный лог и высылает предупреждение в случае обнаружения ошибок.



## Установка и настройка

При отсутствии конфигурационного файла **AppWatch.cfg** , приложение автоматически создаст новый. В таком случае он будет содержать лишь примеры настроек.

Конфигурационный файл состоит из секций, в котором есть параметры относящейся к ней и имеет следующую структуру:

```ini
[Секция1]
Параметр=значение
Параметр1=значение

[Секция2]
Параметр=значение
Параметр1=значение
```

Название каждой секции обозначено квадратными скобками `[]`. Секции не должны повторяться и могут находится в любом порядке. Параметр относится к секции до тех пор, пока не будет объявлена новая.

### Основные

Параметры службы в секции **[service]**:

| **Параметр** | **Описание** |
| --- | --- |
| name | Имя службы. Оно используется для идентификации службы и будет отображаться в диспетчере задач. |
| displayName | Название службы которое будет отображаться в диспетчере служб. |
| description | Описание службы |

Эти параметры используются для удаления и установки службы Windows.

Создание службы для решения позволит ему работать вне зависимости от статуса пользователя выполнять автоматического запуск в случае падения, указывать от имени какого пользователя запускать и другие функции диспетчера служб.

Установка, удаление и изменение служб производится через исполняемый файл с правами администратора.

Вызовите исполняемый файл:

> appwatch.py ***key***
>

Где вместо **key** используется один из доступных ключей:

| Ключ    | Описание                    |
| --- | --- |
| install | установка службы windows |
| remove | удалить службу |
| update | обновить службу |
| run | запуск приложения в консоли |

После создания службы в Диспетчере служб можете задать ей тип запуска &quot;автоматически&quot;.

Для логгирования доступны следующие параметры секции **[logging]**:

| **Параметр** | **Описание** |
| --- | --- |
| enable | Булево значение. При **False** логи отображаются только в консоли |
| loglevel | Уровень событий которые будут записаны.<br>**Full** - запись всех событий включая _debug._ <br>**Normal** - запись событий уровня _info_ и выше. |
| logmaxsizekbs | Максимальный размер файла журнала. При достижении заданного лимита запись начнётся в новый файл, а предыдущий будет переименован. |
| logmaxfiles | Максимальное количество файлов журнала. При достижении заданного лимита коннектор будет удалять самые первые переименованные файлы. |



### Оповещения

Сведения о сервере в секции **[server]**:

| **Параметр** | **Описание** |
| --- | --- |
| localName | Название сервера |
| localIp | Ip адрес сервера |
| Notify | Способ уведомления **email** или **slack** |
| resendTimeoutM | Минимальное время между отправки уведомлениями. |

При повторном возникновения одного и того же события уведомление по нему не будет отослано если не прошло указанное время.

Если указали **notify=email** то задайте настройки почты в секции **[email]**:

| **Параметр** | **Описание** |
| --- | --- |
| userMail | Почта на которую высылать уведомления |
| server | Адрес и порт smtp сервера. Поддерживается как SSL так и простой протокол. |
| port ||
| User | Логин и пароль для авторизации на smpt сервере |
| password ||
| fromHeader | Заголовок письма. <br>**Pantsu Alarm \<bot@pantsumail.ru\>** |

Если же используете **notify=slack, тогда задайте параметры в секции **[slack]**:

| **Параметр** | **Описание** |
| --- | --- |
| url | WEBHOOK URL вашего приложения Slack<br>**https://hooks.slack.com/services/sometoken** |

Получить **WEBHOOK URL** можно на странице _https://api.slack.com/apps_

### Задания

Активные задания указываются в секции **[taskList]:**

| **Параметр** | **Описание** |
| --- | --- |
| intervalCheckMin | Интервал проверки в минутах |
| active | количество активных заданий |

Перечисление заданий начинается от **1**

```ini
[taskList]
intervalCheckMin = 10
active = 2
// 1 = diskUsage
1 = myApp
2 = MyHttpServer
```

Названия заданий должны совпадать с их секциями.

Задание **diskUsage** является встроенным, но не обязательным.

| **Параметр** | **Описание** |
| --- | --- |
| path | Диск за которым надо следить <br> **C:\\** |
| warning | Количество свободного места для отправки предупреждения |
| critical | Количество свободного места для отправки оповещения |

Наконец ваши собственные задания.

| **Параметр** | **Описание** |
| --- | --- |
| alwaysWork | Булево значение. При **False** проверка, перезапуск и оповещение будет происходить только если процесс активен. |
| doRestart | Булево значение. Используйте **True** чтобы выполнять перезапуск приложений. |
| timeForResta rtingSec | Время в секундах которое отводится на запуск приложения. Если за это время процесс упадёт, то перезапуск считается неудачным. |
| url | Любой HTTP запрос приложения который возвращает статус **200**. Если статус будет иным или не будет получен ответ – рестарт приложения. |
| exe | Название процесса приложения. |
| whatStart | Что нужно запускать.<br>**exe** – запуск исполняемого файла процесса.<br>**script** – запуск стороннего файла.<br>**service** – запуск службы windows |
| path | Папка нахождения приложения |
| exeKey | Если нужно запускать приложение с ключами. Используется при **whatStart=exe** |
| script | укажите путь к файлу. Используется при **whatStart=script** |
| service | Укажите имя службы. Используется при **whatStart=service** |



Команда запуска скриптов выглядит так:

> start cmd /c **_script_**