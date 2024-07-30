from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from spring_config import ClientConfigurationBuilder
from spring_config.client import SpringConfigClient

from .utils import api_token_log_hider

if TYPE_CHECKING:
    from .envs import Envs


class ServerConfig:
    def __init__(
        self,
        user_id: str,
        api_token_id: str,
        link_pdf: str,
        link_jpg: str,
        link_audio_ru: str,
        link_video_ru: str,
        link_audio_en: str,
        link_video_en: str,
    ):
        self.user_id = user_id
        self.api_token_id = api_token_id
        self.link_pdf = link_pdf
        self.link_jpg = link_jpg
        self.link_audio_ru = link_audio_ru
        self.link_video_ru = link_video_ru
        self.link_audio_en = link_audio_en
        self.link_video_en = link_video_en


def init_config(envs: Envs, logger: logging.Logger):

    logger.debug(f"DEBUG mode {'ENABLED' if envs.debug else 'DISABLED'}")

    if envs.debug:

        server_config = ServerConfig(
            user_id=envs.debug_user_id,
            api_token_id=envs.debug_api_token_id,
            link_pdf=envs.debug_link_pdf,
            link_jpg=envs.debug_link_jpg,
            link_audio_ru=envs.debug_link_audio_ru,
            link_video_ru=envs.debug_link_video_ru,
            link_audio_en=envs.debug_link_audio_en,
            link_video_en=envs.debug_link_video_en,
        )

    else:

        client_config = (
            ClientConfigurationBuilder()
            .app_name(envs.app_name)
            .profile(envs.active_profile)
            .address(envs.spring_cloud_config_uri)
            .build()
        )

        client = SpringConfigClient(client_config)
        config_result: dict = client.get_config()

        server_config = ServerConfig(
            user_id=str(config_result.get("user_id")),
            api_token_id=str(config_result.get("api_token_id")),
            link_pdf=str(config_result.get("link_pdf")),
            link_jpg=str(config_result.get("link_jpg")),
            link_audio_ru=str(config_result.get("link_audio_ru")),
            link_video_ru=str(config_result.get("link_video_ru")),
            link_audio_en=str(config_result.get("link_audio_en")),
            link_video_en=str(config_result.get("link_video_en")),
        )

    logger.info(f"User ID: {server_config.user_id}")
    logger.info(f"API token: {api_token_log_hider(server_config.api_token_id)}")
    logger.debug(f"PDF url: {server_config.link_pdf}")
    logger.debug(f"JPG url: {server_config.link_jpg}")
    logger.debug(f"RU Audio url: {server_config.link_audio_ru}")
    logger.debug(f"RU Video url: {server_config.link_video_ru}")
    logger.debug(f"EN Audio url: {server_config.link_audio_en}")
    logger.debug(f"EN Video url: {server_config.link_video_en}")

    return server_config
