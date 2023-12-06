from datetime import datetime

from whatsapp_chatbot_python import GreenAPIBot, Notification, filters
from yaml import safe_load

from user import User
from config_loader import get_config


# These parameters are available in the personal cabinet https://console.green-api.com/, copy and paste them in the corresponding fields
# Do not get rid of quotation marks

# Example of filling personal data:

# id_instance = '1101123456'
# api_token_instance = 'abcdefghjklmn1234567890oprstuwxyz'

server_config = get_config()

id_instance = server_config.user_id
api_token_instance = server_config.api_token_id

bot = GreenAPIBot(id_instance, api_token_instance)

with open("data.yml", 'r', encoding='utf8') as stream:
    data = safe_load(stream)


@bot.router.message(type_message=filters.TEXT_TYPES)
def message_handler(notification: Notification) -> None:
    user = User.check(notification.chat)
    user.last_updated = datetime.now()

    if not user.authorized:
        user.authorize()
        notification.answer(data["select_language"])
    else:
        set_language(notification, user)


def set_language(notification: Notification, user: User):
    if not user.language:
        message = "".join(
            i
            for i in notification.message_text
            if i not in ["/", ".", " ", "<", ">", "[", "]"]
        ).lower()

        if message == "1":
            user.set_language("eng")
            notification.answer(
                f'{data["welcome_message"][user.language]}'
                f'{notification.event["senderData"]["senderName"]}'
                f'! '
                f'{data["menu"][user.language]}'
            )

        elif message == "2":
            user.set_language("ru")
            notification.answer(
                f'{data["welcome_message"][user.language]}'
                f'{notification.event["senderData"]["senderName"]}'
                f'! '
                f'{data["menu"][user.language]}'
            )

        else:
            notification.answer(data["specify_language"])
    else:
        options(notification, user)


def options(notification: Notification, user: User):
    message = "".join(
        i
        for i in notification.message_text
        if i not in ["/", ".", " ", "<", ">", "[", "]"]
    ).lower()
    if message == "1":
        notification.answer(
            f'{data["send_text_message"][user.language]}'
            f'{data["links"][user.language]["send_text_documentation"]}'
        )
    elif message == "2":
        notification.api.sending.sendFileByUrl(
            chatId=notification.chat,
            urlFile=server_config.link_1,
            fileName="corgi.pdf",
            caption=f'{data["send_file_message"][user.language]}'
                    f'{data["links"][user.language]["send_file_documentation"]}',
        )
    elif message == "3":
        notification.api.sending.sendFileByUrl(
            chatId=notification.chat,
            urlFile=server_config.link_2,
            fileName="corgi.jpg",
            caption=f'{data["send_image_message"][user.language]}'
                    f'{data["links"][user.language]["send_file_documentation"]}',
        )
    elif message == "4":
        notification.answer(
            f'{data["send_contact_message"][user.language]}'
            f'{data["links"][user.language]["send_contact_documentation"]}'
        )
        notification.api.sending.sendContact(
            chatId=notification.chat,
            contact={
                "phoneContact": notification.chat.split("@")[0],
                "firstName": notification.event["senderData"]["senderName"],
            },
        )
    elif message == "5":
        notification.answer(
            f'{data["send_location_message"][user.language]}'
            f'{data["links"][user.language]["send_location_documentation"]}'
        )
        notification.api.sending.sendLocation(
            chatId=notification.chat,
            latitude=35.888171,
            longitude=14.440230,
        )
    elif message in ["stop", "стоп"]:
        lang = user.language
        user.unauthorize()
        notification.answer(
            f'{data["stop_message"][lang]}'
            f'{notification.event["senderData"]["senderName"]}'
            f'!'
        )
    elif message in ["menu", "меню"]:
        notification.answer(data["menu"][user.language])
    else:
        notification.answer(data["not_recognized_message"][user.language])


bot.run_forever()
