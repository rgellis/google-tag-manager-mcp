"""Google Tag Manager API client for the MCP server.

Tag Manager is a discovery-document API: Google ships no dedicated SDK for it in
any language. The official transport is ``google-api-python-client``, whose
resource objects are built dynamically at runtime and are therefore untyped.

``google-api-python-client-stubs`` supplies complete static types for
``tagmanager/v2``. Those stubs exist only at type-check time, so the
``TagManagerResource`` import below is guarded by ``TYPE_CHECKING`` and must stay
that way -- importing it at runtime raises ImportError.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Optional

import google.auth
from google.auth.credentials import Credentials as BaseCredentials
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from src.utils import env_flag, get_logger

if TYPE_CHECKING:
    from googleapiclient._apis.tagmanager.v2 import TagManagerResource

logger = get_logger(__name__)

TOKEN_URI = "https://oauth2.googleapis.com/token"

SCOPE_READONLY = "https://www.googleapis.com/auth/tagmanager.readonly"
SCOPE_EDIT_CONTAINERS = "https://www.googleapis.com/auth/tagmanager.edit.containers"
SCOPE_EDIT_CONTAINERVERSIONS = (
    "https://www.googleapis.com/auth/tagmanager.edit.containerversions"
)
SCOPE_DELETE_CONTAINERS = "https://www.googleapis.com/auth/tagmanager.delete.containers"
SCOPE_MANAGE_ACCOUNTS = "https://www.googleapis.com/auth/tagmanager.manage.accounts"
SCOPE_MANAGE_USERS = "https://www.googleapis.com/auth/tagmanager.manage.users"
SCOPE_PUBLISH = "https://www.googleapis.com/auth/tagmanager.publish"

#: Every scope the API defines. Tag Manager splits write access six ways -- a
#: token holding only `edit.containers` cannot publish a version or manage
#: users -- so full coverage of the API requires all of them.
SCOPES_FULL: list[str] = [
    SCOPE_READONLY,
    SCOPE_EDIT_CONTAINERS,
    SCOPE_EDIT_CONTAINERVERSIONS,
    SCOPE_DELETE_CONTAINERS,
    SCOPE_MANAGE_ACCOUNTS,
    SCOPE_MANAGE_USERS,
    SCOPE_PUBLISH,
]


class ReadOnlyError(RuntimeError):
    """Raised when a mutating tool is called while the server is read-only."""


class TagManagerClient:
    """Client for the Tag Manager API.

    Credentials are resolved in this order:

    1. OAuth installed-app credentials from ``GOOGLE_CLIENT_ID``,
       ``GOOGLE_CLIENT_SECRET`` and ``GOOGLE_TAG_MANAGER_REFRESH_TOKEN``.
    2. Application Default Credentials, which covers a service account via
       ``GOOGLE_APPLICATION_CREDENTIALS`` as well as local ``gcloud`` auth.

    Setting ``TAG_MANAGER_READ_ONLY=true`` requests only the readonly scope and
    makes every mutating tool refuse to run. This matters more here than on most
    Google APIs: a Tag Manager container holds the tracking code of a live
    website, and publishing a container version takes effect on production
    immediately, with no staged rollout and no undo beyond publishing an older
    version over the top.
    """

    def __init__(self, read_only: Optional[bool] = None) -> None:
        self._service: Optional[TagManagerResource] = None
        self.read_only: bool = (
            read_only
            if read_only is not None
            else env_flag("TAG_MANAGER_READ_ONLY", default=False)
        )

    @property
    def scopes(self) -> list[str]:
        """The OAuth scopes this client requests."""
        return [SCOPE_READONLY] if self.read_only else list(SCOPES_FULL)

    def resolve_credentials(self) -> BaseCredentials:
        """Resolve credentials from the environment."""
        client_id = os.environ.get("GOOGLE_CLIENT_ID")
        client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
        refresh_token = os.environ.get("GOOGLE_TAG_MANAGER_REFRESH_TOKEN")

        if client_id and client_secret and refresh_token:
            logger.info("Using OAuth refresh token authentication")
            return Credentials(
                token=None,
                refresh_token=refresh_token,
                client_id=client_id,
                client_secret=client_secret,
                token_uri=TOKEN_URI,
                scopes=self.scopes,
            )

        logger.info("Using Application Default Credentials")
        credentials, _ = google.auth.default(scopes=self.scopes)
        return credentials

    @property
    def service(self) -> TagManagerResource:
        """Get or build the Tag Manager resource client."""
        if self._service is None:
            self._service = build(
                "tagmanager",
                "v2",
                credentials=self.resolve_credentials(),
                cache_discovery=False,
            )
            logger.info("Tag Manager client initialized (read_only=%s)", self.read_only)
        return self._service

    def require_write(self, operation: str) -> None:
        """Refuse a mutating operation when the server is in read-only mode."""
        if self.read_only:
            raise ReadOnlyError(
                f"Refusing to run '{operation}': this server is running with "
                "TAG_MANAGER_READ_ONLY=true, which permits read operations only."
            )

    def close(self) -> None:
        """Release the underlying client."""
        if self._service is not None:
            self._service.close()
            self._service = None
            logger.info("Tag Manager client closed")


_client: Optional[TagManagerClient] = None


def get_client() -> TagManagerClient:
    """Get the global Tag Manager client instance."""
    if _client is None:
        raise RuntimeError("Client not initialized. Call set_client first.")
    return _client


def set_client(client: Optional[TagManagerClient]) -> None:
    """Set (or clear) the global Tag Manager client instance."""
    global _client
    _client = client
