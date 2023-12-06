import logging
import os
from functools import cache

from dotenv import load_dotenv
from spring_config import ClientConfigurationBuilder
from spring_config.client import SpringConfigClient

logger = logging.getLogger(__name__)


class ServerConfig:
    def __init__(self, user_id: str, api_token_id: str, pool_id: str,
                 server_id: str, app_name: str, link_1: str, link_2: str):
        self.user_id = user_id
        self.api_token_id = api_token_id
        self.pool_id = pool_id
        self.server_id = server_id
        self.app_name = app_name
        self.link_1 = link_1
        self.link_2 = link_2


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
    pool_id, server_id = active_profile.split(",")

    endpoint = __none_if_empty_str(os.environ.get("SPRING_CLOUD_CONFIG_URI"))
    if not debug and endpoint is None:
        raise Exception("SPRING_CLOUD_CONFIG_URI not set!")

    if endpoint is None:
        api_port = 0
        sapi_params_dict = os.environ
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
    slink_1 = str(config_result.get("link_1"))
    slink_2 = str(config_result.get("link_2"))

    logger.info("user id is: " + sapi_user_id)
    logger.info("api token id is: " + sapi_user_token)
    logger.info("link for pdf is: " + slink_1)
    logger.info("link for jpg is: " + slink_2)
    logger.info("config loaded")

    return ServerConfig(
        user_id=sapi_user_id,
        api_token_id=sapi_user_token,
        link_1=slink_1,
        link_2=slink_2,
        pool_id=pool_id,
        server_id=server_id,
        app_name=app_name,
    )
