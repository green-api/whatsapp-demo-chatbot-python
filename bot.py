from os.path import basename
from re import IGNORECASE
from urllib.parse import urlparse

from whatsapp_chatbot_python import GreenAPIBot, Notification
from whatsapp_chatbot_python.filters import TEXT_TYPES
from yaml import safe_load

from internal.config import init_config
from internal.envs import init_envs
from internal.logger import init_logger
from internal.utils import (
    AVAILABLE_LANGUAGES,
    LANGUAGE_CODE_KEY,
    States,
    debug_profiler,
    get_main_menu_image_by_lang_code,
    sender_state_data_updater,
    sender_state_reset,
)

YAML_DATA_RELATIVE_PATH = "config/data.yml"

envs = init_envs()
logger = init_logger(debug=envs.debug)
config = init_config(envs=envs, logger=logger)


with open(YAML_DATA_RELATIVE_PATH, encoding="utf8") as f:
    answers_data = safe_load(f)

bot = GreenAPIBot(
    config.user_id,
    config.api_token_id,
    settings={
        "webhookUrl": "",
        "webhookUrlToken": "",
        "delaySendMessagesMilliseconds": 500,
        "markIncomingMessagesReaded": "yes",
        "incomingWebhook": "yes",
        "keepOnlineStatus": "yes",
        "pollMessageWebhook": "yes",
    },
)


