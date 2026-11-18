"""Saturn Cloud connection helpers."""

import os
from typing import Optional

from saturn_client import SaturnConnection
from saturn_api import ApiClient, Configuration


_connection: Optional[SaturnConnection] = None
_api_client: Optional[ApiClient] = None
_user_api_client: Optional[ApiClient] = None

#: Optional user API token for routes that refuse resource tokens (SSH keys).
#: Inside a Saturn workspace, job or deployment, SATURN_TOKEN is that
#: resource's own token, which Atlas refuses on those routes.
USER_TOKEN_ENV = "SATURN_USER_TOKEN"


def get_connection() -> SaturnConnection:
    """Get or create a cached SaturnConnection instance."""
    global _connection
    if _connection is None:
        _connection = SaturnConnection()
    return _connection


def get_api_client() -> ApiClient:
    """Get or create a cached saturn-api ApiClient.

    Reads SATURN_BASE_URL and SATURN_TOKEN from the environment (handled
    by saturn_api.Configuration's defaults).
    """
    global _api_client
    if _api_client is None:
        _api_client = ApiClient(Configuration())
    return _api_client


def get_user_api_client() -> ApiClient:
    """Get a saturn-api ApiClient for routes that need a user API token.

    Uses SATURN_USER_TOKEN when it is set and not empty, otherwise falls
    back to the SATURN_TOKEN client from get_api_client().
    """
    global _user_api_client
    user_token = os.getenv(USER_TOKEN_ENV, "").strip()
    if not user_token:
        return get_api_client()
    if _user_api_client is None:
        _user_api_client = ApiClient(Configuration(access_token=user_token))
    return _user_api_client


def resolve_resource_id(resource_type: str, resource_name: str, owner_name: Optional[str] = None) -> str:
    """Look up a resource and return its state.id."""
    conn = get_connection()
    resource = conn.get_resource(resource_type, resource_name, owner_name=owner_name)
    return resource["state"]["id"]
