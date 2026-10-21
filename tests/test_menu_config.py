import logging
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from yaml import safe_load

from internal.config import init_config
from internal.envs import Envs
from internal.utils import render_main_menu


class MenuConfigTest(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.answers = safe_load(Path("config/data.yml").read_text(encoding="utf-8"))

    def test_chatgpt_is_always_visible_and_call_item_keeps_line_breaks(self):
        for language in ("ru", "en", "he", "es", "kz"):
            with self.subTest(language=language):
                enabled = render_main_menu(self.answers, language, True)
                disabled = render_main_menu(self.answers, language, False)
                self.assertIn("*13*.", enabled)
                self.assertIn("\n*14*.", enabled)
                self.assertIn("\n*18*.", enabled)
                self.assertIn("\n*14*.", disabled)
                self.assertIn("\n*15*.", disabled)
                self.assertIn("\n*17*.", disabled)
                self.assertNotIn("*18*.", disabled)
                self.assertNotIn("{menu_item_", enabled + disabled)
                self.assertNotIn("\n\n*15*.", disabled)

    def test_spring_call_settings_fall_back_to_debug_envs(self):
        envs = Envs(
            debug=False, debug_call_ring_timeout_seconds=31,
            debug_call_incoming_ring_timeout_seconds=59,
            debug_call_talk_timeout_seconds=181,
            debug_call_realtime_model="test-model",
            debug_call_realtime_voice="test-voice",
            _env_file=None,
        )
        spring_values = {
            "api_url": "https://api.invalid",
            "media_url": "https://media.invalid",
            "call_shutdown_timeout_seconds": 10,
        }
        with patch("internal.config.ClientConfigurationBuilder") as builder, patch(
            "internal.config.SpringConfigClient"
        ) as client:
            builder.return_value.app_name.return_value.profile.return_value.address.return_value.build.return_value = object()
            client.return_value.get_config.return_value = spring_values
            config = init_config(envs, logging.getLogger("test-menu-config"))
            self.assertEqual(
                (
                    config.call_ring_timeout_seconds,
                    config.call_incoming_ring_timeout_seconds,
                    config.call_talk_timeout_seconds,
                    config.call_realtime_model,
                    config.call_realtime_voice,
                ),
                (31, 59, 181, "test-model", "test-voice"),
            )

            spring_values.update({
                "call_ring_timeout_seconds": 41,
                "call_incoming_ring_timeout_seconds": 61,
                "call_talk_timeout_seconds": 201,
                "call_realtime_model": "spring-model",
                "call_realtime_voice": "spring-voice",
            })
            config = init_config(envs, logging.getLogger("test-menu-config"))
            self.assertEqual(
                (
                    config.call_ring_timeout_seconds,
                    config.call_incoming_ring_timeout_seconds,
                    config.call_talk_timeout_seconds,
                    config.call_realtime_model,
                    config.call_realtime_voice,
                ),
                (41, 61, 201, "spring-model", "spring-voice"),
            )
