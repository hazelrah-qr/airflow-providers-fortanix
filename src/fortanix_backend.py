from __future__ import annotations

import os
import time

from airflow.secrets import BaseSecretsBackend
from airflow.utils.log.logging_mixin import LoggingMixin
from sdkms.v1.api_client import ApiClient
from sdkms.v1.apis.authentication_api import AuthenticationApi
from sdkms.v1.apis.security_objects_api import SecurityObjectsApi
from sdkms.v1.configuration import Configuration


class FortanixApiToken:
    """
    A Fortanix API token
    """

    def __init__(self, access_token: str, expires: int = 600) -> None:
        self.access_token = access_token
        self.expires = time.time() + expires

    def expired(self) -> bool:
        """
        Check if the token has expired
        """
        return time.time() > self.expires


class FortanixBackend(BaseSecretsBackend, LoggingMixin):
    """
    Fortanix KMS backend for Airflow
    """

    def __init__(self) -> None:
        super().__init__()
        self.default_config = self._create_api_config()
        self._client = ApiClient(configuration=self.default_config)
        self.api_token = None

    def _get_token(self) -> str:
        auth_instance = AuthenticationApi(api_client=self._client)
        auth = auth_instance.authorize()
        return FortanixApiToken(auth.access_token, auth.expires_in)

    def _create_api_config(self) -> Configuration:
        if os.environ.get("FORTANIX_HOST") is None:
            self.logger().warning("FORTANIX_HOST environment variable is not set")
        if os.environ.get("FORTANIX_API_KEY") is None:
            self.logger().warning("FORTANIX_API_KEY environment variable is not set")

        config = Configuration()
        config.host = os.environ.get("FORTANIX_HOST")
        config.app_api_key = os.environ.get("FORTANIX_API_KEY")
        config.api_key_prefix["Authorization"] = "Bearer"
        config.ssl_ca_cert = "/etc/ssl/certs/ca-certificates.crt"
        return config

    def _get_secret(self, conn_id: str) -> str:
        if not self.api_token or self.api_token.expired():
            self.api_token = self._get_token()

        self._client.configuration.api_key[
            "Authorization"
        ] = self.api_token.access_token

        api_instance = SecurityObjectsApi(api_client=self._client)
        secrets = api_instance.get_security_objects()
        for secret in secrets:
            if secret.name == conn_id:
                key = api_instance.get_security_object_value(key_id=secret.kid)
                return key.value.decode("utf-8")
        return None

    def get_connection(self, conn_id: str):
        """
        Get a connection from Fortanix KMS
        """

        # The Connection needs to be locally imported because otherwisewe get
        # cyclic import problems when instantiating the backend during configuration
        from airflow.models.connection import Connection

        secret = self._get_secret(conn_id)
        if secret is None:
            return None
        return Connection.from_json(value=secret, conn_id=conn_id)
