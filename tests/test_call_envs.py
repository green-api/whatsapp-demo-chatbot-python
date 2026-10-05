from unittest import TestCase
from pydantic import ValidationError
from internal.envs import Envs


class CallEnvsTest(TestCase):
    def test_default_and_custom_hosts(self):
        defaults = Envs(debug=False, _env_file=None)

        self.assertEqual(defaults.api_url, "https://api.green-api.com")
        self.assertEqual(defaults.media_url, "https://media.green-api.com")

        custom = Envs(
            debug=False, api_url="https://pool.api.invalid",
            media_url="https://pool.media.invalid", _env_file=None,
        )

        self.assertEqual(custom.api_url, "https://pool.api.invalid")
        self.assertEqual(custom.media_url, "https://pool.media.invalid")

    def test_invalid_media_url_is_rejected(self):
        with self.assertRaises(ValidationError):
            Envs(debug=False, media_url="pool.media.invalid", _env_file=None)
