from unittest import mock
import os
from src.fortanix_backend import FortanixBackend


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
        backend._client.configuration.host = os.environ.get("FORTANIX_HOST")
        backend._client.configuration.app_api_key = os.environ.get("FORTANIX_API_KEY")
