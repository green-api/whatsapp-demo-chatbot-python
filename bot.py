from yaml import safe_load
from user_manager import Manager
from re import IGNORECASE
from config_loader import get_config
from whatsapp_chatbot_python import (
    BaseStates,
    GreenAPIBot,
    Notification,
    filters,
)


# These parameters are available in the personal cabinet
# https://console.green-api.com/, copy and paste them in the corresponding
# fields

# Do not get rid of quotation marks

# Example of filling personal data:

# ID_INSTANCE = '1101123456'
# API_TOKEN_INSTANCE= 'abcdefghjklmn1234567890oprstuwxyz'

server_config = get_config()

ID_INSTANCE = server_config.user_id
API_TOKEN_INSTANCE = server_config.api_token_id

bot = GreenAPIBot(
    ID_INSTANCE,
    API_TOKEN_INSTANCE,
    raise_errors=False,
    delete_notifications_at_startup=False
)

with open('data.yml', 'r', encoding='utf8') as stream:
    data = safe_load(stream)


class States(BaseStates):
    ACTIVE = 'active'
    LANGUAGE_SET = 'lang_set'


manager = Manager()


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=None)
def message_handler(notification: Notification) -> None:
    notification.state_manager.update_state(notification.sender,
                                            States.ACTIVE.value)
    user = manager.check_user(notification.chat)
    notification.answer(data['select_language'])


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


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.ACTIVE.value,
                    text_message=['2', '/2', '2.', '2 '])
def set_ru(notification: Notification) -> None:
    user = manager.check_user(notification.chat)
    if not user: return message_handler(Notification)
    user.set_language('ru')
    notification.state_manager.update_state(notification.sender,
                                            States.LANGUAGE_SET.value)
    notification.answer(
        f'{data["welcome_message"][user.language]}'
        f'{notification.event["senderData"]["senderName"]}'
        f'! '
        f'{data["menu"][user.language]}'
    )


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


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.LANGUAGE_SET.value,
                    text_message=['2', '/2', '2.', '2 '])
def option_2(notification: Notification) -> None:
    user = manager.check_user(notification.chat)
    if not user: return message_handler(Notification)
    notification.api.sending.sendFileByUrl(
        chatId=notification.chat,
        urlFile=server_config.link_1,
        fileName='corgi.pdf',
        caption=f'{data["send_file_message"][user.language]}'
        f'{data["links"][user.language]["send_file_documentation"]}',
        )


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.LANGUAGE_SET.value,
                    text_message=['3', '/3', '3.', '3 '])
def option_3(notification: Notification) -> None:
    user = manager.check_user(notification.chat)
    if not user: return message_handler(Notification)
    notification.api.sending.sendFileByUrl(
        chatId=notification.chat,
        urlFile=server_config.link_2,
        fileName='corgi.jpg',
        caption=f'{data["send_image_message"][user.language]}'
        f'{data["links"][user.language]["send_file_documentation"]}',
    )


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.LANGUAGE_SET.value,
                    text_message=['4', '/4', '4.', '4 '])
def option_4(notification: Notification) -> None:
    user = manager.check_user(notification.chat)
    if not user: return message_handler(Notification)
    notification.answer(
        f'{data["send_contact_message"][user.language]}'
        f'{data["links"][user.language]["send_contact_documentation"]}'
    )
    notification.api.sending.sendContact(
        chatId=notification.chat,
        contact={
            'phoneContact': notification.chat.split('@')[0],
            'firstName': notification.event['senderData']['senderName'],
        },
    )


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.LANGUAGE_SET.value,
                    text_message=['5', '/5', '5.', '5 '])
def option_5(notification: Notification) -> None:
    user = manager.check_user(notification.chat)
    if not user: return message_handler(Notification)
    notification.answer(
        f'{data["send_location_message"][user.language]}'
        f'{data["links"][user.language]["send_location_documentation"]}'
    )
    notification.api.sending.sendLocation(
        chatId=notification.chat,
        latitude=35.888171,
        longitude=14.440230,
    )


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.LANGUAGE_SET.value,
                    text_message=['stop', 'стоп'])
def stop(notification: Notification) -> None:
    user = manager.check_user(notification.chat)
    if not user: return message_handler(Notification)
    notification.state_manager.update_state(notification.chat, None)
    notification.answer(
        f'{data["stop_message"][user.language]}'
        f'{notification.event["senderData"]["senderName"]}'
        f'!'
    )


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.LANGUAGE_SET.value,
                    text_message=['menu', 'меню'])
def menu_eng(notification: Notification) -> None:
    user = manager.check_user(notification.chat)
    if not user: return message_handler(Notification)
    notification.answer(data['menu'][user.language])


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.ACTIVE.value,
                    regexp=(r'^((?!1|2).)*$', IGNORECASE))
def menu_ru(notification: Notification) -> None:
    user = manager.check_user(notification.chat)
    if not user: message_handler(Notification)
    notification.answer(data['specify_language'])


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.LANGUAGE_SET.value,
                    regexp=(r'^((?![1-5]|menu|меню|stop|стоп|'
                            r'Menu|Меню|Stop|Стоп).)*$',
                            IGNORECASE))
def menu_ru(notification: Notification) -> None:
    user = manager.check_user(notification.chat)
    if not user: message_handler(Notification)
    notification.answer(data['not_recognized_message'][user.language])


bot.run_forever()
