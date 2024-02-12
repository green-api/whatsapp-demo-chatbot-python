import requests
from yaml import safe_load
from user_manager import Manager, User
from re import IGNORECASE
from whatsapp_chatbot_python import BaseStates, GreenAPIBot, Notification, filters
from config_loader import get_config
from whatsapp_api_client_python.response import Response


# These parameters are available in the personal cabinet
# https://console.green-api.com/, copy and paste them in the corresponding
# fields

# Do not get rid of quotation marks

# Example of filling personal data:

# ID_INSTANCE = '1101123456'
# API_TOKEN_INSTANCE= 'abcdefghjklmn1234567890oprstuwxyz'


def write_apology(notification: Notification) -> None:
    notification.answer(
        message="We are sorry, an error occured while processing your request")


server_config = get_config()

ID_INSTANCE: str = 'ID_INSTANCE'
API_TOKEN_INSTANCE: str = 'API_TOKEN_INSTANCE'

bot = GreenAPIBot(
    ID_INSTANCE,
    API_TOKEN_INSTANCE,
    raise_errors=False,
    delete_notifications_at_startup=False
)

with open('data.yml', 'r', encoding='utf8') as stream:
    data = safe_load(stream)


class States(BaseStates):
    ACTIVE: str = 'active'
    LANGUAGE_SET: str = 'lang_set'
    WAITING_RESPONSE: str = 'waiting_response'
    NOT_ACTIVE: str = 'not_active'


manager: Manager = Manager()


@bot.router.message(type_message=filters.TEXT_TYPES, state=None)
@bot.router.message(type_message=filters.TEXT_TYPES, state=States.NOT_ACTIVE.value)
def message_handler(notification: Notification) -> None:
    try:
        notification.state_manager.update_state(
            notification.sender,
            States.ACTIVE.value
        )
        notification.answer(data['select_language'])
    except Exception:
        write_apology(notification)


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.ACTIVE.value,
                    regexp=(r'^[.\s]?[1-5][.\s]?$'))
def set_language(notification: Notification) -> None:
    try:
        user: User | None = manager.check_user(notification.chat)
        if not user:
            return message_handler(Notification)

        language_dict = {
            '1': 'en',
            '2': 'kz',
            '3': 'ru',
            '4': 'es',
            '5': 'he',
        }

        text_message: str = notification.message_text
        num: str = str(next(char for char in text_message if char.isdigit()))
        selected_language: str = language_dict[num]
        
        user.set_language(selected_language)
        notification.state_manager.update_state(
            notification.sender, States.LANGUAGE_SET.value)
        
        landing_image: str = "media/welcome_ru.png" if selected_language in [
            'kz', 'ru'] else "media/welcome_en.png"
        
        notification.answer_with_file(
            caption=f'{data["welcome_message"][user.language]}'
            f'*{notification.event["senderData"]["senderName"]}*'
            f'! '
            f'{data["menu"][user.language]}',
            file=landing_image,
            file_name="welcome.png"
        )
    except Exception:
        write_apology(notification)


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.LANGUAGE_SET.value,
                    text_message=['1', '/1', '1.', '1 '])
def option_1(notification: Notification) -> None:
    try:
        user: User | None = manager.check_user(notification.chat)
        if not user:
            return message_handler(Notification)
        notification.answer(
            f'{data["send_text_message"][user.language]}'
            f'{data["links"][user.language]["send_text_documentation"]}'
        )
    except Exception:
        write_apology(notification)


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.LANGUAGE_SET.value,
                    text_message=['2', '/2', '2.', '2 '])
def option_2(notification: Notification) -> None:
    try:
        user = manager.check_user(notification.chat)
        if not user:
            return message_handler(Notification)
        url_file: str = server_config.link_pdf
        notification.answer_with_file(
            urlFile=url_file,
            fileName='corgi.pdf',
            caption=f'{data["send_file_message"][user.language]}'
            f'{data["links"][user.language]["send_file_documentation"]}',
        )
    except Exception:
        write_apology(notification)


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.LANGUAGE_SET.value,
                    text_message=['3', '/3', '3.', '3 '])
