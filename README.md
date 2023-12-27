# whatsapp-demo-chatbot-python

![](https://img.shields.io/badge/license-CC%20BY--ND%204.0-green)

- [Документация на русском языке](https://github.com/green-api/whatsapp-demo-chatbot-python/blob/main/README_RU.md).

Simple chatbot created with python based on API service [green-api.com](https://green-api.com/en/).
The chatbot provides a demonstration of APIs available for users - sending messages of texts, images, locations, files, and contacts.


## Table of contents
* [Installation](#installation)
* [Launching a chatbot](#launching-a-chatbot)
* [Setup](#setup)
* [Usage](#usage)
* [Code structure](#code-structure)
* [Message handling](#message-handling)


## Installation
Preparing the python environment to run the project is required. To set up an environment one should go to the [python](https://www.python.org/) official website and download the latest release compatible for the OS. 

This action will download the installer, which one will need to open and start. Follow the guidelines in the installer and complete the installation.

To check if the environment was established correct, run the following command in cmd / bash:
```
python --version
```
The returning statement should contain the version of python installed on your machine similar to:
```
Python 3.N.N
```
After ensuring that environment is set up, copy the project on your local machine by downloading the zip file from [whatsapp-demo-chatbot-python](https://github.com/green-api/whatsapp-demo-chatbot-python) and unpacking it.

Or if one's familiar with distributed version control system s/he can clone the project by running:
```
git clone https://github.com/green-api/whatsapp-demo-chatbot-python.git
```
Open the directory containing the project and call the cmd / bash from the current directory. To do this one must add `cmd` to the path and type in `Enter`.

Then, use the package manager [pip](https://pip.pypa.io/en/stable/) to install the [whatsapp-chatbot-python](https://github.com/green-api/whatsapp-chatbot-python) and other modules required to run the code.

The following command calls the pip package manager and installs the modules to the environment. The package manager is installed in the environment by default.
```
python -m pip install -r requirements.txt
```
Environment for running chatbot is ready, now one must set up and launch the chatbot on the Whatsapp account.


## Launching a chatbot
To use the chatbot on Whatsapp account one must sign up to [personal cabinet](https://console.green-api.com/), as the chatbot is based on the APIs provided. There's a [guideline](https://green-api.com/en/docs/before-start/) available for new users how to set up the account and get parameters for working with API, mainly:
```bash
idInstance
apiTokenInstance
```
After obtaining the mentioned parameters, one has to open the `bot.py` file and fill up the account's parameters with `idInstance` and `apiTokenInstance` values correspondingly in the 23th line. 
Initialization is essential to synchronize with one's Whatsapp account:
```python
ID_INSTANCE = ''
API_TOKEN_INSTANCE = ''
```
Then the chatbot will get access to one's Whatsapp account via these parameters:
```python
bot = GreenAPIBot(
    ID_INSTANCE,
    API_TOKEN_INSTANCE
)
```
Save the changes to the file and run the following command in the cmd / bash from the current directory:
```
python bot.py
```
This command will launch the bot. The process of launching starts with the initialization of the bot, which includes the setting up the associated account.

The parent library of the chatbot [whatsapp-chatbot-python](https://github.com/green-api/whatsapp-chatbot-python) will change the settings of the associated account by calling [SetSettings](https://green-api.com/en/docs/api/account/SetSettings/) API to.

The following settings will turned, namely:
```
"incomingWebhook": "yes",
"outgoingMessageWebhook": "yes",
"outgoingAPIMessageWebhook": "yes",
```
making the instance getting the notifications about the outgoing and incoming messages.

The settings update will take a few minutes, so the associated instance will be unavailable during the time. The messages sent to the chatbot meanwhile will not be processed.

Then there will be deletion of the old notifications, another process invoked by the parent library [whatsapp-chatbot-python](https://github.com/green-api/whatsapp-chatbot-python), which is essential to make sure chatbot will not process the messages from the already opened chats. 

After the initialization is completed, chatbot is ready to answer the messages. The whole process of initialization will take up to 5 minutes.

To stop the chatbot hover the cmd / bash from the current directory and click `Ctrl + C`


## Setup
The chatbot has default values for links to send files and images, but users can change them to their liking. 

To do that, provide one link to the pdf/any other format file and one to jpg. Links can lead to cloud storage or open source. In the 101th line in the bot.py file:
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
Fill url of the file to the `urlFile=''` and give it a name in the `fileName=''`.

Then it should look similar to the following:
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
In the same fashion fill the link and the name for the jpg image in the 120th line
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
All the changes must be saved, then the chatbot can be launched. To see how to launch chatbot return to the [section 2](#launching-a-chatbot)


## Usage
If everything was set up correct, the code is running and the Whatsapp chatbot should be working on the number associated with instance. Importantly, instance must be authorized in the [personal cabinet](https://console.green-api.com/) for code to work.

Let's try to send a message to chatbot!

Any message will invoke the bot to start a conversation.
As bot provides the service on two languages - English and Russian - even before welcoming a user, a choice of language is encouraged:
```
1 - English
2 - Русский
```
Then, one must answer with either 1 or 2 to set up a language of conversation. Type in, for example, 2 to choose English. The welcome message alongside menu pops up in the dialogue:
```
Welcome the to the GREEN-API chatbot, user! GREEN-API provides the following kinds of message services. Type in a number to see how the corresponding method works

1. Text message 📩
2. File 📋
3. Image 🖼
4. Contact 📱
5. Location 🌎

To restart the conversation type stop
```
By typing in item number in menu, the chatbot answers by using specific API assigned for the task and attaches a link for a detailed information page. 

For exapmle, by sending 1 to chatbot the user will get:
```
This message is sent via sendMessage method

If you want to know how the method works, follow the link
https://green-api.com/en/docs/api/sending/SendMessage/
```
By sending anything other from digits 1-5, the chatbot will answer gracefully:
```
Sorry, I cannot understand what you are talking about, type menu to see the available options
```
One also can send a message 'menu' to call back to menu to see the available options. Lastly, by sending 'stop', the user will forcefully stop the conversation and chatbot will send goodbye message:
```
Thank you for using the GREEN-API chatbot, user!
```


## Code structure
The main part of the code is contained within the `bot.py` file. 
It imports the chatbot library, on which the chatbot is based:
```python
from whatsapp_chatbot_python import (
    BaseStates,
    GreenAPIBot,
    Notification,
    filters,
)
```
There is initialization of chatbot on 26th line:
```python
bot = GreenAPIBot(
    ID_INSTANCE,
    API_TOKEN_INSTANCE
)
```
Then, there is router that listens to notifications that is invoked everytime the text message is sent to the chatbot. The messages are processed ruther if they pass through set up filters. For example, every time the user sends a message, the state of the chat is `None`, which is filtered by router:
```python
@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=None)
```
Once the message handler got the notification it retrieves the data from the inside, which is dictionary of type [webhook](https://green-api.com/en/docs/api/receiving/notifications-format/).
Getting the user's data, the chatbot saves that in the object of the same named class. The `user` class is within the `user_manager.py` file and has 2 fields:
```python
@dataclass
class User:
    language: Optional[str] = None
    ts: Optional[datetime] = None
```
The fields correspond to the chosen languagenand timestamp of last interaction with bot. Every field has a role in the logic, which will be explained later.

So, returning to `bot.py`, after the user sends a first message to the chatbot, there's checking if the user has active chat with the bot on the server side. If not, new user is created and the state of the chat is set to `ACTIVE`.
```python
notification.state_manager.update_state(notification.sender,
                                        States.ACTIVE.value)
user = manager.check_user(notification.chat)
notification.answer(data['select_language'])
```
The ```notification.answer()``` is the function of the chatbot library, it takes the parameters of user and sends a text message to the assigned user. The ```data['select_language']``` is the text we prepared for the chatbots answers, which is:
```
"1 - English\n2 - Русский"
```
So, then the user sends either 1 or 2 to set up English or Russian as the text of conversation.

The chatbot sees that user with such number has active chat by checking the filter `state=States.ACTIVE.value`. The function sets the user's language field and sets the value of the state to `state=States.LANGUAGE_SET.value`, letting the bot to know that the language of interaction in this chat is already selected:
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
The text_message filter processes`['1', '/1', '1.', '1 ']` in case the user sent redundant symbols.
After that the chatbot sets state of the chat to `state=States.LANGUAGE_SET.value` and expects commands 1-5 from the user

So, if user sends 1, router will proceed to the following line:
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
And this part of code will send the corresponding message to user:
```
This message is sent via sendMessage method

If you want to know how the method works, follow the link
https://green-api.com/en/docs/api/sending/SendMessage/
```
All the answers are prepared in the `data.yml` file and loaded to the `bot.py` by following:
```python
with open("data.yml", 'r', encoding='utf8') as stream:
    data = safe_load(stream)
```
Then one can access the answers from the data dictionary, which has, for example, `data['welcome_message']['eng']` as the welcome message in English, and `data['welcome_message']['ru']` as in Russian:
```yml
welcome_message:
  ru: "Добро пожаловать в GREEN-API чатбот, "
  eng: "Welcome the to the GREEN-API chatbot, "
```
Lastly, everytime there's a message from user, the timestamp called `ts` is updated:
```python
def update_ts(self):
    self.ts = datetime.now()
```
This must be done in order to compare the time between last timestamp and new one, so if there's time interval more than 2 minutes between ones, the user authorization and language are reset:
```python
if diff > 120:
    self.users.get(chat).set_language(None)
```


## Message handling
As chatbot states, all the messages were sent by API. Documentation of the mentioned methods can be found at [green-api.com/docs/api/sending](https://green-api.com/en/docs/api/sending/).

When it comes to receiving messages, they've been handled by HTTP API. Documentation of the methods of receving messages can be found at [green-api.com/docs/api/receiving/technology-http-api](https://green-api.com/en/docs/api/receiving/technology-http-api/).

The chatbot uses library [whatsapp-chatbot-python](https://github.com/green-api/whatsapp-chatbot-python), where methods of sending and receiving messages is already intergarted, that's why the process of receiving messages is automated, and sending text messages is simplified. 

For example, chatbot answers the person who sent a message by following:
```python
notification.answer(data["select_language"])
```
However, the API can be accessed directly from [whatsapp-api-client-python](https://github.com/green-api/whatsapp-api-client-python), as, for example, when sending a contact:
```python
notification.api.sending.sendContact(
    chatId=notification.chat,
    contact={
        "phoneContact": notification.chat.split("@")[0],
        "firstName": notification.event["senderData"]["senderName"],
    },
```


## License

Licensed under [Creative Commons Attribution-NoDerivatives 4.0 International (CC BY-ND 4.0)](https://creativecommons.org/licenses/by-nd/4.0/) terms. 

Please see file [LICENSE](https://github.com/green-api/whatsapp-demo-chatbot-python/blob/main/LICENCE).
