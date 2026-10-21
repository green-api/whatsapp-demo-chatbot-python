from unittest import TestCase
from unittest.mock import patch
from pydantic import ValidationError
from internal.envs import Envs


class CallEnvsTest(TestCase):
    def test_default_and_custom_hosts(self):
        defaults = Envs(debug=False, _env_file=None)

        self.assertEqual(defaults.debug_api_url, "https://api.green-api.com")
        self.assertEqual(defaults.debug_media_url, "https://media.green-api.com")

        custom = Envs(
            debug=False, debug_api_url="https://pool.api.invalid",
            debug_media_url="https://pool.media.invalid", _env_file=None,
        )

        self.assertEqual(custom.debug_api_url, "https://pool.api.invalid")
        self.assertEqual(custom.debug_media_url, "https://pool.media.invalid")

    def test_invalid_media_url_is_rejected(self):
        with self.assertRaises(ValidationError):
            Envs(debug=False, debug_media_url="pool.media.invalid", _env_file=None)

    def test_debug_environment_variable_names(self):
        values = {
            "DEBUG": "true",
            "DEBUG_USER_ID": "test-instance",
            "DEBUG_API_TOKEN_ID": "test-token",
            "DEBUG_API_URL": "https://debug-api.invalid",
            "DEBUG_MEDIA_URL": "https://debug-media.invalid",
            "DEBUG_CALL_RING_TIMEOUT_SECONDS": "31",
            "DEBUG_CALL_INCOMING_RING_TIMEOUT_SECONDS": "59",
            "DEBUG_CALL_TALK_TIMEOUT_SECONDS": "181",
            "DEBUG_CALL_SHUTDOWN_TIMEOUT_SECONDS": "32",
            "DEBUG_CALL_REALTIME_MODEL": "test-model",
            "DEBUG_CALL_REALTIME_VOICE": "test-voice",
            "OPENAI_API_KEY": "test-key",
        }

        with patch.dict("os.environ", values, clear=True):
            envs = Envs(_env_file=None)

        self.assertEqual(envs.debug_api_url, values["DEBUG_API_URL"])
        self.assertEqual(envs.debug_media_url, values["DEBUG_MEDIA_URL"])
        self.assertEqual(envs.debug_call_ring_timeout_seconds, 31)
        self.assertEqual(envs.debug_call_incoming_ring_timeout_seconds, 59)
        self.assertEqual(envs.debug_call_talk_timeout_seconds, 181)
        self.assertEqual(envs.debug_call_shutdown_timeout_seconds, 32)
        self.assertEqual(envs.debug_call_realtime_model, values["DEBUG_CALL_REALTIME_MODEL"])
        self.assertEqual(envs.debug_call_realtime_voice, values["DEBUG_CALL_REALTIME_VOICE"])