@bot.router.message(type_message=TEXT_TYPES, state=None)
@debug_profiler(logger=logger)
def initial_handler(notification: Notification) -> None:
    """
    Initial handler for new senders without any state

    From here we will add user into state for a
    first time and set `INITIAL` state with initial data
    """

    sender_state_data_updater(notification)
    notification.answer(answers_data["select_language"])


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.INITIAL.value,
    regexp=r"^\s*[1-5]\s*$",
)
@debug_profiler(logger=logger)
def set_language_handler(notification: Notification) -> None:
    """
    Handler for senders with `INITIAL` state.


    Either this is a new user who must select a language for the first time
    OR this is a user who has not communicated with the bot for a while
    """

    # Check state and return to initial if it was reset

    if sender_state_data_updater(notification):
        return initial_handler(notification)

    # Get language from message
    try:
        chosen_language_code = AVAILABLE_LANGUAGES[notification.message_text.strip()]
    except KeyError as e:
        logger.exception(e)
        return

    # Update sender's state data for chosen language
    notification.state_manager.update_state_data(
        notification.sender,
        {
            LANGUAGE_CODE_KEY: chosen_language_code,
        },
    )

    # Get main menu image based on chosen language
    menu_image_path, menu_image_name = get_main_menu_image_by_lang_code(
        chosen_language_code
    )

    # Generate message for main menu
    try:
        answer_text = (
            f'{answers_data["welcome_message"][chosen_language_code]}'
            f'*{notification.event["senderData"]["senderName"]}*!'
            f'{answers_data["menu"][chosen_language_code]}'
        )
    except KeyError as e:
        logger.exception(e)
        return

    # Updating sender's state to MENU value
    notification.state_manager.update_state(
        notification.sender,
        States.MENU.value,
    )

    # Sending main menu answer
    notification.answer_with_file(
        file=menu_image_path,
        file_name=menu_image_name,
        caption=answer_text,
    )


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.MENU.value,
    regexp=r"^\s*1\s*$",
)
@debug_profiler(logger=logger)
def main_menu_option_1_handler(notification: Notification) -> None:
    """
    "Send text message" option handler for senders with `MENU` state.
    """

    if sender_state_data_updater(notification):
        return initial_handler(notification)

    sender = notification.sender
    sender_state_data = notification.state_manager.get_state_data(sender)

    try:
        sender_lang_code = sender_state_data[LANGUAGE_CODE_KEY]
        first_option_answer_text = (
            f'{answers_data["send_text_message"][sender_lang_code]}'
            f'{answers_data["links"][sender_lang_code]["send_text_documentation"]}'
        )
    except KeyError as e:
        logger.exception(e)
        return

    notification.answer(first_option_answer_text)


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.MENU.value,
    regexp=r"^\s*2\s*$",
)
@debug_profiler(logger=logger)
def main_menu_option_2_handler(notification: Notification) -> None:
    """
    "Send file message" option handler for senders with `MENU` state.
    """

    if sender_state_data_updater(notification):
        return initial_handler(notification)

    sender = notification.sender
    sender_state_data = notification.state_manager.get_state_data(sender)

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
    )


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.MENU.value,
    regexp=r"^\s*3\s*$",
)
@debug_profiler(logger=logger)
def main_menu_option_3_handler(notification: Notification) -> None:
    """
    "Send image" option handler for senders with `MENU` state.
    """

    if sender_state_data_updater(notification):
        return initial_handler(notification)

    sender = notification.sender
    sender_state_data = notification.state_manager.get_state_data(sender)

    try:
        sender_lang_code = sender_state_data[LANGUAGE_CODE_KEY]
        third_option_answer_text = (
            f'{answers_data["send_image_message"][sender_lang_code]}'
            f'{answers_data["links"][sender_lang_code]["send_file_documentation"]}'
        )

    except KeyError as e:
        logger.exception(e)
        return

    notification.api.sending.sendFileByUrl(
        notification.chat,
        config.link_jpg,
        "corgi.jpg",
        caption=third_option_answer_text,
    )


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.MENU.value,
    regexp=r"^\s*4\s*$",
)
@debug_profiler(logger=logger)
def main_menu_option_4_handler(notification: Notification) -> None:
    """
    "Send audio" option handler for senders with `MENU` state.
    """

    if sender_state_data_updater(notification):
        return initial_handler(notification)

    sender = notification.sender
    sender_state_data = notification.state_manager.get_state_data(sender)

    try:
        sender_lang_code = sender_state_data[LANGUAGE_CODE_KEY]
        fourth_option_answer_text = (
            f'{answers_data["send_audio_message"][sender_lang_code]}'
            f'{answers_data["links"][sender_lang_code]["send_file_documentation"]}'
        )

    except KeyError as e:
        logger.exception(e)
        return

    if sender_lang_code in ("kz", "ru"):
        url_file = config.link_audio_ru
    else:
        url_file = config.link_audio_en

    url = urlparse(url_file)
    file_name = basename(url.path)

    notification.answer(fourth_option_answer_text)
    notification.api.sending.sendFileByUrl(
        notification.chat,
        url_file,
        file_name,
    )


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.MENU.value,
    regexp=r"^\s*5\s*$",
)
@debug_profiler(logger=logger)
def main_menu_option_5_handler(notification: Notification) -> None:
    """
    "Send video" option handler for senders with `MENU` state.
    """

    if sender_state_data_updater(notification):
        return initial_handler(notification)

    sender = notification.sender
    sender_state_data = notification.state_manager.get_state_data(sender)

    try:
        sender_lang_code = sender_state_data[LANGUAGE_CODE_KEY]
        fifth_option_answer_text = (
            f'{answers_data["send_video_message"][sender_lang_code]}'
            f'{answers_data["links"][sender_lang_code]["send_file_documentation"]}'
        )

    except KeyError as e:
        logger.exception(e)
        return

    if sender_lang_code in ("kz", "ru"):
        url_file = config.link_video_ru
    else:
        url_file = config.link_video_en

    url = urlparse(url_file)
    file_name = basename(url.path)

    notification.api.sending.sendFileByUrl(
        notification.chat,
        url_file,
        file_name,
        caption=fifth_option_answer_text,
    )


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.MENU.value,
    regexp=r"^\s*6\s*$",
)
@debug_profiler(logger=logger)
def main_menu_option_6_handler(notification: Notification) -> None:
    """
    "Send video" option handler for senders with `MENU` state.
    """

    if sender_state_data_updater(notification):
        return initial_handler(notification)

    sender = notification.sender
    sender_state_data = notification.state_manager.get_state_data(sender)

    try:
        sender_lang_code = sender_state_data[LANGUAGE_CODE_KEY]
        sixth_option_answer_text = (
            f'{answers_data["send_contact_message"][sender_lang_code]}'
            f'{answers_data["links"][sender_lang_code]["send_contact_documentation"]}'
        )

    except KeyError as e:
        logger.exception(e)
        return

    notification.answer(sixth_option_answer_text)
    notification.api.sending.sendContact(
        notification.chat,
        contact={
            "phoneContact": notification.sender.split("@")[0],
            "firstName": notification.event["senderData"]["senderName"],
        },
    )


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.MENU.value,
    regexp=r"^\s*7\s*$",
)
@debug_profiler(logger=logger)
def main_menu_option_7_handler(notification: Notification) -> None:
    """
    "Send location" option handler for senders with `MENU` state.
    """

    if sender_state_data_updater(notification):
        return initial_handler(notification)

    sender = notification.sender
    sender_state_data = notification.state_manager.get_state_data(sender)

    try:
        sender_lang_code = sender_state_data[LANGUAGE_CODE_KEY]
        seventh_option_answer_text = (
            f'{answers_data["send_location_message"][sender_lang_code]}'
            f'{answers_data["links"][sender_lang_code]["send_location_documentation"]}'
        )

    except KeyError as e:
        logger.exception(e)
        return

    notification.answer(seventh_option_answer_text)
    notification.api.sending.sendLocation(
        notification.chat,
        latitude=35.888171,
        longitude=14.440230,
    )


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.MENU.value,
    regexp=r"^\s*8\s*$",
)
@debug_profiler(logger=logger)
def main_menu_option_8_handler(notification: Notification) -> None:
    """
    "Send poll" option handler for senders with `MENU` state.
    """

    if sender_state_data_updater(notification):
        return initial_handler(notification)

    sender = notification.sender
    sender_state_data = notification.state_manager.get_state_data(sender)

    try:
        sender_lang_code = sender_state_data[LANGUAGE_CODE_KEY]
        eighth_option_answer_text = (
            f'{answers_data["send_poll_message"][sender_lang_code]}'
            f'{answers_data["links"][sender_lang_code]["send_poll_as_buttons"]}'
            f'{answers_data["send_poll_message_1"][sender_lang_code]}'
            f'{answers_data["links"][sender_lang_code]["send_poll_documentation"]}'
        )
        poll_question_text = f'{answers_data["poll_question"][sender_lang_code]}'
        poll_options = [
            {"optionName": f'{answers_data["poll_option_1"][sender_lang_code]}'},
            {"optionName": f'{answers_data["poll_option_2"][sender_lang_code]}'},
            {"optionName": f'{answers_data["poll_option_3"][sender_lang_code]}'},
        ]

    except KeyError as e:
        logger.exception(e)
        return

    notification.answer(eighth_option_answer_text)
    notification.answer_with_poll(
        message=poll_question_text,
        options=poll_options,
        multiple_answers=False,
    )


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.MENU.value,
    regexp=r"^\s*9\s*$",
)
@debug_profiler(logger=logger)
def main_menu_option_9_handler(notification: Notification) -> None:
    """
    "Getting image of sender's avatar" option handler for senders with `MENU` state.
    """

    if sender_state_data_updater(notification):
        return initial_handler(notification)

    sender = notification.sender
    sender_state_data = notification.state_manager.get_state_data(sender)

    try:
        sender_lang_code = sender_state_data[LANGUAGE_CODE_KEY]
        ninth_option_answer_text = (
            f'{answers_data["get_avatar_message"][sender_lang_code]}'
            f'{answers_data["links"][sender_lang_code]["get_avatar_documentation"]}'
        )

        caption_text = f'{answers_data["avatar_found"][sender_lang_code]}'
        avatar_not_found_answer_text = (
            f'{answers_data["avatar_not_found"][sender_lang_code]}'
        )

    except KeyError as e:
        logger.exception(e)
        return

    notification.answer(ninth_option_answer_text)
    green_api_response = notification.api.serviceMethods.getAvatar(notification.sender)

    try:
        avatar_url = green_api_response.data["urlAvatar"]
        if not avatar_url:
            notification.answer(avatar_not_found_answer_text)
            return

    except KeyError as e:
        logger.exception(e)
        return

    try:
        avatar_filename = avatar_url.split("?")[0].split("/")[-1]
    except IndexError:
        logger.warn(
            "Can not parse avatar image name from url, "
            "avatar filenase set as 'avatar'"
        )
        avatar_filename = "avatar"

    notification.api.sending.sendFileByUrl(
        notification.chat,
        avatar_url,
        avatar_filename,
        caption=caption_text,
    )


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.MENU.value,
    regexp=r"^\s*10\s*$",
)
@debug_profiler(logger=logger)
def main_menu_option_10_handler(notification: Notification) -> None:
    """
    "Send link" option handler for senders with `MENU` state.
    """

    if sender_state_data_updater(notification):
        return initial_handler(notification)

    sender = notification.sender
    sender_state_data = notification.state_manager.get_state_data(sender)

    try:
        sender_lang_code = sender_state_data[LANGUAGE_CODE_KEY]
        tenth_option_with_preview_answer_text = (
            f'{answers_data["send_link_message_preview"][sender_lang_code]}'
            f'{answers_data["links"][sender_lang_code]["send_link_documentation"]}'
        )
        tenth_option_without_preview_answer_text = (
            f'{answers_data["send_link_message_no_preview"][sender_lang_code]}'
            f'{answers_data["links"][sender_lang_code]["send_link_documentation"]}'
        )

    except KeyError as e:
        logger.exception(e)
        return

    notification.answer(
        tenth_option_with_preview_answer_text,
        link_preview=True,
    )
    notification.answer(
        tenth_option_without_preview_answer_text,
        link_preview=False,
    )


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.MENU.value,
    regexp=r"^\s*11\s*$",
)
@debug_profiler(logger=logger)
def main_menu_option_11_handler(notification: Notification) -> None:
    """
    "Create group with bot" option handler for senders with `MENU` state.
    """

    if sender_state_data_updater(notification):
        return initial_handler(notification)

    sender = notification.sender
    sender_state_data = notification.state_manager.get_state_data(sender)

    try:
        sender_lang_code = sender_state_data[LANGUAGE_CODE_KEY]
        eleventh_option_answer_text = (
            f'{answers_data["add_to_contact"][sender_lang_code]}'
        )

    except KeyError as e:
        logger.exception(e)
        return

    notification.answer(eleventh_option_answer_text)

    try:
        bot_phone_number = int(bot.api.account.getSettings().data["wid"].split("@")[0])
    except Exception as e:
        logger.exception(e)
        return

    notification.api.sending.sendContact(
        chatId=notification.chat,
        contact={
            "phoneContact": bot_phone_number,
            "firstName": answers_data["bot_name"][sender_lang_code],
        },
    )

    notification.state_manager.update_state(
        sender,
        States.GROUP_CREATION.value,
    )


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.MENU.value,
    regexp=r"^\s*12\s*$",
)
@debug_profiler(logger=logger)
def main_menu_option_12_handler(notification: Notification) -> None:
    """
    "Send quoted message" option handler for senders with `MENU` state.
    """

    if sender_state_data_updater(notification):
        return initial_handler(notification)

    sender = notification.sender
    sender_state_data = notification.state_manager.get_state_data(sender)

    try:
        sender_lang_code = sender_state_data[LANGUAGE_CODE_KEY]
        twelfth_option_answer_text = (
            f'{answers_data["send_quoted_message"][sender_lang_code]}'
            f'{answers_data["links"][sender_lang_code]["send_quoted_message_documentation"]}'  # noqa: E501
        )

        quoted_message_id = notification.event["idMessage"]

    except KeyError as e:
        logger.exception(e)
        return

    notification.answer(
        twelfth_option_answer_text,
        quoted_message_id=quoted_message_id,
    )


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.MENU.value,
    regexp=r"^\s*13\s*$",
)
@debug_profiler(logger=logger)
def main_menu_option_13_handler(notification: Notification) -> None:
    """
    "About" option handler for senders with `MENU` state.
    """

    if sender_state_data_updater(notification):
        return initial_handler(notification)

    sender = notification.sender
    sender_state_data = notification.state_manager.get_state_data(sender)

    try:
        sender_lang_code = sender_state_data[LANGUAGE_CODE_KEY]
        thirteenth_option_answer_text = (
            f'{answers_data["about_python_chatbot"][sender_lang_code]}'
            f'{answers_data["link_to_docs"][sender_lang_code]}'
            f'{answers_data["links"][sender_lang_code]["chatbot_documentation"]}'
            f'{answers_data["link_to_source_code"][sender_lang_code]}'
            f'{answers_data["links"][sender_lang_code]["chatbot_source_code"]}'
            f'{answers_data["link_to_green_api"][sender_lang_code]}'
            f'{answers_data["links"][sender_lang_code]["greenapi_website"]}'
            f'{answers_data["link_to_console"][sender_lang_code]}'
            f'{answers_data["links"][sender_lang_code]["greenapi_console"]}'
            f'{answers_data["link_to_youtube"][sender_lang_code]}'
            f'{answers_data["links"][sender_lang_code]["youtube_channel"]}'
        )

    except KeyError as e:
        logger.exception(e)
        return

    notification.answer_with_file(
        file="media/about.jpg",
        file_name="about.jpg",
        caption=thirteenth_option_answer_text,
    )


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.MENU.value,
    regexp=(r"^(?:0|stop|стоп)$", IGNORECASE),
)
@debug_profiler(logger=logger)
def main_menu_stop_handler(notification: Notification) -> None:
    """
    Stop command handler for senders with `MENU` state.
    Must reset sender's state to initial
    """

    if sender_state_data_updater(notification):
        return initial_handler(notification)

    sender = notification.sender
    sender_state_data = notification.state_manager.get_state_data(sender)

    try:
        sender_lang_code = sender_state_data[LANGUAGE_CODE_KEY]
        stop_option_answer_text = (
            f'{answers_data["stop_message"][sender_lang_code]}'
            f'*{notification.event["senderData"]["senderName"]}*!'
        )

    except KeyError as e:
        logger.exception(e)
        return

    notification.answer(stop_option_answer_text)
    sender_state_reset(notification, reset_to_zero_state=True)


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.MENU.value,
    regexp=(r"^(?:меню|menu)$", IGNORECASE),
)
@debug_profiler(logger=logger)
def main_menu_menu_handler(notification: Notification) -> None:
    """
    Menu command handler for senders with `MENU` state.
    Does not change state, just returns menu
    """

    if sender_state_data_updater(notification):
        return initial_handler(notification)

    sender = notification.sender
    sender_state_data = notification.state_manager.get_state_data(sender)

    try:
        sender_lang_code = sender_state_data[LANGUAGE_CODE_KEY]
        answer_text = f'{answers_data["menu"][sender_lang_code]}'.lstrip()
    except KeyError as e:
        logger.exception(e)
        return

    # Get main menu image based on chosen language
    menu_image_path, menu_image_name = get_main_menu_image_by_lang_code(
        sender_lang_code
    )

    # Sending main menu answer
    notification.answer_with_file(
        file=menu_image_path,
        file_name=menu_image_name,
        caption=answer_text,
    )


