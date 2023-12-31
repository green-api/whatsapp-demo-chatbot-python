# whatsapp-demo-chatbot-python

![](https://img.shields.io/badge/license-CC%20BY--ND%204.0-green)

- [Documentation in English](https://github.com/green-api/whatsapp-demo-chatbot-python/blob/main/README.md).

Пример чатбота написанного на python с использованием API сервиса для Whatsapp [green-api.com](https://green-api.com/en/).
Чатбот наглядно демонстрирует использование API для отправки текстовых сообщений, файлов, картинок, локаций и контактов.


## Содержание
* [Установка среды для запуска чатбота](#установка-среды-для-запуска-чатбота)
* [Запуск чатбота](#запуск-чатбота)
* [Настройка чатбота](#настройка-чатбота)
* [Использование](#использование)
* [Структура кода](#структура-кода)
* [Управление сообщениями](#управление-сообщениями)


## Установка среды для запуска чатбота
Для запуска чатбота необходимо произвести установку среды python. Для этого надо пройти по официальный вэбсайт [python](https://www.python.org/) и загрузить последний релиз подходящий для вашей операционной системы.

После этого загрузится установщик, который надо открыть и начать установку. Следуйте настройкам по умолчанию и завершите установку среды.

После завершения необходимо проверить была ли среда развернута корректно. Для этого откройте командную строку (cmd) и введите запрос:
```
python --version
```
Ответом на введеный запрос должна быть версия python в следующем формате:
```
Python 3.N.N
```
После того, как вы убедились, что среда python установлена на ваш компьютер, надо скачать зип-файл проекта [whatsapp-demo-chatbot-python](https://github.com/green-api/whatsapp-demo-chatbot-python) и распаковать его.

Если же вы знакомы с git, то скопировать проект можно следующим запросом:
```
git clone https://github.com/green-api/whatsapp-demo-chatbot-python.git
```
Далее, откройте папку с чатботом и вызовите командную строку. Для этого надо перейти в адресную строку проводника, ввести `cmd` и нажать `Enter`.

Для запуска чатбота так же необходимо установить модуль [whatsapp-chatbot-python](https://github.com/green-api/whatsapp-chatbot-python) и несколько других модулей через менеджер пакетов [pip](https://pip.pypa.io/en/stable/), который установлен в среде по умолчанию.

Список необходимых модулей для чатбота хранятся в файле requirements.txt. Введите следующий запрос в командную строку чтобы установить их
```
python -m pip install -r requirements.txt
```
Среда для запуска чатбота готова, теперь необходимо произвести настройку и запустить чатбот на вашем аккаунте Whatsapp.


## Запуск чатбота
Для того, чтобы настроить чатбот на своем аккаунте Whatsapp, Вам необходимо перейти в [личный кабинет](https://console.green-api.com/) и зарегистрироваться. Для новых пользователей предоставлена [инструкция](https://green-api.com/docs/before-start/) для настройки аккаунта и получения необходимых для работы чатбота параметров, а именно:
```bash
idInstance
apiTokenInstance
```
После получения данных параметров, откройте файл `bot.py` и введите `idInstance` и `apiTokenInstance` в следующие обьекты на 23-й строке. 
Иниализация данных необходима для связывания бота с Вашим Whatsapp аккаунтом:
```python
ID_INSTANCE = ''
API_TOKEN_INSTANCE = ''
```
Далее чатбот получит доступ к Вашему аккаунту через эти данные:
```python
bot = GreenAPIBot(
    ID_INSTANCE,
    API_TOKEN_INSTANCE
)
```
Сохраните изменения в файле. Далее можно запускать чатбот, для этого введите следующий запрос в командной строке:
```
python bot.py
```
Данный запрос запустит работу чатбота. Процесс начинается с инициализации чатбота, которая включает в себя изменение настроек связанного инстанса.

В библиотеке [whatsapp-chatbot-python](https://github.com/green-api/whatsapp-chatbot-python) прописан механизм изменения настроек инстанса методом [SetSettings](https://green-api.com/en/docs/api/account/SetSettings/), который запускается при включении чатбота.

Все настройки по получению уведомлений выключены по умолчанию, чатбот включит следующие настройки:
```
"incomingWebhook": "yes",
"outgoingMessageWebhook": "yes",
"outgoingAPIMessageWebhook": "yes",
```
которые отвечают за получение уведомлений о входящих и исходящих сообщениях.

Процесс изменения настроек занимает несколько минут, в течении этого времени инстанс будет недоступен. Сообщения отправленные чатботу в это время не будут обработаны.

После того, как будут применены настройки, произойдет удаление уведомлений о полученных ранее входящих сообщениях. Этот процесс так же прописан в библиотеке [whatsapp-chatbot-python](https://github.com/green-api/whatsapp-chatbot-python) и автоматически запускается после изменения настроек.

Это необходимо для того, чтобы чатбот не начал обрабатывать сообщения со старых чатов.

После того, как изменения настроек и удаление входящих уведомлений будут исполнены, чатбот начнет стандартно отвечать на сообщения. Суммарно этот процесс занимает не больше 5 минут.

Чтобы остановить работу чатбота, наведите курсор на командную строку и используйте сочетание клавиш `Ctrl + C`


## Настройка чатбота
По умолчанию чатбот использует ссылки для выгрузки файлов из сети, однако пользователи могут добавить свои ссылки на файлы, одну для файла любого расширения pdf / docx /... и одну для картинки. 

Ссылки должны вести на файлы из облачного хранилища или открытого доступа. На 101-й строке содержится следующий код:
```python
def option_2(notification: Notification) -> None:
    user = manager.check_user(notification.chat)
    if not user: return message_handler(Notification)
    notification.api.sending.sendFileByUrl(
        chatId=notification.chat,
        urlFile='https://...png',
        fileName='...png',
        caption=f'{data["send_file_message"][user.language]}'
        f'{data["links"][user.language]["send_file_documentation"]}',
        )
```
Добавьте ссылку на файл любого расширения в `urlFile=''` и задайте имя файлу в `fileName=''`. Имя файла должно содержать расширение, например "somefile.pdf".
Данная строка после изменения будет в следующем формате:
```python
def option_2(notification: Notification) -> None:
    user = manager.check_user(notification.chat)
    if not user: return message_handler(Notification)
    notification.api.sending.sendFileByUrl(
        chatId=notification.chat,
        urlFile='https://...somefile.pdf',
        fileName='somefile.pdf',
        caption=f'{data["send_file_message"][user.language]}'
        f'{data["links"][user.language]["send_file_documentation"]}',
        )
```
Таким же образом введите ссылку и название для картинки на 120-й строке:
```python
def option_3(notification: Notification) -> None:
    user = manager.check_user(notification.chat)
    if not user: return message_handler(Notification)
    notification.api.sending.sendFileByUrl(
        chatId=notification.chat,
        urlFile='https://...someimage.jpg',
        fileName='someimage.jpg',
        caption=f'{data["send_image_message"][user.language]}'
        f'{data["links"][user.language]["send_file_documentation"]}',
    )
```
Все изменения должны быть сохранены, после чего можно запускать чатбот. Для запуска чатбота вернитесь к [пункту 2](#запуск-чатбота).


## Использование
Если предыдущие шаги были выполнены, то на вашем аккаунте Whatsapp должен работать чатбот. Важно помнить, что пользователь должен быть авторизован в [личном кабинете](https://console.green-api.com/).

Теперь вы можете отправлять сообщения чатботу!

Чатбот откликнется на любое сообщение отправленное на аккаунт.
Так как чатбот поддерживает 2 языка - русский и английский - то прежде чем поприветсвовать собеседника, чатбот попросит выбрать язык общения:
```
1 - English
2 - Русский
```
Ответьте 1 или 2, чтобы выбрать язык для дальнейшего общения. После того, как вы отправите 2, чатбот пришлет приветственное сообщение на русском языке:
```
Добро пожаловать в GREEN-API чатбот, пользователь! GREEN-API предоставляет отправку данных следующих видов. Выберите цифру из списка, чтобы проверить как работает метод отправки

1. Текстовое сообщение 📩
2. Файл 📋
3. Картинка 🖼
4. Контакт 📱
5. Геолокация 🌎

Чтобы вернуться в начало напишите стоп
```
Выбрав число из списка и отправив его, чатбот ответит каким API был отправлен данный тип сообщения и поделится ссылкой на информацию об API. 

Например, отправив 1, пользователь получит в ответ:
```
Это сообщение отправлено через sendMessage метод

Чтобы узнать как работает метод, пройдите по ссылке
https://green-api.com/docs/api/sending/SendMessage/
```
Если отправить что-то помимо чисел 1-5, то чатбот лаконично ответит:
```
Извините, я не совсем вас понял, напишите меню, чтобы посмотреть возможные опции
```
Так же пользователь может вызвать меню, отправив сообщение содержащее "меню". И отправив "стоп", пользователь завершит беседу с чатботом и получит сообщение:
```
Спасибо за использование чатбота GREEN-API, пользователь!
```


## Структура кода
Функциональная часть чатбота находится в файле `bot.py`.
Здесь импортируется класс чатбота `GreenAPIBot`, входящее уведомление `Notification`, класс состояния чата `BaseStates` и фильтры `filters` для обработки сообщений:
```python
from whatsapp_chatbot_python import (
    BaseStates,
    GreenAPIBot,
    Notification,
    filters,
)
```
Инициализация чатбота происходит на 26-й строке:
```python
bot = GreenAPIBot(
    ID_INSTANCE,
    API_TOKEN_INSTANCE
)
```
Каждое сообщение отправленное чатботу обрабатывается роутером, импортируемые фильтры используются для проверки состояния чата с пользователем, типа сообщения и текствого значения. При поступлении сообщения от нового пользователя состояние чата имеет значение `None` по умолчанию.
```python
@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=None)
```
Обработчик получает сообщения через входящие уведомления типа [webhook](https://green-api.com/docs/api/receiving/notifications-format/incoming-message/Webhook-IncomingMessageReceived/).
Проверив данные о пользователе, который отправил сообщение, чатбот сохраняет отправителя в объекте класса `user`. Данный класс хранится в файле `user_manager.py` и имеет 2 поля:
```python
@dataclass
class User:
    language: Optional[str] = None
    ts: Optional[datetime] = None
```
В полях язык общения и время последнего общения с пользователем. Каждое поле используется в логике чатбота, но об этом будет упоминаться позже.

Возвращаясь к файлу `bot.py`, после того, как пользователь отправит первое сообщение чатботу, чатбот проверяет есть ли данный пользователь в списке пользователей. Если нет, то новый пользователь создается и состояние чата изменяется на `ACTIVE`.
```python
notification.state_manager.update_state(notification.sender,
                                        States.ACTIVE.value)
user = manager.check_user(notification.chat)
notification.answer(data['select_language'])
```
```notification.answer()``` это функция библиотеки чатбота, которая проверяет данные о пользователе из входящего уведомления и отправляет ответ данному пользователю. ```data['select_language']``` это один из текстовых ответов чатбота, приготовленных заранее:
```
"1 - English\n2 - Русский"
```
Пользователь отправляет 1 или 2, тем самым выбрав язык общения с чатботом.

Чатбот принимает входящее уведомление и видит, что чат с данным пользователем активен проверив статус состояния чата через фильтр `state=States.ACTIVE.value`. После этого устанавливает язык общения и обновляет состояние чата на `state=States.LANGUAGE_SET.value`, тем самым давая боту понять, что язык общения в данном чате установлен.
```python
@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.ACTIVE.value,
                    text_message=['1', '/1', '1.', '1 '])
def set_eng(notification: Notification) -> None:
    user = manager.check_user(notification.chat)
    if not user: return message_handler(Notification)
    user.set_language('eng')
    notification.state_manager.update_state(notification.sender,
                                            States.LANGUAGE_SET.value)
    notification.answer(
        f'{data["welcome_message"][user.language]}'
        f'{notification.event["senderData"]["senderName"]}'
        f'! '
        f'{data["menu"][user.language]}'
    )
```
Фильтр на проверку текста сообщения принимает значения с символами `['1', '/1', '1.', '1 ']`, чтобы чатбот все равно мог разпознать его:
После того, как установлен язык общения, обработчик проверяет все входящие уведомления через `state=States.LANGUAGE_SET.value` и отвечает на команды 1-5. 

Например, если пользователь отправит 1, следующий код будет запущен:
```python
@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.LANGUAGE_SET.value,
                    text_message=['1', '/1', '1.', '1 '])
def option_1(notification: Notification) -> None:
    user = manager.check_user(notification.chat)
    if not user: return message_handler(Notification)
    notification.answer(
        f'{data["send_text_message"][user.language]}'
        f'{data["links"][user.language]["send_text_documentation"]}'
        )
```
и отправит следующий ответ пользователю:
```
Это сообщение отправлено через sendMessage метод

Чтобы узнать как работает метод, пройдите по ссылке
https://green-api.com/docs/api/sending/SendMessage/
```
Все ответы чатбота хранятся в файле `data.yml` и загружены в `bot.py`:
```python
with open("data.yml", 'r', encoding='utf8') as stream:
    data = safe_load(stream)
```
Ответы чатбота хранятся в следующем формате, где `data['welcome_message']['ru']` вернет приветсвенное сообщение на русском языке, а `data['welcome_message']['eng']` - на английском языке:
```yml
welcome_message:
  ru: "Добро пожаловать в GREEN-API чатбот, "
  eng: "Welcome the to the GREEN-API chatbot, "
```
Так же каждый раз, когда пользователь отправляет новое сообщение, поле `ts` обновляется новым временем:
```python
def update_ts(self):
    self.ts = datetime.now()
```
Это сделано для того, чтобы проверять когда пользователь обращался в последний раз. Если прошло более 2 минут с последнего обращения, значит чатбот сбросит авторизацию и язык общения, и начнет чат заново:
```python
if diff > 120:
    self.users.get(chat).set_language(None)
```


## Управление сообщениями
Как и указывает чатбот в ответах, все сообщения отправлены через API. Документацию по методам отправки сообщений можно найти на сайте [green-api.com/docs/api/sending](https://green-api.com/docs/api/sending/).

Что касается получения сообщений, то сообщения вычитываются через HTTP API. Документацию по методам получения сообщений можно найти на сайте [green-api.com/docs/api/receiving/technology-http-api](https://green-api.com/docs/api/receiving/technology-http-api/).

Чатбот использует библиотеку [whatsapp-chatbot-python](https://github.com/green-api/whatsapp-chatbot-python), где уже интегрированы методы отправки и получения сообщений, поэтому сообщения вычитываются автоматически, а отправка обычных текстовых сообщений упрощена. 

Например, чатбот автоматически отправляет сообщение контакту, от которого получил сообщение:
```python
notification.answer(data["select_language"])
```
Однако другие методы отправки можно вызвать напрямую из библиотеки [whatsapp-api-client-python](https://github.com/green-api/whatsapp-api-client-python). Как, например, при отправке контакта:
```python
notification.api.sending.sendContact(
    chatId=notification.chat,
    contact={
        "phoneContact": notification.chat.split("@")[0],
        "firstName": notification.event["senderData"]["senderName"],
    },
```


## Лицензия

Лицензировано на условиях [Creative Commons Attribution-NoDerivatives 4.0 International (CC BY-ND 4.0)](https://creativecommons.org/licenses/by-nd/4.0/).

[LICENSE](https://github.com/green-api/whatsapp-demo-chatbot-python/blob/main/LICENCE).
