import os
from unittest import mock

from src.providers.fortanix.backend import FortanixBackend


class TestFortanixSecrets:
    @mock.patch.dict(
        "os.environ",
        {
            "FORTANIX_HOST": "https://sdkms.example.com",
            "FORTANIX_API_KEY": "1234567890",
        },
    )
    def test_fortanix_secrets(self):
        backend = FortanixBackend()
        assert backend._client.configuration.host == os.environ.get("FORTANIX_HOST")
        assert backend._client.configuration.app_api_key == os.environ.get("FORTANIX_API_KEY")