@bot.router.poll_update_message()
@debug_profiler(logger=logger)
def polls_handler(notification: Notification) -> None:
    """
    Handler for senders with any state, only for polls
    (sender answer poll -> this handler works)
    """

    if sender_state_data_updater(notification):
        return initial_handler(notification)

    sender = notification.sender
    sender_state_data = notification.state_manager.get_state_data(sender)

    try:
        sender_lang_code = sender_state_data[LANGUAGE_CODE_KEY]
        votes = notification.event["messageData"]["pollMessageData"]["votes"]
    except KeyError as e:
        logger.exception(e)
        return

    try:

        for vote_data in votes:
            voters = vote_data["optionVoters"]
            option_name = vote_data["optionName"]

            if voters:
                if option_name == f'{answers_data["poll_option_1"][sender_lang_code]}':
                    notification.answer(
                        f'{answers_data["poll_answer_1"][sender_lang_code]}'
                    )

                elif (
                    option_name == f'{answers_data["poll_option_2"][sender_lang_code]}'
                ):
                    notification.answer(
                        f'{answers_data["poll_answer_2"][sender_lang_code]}'
                    )

                elif (
                    option_name == f'{answers_data["poll_option_3"][sender_lang_code]}'
                ):
                    notification.answer(
                        f'{answers_data["poll_answer_3"][sender_lang_code]}'
                    )

    except KeyError as e:
        logger.exception(e)
        return


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.GROUP_CREATION.value,
    regexp=(r"^\s*0|menu|меню\s*$", IGNORECASE),
)
@debug_profiler(logger=logger)
def group_creation_0_option_handler(notification: Notification) -> None:
    """
    Handler for senders with `GROUP_CREATION` state.

    Must handle "Will not add" option in group creation flow.
    Changing state to `MENU` and showing main menu
    """

    if sender_state_data_updater(notification):
        return initial_handler(notification)

    # Updating sender's state to MENU value
    notification.state_manager.update_state(
        notification.sender,
        States.MENU.value,
    )

    return main_menu_menu_handler(notification)


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.GROUP_CREATION.value,
    regexp=r"^\s*1\s*$",
)
@debug_profiler(logger=logger)
def group_creation_1_option_handler(notification: Notification) -> None:
    """
    Handler for senders with `GROUP_CREATION` state.

    Must handle "Added, can create group" option in group creation flow.
    """

    if sender_state_data_updater(notification):
        return initial_handler(notification)

    sender = notification.sender
    sender_state_data = notification.state_manager.get_state_data(sender)

    try:
        sender_lang_code = sender_state_data[LANGUAGE_CODE_KEY]
        group_name = f'{answers_data["group_name"][sender_lang_code]}'

        img_set_success_message = (
            f'{answers_data["send_group_message"][sender_lang_code]}'
            f'{answers_data["links"][sender_lang_code]["groups_documentation"]}'
        )

        img_set_fail_message = (
            f'{answers_data["send_group_message_set_picture_false"][sender_lang_code]}'
            f'{answers_data["links"][sender_lang_code]["groups_documentation"]}'
        )

    except KeyError as e:
        logger.exception(e)
        return

    group_response = notification.api.groups.createGroup(
        group_name,
        [bot.api.account.getSettings().data["wid"], sender],
    )

    try:
        if group_response.data["created"]:

            group_picture_response = notification.api.groups.setGroupPicture(
                f'{group_response.data["chatId"]}',
                "media/green-api-full.png",
            )

            if group_picture_response.data["setGroupPicture"]:
                notification.api.sending.sendMessage(
                    f'{group_response.data["chatId"]}',
                    img_set_success_message,
                )

            else:
                notification.api.sending.sendMessage(
                    f'{group_response.data["chatId"]}',
                    img_set_fail_message,
                )

            answer_message = (
                f'{answers_data["group_created_message"][sender_lang_code]}'
                f'{group_response.data["groupInviteLink"]}'
            )

    except KeyError as e:
        logger.exception(e)
        return

    notification.answer(answer_message)

    # Updating sender's state to MENU value
    notification.state_manager.update_state(
        notification.sender,
        States.MENU.value,
    )


