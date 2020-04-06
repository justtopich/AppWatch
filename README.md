# AppWatch

Оповещает о падении REST приложений и перезапускает их.
Возможности:

- Отслеживание свободного места на диске

- Выявление ошибок лицензий

- Отслеживание процессов приложений.

- Проверка отклика REST API приложений

- Запуск приложений или его служб или сторонних скриптов

- Оповещение событиях через сторонние сервисы (email, slack и прочее)

  

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

После создания службы в Диспетчере служб можете задать ей тип запуска &quot;автоматически&quot;. Служба должна запускаться от имени администратора.

Для логирования доступны следующие параметры секции **[logging]**:

| **Параметр** | **Описание** |
| --- | --- |
| enable | Булево значение. При **False** логи отображаются только в консоли |
| loglevel | Уровень событий которые будут записаны.<br>**Full** - запись всех событий включая _debug._ <br>**Normal** - запись событий уровня _info_ и выше. |
| logmaxsizekbs | Максимальный размер файла журнала. При достижении заданного лимита запись начнётся в новый файл, а предыдущий будет переименован. |
| logmaxfiles | Максимальное количество файлов журнала. При достижении заданного лимита коннектор будет удалять самые первые переименованные файлы. |



### Оповещения

Сведения о сервере в секции **[notify]**:

| **Параметр** | **Описание** |
| --- | --- |
| localName | Название сервера |
| localIp | Ip адрес сервера |
| resendTimeoutM | Минимальное время между отправки уведомлениями |
| type | коннектор к сервису рассылки |

AppWatch предоставляет три коннектора: email, slack и discord. 

При повторном возникновения одного и того же события, уведомление по нему не будет отослано если не прошло заданное в **resendTimeoutM** время.

Если указали **type=email** то задайте настройки почты в секции **[email]**:

| **Параметр** | **Описание** |
| --- | --- |
| sendTo | Почта на которую высылать уведомления |
| server | Адрес и порт smtp сервера. |
| port ||
| useSSL |Использовать защищённое соединение|
| user | Логин и пароль для авторизации на smpt сервере |
| password ||
| fromHeader | Заголовок письма. <br>**Pantsu Alarm \<bot@pantsumail.ru\>** |

Некоторые сервисы требуют разрешение на подключение сторонних приложений. Например для gmail нужно разрешить небезопасные приложения.

Если используете **slack** или **discord**, тогда задайте параметры в их секции:

| **Параметр** | **Описание** |
| --- | --- |
| url | WEBHOOK URL вашего приложения |



#### Шаблоны оповещений

Для каждого события можно использовать свой шаблон текста, который будет отсылаться. В них можно ссылаться на различные данные. По умолчанию доступны:

| Переменная | Значение                                                |
| ---------- | ------------------------------------------------------- |
| localName  | Название сервера                                        |
| localIp    | ip адрес сервера                                        |
| diskUsage  | Диск за которым следит AppWatch                         |
| diskFree   | Размер свободного места на диске в GB                   |
| diskWarn   | Количество свободного места для отправки предупреждения |
| creetFree  | Количество свободного места для отправки оповещения     |
| app        | имя процесса по которому создано оповещение             |
| uid        | UID лицензии с которой возникла проблема                |

Чтобы вставить эти переменные в текст, укажите их в **{{ }}** Например:

 `Сервер {{localName}} в большой беде!`

Шаблоны настраиваются через **templates.cfg**. Каждая секция отвечает за конкретный модуль.

| Шаблон | Событие |
| -------------- | ------- |
||**disk_inspector**         |
| critFree      | Закончилось место на диске |
| diskWarn       | Заканчивается место на диске |
|           | **email** |
| subject      | заголовок письма |
|  | **license_inspector** |
| error | ошибка лицензии |
|  | **process_inspector** |
| alive | процесс вернулся к работе без участия AppWatch |
| badAnswer | процесс не ответил на запрос или вернул неверный ответ |
| notFound | процесс не запущен |
|  |  |



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