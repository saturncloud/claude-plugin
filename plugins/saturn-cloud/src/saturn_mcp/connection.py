"""Saturn Cloud connection helpers."""

from typing import Optional

from saturn_client import SaturnConnection
from saturn_api import ApiClient, Configuration


_connection: Optional[SaturnConnection] = None
_api_client: Optional[ApiClient] = None


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


def resolve_resource_id(resource_type: str, resource_name: str, owner_name: Optional[str] = None) -> str:
    """Look up a resource and return its state.id."""
    conn = get_connection()
    resource = conn.get_resource(resource_type, resource_name, owner_name=owner_name)
    return resource["state"]["id"]