def option_3(notification: Notification) -> None:
    try:
        user = manager.check_user(notification.chat)
        if not user:
            return message_handler(Notification)
        url_file: str = server_config.link_jpg
        notification.answer_with_file(
            urlFile=url_file,
            fileName='corgi.jpg',
            caption=f'{data["send_image_message"][user.language]}'
            f'{data["links"][user.language]["send_file_documentation"]}',
        )
    except Exception:
        write_apology(notification)


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.LANGUAGE_SET.value,
                    text_message=['4', '/4', '4.', '4 '])
def option_4(notification: Notification) -> None:
    try:
        user = manager.check_user(notification.chat)
        if not user:
            return message_handler(Notification)
        url_file: str = server_config.link_audio_en
        if user.language in ["kz", "ru"]:
            url_file: str = server_config.link_audio_ru
        notification.answer(
            f'{data["send_audio_message"][user.language]}'
            f'{data["links"][user.language]["send_file_documentation"]}',
        )
        notification.answer_with_file(
            urlFile=url_file,
            fileName='green-api.wov'
        )
    except Exception:
        write_apology(notification)


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.LANGUAGE_SET.value,
                    text_message=['5', '/5', '5.', '5 '])
def option_5(notification: Notification) -> None:
    try:
        user = manager.check_user(notification.chat)
        if not user:
            return message_handler(Notification)
        url_file: str = server_config.link_video_en
        if user.language in ["kz", "ru"]:
            url_file: str = server_config.link_video_ru
        notification.answer_with_file(
            urlFile=url_file,
            fileName='green-api.mp4',
            caption=f'{data["send_video_message"][user.language]}'
            f'{data["links"][user.language]["send_file_documentation"]}',
        )
    except Exception:
        write_apology(notification)


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.LANGUAGE_SET.value,
                    text_message=['6', '/6', '6.', '6 '])
def option_6(notification: Notification) -> None:
    try:
        user: User | None = manager.check_user(notification.chat)
        if not user:
            return message_handler(Notification)
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
    except Exception:
        write_apology(notification)


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.LANGUAGE_SET.value,
                    text_message=['7', '/7', '7.', '7 '])
def option_7(notification: Notification) -> None:
    try:
        user: User | None = manager.check_user(notification.chat)
        if not user:
            return message_handler(Notification)
        notification.answer(
            f'{data["send_location_message"][user.language]}'
            f'{data["links"][user.language]["send_location_documentation"]}'
        )
        notification.api.sending.sendLocation(
            chatId=notification.chat,
            latitude=35.888171,
            longitude=14.440230,
        )
    except Exception:
        write_apology(notification)


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.LANGUAGE_SET.value,
                    text_message=['8', '/8', '8.', '8 '])
def option_8(notification: Notification) -> None:
    try:
        user: User | None = manager.check_user(notification.chat)
        if not user:
            return message_handler(Notification)
        notification.answer(
            f'{data["send_poll_message"][user.language]}'
            f'{data["links"][user.language]["send_poll_documentation"]}'
        )
        notification.answer_with_poll(
            message=f'{data["poll_question"][user.language]}',
            options=[
                {"optionName": f'{data["poll_option_1"][user.language]}'},
                {"optionName": f'{data["poll_option_2"][user.language]}'},
                {"optionName": f'{data["poll_option_3"][user.language]}'}
            ],
            multiple_answers=False
        )
    except Exception:
        write_apology(notification)


@bot.router.poll_update_message()
def polls_handler(notification: Notification) -> None:
    try:
        user: User | None = manager.check_user(notification.chat)
        if not user:
            return message_handler(Notification)
        votes: list[dict[str, str]
                    ] = notification.event["messageData"]["pollMessageData"]["votes"]

        for vote_data in votes:
            voters = vote_data["optionVoters"]
            if voters:
                option_name = vote_data["optionName"]
                if option_name == f"{data["poll_option_1"][user.language]}":
                    notification.answer(
                        f'{data["poll_answer_1"][user.language]}')
                elif option_name == f"{data["poll_option_2"][user.language]}":
                    notification.answer(
                        f'{data["poll_answer_2"][user.language]}')
                elif option_name == f"{data["poll_option_3"][user.language]}":
                    notification.answer(
                        f'{data["poll_answer_3"][user.language]}')
    except Exception:
        write_apology(notification)


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.LANGUAGE_SET.value,
                    text_message=['9', '/9', '9.', '9 '])
