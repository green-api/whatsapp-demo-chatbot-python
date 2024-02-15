from os.path import basename
from re import IGNORECASE
from urllib.parse import urlparse

import requests
from whatsapp_api_client_python.API import GreenAPIResponse
from whatsapp_chatbot_python import BaseStates, GreenAPIBot, Notification
from whatsapp_chatbot_python.filters import TEXT_TYPES
from yaml import safe_load

from config_loader import get_config
from user_manager import Manager, User


def send_error_message(notification: Notification) -> None:
    notification.answer(
        "We are sorry, an error occurred while processing your request"
    )


server_config = get_config()

ID_INSTANCE: str = server_config.user_id
API_TOKEN_INSTANCE: str = server_config.api_token_id

bot = GreenAPIBot(
    ID_INSTANCE, API_TOKEN_INSTANCE,
    debug_mode=True, bot_debug_mode=True,

    # https://green-api.com/en/docs/api/account/GetSettings/
    settings={
        "webhookUrl": "",
        "webhookUrlToken": "",
        "delaySendMessagesMilliseconds": 500,
        "markIncomingMessagesReaded": "yes",
        "incomingWebhook": "yes",
        "keepOnlineStatus": "yes",
        "pollMessageWebhook": "yes",
    }
)

with open("config/data.yml", "r", encoding="utf8") as stream:
    data = safe_load(stream)


class States(BaseStates):
    ACTIVE = "ACTIVE"
    LANGUAGE_SET = "LANG_SET"
    WAITING_RESPONSE = "WAITING_RESPONSE"
    NOT_ACTIVE = "NOT_ACTIVE"


manager: Manager = Manager()


