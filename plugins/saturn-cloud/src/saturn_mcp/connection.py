"""Saturn Cloud connection helpers."""

from typing import Optional

from saturn_client import SaturnConnection


_connection: Optional[SaturnConnection] = None


def get_connection() -> SaturnConnection:
    """Get or create a cached SaturnConnection instance."""
    global _connection
    if _connection is None:
        _connection = SaturnConnection()
    return _connection


def resolve_resource_id(resource_type: str, resource_name: str, owner_name: Optional[str] = None) -> str:
    """Look up a resource and return its state.id."""
    conn = get_connection()
    resource = conn.get_resource(resource_type, resource_name, owner_name=owner_name)
    return resource["state"]["id"]
