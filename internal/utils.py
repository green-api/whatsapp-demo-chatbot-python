from __future__ import annotations

from logging import Logger
from time import time
from typing import TYPE_CHECKING, Callable, Tuple

from whatsapp_chatbot_python import BaseStates

if TYPE_CHECKING:
    from whatsapp_chatbot_python import Notification


class States(BaseStates):
    INITIAL = "INITIAL"
    MENU = "MENU"
    GROUP_CREATION = "GROUP_CREATION"


AVAILABLE_LANGUAGES = {
    "1": "en",
    "2": "kz",
    "3": "ru",
    "4": "es",
    "5": "he",
}

LANGUAGE_CODE_KEY = "language_code"
LAST_INTERACTION_KEY = "last_interaction_ts"


def api_token_log_hider(token: str | None) -> str:
    """
    Hide all but the last HIDDEN_SYMBOLS_COUNT characters of a token string.

    Args:
        token (str | None): The token string to be hidden.

    Returns:
        str: The token string with all but the last HIDDEN_SYMBOLS_COUNT
             characters replaced by '*'. Returns '*empty*' if the input is None.
    """
    HIDDEN_SYMBOLS_COUNT = 16

    if token:
        hidden_part = "*" * (len(token) - HIDDEN_SYMBOLS_COUNT)
        visible_part = token[-HIDDEN_SYMBOLS_COUNT:]
        return f"{hidden_part}{visible_part}"
    else:
        return "*empty*"


def get_main_menu_image_by_lang_code(lang_code: str) -> Tuple[str, str]:
    """
    Returns tuple, where first value is
    main menu image path and second one is main menu image name
    """

    RUSSIAN_IMAGE_CODES = ("kz", "ru")

    image_path = (
        "media/welcome_ru.png"
        if lang_code in RUSSIAN_IMAGE_CODES
        else "media/welcome_en.png"
    )

    image_name = (
        "welcome_ru.png" if lang_code in RUSSIAN_IMAGE_CODES else "welcome_en.png"
    )

    return image_path, image_name


def sender_state_reset(
    notification: Notification, reset_to_zero_state: bool = False
) -> bool:
    """
    Reset notification's sender state & data for initial and returns `True`

    If `reset_to_zero_state` is `True`, resets state to `None`
    """

    if reset_to_zero_state:
        notification.state_manager.set_state(notification.sender, None)
        notification.state_manager.delete_state_data(notification.sender)

    else:
        notification.state_manager.set_state(notification.sender, States.INITIAL.value)
        notification.state_manager.set_state_data(
            notification.sender,
            {
                LAST_INTERACTION_KEY: int(time()),
                LANGUAGE_CODE_KEY: None,
            },
        )

    return True


def sender_state_data_updater(notification: Notification) -> bool:
    """
    Helper for checking & updating sender's state.
    Must return `True`, if state was reset, otherwise - `False`
    """

    MAX_INACTIVITY_TIME_SECONDS = 300

    sender = notification.sender
    now_ts = int(time())

    current_sender_state_data = notification.state_manager.get_state_data(sender)

    if current_sender_state_data is None:
        return sender_state_reset(notification)

    current_last_interaction_ts = current_sender_state_data[LAST_INTERACTION_KEY]

    # We also wants to reset state if user was
    # inactive some time (MAX_INACTIVITY_TIME_SECONDS)

    if now_ts - current_last_interaction_ts > MAX_INACTIVITY_TIME_SECONDS:
        return sender_state_reset(notification)

    notification.state_manager.update_state_data(
        sender, state_data={LAST_INTERACTION_KEY: int(time())}
    )
    return False


def debug_profiler(logger: Logger):
    """
    Simple decorator for sending some usefull
    logs into debug logger. Only for local dev.
    """

    def outer(func: Callable):

        def inner(*args, **kwargs):

            start_timestamp = time()
            notification: Notification = args[0]
            logger.debug(f"Message sender: {notification.sender}")
            logger.debug(f"Message text: {notification.message_text}")
            logger.debug(
                "Notification storage: (before handling): "
                f"{notification.state_manager.storage}"
            )

            result = func(*args, **kwargs)

            logger.debug(
                "Notification storage: (after handling): "
                f"{notification.state_manager.storage}"
            )

            finish_timestamp = time()
            t = finish_timestamp - start_timestamp

            logger.debug(
                f"Seconds for processing request ({func.__name__}): {round(t, 3)}"
            )

            return result

        return inner

    return outer