@bot.router.message(type_message=TEXT_TYPES, state=None)
@bot.router.message(type_message=TEXT_TYPES, state=States.NOT_ACTIVE.value)
def message_handler(notification: Notification) -> None:
    try:
        notification.state_manager.update_state(
            notification.sender, States.ACTIVE.value
        )

        notification.answer(data["select_language"])
    except Exception:
        send_error_message(notification)


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.ACTIVE.value,
    regexp=r"^[.\s]?[1-5][.\s]?$"
)
def set_language(notification: Notification) -> None:
    try:
        user: User | None = manager.check_user(notification.sender)
        if not user:
            return message_handler(notification)

        language_dict: dict[str, str] = {
            "1": "en",
            "2": "kz",
            "3": "ru",
            "4": "es",
            "5": "he",
        }

        message_text: str = notification.message_text
        num: str = next(char for char in message_text if char.isdigit())
        selected_language: str = language_dict[num]

        user.set_language(selected_language)
        notification.state_manager.update_state(
            notification.sender, States.LANGUAGE_SET.value
        )

        landing_image: str = "media/welcome_ru.png" if selected_language in [
            "kz", "ru"
        ] else "media/welcome_en.png"

        notification.answer_with_file(
            landing_image,
            file_name="welcome.png",
            caption=(
                f'{data["welcome_message"][user.language]}'
                f'*{notification.event["senderData"]["senderName"]}*'
                f'! '
                f'{data["menu"][user.language]}'
            ),
        )
    except Exception:
        send_error_message(notification)


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.LANGUAGE_SET.value,
    text_message=["1", "/1", "1.", "1 "]
)
def option_1(notification: Notification) -> None:
    try:
        user: User | None = manager.check_user(notification.sender)
        if not user:
            return message_handler(notification)

        notification.answer((
            f'{data["send_text_message"][user.language]}'
            f'{data["links"][user.language]["send_text_documentation"]}'
        ))
    except Exception:
        send_error_message(notification)


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.LANGUAGE_SET.value,
    text_message=["2", "/2", "2.", "2 "]
)
def option_2(notification: Notification) -> None:
    try:
        user = manager.check_user(notification.sender)
        if not user:
            return message_handler(notification)

        url_file: str = server_config.link_pdf

        notification.api.sending.sendFileByUrl(
            notification.chat,
            url_file,
            "corgi.pdf",
            caption=(
                f'{data["send_file_message"][user.language]}'
                f'{data["links"][user.language]["send_file_documentation"]}'
            )
        )
    except Exception:
        send_error_message(notification)


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.LANGUAGE_SET.value,
    text_message=["3", "/3", "3.", "3 "]
)
def option_3(notification: Notification) -> None:
    try:
        user = manager.check_user(notification.sender)
        if not user:
            return message_handler(notification)
        url_file: str = server_config.link_jpg

        notification.api.sending.sendFileByUrl(
            notification.chat,
            url_file,
            "corgi.jpg",
            caption=(
                f'{data["send_image_message"][user.language]}'
                f'{data["links"][user.language]["send_file_documentation"]}'
            )
        )
    except Exception:
        send_error_message(notification)


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.LANGUAGE_SET.value,
    text_message=["4", "/4", "4.", "4 "]
)
def option_4(notification: Notification) -> None:
    try:
        user = manager.check_user(notification.sender)
        if not user:
            return message_handler(notification)

        url_file: str = server_config.link_audio_en

        if user.language in ["kz", "ru"]:
            url_file = server_config.link_audio_ru

        notification.answer((
            f'{data["send_audio_message"][user.language]}'
            f'{data["links"][user.language]["send_file_documentation"]}'
        ))

        url = urlparse(url_file)
        file_name = basename(url.path)

        notification.api.sending.sendFileByUrl(
            notification.chat,
            url_file,
            file_name
        )
    except Exception:
        send_error_message(notification)


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.LANGUAGE_SET.value,
    text_message=["5", "/5", "5.", "5 "]
)
def option_5(notification: Notification) -> None:
    try:
        user = manager.check_user(notification.sender)
        if not user:
            return message_handler(notification)

        url_file: str
        if user.language in ("kz", "ru"):
            url_file = server_config.link_video_ru
        else:
            url_file = server_config.link_video_en

        notification.api.sending.sendFileByUrl(
            notification.chat,
            url_file,
            "green-api.mp4",
            caption=(
                f'{data["send_video_message"][user.language]}'
                f'{data["links"][user.language]["send_file_documentation"]}'
            )
        )
    except Exception:
        send_error_message(notification)


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.LANGUAGE_SET.value,
    text_message=["6", "/6", "6.", "6 "]
)
def option_6(notification: Notification) -> None:
    try:
        user: User | None = manager.check_user(notification.sender)
        if not user:
            return message_handler(notification)
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
        send_error_message(notification)


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.LANGUAGE_SET.value,
    text_message=["7", "/7", "7.", "7 "]
)
def option_7(notification: Notification) -> None:
    try:
        user: User | None = manager.check_user(notification.sender)
        if not user:
            return message_handler(notification)
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
        send_error_message(notification)


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.LANGUAGE_SET.value,
    text_message=["8", "/8", "8.", "8 "]
)
def option_8(notification: Notification) -> None:
    try:
        user: User | None = manager.check_user(notification.sender)
        if not user:
            return message_handler(notification)
        notification.answer(
            f'{data["send_poll_message"][user.language]}'
            f'{data["links"][user.language]["send_poll_as_buttons"]}'
            f'{data["send_poll_message_1"][user.language]}'
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
        send_error_message(notification)


@bot.router.poll_update_message()
def polls_handler(notification: Notification) -> None:
    try:
        user: User | None = manager.check_user(notification.sender)
        if not user:
            return message_handler(notification)
        votes: list[dict[str, str]] = (
            notification.event["messageData"]["pollMessageData"]["votes"]
        )

        for vote_data in votes:
            voters = vote_data["optionVoters"]
            if voters:
                option_name = vote_data["optionName"]
                if option_name == f'{data["poll_option_1"][user.language]}':
                    notification.answer(
                        f'{data["poll_answer_1"][user.language]}')
                elif option_name == f'{data["poll_option_2"][user.language]}':
                    notification.answer(
                        f'{data["poll_answer_2"][user.language]}')
                elif option_name == f'{data["poll_option_3"][user.language]}':
                    notification.answer(
                        f'{data["poll_answer_3"][user.language]}')
    except Exception:
        send_error_message(notification)


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.LANGUAGE_SET.value,
    text_message=["9", "/9", "9.", "9 "]
)
def option_9(notification: Notification) -> None:
    try:
        user: User | None = manager.check_user(notification.sender)
        if not user:
            return message_handler(notification)

        notification.answer((
            f'{data["get_avatar_message"][user.language]}'
            f'{data["links"][user.language]["get_avatar_documentation"]}'
        ))

        response: GreenAPIResponse = notification.api.serviceMethods.getAvatar(
            notification.sender
        )
        if response.data["urlAvatar"]:
            mime_type = requests.head(
                response.data["urlAvatar"]
            ).headers.get("content-type")
            extension = mime_type.split("/")[-1]

            notification.api.sending.sendFileByUrl(
                notification.chat,
                response.data["urlAvatar"],
                f"your_avatar.{extension}",
                caption=f'{data["avatar_found"][user.language]}'
            )
        else:
            notification.answer(f'{data["avatar_not_found"][user.language]}')
    except Exception:
        send_error_message(notification)


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.LANGUAGE_SET.value,
    text_message=["10", "/10", "10.", "10 "]
)
def option_10(notification: Notification) -> None:
    try:
        user: User | None = manager.check_user(notification.sender)
        if not user:
            return message_handler(notification)
        notification.answer(
            f'{data["send_link_message_preview"][user.language]}'
            f'{data["links"][user.language]["send_link_documentation"]}',
            link_preview=True
        )
        notification.answer(
            f'{data["send_link_message_no_preview"][user.language]}'
            f'{data["links"][user.language]["send_link_documentation"]}',
            link_preview=False
        )
    except Exception:
        send_error_message(notification)


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.LANGUAGE_SET.value,
    text_message=["11", "/11", "11.", "11 "]
)
def option_11(notification: Notification) -> None:
    try:
        user: User | None = manager.check_user(notification.sender)
        if not user:
            return message_handler(notification)
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
        send_error_message(notification)


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.WAITING_RESPONSE.value,
    regexp=(r"^[.\s]?1[.\s]?$", IGNORECASE)
)
def option_11_1(notification: Notification) -> None:
    try:
        user: User | None = manager.check_user(notification.sender)
        if not user:
            return message_handler(notification)
        notification.state_manager.update_state(
            notification.sender, States.LANGUAGE_SET.value)
        group_response: GreenAPIResponse = notification.api.groups.createGroup(
            f'{data["group_name"][user.language]}',
            [notification.sender,
             bot.api.account.getSettings().data["wid"]]
        )
        if group_response.data["created"]:
            group_picture_response: GreenAPIResponse = (
                notification.api.groups.setGroupPicture(
                    f'{group_response.data["chatId"]}',
                    "media/green-api-full.png"
                )
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
                    f'{data["send_group_message_set_picture_false"][user.language]}'
                    f'{data["links"][user.language]["groups_documentation"]}',
                )
            notification.answer(
                f'{data["group_created_message"][user.language]}'
                f'{group_response.data["groupInviteLink"]}'
            )
    except Exception:
        send_error_message(notification)


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.WAITING_RESPONSE.value,
    regexp=(r"^[.\s]?0[.\s]?$", IGNORECASE)
)
def option_11_0(notification: Notification) -> None:
    try:
        user: User | None = manager.check_user(notification.sender)
        if not user:
            return message_handler(notification)
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
        send_error_message(notification)


