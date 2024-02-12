import logging
import os
import urllib.request
from functools import cache

from dotenv import load_dotenv
from spring_config import ClientConfigurationBuilder
from spring_config.client import SpringConfigClient

logger = logging.getLogger(__name__)


class ServerConfig:
    def __init__(self, user_id: str, api_token_id: str,
                 link_pdf: str, link_jpg: str,
                 link_audio_ru: str, link_video_ru: str,
                 link_audio_en: str, link_video_en: str,
                 link_group_image: str):
        self.user_id = user_id
        self.api_token_id = api_token_id
        self.link_pdf = link_pdf
        self.link_jpg = link_jpg
        self.link_audio_ru = link_audio_ru
        self.link_video_ru = link_video_ru
        self.link_audio_en = link_audio_en
        self.link_video_en = link_video_en
        self.link_group_image = link_group_image


def __none_if_empty_str(s: str):
    return s if s and (s != "") else None


@cache
def get_config():
    logger.info("loading config started")

    debug = int(os.environ.get("DEBUG", 0)) > 0 or False

    if not debug:
        env_loaded = load_dotenv()
        if not env_loaded:
            raise Exception(".env not found")

    app_name = "sw-chatbot-7103"

    active_profile = __none_if_empty_str(os.environ.get("ACTIVE_PROFILE"))

    endpoint = __none_if_empty_str(os.environ.get("SPRING_CLOUD_CONFIG_URI"))
    if not debug and endpoint is None:
        raise Exception("SPRING_CLOUD_CONFIG_URI not set!")

    else:
        client_config = (
            ClientConfigurationBuilder()
            .app_name(app_name)
            .profile(active_profile)
            .address(endpoint)
            .build()
        )
        client = SpringConfigClient(client_config)
        config_result = client.get_config()

    sapi_user_id = str(config_result.get("user_id"))
    sapi_user_token = str(config_result.get("api_token_id"))
    slink_pdf = str(config_result.get("link_pdf"))
    slink_jpg = str(config_result.get("link_jpg"))
    slink_audio_en = str(config_result.get("link_audio_en"))
    slink_video_en = str(config_result.get("link_video_en"))
    slink_audio_ru = str(config_result.get("link_audio_ru"))
    slink_video_ru = str(config_result.get("link_video_ru"))
    slink_group_image = str(config_result.get("link_group_image"))

    try:
        urllib.request.urlretrieve(slink_group_image, "green_api.jpg")
    except Exception:
        logger.error(
            "Failed to download group_image from: " +
            slink_group_image)

    logger.info("user id is: " + sapi_user_id)
    logger.info("api token id is: " + sapi_user_token)
    logger.info("link for pdf is: " + slink_pdf)
    logger.info("link for jpg is: " + slink_jpg)
    logger.info("link for audio (ru) is: " + slink_audio_ru)
    logger.info("link for video (ru) is: " + slink_video_ru)
    logger.info("link for audio (en) is: " + slink_audio_en)
    logger.info("link for video (en) is: " + slink_video_en)
    logger.info("link for group_image is: " + slink_group_image)
    logger.info("config loaded")

    return ServerConfig(
        user_id=sapi_user_id,
        api_token_id=sapi_user_token,
        link_pdf=slink_pdf,
        link_jpg=slink_jpg,
        link_audio_ru=slink_audio_ru,
        link_video_ru=slink_video_ru,
        link_audio_en=slink_audio_en,
        link_video_en=slink_video_en,
        link_group_image=slink_group_image
    )