def option_9(notification: Notification) -> None:
    try:
        user: User | None = manager.check_user(notification.chat)
        if not user:
            return message_handler(Notification)
        notification.answer(
            f'{data["get_avatar_message"][user.language]}'
            f'{data["links"][user.language]["get_avatar_documentation"]}'
        )
        response: Response = notification.api.serviceMethods.getAvatar(
            notification.chat)
        if response.data["urlAvatar"]:
            mime_type = requests.head(
                response.data["urlAvatar"]).headers.get('content-type')
            extension = mime_type.split('/')[-1]
            notification.answer_with_file(
                urlFile=response.data["urlAvatar"],
                fileName="your_avatar." + extension,
                caption=f'{data["avatar_found"][user.language]}'
            )
        else:
            notification.answer(
                notification.chat, f'{data["avatar_not_found"][user.language]}')
    except Exception:
        write_apology(notification)


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.LANGUAGE_SET.value,
                    text_message=['10', '/10', '10.', '10 '])
def option_10(notification: Notification) -> None:
    try:
        user: User | None = manager.check_user(notification.chat)
        if not user:
            return message_handler(Notification)
        notification.answer(
            f'{data["send_link_message_preview"][user.language]}'
            f'{data["links"][user.language]["send_link_documentation"]}',
            linkPreview=True
        )
        notification.answer(
            f'{data["send_link_message_no_preview"][user.language]}'
            f'{data["links"][user.language]["send_link_documentation"]}',
            linkPreview=False
        )
    except Exception:
        write_apology(notification)

# To add user to a group that user's number must be in your phone numbers contact list!
# Attempt to add user who is not included in your contact list will result
# in a group without the targeted user.


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.LANGUAGE_SET.value,
                    text_message=['11', '/11', '11.', '11 '])
def option_11(notification: Notification) -> None:
    try:
        user: User | None = manager.check_user(notification.chat)
        if not user:
            return message_handler(Notification)
        notification.answer(
            f'{data["add_to_contact"][user.language]}'
        )
        bot_number: int = int(
            bot.api.account.getSettings().data["wid"].split("@")[0])
        notification.api.sending.sendContact(
            chatId=notification.chat,
            contact={
                'phoneContact': bot_number,
                'firstName': data["bot_name"][user.language],
            },
        )
        notification.state_manager.update_state(
            notification.sender, States.WAITING_RESPONSE.value)
    except Exception:
        write_apology(notification)


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.WAITING_RESPONSE.value,
                    regexp=(r'^[.\s]?1[.\s]?$',
                            IGNORECASE))
def option_11_1(notification: Notification) -> None:
    try:
        user: User | None = manager.check_user(notification.chat)
        if not user:
            return message_handler(Notification)
        notification.state_manager.update_state(
            notification.sender, States.LANGUAGE_SET.value)
        group_response: Response = notification.api.groups.createGroup(
            f'{data["group_name"][user.language]}',
            [notification.event["senderData"]["chatId"],
                bot.api.account.getSettings().data["wid"]]
        )
        if group_response.data["created"]:
            group_picture_response: Response = notification.api.groups.setGroupPicture(
                f'{group_response.data["chatId"]}',
                "media/green_api.jpg"
            )
            if group_picture_response.data["setGroupPicture"]:
                notification.api.sending.sendMessage(
                    f'{group_response.data["chatId"]}',
                    f'{data["send_group_message"][user.language]}'
                    f'{data["links"][user.language]["groups_documentation"]}',
                )
            else:
                notification.api.sending.sendMessage(
                    f'{group_response.data["chatId"]}',
                    f'{data["send_group_message_set_picture_false"]
                        [user.language]}'
                    f'{data["links"][user.language]["groups_documentation"]}',
                )
            notification.answer(
                f'{data["group_created_message"][user.language]}'
                f'{group_response.data["groupInviteLink"]}'
            )
    except Exception:
        write_apology(notification)


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.WAITING_RESPONSE.value,
                    regexp=(r'^[.\s]?0[.\s]?$',
                            IGNORECASE))