# HANDLERS FOR UNRECOGNIZED MESSAGES IN DIFFERENT STATES


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.INITIAL.value,
    regexp=(r"^\s*(?![1-5]\s*$).*\s*$", IGNORECASE),
)
@debug_profiler(logger=logger)
def set_language_incorrect_message_handler(notification: Notification) -> None:
    """
    Handler for senders with `INITIAL` state.

    Used as helper for any unrecognized
    commands from user just for displaying pretty message
    """

    if sender_state_data_updater(notification):
        return initial_handler(notification)

    try:
        notification.answer(answers_data["incorrect_language"])
    except KeyError as e:
        logger.exception(e)
        return


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.MENU.value,
    regexp=(r"^(?!\s*(?:1[0-3]|[0-9]|stop|стоп|menu|меню)\s*$).*$", IGNORECASE),
)
@debug_profiler(logger=logger)
def main_menu_incorrect_message_handler(notification: Notification) -> None:
    """
    Handler for senders with `MENU` state.

    Used as helper for any unrecognized
    commands from user just for displaying pretty message
    """

    if sender_state_data_updater(notification):
        return initial_handler(notification)

    sender = notification.sender
    sender_state_data = notification.state_manager.get_state_data(sender)

    try:
        sender_lang_code = sender_state_data[LANGUAGE_CODE_KEY]
        notification.answer(answers_data["not_recognized_message"][sender_lang_code])
    except KeyError as e:
        logger.exception(e)
        return


@bot.router.message(
    type_message=TEXT_TYPES,
    state=States.GROUP_CREATION.value,
    regexp=(r"^(?!\s*(?:[0-1]|menu|меню)\s*$).*$", IGNORECASE),
)
@debug_profiler(logger=logger)
def group_creation_incorrect_message_handler(notification: Notification) -> None:
    """
    Handler for senders with `GROUP_CREATION` state.

    Used as helper for any unrecognized
    commands from user just for displaying pretty message
    """

    if sender_state_data_updater(notification):
        return initial_handler(notification)

    sender = notification.sender
    sender_state_data = notification.state_manager.get_state_data(sender)

    try:
        sender_lang_code = sender_state_data[LANGUAGE_CODE_KEY]
        notification.answer(answers_data["not_recognized_message"][sender_lang_code])
    except KeyError as e:
        logger.exception(e)
        return


bot.run_forever()