@bot.router.message(
    type_message=TEXT_TYPES, state=States.WAITING_RESPONSE.value
)
def response_wait_handler(notification: Notification) -> None:
    user: User | None = manager.check_user(notification.sender)
    if not user:
        return message_handler(notification)

    notification.answer(data["not_recognized_message"][user.language])


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.LANGUAGE_SET.value,
    text_message=["12", "/12", "12.", "12 "]
)
def option_12(notification: Notification) -> None:
    try:
        user: User | None = manager.check_user(notification.sender)
        if not user:
            return message_handler(notification)
        notification.answer(
            f'{data["send_quoted_message"][user.language]}'
            f'{data["links"][user.language]["send_quoted_message_documentation"]}',
            quoted_message_id=notification.event["idMessage"]
        )
    except Exception:
        send_error_message(notification)


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.LANGUAGE_SET.value,
    text_message=["13", "/13", "13.", "13 "]
)
def option_13(notification: Notification) -> None:
    try:
        user: User | None = manager.check_user(notification.sender)
        if not user:
            return message_handler(notification)
        notification.answer_with_file(
            file="media/about.jpg",
            file_name="about.jpg",
            caption=(
                f'{data["about_python_chatbot"][user.language]}'
                f'{data["link_to_docs"][user.language]}'
                f'{data["links"][user.language]["chatbot_documentation"]}'
                f'{data["link_to_source_code"][user.language]}'
                f'{data["links"][user.language]["chatbot_source_code"]}'
                f'{data["link_to_green_api"][user.language]}'
                f'{data["links"][user.language]["greenapi_website"]}'
                f'{data["link_to_console"][user.language]}'
                f'{data["links"][user.language]["greenapi_console"]}'
                f'{data["link_to_youtube"][user.language]}'
                f'{data["links"][user.language]["youtube_channel"]}'
            )
        )
    except Exception:
        send_error_message(notification)


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.LANGUAGE_SET.value,
    text_message=["stop", "стоп", "Stop", "Стоп", "0"]
)
def stop(notification: Notification) -> None:
    try:
        user: User | None = manager.check_user(notification.sender)
        if not user:
            return message_handler(notification)

        notification.state_manager.update_state(
            notification.sender, States.NOT_ACTIVE.value
        )

        notification.answer((
            f'{data["stop_message"][user.language]}'
            f'*{notification.event["senderData"]["senderName"]}*!'
        ))
    except Exception:
        send_error_message(notification)


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.LANGUAGE_SET.value,
    text_message=["menu", "меню", "Menu", "Меню"]
)
@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.WAITING_RESPONSE.value,
    text_message=["menu", "меню", "Menu", "Меню"]
)
def menu(notification: Notification) -> None:
    try:
        user: User | None = manager.check_user(notification.sender)
        if not user:
            return message_handler(notification)

        landing_image: str
        if user.language in ("kz", "ru"):
            landing_image = "media/welcome_ru.png"
        else:
            landing_image = "media/welcome_en.png"

        notification.answer_with_file(
            landing_image,
            file_name="welcome.png",
            caption=(
                f'{data["welcome_message"][user.language]}'
                f'*{notification.event["senderData"]["senderName"]}*'
                f'! '
                f'{data["menu"][user.language]}'
            )
        )
    except Exception:
        send_error_message(notification)


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.ACTIVE.value,
    regexp=(r"^(?![.\s]?[1-5][.\s]?$).*", IGNORECASE)
)
def not_recognized_message1(notification: Notification) -> None:
    try:
        user: User | None = manager.check_user(notification.sender)
        if not user:
            message_handler(notification)

        notification.answer(data["specify_language"])
    except Exception:
        send_error_message(notification)


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.LANGUAGE_SET.value,
    regexp=(r"^(?!(?:[0-9]|10|11|12|13|menu|меню|stop|стоп)$).*", IGNORECASE)
)
def not_recognized_message2(notification: Notification) -> None:
    try:
        user: User | None = manager.check_user(notification.sender)
        if not user:
            message_handler(notification)

        notification.answer(data["not_recognized_message"][user.language])
    except Exception:
        send_error_message(notification)


bot.run_forever()
