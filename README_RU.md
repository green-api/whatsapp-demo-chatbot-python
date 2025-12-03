# whatsapp-demo-chatbot-python  

![](https://img.shields.io/badge/license-CC%20BY--ND%204.0-green)  

- [Documentation in English](https://github.com/green-api/whatsapp-demo-chatbot-python/blob/main/README.md).  

Демонстрационная версия Whatsapp чатбота основанного на API сервиса [GREEN-API](https://green-api.com). 
При помощи API чатбот отправляет текстовые сообщения, файлы, изображения, музыку, видео, контакты, геолокацию, проводит опросы, запрашивает аватар, отправляет ссылки, создает группу с ботом, цитирует сообщение.  

## Содержание
* [Установка среды для запуска чатбота](#установка-среды-для-запуска-чатбота)  
* [Авторизация в GREEN-API](#авторизация-в-green-api)  
* [Запуск чатбота](#запуск-чатбота)  
* [Как запустить чатбота локально в debug-режиме](#как-запустить-чатбота-локально-в-debug-режиме)
* [Настройка чатбота](#настройка-чатбота)  
* [Использование](#использование)  
* [Структура кода](#структура-кода)  
* [Управление сообщениями](#управление-сообщениями)  

## Установка среды для запуска чатбота  

Для запуска чатбота необходимо иметь установленный интерпретатор Python. На Linux & MacOS он уже установлен. Для Windows скачайте последнюю стабильную версию с [официального сайта](https://www.python.org/), запустите установщик и следуйте рекомендациям.

Проверьте версию Python, для этого откройте командную строку (PowerShell - для Windows) и введите запрос:

```
python --version
```
Ответом на введенный запрос должна быть версия Python в следующем формате:

```
Python 3.N.N
```

у вас должен быть Python версии 3.8 и выше.

Сделайте копию чат бота с помощью:
```
git clone https://github.com/green-api/whatsapp-demo-chatbot-python.git
```

Или скачайте архив [whatsapp-demo-chatbot-python](https://github.com/green-api/whatsapp-demo-chatbot-python).

Перейдите в папку с чатботом в командной строке и установите необходимые библиотеки Python. Убедитесь, что у вас установлен пакетный менеджер [pip](https://pip.pypa.io/en/stable/).

Перечень необходимых библиотек находится в файле requirements.txt. Выполните следующую команду для их установки:  
```
python -m pip install -r requirements.txt
```  
Среда и необходимые библиотеки установлены. Можно приступить к настройке и запуска чатбота на вашем аккаунте Whatsapp.  

## Авторизация в GREEN-API  

Для того, чтобы настроить чатбот на своем аккаунте Whatsapp, Вам необходимо перейти в [личный кабинет](https://console.green-api.com/) и зарегистрироваться. Для новых пользователей предоставлена [инструкция](https://green-api.com/docs/before-start/) для настройки аккаунта и получения необходимых для работы чатбота параметров, а именно:  
```bash
idInstance
apiTokenInstance
```
Не забудьте включить все уведомления в настройках инстанса, чтобы чатбот мог сразу начать принимать сообщения.  

## Запуск чатбота  

Бота можно запустить на сервере или локально. Для локального развертывания необходимо либо включить DEBUG MODE, либо запустить локальный сервер для передачи необходимых данных.  

Файл конфигурации *.env* находится в папке *config*. При получении данных с сервера конфигурационный файл имеет вид:

```
active_profile=GreenAPI
spring_cloud_config_uri=http://localhost:8000
```

Где active_profile - идентификатор вашего профиля, в виде значений принимает строку.
spring_cloud_config_uri - адрес до сервера с указание порта, откуда приходит json c указанием параметров.

Можете написать небольшой локальный сервер для передачи данных Вашему боту.

Пример сервера:
```python3
#!/usr/bin/env python3

from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
import json

class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps({
            'user_id': 'Ваш ID',
            'api_token_id': 'ВАШ ТОКЕН',
            'link_pdf': 'url ССЫЛКА НА ФАЙЛ',
            'link_jpg': 'url ССЫЛКА НА картинку',
            'link_audio_ru': 'url ССЫЛКА НА аудио файл',
            'link_video_ru': 'url ССЫЛКА НА видео файл',
            'link_audio_en': 'url ССЫЛКА НА аудио файл',
            'link_video_en': 'url ССЫЛКА НА видео файл'
        }).encode())
        return

if __name__ == '__main__':
    server = HTTPServer(('localhost', 8000), RequestHandler)
    print('Starting server at http://localhost:8000')
    server.serve_forever()
```
Введите необходимые значения в GET запрос. Запустите сначала сервер, а потом в другой консоли запустите вашего бота.

```
python bot.py
```
Данный запрос запустит работу чатбота. Процесс начинается с инициализации чатбота, которая включает в себя изменение настроек связанного инстанса.

В библиотеке [whatsapp-chatbot-python](https://github.com/green-api/whatsapp-chatbot-python) прописан механизм изменения настроек инстанса методом [SetSettings](https://green-api.com/docs/api/account/SetSettings/), который запускается при включении чатбота.

Все настройки по получению уведомлений выключены по умолчанию, чатбот включит следующие настройки:
```
"incomingWebhook": "yes",
"outgoingMessageWebhook": "yes",
"outgoingAPIMessageWebhook": "yes",
```
которые отвечают за получение уведомлений о входящих и исходящих сообщениях.

Процесс изменения настроек занимает несколько минут, в течение этого времени инстанс будет недоступен. Сообщения отправленные чатботу в это время не будут обработаны.

После того, как будут применены настройки, произойдет удаление уведомлений о полученных ранее входящих сообщениях. Этот процесс так же прописан в библиотеке [whatsapp-chatbot-python](https://github.com/green-api/whatsapp-chatbot-python) и автоматически запускается после изменения настроек.

Это необходимо для того, чтобы чатбот не начал обрабатывать сообщения со старых чатов.

После того, как изменения настроек и удаление входящих уведомлений будут исполнены, чатбот начнет стандартно отвечать на сообщения. Суммарно этот процесс занимает не больше 5 минут.

Чтобы остановить работу чатбота, наведите курсор на командную строку и используйте сочетание клавиш `Ctrl + C`

### Как запустить чатбота локально в debug-режиме

Для того, чтобы запустить бота локально, используйте переменную окружения `DEBUG=True`. Все прочие необходимые переменные представлены ниже (создайте файл `.env` и вставить свои действительные значения):
```
DEBUG=True
DEBUG_USER_ID=<Your Instance ID>
DEBUG_API_TOKEN_ID=<Your Api token ID>
DEBUG_LINK_PDF=<Full URL string for .pdf file>
DEBUG_LINK_JPG=<Full URL string for .jpg file>
DEBUG_LINK_AUDIO_RU=<Full URL string for .mp3 file (RU)>
DEBUG_LINK_VIDEO_RU=<Full URL string for .mp4 file (RU)>
DEBUG_LINK_AUDIO_EN=<Full URL string for .mp3 file (EN)>
DEBUG_LINK_VIDEO_EN=<Full URL string for .mp4 file (EN)>
LINK_PREVIEW=True

ACTIVE_PROFILE=<Any name>
SPRING_CLOUD_CONFIG_URI=http://localhost:8000
```

Пример ссылки  
```
DEBUG_LINK_JPG="https://google.com/i/db/2022/11/1817828/image.jpg"
```

Значения ACTIVE_PROFILE и SPRING_CLOUD_CONFIG_URI - используются для совместимости.  

Далее чатбот получит доступ к Вашему аккаунту через эти данные:
```python
bot = GreenAPIBot(id_instance, api_token_instance)
```
Сохраните изменения в файле. 
```
python bot.py
```
Данный запрос запустит работу чатбота. Процесс начинается с инициализации чатбота, которая включает в себя изменение настроек связанного инстанса.

## Настройка чатбота
По умолчанию чатбот использует ссылки для выгрузки файлов из сети, однако пользователи могут добавить свои ссылки на файлы, одну для файла любого расширения pdf / docx /... и одну для картинки.

Ссылки должны вести на файлы из облачного хранилища или открытого доступа. Все они либо прописываются непосредственно в файле *.env*, либо передаются по сети.

```
    'link_pdf': 'url ССЫЛКА НА ФАЙЛ',
    'link_jpg': 'url ССЫЛКА НА картинку',
    'link_audio_ru': 'url ССЫЛКА НА аудио файл',
    'link_video_ru': 'url ССЫЛКА НА видео файл',
    'link_audio_en': 'url ССЫЛКА НА аудио файл',
    'link_video_en': 'url ССЫЛКА НА видео файл'
```

Для более глубокой настройки пройдитесь по всем пунктам меню, смотрите в функциях - def main_menu_option_1_handler до main_menu_option_13_handler.  

Все изменения должны быть сохранены, после чего можно запускать чатбот.  

Ссылки должны вести на файлы из облачного хранилища или открытого доступа и прописываются в .env. Текстовая информация содержится в data.yml. На 159-й строке в bot.py находится def main_menu_option_2_handler в функции есть следующий код:
```python
    try:
        sender_lang_code = sender_state_data[LANGUAGE_CODE_KEY]
        second_option_answer_text = (
            f'{answers_data["send_file_message"][sender_lang_code]}'
            f'{answers_data["links"][sender_lang_code]["send_file_documentation"]}'
        )
    except KeyError as e:
        logger.exception(e)
        return
    notification.api.sending.sendFileByUrl(
        notification.chat,
        config.link_pdf,
        "corgi.pdf",
        caption=second_option_answer_text,
```
Можете настроить имя для вашего файла.  

Таким же образом введите ссылку и название для картинки на 221-й строке:
```python
    notification.api.sending.sendFileByUrl(
        notification.chat,
        config.link_jpg,
        "corgi.jpg",
        caption=third_option_answer_text,
    )
```
Все изменения должны быть сохранены, после чего можно запускать чатбот. Для запуска чатбота вернитесь к [пункту 3](#запуск-чатбота).

## Использование  
Если предыдущие шаги были выполнены, то на вашем аккаунте Whatsapp должен работать чатбот. Важно помнить, что вы должны быть авторизованы в [личном кабинете](https://console.green-api.com/).

Теперь можно отправлять сообщения чатботу!

Чатбот откликнется на любое сообщение отправленное на аккаунт.
Так как чатбот поддерживает 5 языков -  English, Қазақша, Русский, Español, עברית.
Прежде чем поприветствовать собеседника, чатбот попросит выбрать язык общения:
```
  *1* - English
  *2* - Қазақша
  *3* - Русский
  *4* - Español
  *5* - עברית
```
Отправьте от 1 до 5, чтобы выбрать язык для дальнейшего общения. После того, как вы отправите 3, чатбот пришлет приветственное сообщение на русском языке:
```
GREEN API предоставляет отправку данных следующих видов.  

Выберите цифру из списка, чтобы проверить как работает метод отправки!

*1*. Текстовое сообщение 📩
*2*. Файл 📋
*3*. Картинка 🖼\
*4*. Аудио 🎵
*5*. Видео 📽
*6*. Контакт 📱
*7*. Геолокация 🌎
*8*. Опрос ✔
*9*. Получить картинку моего аватара 👤
*10*. Отправить ссылку 🔗
*11*. Создать группу с ботом 👥
*12*. Цитировать сообщение ©️
*13*. О PYTHON GREEN API чат-боте 🦎
*14.* 🔥 Разговор с ChatGPT 🤖  
*15.* Интерактивные кнопки 📌
*16.* Уведомление о наборе текстового сообщения ✒️
*17.* Уведомление о записи аудиосообщения 🎙️

Чтобы вернуться в начало напишите *стоп* или *0*
```
Выбрав число из списка и отправив его, чатбот ответит каким API был отправлен данный тип сообщения и поделится ссылкой на информацию об API.

Например, отправив 1, пользователь получит в ответ:
```
Это сообщение отправлено через sendMessage метод

Чтобы узнать как работает метод, пройдите по ссылке
https://green-api.com/docs/api/sending/SendMessage/
```
Если отправить что-то помимо чисел 1-17, то чатбот лаконично ответит:
```
Извините, я не совсем вас понял, напишите меню, чтобы посмотреть возможные опции
```
Так же пользователь может вызвать меню, отправив сообщение содержащее "меню". И отправив "стоп", пользователь завершит беседу с чатботом и получит сообщение:
```
Спасибо за использование чатбота GREEN-API, пользователь!
```

## Структура кода

Функциональная часть чатбота находится в файле `bot.py`.
Здесь импортируется класс чатбота `GreenAPIBot` и входящее уведомление `Notification` для обработки сообщений:
```python
from whatsapp_chatbot_python import GreenAPIBot, Notification
```
Инициализация чатбота происходит на 31-й строке:
```python
bot = GreenAPIBot(id_instance, api_token_instance)
```
Каждое сообщение отправленное чатботу обрабатывается на 45-й строке:
```python
@bot.router.message(type_message=TEXT_TYPES, state=None)
@debug_profiler(logger=logger)
def initial_handler(notification: Notification) -> None:
```  

Обработчик получает сообщения через входящие уведомления типа [webhook](https://green-api.com/docs/api/receiving/notifications-format/incoming-message/Webhook-IncomingMessageReceived/).
Проверив данные о пользователе, который отправил сообщение, чатбот сохраняет отправителя используя библиотеку **internal/utils.py**.

Возвращаясь к файлу `bot.py`, после того, как пользователь отправит первое сообщение чатботу, чатбот проверяет есть ли данный пользователь в списке пользователей. Если нет, то новый пользователь создается.

Потом, чатбот ставит статус авторизации данного пользователя на `True`, чтобы обозначить что данный чат активен и просит пользователя выбрать язык общения:
```python
def initial_handler(notification: Notification) -> None:
    sender_state_data_updater(notification)
    notification.answer(answers_data["select_language"])
```
```notification.answer()``` это функция библиотеки чатбота, которая проверяет данные о пользователе из входящего уведомления и отправляет ответ данному пользователю. ```data['select_language']``` это один из текстовых ответов чатбота, приготовленных заранее:
```
  *1* - English
  *2* - Қазақша
  *3* - Русский
  *4* - Español
  *5* - עברית
```
Пользователь отправляет от 1 до 5 , тем самым выбрав язык общения с чатботом.

Чатбот принимает входящее уведомление и видит, что чат с данным пользователем активен проверив статус авторизации. После этого чатбот передает входящее уведомление в локальную функцию `chosen_language_code`, устанавливает язык общения с пользователем:
```python
    try:
        answer_text = (
            f'{answers_data["welcome_message"][chosen_language_code]}'
            f'*{notification.event["senderData"]["senderName"]}*!'
            f'{answers_data["menu"][chosen_language_code]}'
        )
```
Все полученные сообщения чатбот избавляет от лишних символов, чтобы если пользователь ответит "/1" или допустит лишний пробел, чатбот все равно мог распознать его, для этого используется regxp.

После того, как установлен язык общения, все входящие уведомления переходят к функции `options`, которые отвечают на команды 1-13, стоп, меню.

Например, если пользователь отправит 1, следующий код будет запущен:
```python
    try:
        sender_lang_code = sender_state_data[LANGUAGE_CODE_KEY]
        first_option_answer_text = (
            f'{answers_data["send_text_message"][sender_lang_code]}'
            f'{answers_data["links"][sender_lang_code]["send_text_documentation"]}'
        )
```
и отправит следующий ответ пользователю:  
```
Это сообщение отправлено через sendMessage метод
Чтобы узнать, как работает метод, пройдите по ссылке
https://green-api.com/docs/api/sending/SendMessage/
```
Все ответы чатбота хранятся в файле `data.yml` и загружены в `bot.py`:
```python
YAML_DATA_RELATIVE_PATH = "config/data.yml"

with open(YAML_DATA_RELATIVE_PATH, encoding="utf8") as f:
    answers_data = safe_load(f)
```
Ответы чатбота хранятся в следующем формате, где `data['welcome_message']['ru']` вернет приветственное сообщение на русском языке, а `data['welcome_message']['eng']` - на английском языке:
```yml
welcome_message:
  en: "Welcome the to the GREEN API chatbot, "
  kz: "GREEN API чат-ботына қош келдіңіз, "
  ru: "Добро пожаловать в GREEN API чат-бот, "
  es: "Bienvenido al chatbot GREEN API, "
  he: "ברוכים הבאים לצ'אטבוט GREEN API, "
```
Так же каждый раз, когда пользователь отправляет новое сообщение, поле ```current_last_interaction_ts``` обновляется новым временем:
```python
current_last_interaction_ts = current_sender_state_data[LAST_INTERACTION_KEY]
```
Это сделано для того, чтобы проверять когда пользователь обращался в последний раз. Если прошло более 5 минут с последнего обращения, значит чатбот сбросит авторизацию и язык общения, и начнет чат заново:
```python
 MAX_INACTIVITY_TIME_SECONDS = 300

    if now_ts - current_last_interaction_ts > MAX_INACTIVITY_TIME_SECONDS:
        return sender_state_reset(notification)
```

## Управление сообщениями  
Как и указывает чатбот в ответах, все сообщения отправлены через API. Документацию по методам отправки сообщений можно найти на сайте в разделе [Методы отправки](https://green-api.com/docs/api/sending/).

Что касается получения сообщений, то сообщения вычитываются через HTTP API. Документацию по методам получения сообщений можно найти на [сайте](https://green-api.com/docs/api/receiving/technology-http-api/).

Чатбот использует библиотеку [whatsapp-chatbot-python](https://github.com/green-api/whatsapp-chatbot-python), где уже интегрированы методы отправки и получения сообщений, поэтому сообщения вычитываются автоматически, а отправка обычных текстовых сообщений упрощена.

Например, чатбот автоматически отправляет сообщение контакту, от которого получил сообщение:
```python
notification.answer(answers_data["select_language"])
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

## Интеграция с ChatGPT

Демо чатбот теперь включает интеграцию с ChatGPT (опция 14 в меню), которая позволяет пользователям вести интерактивные беседы с моделями GPT от OpenAI прямо в чате WhatsApp.

### Настройка

Для включения функциональности ChatGPT необходимо настроить API-ключ OpenAI:

1. Получите API-ключ на сайте [OpenAI](https://platform.openai.com/api-keys)
2. Добавьте ключ в переменные окружения или файл `.env`:

```
OPENAI_API_KEY=ваш_api_ключ_openai
```

Если API-ключ OpenAI не настроен, чатбот отобразит сообщение об ошибке, когда пользователь попытается использовать функцию ChatGPT.

### Конфигурация

Интеграция с ChatGPT настраивается при инициализации бота:

```python
gpt_bot = WhatsappGptBot(
    id_instance=config.user_id,
    api_token_instance=config.api_token_id,
    openai_api_key=config.openai_api_key,
    model="gpt-4o",
    system_message="You are a helpful assistant in a WhatsApp chat. Be concise and accurate in your responses.",
    max_history_length=10,
    temperature=0.7
)
```

Вы можете настроить следующие параметры:
- `model`: Модель OpenAI для использования (по умолчанию "gpt-4o")
- `system_message`: Системное сообщение, которое определяет поведение ChatGPT
- `max_history_length`: Количество предыдущих сообщений, сохраняемых в контексте
- `temperature`: Управление "случайностью" в ответах (от 0.0 до 1.0)

### Использование

Пользователи могут получить доступ к функции ChatGPT, отправив "14" в главном меню. Чатбот перейдет в специальный режим разговора с ChatGPT, где все сообщения будут пересылаться модели GPT для обработки.

Чтобы выйти из разговора с ChatGPT и вернуться в главное меню, пользователи могут написать одно из следующих ключевых слов (в зависимости от выбранного языка):
- Английский: "exit", "menu", "stop", "back"
- Русский: "выход", "меню", "стоп", "назад"
- Казахский: "шығу", "мәзір", "тоқта", "артқа", "menu", "меню"
- Испанский: "salir", "menú", "parar", "atrás", "menu", "exit"
- Иврит: "יציאה", "תפריט", "עצור", "exit", "menu", "חזור"

### Ограничения

- Использование API может повлечь за собой расходы в зависимости от вашего плана подписки OpenAI
- Время ответа может варьироваться в зависимости от задержки API OpenAI и скорости вашего интернет-соединения

## Лицензия  
Лицензировано на условиях [Creative Commons Attribution-NoDerivatives 4.0 International (CC BY-ND 4.0)](https://creativecommons.org/licenses/by-nd/4.0/).

[LICENSE](https://github.com/green-api/whatsapp-demo-chatbot-python/blob/main/LICENCE).  
