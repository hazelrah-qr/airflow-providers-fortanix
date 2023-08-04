from __future__ import annotations

import os
import time

from airflow.secrets import BaseSecretsBackend
from airflow.utils.log.logging_mixin import LoggingMixin
from sdkms.v1.api_client import ApiClient
from sdkms.v1.apis.authentication_api import AuthenticationApi
from sdkms.v1.apis.security_objects_api import SecurityObjectsApi
from sdkms.v1.models.sobject_descriptor import SobjectDescriptor


class FortanixApiToken:
    """
    A Fortanix API token
    """

    def __init__(self, token: str, expires: int = 600) -> None:
        self.token = token
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
        self._client = ApiClient()
        self._client.configuration.host = os.environ.get("FORTANIX_HOST")
        self._client.configuration.app_api_key = os.environ.get("FORTANIX_API_KEY")
        self.api_token = None
        if self._client.configuration.host is None:
            self.logger().warning("FORTANIX_HOST environment variable is not set")
        if self._client.configuration.app_api_key is None:
            self.logger().warning("FORTANIX_API_KEY environment variable is not set")

    def _get_token(self) -> str:
        auth_instance = AuthenticationApi(api_client=self._client)
        auth = auth_instance.authorize()
        return FortanixApiToken(auth.access_token, auth.expires_in)

    def _get_secret(self, conn_id: str) -> str:
        if not self.api_token or self.api_token.expired():
            self.api_token = self._get_token()

        self._client.configuration.access_token = self.api_token.token
        api_instance = SecurityObjectsApi(api_client=self._client)
        request = SobjectDescriptor(name=conn_id)
        secret = api_instance.get_security_object_value(request)
        return secret

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

        return Connection(conn_id, uri=secret.value)
