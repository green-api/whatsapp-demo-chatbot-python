from pydantic import Field, model_validator
from pydantic_settings import BaseSettings


class Envs(BaseSettings):

    # Debug mode. Can be extracted from DEBUG env, default == False
    # Use it for local development
    debug: bool | None = False

    # Instance credentials (for DEBUG mode only).
    # Default None for both (required when DEBUG=True)
    debug_user_id: str | None = None
    debug_api_token_id: str | None = None

    # Link for file urls (for DEBUG mode only)
    # (required when DEBUG=True)
    debug_link_pdf: str | None = None
    debug_link_jpg: str | None = None
    debug_link_audio_ru: str | None = None
    debug_link_video_ru: str | None = None
    debug_link_audio_en: str | None = None
    debug_link_video_en: str | None = None

    # App name. Can be extracted from APP_NAME env, default == "sw-chatbot-7103"
    app_name: str | None = "sw-chatbot-7103"

    # Envs from config/.env file (Just for backwards compability)
    active_profile: str = Field(..., env="ACTIVE_PROFILE")
    spring_cloud_config_uri: str = Field(..., env="SPRING_CLOUD_CONFIG_URI")

    @model_validator(mode="after")
    def debug_mode_validator(self):
        """
        If debug mode enabled, this validator
        checking all required envs for DEBUG mode
        """

        if self.debug and not self.debug_user_id and not self.debug_api_token_id:
            raise ValueError(
                "When debug mode is enabled, "
                "you must pass both instance credentials in "
                "DEBUG_USER_ID and DEBUG_API_TOKEN_ID envs"
            )

        if self.debug and not all(
            (
                self.debug_link_pdf,
                self.debug_link_jpg,
                self.debug_link_audio_ru,
                self.debug_link_video_ru,
                self.debug_link_audio_en,
                self.debug_link_video_en,
            )
        ):
            raise ValueError(
                "When debug mode is enabled, you must pass all "
                "required links for correct bot functionality (DEBUG_LINK_*)"
            )

        return self

    class Config:
        env_file = "config/.env"
        env_file_encoding = "utf-8"


def init_envs():
    return Envs()
