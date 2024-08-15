# whatsapp-demo-chatbot-python  

![](https://img.shields.io/badge/license-CC%20BY--ND%204.0-green)  

- [Документация на русском языке](https://github.com/green-api/whatsapp-demo-chatbot-python/blob/main/README_RU.md).  

Demo version of Whatsapp chatbot based on API service [GREEN-API](https://green-api.com/en).
Using API, the chatbot sends text messages, files, images, music, videos, contacts, geolocation, surveys, requests an avatar, sends links, creates a group with the bot, and quotes a message.  

## Table of contents
* [Installation](#installation)
* [Authorization in GREEN-API](#authorization-in-green-api)
* [Launching the chatbot](#launching-the-chatbot)
* [Launch the chatbot in debug mode](#launch-the-chatbot-in-debug-mode)
* [Setup](#setup)
* [Usage](#usage)
* [Code structure](#code-structure)
* [Message handling](#message-handling)

## Installation  

To run the chatbot, you need to have the Python interpreter installed. It is already installed on Linux and MacOS. For Windows, download the latest stable version from the [official website](https://www.python.org/), run the installer and follow the recommendations.  

Check the Python version by entering the command line (PowerShell - for Windows) and entering the query:  ``` python --version ```  
The response to the entered query should be the Python version in the following format: ``` Python 3.N.N ```. You must have installed Python version 3.8 or higher.  

Make a copy of the bot chat with ``` git clone https://github.com/green-api/whatsapp-demo-chatbot-python.git ``` or download the archive [whatsapp-demo-chatbot-python](https ://github.com/green-api/whatsapp-demo-chatbot-python).  

The list of necessary libraries is in the requirements.txt file. Run the following command to install them: ``` python -m pip install -r requirements.txt ```. The environment and necessary libraries are installed and ready for running chatbot. You can set up and launch the chatbot on the Whatsapp account.

## Authorization in GREEN-API  

To set up the chatbot on your Whatsapp account you must sign up to [console](https://console.green-api.com/) and register. For new users, [instructions](https://green-api.com/en/docs/before-start/) are provided for setting up an account and obtaining the parameters necessary for the chatbot to work, namely:  
```bash
idInstance
apiTokenInstance
```  

## Launching the chatbot  

The bot can be launched on the server or locally. To start chatbot local deployment, you must enable DEBUG MODE or start a local server to transfer the necessary data.

The configuration file *.env* is located in the *config* directory. When receiving data from the server, the configuration file looks like this:

```
active_profile=GreenAPI
spring_cloud_config_uri=http://localhost:8000
```

Where active_profile is your profile ID, it takes a string as a value.
spring_cloud_config_uri is the address to the server with the port from where JSON with parameters is received.

You can write a small local server to transfer data to your bot.

Server example:

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
            'user_id': 'Your ID',
            'api_token_id': 'Your TOKEN',
            'link_pdf': 'url LINK TO FILE',
            'link_jpg': 'url LINK TO IMAGE',
            'link_audio_ru': 'url LINK TO audio file',
            'link_video_ru': 'url LINK TO video file',
            'link_audio_en': 'url LINK TO audio file',
            'link_video_en': 'url LINK TO video file'
        }).encode())
        return

if __name__ == '__main__':
    server = HTTPServer(('localhost', 8000), RequestHandler)
    print('Starting server at http://localhost:8000')
    server.serve_forever()
```

Enter the required values ​​in the GET request. First, start the server and then start your bot in another console.

```
python bot.py
```
This request will start the chatbot. The process begins with the initialization of the chatbot, which includes changing the settings of the associated instance.

The [whatsapp-chatbot-python](https://github.com/green-api/whatsapp-chatbot-python) library contains a mechanism for changing the instance settings using the [SetSettings](https://green-api.com/en/docs/api/account/SetSettings/) method, which is launched when the chatbot is running.

All settings for receiving notifications are disabled by default, the chatbot turn on the following settings:
```
"incomingWebhook": "yes",
"outgoingMessageWebhook": "yes",
"outgoingAPIMessageWebhook": "yes",
```
which are responsible for receiving notifications about incoming and outgoing messages.  

The settings changing process takes several minutes, the instance will be unavailable during which times. Messages sent to the chatbot during this time will not be processed.  

Then there will be deletion of the old notifications, another process invoked by the parent library [whatsapp-chatbot-python](https://github.com/green-api/whatsapp-chatbot-python), which is essential to make sure chatbot will not process the messages from the already opened chats.

After the initialization is completed, chatbot is ready to answer the messages. The whole process of initialization will take up to 5 minutes.

To stop the chatbot hover the cmd / bash from the current directory and click `Ctrl + C`  

### Launch the chatbot in debug mode  

To run the bot locally, use the environment variable `DEBUG=True`. All other necessary variables are presented below (create a `.env` file and insert your actual values):

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

ACTIVE_PROFILE=<Any name>
SPRING_CLOUD_CONFIG_URI=http://localhost:8000
```

Link example
```
DEBUG_LINK_JPG="https://google.com/i/db/2022/11/1817828/image.jpg"
```

The ACTIVE_PROFILE and SPRING_CLOUD_CONFIG_URI values ​​are used for compatibility.

Then the chatbot will access your account using these details:
```python
bot = GreenAPIBot(id_instance, api_token_instance)
```
Save the changes to the file.

```
python bot.py
```
This request will start the chatbot. The process begins with the initialization of the chatbot, which includes changing the settings of the associated instance.

## Setup  

By default, the chatbot uses links to download files from the network, but users can add their links to files, one for a file of any extension pdf / docx / ... and one for an image.

Links must lead to files from cloud storage or open access. You can write them directly in the *.env* file or transmit them over the network.

```
'link_pdf': 'url LINK TO FILE',
'link_jpg': 'url LINK TO image',
'link_audio_ru': 'url LINK TO audio file',
'link_video_ru': 'url LINK TO video file',
'link_audio_en': 'url LINK TO audio file',
'link_video_en': 'url LINK TO video file'
```

For more in-depth customization, go through all the menu items, see the functions - def main_menu_option_1_handler to main_menu_option_13_handler.

All changes must be saved, after which you can launch the chatbot.

Links must lead to files from cloud storage or open access and are written in .env. Text information is contained in data.yml. On line 159 in bot.py is def main_menu_option_2_handler in the function there is the following code:
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
You can choose the name for your file.

Likewise enter the link and name for the image on line 221:
```python
notification.api.sending.sendFileByUrl(
notification.chat,
config.link_jpg,
"corgi.jpg",
caption=third_option_answer_text,
)
```
All changes must be saved, after which you can launch the chatbot. Return to [step 2](#launching-the-chatbot) to launch the chatbot.  

## Usage  
After completing the previous steps, you can run the chatbot with your Whatsapp account. It is important to remember that you must be logged in to your [console](https://console.green-api.com/).

Now you can send messages to the chatbot!

The chatbot will respond to any message sent to the account.
This chatbot version supports 5 languages ​​- English, Kazakh, Russian, Español, עברית.
Before greeting a user, the chatbot will ask to select the language of communication:
```
*1* - English
*2* - Kazakh
*3* - Russian
*4* - Español
*5* - עברית
```
Send from 1 to 5 to select the language for communication. After you send 3, the chatbot will send a greeting message in Russian:
```
GREEN API provides the following kinds of message services.

Select a number from the list to check how the sending method works!

*1*. Text message 📩
*2*. File 📋
*3*. Image 🖼\
*4*. Audio 🎵
*5*. Video 📽
*6*. Contact 📱
*7*. Location 🌎
*8*. Poll ✔
*9*. Get image of my avatar👤
*10*. Send link 🔗
*11*. Create a group with the bot 👥
*12*. Quote message ©️
*13*. About PYTHON GREEN API chatbot 🦎

To return to the beginning, write *stop* or *0*
```

By selecting a number from the list and sending it, the chatbot will respond to which API sent this type of message and share a link to information about the API.

For example, by sending 1, the user will receive in response:
```
This message was sent via the sendMessage method

To find out how the method works, follow the link
https://green-api.com/docs/api/sending/SendMessage/
```
If you send something other than numbers 1-13, the chatbot will briefly respond:
```
Sorry, I didn't quite understand you, write a menu to see the possible options
```
The user can also call the menu by sending a message containing "menu". And by sending "stop", the user will end the conversation with the chatbot and receive a message:
```
Thank you for using the GREEN-API chatbot, user!
```

## Code structure  
The functional part of the chatbot is in the `bot.py` file.
Here the `GreenAPIBot` chatbot class and the `Notification` incoming notification are imported to handle messages:
```python
from whatsapp_chatbot_python import GreenAPIBot, Notification
```
The chatbot is initialized on line 31:
```python
bot = GreenAPIBot(id_instance, api_token_instance)
```
Each message sent to the chatbot is processed on line 45:
```python
@bot.router.message(type_message=TEXT_TYPES, state=None)
@debug_profiler(logger=logger)
def initial_handler(notification: Notification) -> None:
```

The handler receives messages via incoming notifications of type [webhook](https://green-api.com/en/docs/api/receiving/notifications-format/incoming-message/Webhook-IncomingMessageReceived/).
The chatbot checks the details from the sender and then saves the sender using the **internal/utils.py** library.

Returning to the `bot.py` file, after the user sends the first message to the chatbot, the chatbot checks if the user is already in the list of users. If not, a new user is created.

Then, the chatbot sets the user's authorization status to `True` to indicate that the chat is active and asks the user to select a language for communication:
```python
def initial_handler(notification: Notification) -> None:
sender_state_data_updater(notification)
notification.answer(answers_data["select_language"])
```
```notification.answer()``` is a chatbot library function that checks the user data from the incoming notification and sends a response to the user. ```data['select_language']``` is one of the chatbot's pre-prepared text responses:
```
*1* - English
*2* - Қазақша
*3* - Русский
*4* - Español
*5* - עברית
```
The user sends from 1 to 5 to select the language of communication with the chatbot.

The chatbot receives an incoming notification and sees that the chat with this user is active by checking the authorization status. After that, the chatbot passes the incoming notification to the local function `chosen_language_code`, and sets the language of communication with the user:
```python
try:
answer_text = (
f'{answers_data["welcome_message"][chosen_language_code]}'
f'*{notification.event["senderData"]["senderName"]}*!'
f'{answers_data["menu"][chosen_language_code]}'
)
```
The chatbot removes unnecessary characters from all received messages so that if the user answers "/1" or makes an extra space, the chatbot can still recognize it, for this purpose, regxp is used.

After the communication language is set, all incoming notifications go to the `options` function, which responds to commands 1-13, stop, menu.

For example, if the user sends 1, the following code will be run:
```python
try:
sender_lang_code = sender_state_data[LANGUAGE_CODE_KEY]
first_option_answer_text = (
f'{answers_data["send_text_message"][sender_lang_code]}'
f'{answers_data["links"][sender_lang_code]["send_text_documentation"]}'
)
```
and send the following response to the user:

```
This message is sent via the sendMessage method.
How to the method works, follow the link
https://green-api.com/en/docs/api/sending/SendMessage/
```
All chatbot responses are stored in the `data.yml` file and loaded into `bot.py`:
```python
YAML_DATA_RELATIVE_PATH = "config/data.yml"

with open(YAML_DATA_RELATIVE_PATH, encoding="utf8") as f:
answers_data = safe_load(f)
```
The chatbot responses are stored in the following format, where `data['welcome_message']['ru']` will return a welcome message in Russian, and `data['welcome_message']['eng']` - in English:
```yml
welcome_message:
en: "Welcome the to the GREEN API chatbot, "
kz: "GREEN API chat-bot, "
ru: "Welcome to the GREEN API chat-bot, "
es: "Bienvenido al chatbot GREEN API, "
he: "GREEN API for Chatbots,"
```
Also, every time a user sends a new message, the ```current_last_interaction_ts``` field is updated with a new time:
```python
current_last_interaction_ts = current_sender_state_data[LAST_INTERACTION_KEY]
```
This is done to check when the user connected last time. If more than 5 minutes have passed since the last contact, then the chatbot will reset authorization and language of communication, and start the chat again:
```python
MAX_INACTIVITY_TIME_SECONDS = 300

if now_ts - current_last_interaction_ts > MAX_INACTIVITY_TIME_SECONDS:
return sender_state_reset(notification)
```

## Message handling  
The chatbot indicates in its responses, all messages are sent via API. Documentation on sending methods can be found at [Sending methods](https://green-api.com/en/docs/api/sending/).

As for receiving messages, messages are read via HTTP API. Documentation on receiving methods can be found at [site](https://green-api.com/en/docs/api/receiving/technology-http-api/).

The chatbot uses the [whatsapp-chatbot-python](https://github.com/green-api/whatsapp-chatbot-python) library, which already integrates sending and receiving methods, so messages are read automatically, and sending regular text messages is simplified.

For example, the chatbot automatically sends a message to the contact from whom it received a message:
```python
notification.answer(answers_data["select_language"])
```
However, other sending methods can be called directly from the [whatsapp-api-client-python](https://github.com/green-api/whatsapp-api-client-python) library. For example, when sending a contact:
```python
notification.api.sending.sendContact(
chatId=notification.chat,
contact={
"phoneContact": notification.chat.split("@")[0],
"firstName": notification.event["senderData"]["senderName"],
},
```  

## License

Licensed under [Creative Commons Attribution-NoDerivatives 4.0 International (CC BY-ND 4.0)](https://creativecommons.org/licenses/by-nd/4.0/).

Please see file [LICENSE](https://github.com/green-api/whatsapp-demo-chatbot-python/blob/main/LICENCE).