def option_11_0(notification: Notification) -> None:
    try:
        user: User | None = manager.check_user(notification.chat)
        if not user:
            return message_handler(Notification)
        notification.state_manager.update_state(
            notification.sender, States.LANGUAGE_SET.value)
        landing_image: str = "media/welcome_ru.png" if user.language in [
            'kz', 'ru'] else "media/welcome_en.png"
        notification.answer_with_file(
            caption=f'{data["menu"][user.language]}',
            file=landing_image,
            file_name="welcome.png"
        )
    except Exception:
        write_apology(notification)


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.LANGUAGE_SET.value,
                    text_message=['12', '/12', '12.', '12 '])
def option_12(notification: Notification) -> None:
    try:
        user: User | None = manager.check_user(notification.chat)
        if not user:
            return message_handler(Notification)
        notification.answer(
            f'{data["send_quoted_message"][user.language]}'
            f'{data["links"][user.language]
                ["send_quoted_message_documentation"]}',
            quotedMessageId=notification.event["idMessage"]
        )
    except Exception:
        write_apology(notification)


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.LANGUAGE_SET.value,
                    text_message=['13', '/13', '13.', '13 '])
def option_13(notification: Notification) -> None:
    try:
        user: User | None = manager.check_user(notification.chat)
        if not user:
            return message_handler(Notification)
        notification.answer_with_file(
            file="media/about.jpg",
            file_name="about.jpg",
            caption=(f'{data["about_python_chatbot"][user.language]}'
            f'{data["link_to_docs"][user.language]}'
            f'{data["links"][user.language]["chatbot_documentation"]}'
            f'{data["link_to_source_code"][user.language]}'
            f'{data["links"][user.language]["chatbot_source_code"]}'
            f'{data["link_to_green_api"][user.language]}'
            f'{data["links"][user.language]["greenapi_website"]}'
            f'{data["link_to_console"][user.language]}'
            f'{data["links"][user.language]["greenapi_console"]}'
            f'{data["link_to_youtube"][user.language]}'
            f'{data["links"][user.language]["youtube_channel"]}')
        )
    except Exception:
        write_apology(notification)


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.LANGUAGE_SET.value,
                    text_message=['stop', 'стоп', 'Stop', 'Стоп', '0'])
def stop(notification: Notification) -> None:
    try:
        user: User | None = manager.check_user(notification.chat)
        if not user:
            return message_handler(Notification)
        notification.state_manager.update_state(
            notification.chat, States.NOT_ACTIVE.value)
        notification.answer(
            f'{data["stop_message"][user.language]}'
            f'*{notification.event["senderData"]["senderName"]}*'
            f'!'
        )
    except Exception:
        write_apology(notification)


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.LANGUAGE_SET.value,
                    text_message=['menu', 'меню', 'Menu', 'Меню'])
def menu(notification: Notification) -> None:
    try:
        user: User | None = manager.check_user(notification.chat)
        if not user:
            return message_handler(Notification)
        landing_image: str = "media/welcome_ru.png" if user.language in [
            'kz', 'ru'] else "media/welcome_en.png"
        notification.answer_with_file(
            caption=f'{data["welcome_message"][user.language]}'
            f'*{notification.event["senderData"]["senderName"]}*'
            f'! '
            f'{data["menu"][user.language]}',
            file=landing_image,
            file_name="welcome.png"
        )
    except Exception:
        write_apology(notification)


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.ACTIVE.value,
                    regexp=(r'^(?![.\s]?[1-5][.\s]?$).*', IGNORECASE))
def not_recognized_message1(notification: Notification) -> None:
    try:
        user: User | None = manager.check_user(notification.chat)
        if not user:
            message_handler(Notification)
        notification.answer(data['specify_language'])
    except Exception:
        write_apology(notification)


@bot.router.message(type_message=filters.TEXT_TYPES,
                    state=States.LANGUAGE_SET.value,
                    regexp=(r'^(?!(?:[0-9]|10|11|12|13|menu|меню|stop|стоп)$).*',
                            IGNORECASE))
def not_recognized_message2(notification: Notification) -> None:
    try:
        user: User | None = manager.check_user(notification.chat)
        if not user:
            message_handler(Notification)
        notification.answer(data['not_recognized_message'][user.language])
    except Exception:
        write_apology(notification)


bot.run_forever()
