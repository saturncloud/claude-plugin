"""Saturn Cloud MCP server for Claude Code."""

import json
import os
import socket
import subprocess
from pathlib import Path
from typing import Any, Awaitable, Dict, List, Optional, TypeVar

from fastmcp import FastMCP
from saturn_api.api.deployments_api import DeploymentsApi
from saturn_api.api.ssh_public_keys_api import SshPublicKeysApi
from saturn_api.api.workspaces_api import WorkspacesApi
from saturn_api.exceptions import ApiException
from saturn_api.models.ssh_public_key_create import SSHPublicKeyCreate
from saturn_client.core import ServerOptionTypes

from saturn_mcp.connection import get_api_client, get_connection, resolve_resource_id

mcp = FastMCP("saturn")

T = TypeVar("T")


@mcp.tool()
def saturn_list_resources(
    resource_type: Optional[str] = None,
    name: Optional[str] = None,
    status: Optional[str] = None,
) -> str:
    """List Saturn Cloud resources with optional filters.

    Args:
        resource_type: Filter by type: workspace, job, or deployment.
        name: Filter by resource name (exact match).
        status: Filter by status: running, stopped, pending, or error.

    Returns:
        JSON array of resource recipes (with state).
    """
    conn = get_connection()
    results = conn.list_resources(
        resource_type=resource_type,
        resource_name=name,
        status=status,
    )
    return json.dumps(results, indent=2)


@mcp.tool()
def saturn_list_instance_types(glob: Optional[str] = None) -> str:
    """List available compute instance types (sizes) for the Saturn Cloud installation.

    Hits /api/info/servers and returns the sizes catalog, sorted by (gpu, cores).

    Args:
        glob: Optional glob pattern to filter by name (e.g. 'nebius-cpu-*').

    Returns:
        JSON array of size dicts with at least name, cores, gpu, memory.
    """
    conn = get_connection()
    sizes = conn.list_options(ServerOptionTypes.SIZES, glob=glob)
    return json.dumps(list(sizes), indent=2)


@mcp.tool()
def saturn_list_instance_type_configs() -> str:
    """List the recommended instance type configurations of the installation.

    A configuration is an operator-defined, ordered list of instance types on
    one cluster (for example `shadeform-rtxpro6000-1gpu`: one GPU type at
    several sites). A recipe names one with `instance_type_config` instead of
    `instance_type`; the resource starts at whichever listed type has stock,
    tried in order. Prefer one on clusters where it is offered: a single site
    waits whenever that site is sold out.

    Returns:
        JSON array of {name, display_name, description, cluster, sizes, default}.
        Empty on installations that offer none.
    """
    conn = get_connection()
    response = conn.session.get(f"{conn.url.rstrip('/')}/api/info/servers")
    response.raise_for_status()
    return json.dumps(response.json().get("instance_type_configs", []), indent=2)


@mcp.tool()
def saturn_get_resource(
    resource_type: str,
    resource_name: str,
    owner_name: Optional[str] = None,
    as_template: bool = False,
) -> str:
    """Get a single Saturn Cloud resource's full recipe.

    Args:
        resource_type: The resource type: workspace, job, or deployment.
        resource_name: The name of the resource.
        owner_name: Owner name if looking up another user's resource.
        as_template: If true, return the recipe without state (for cloning/modifying).

    Returns:
        Full recipe dict as JSON.
    """
    conn = get_connection()
    result = conn.get_resource(
        resource_type, resource_name, owner_name=owner_name, as_template=as_template
    )
    return json.dumps(result, indent=2)


@mcp.tool()
def saturn_apply_recipe(recipe: Dict[str, Any]) -> str:
    """Create or update a Saturn Cloud resource from a recipe dict.

    Use this to create new resources or update existing ones. The recipe dict
    should follow the Saturn Cloud recipe schema (see recipe-reference.md).

    Args:
        recipe: The full recipe dict with 'type' and 'spec' fields.

    Returns:
        The applied recipe with state, as JSON.
    """
    conn = get_connection()
    result = conn.apply(recipe)
    return json.dumps(result, indent=2)


@mcp.tool()
def saturn_delete_resource(
    resource_type: str,
    resource_name: str,
    owner_name: Optional[str] = None,
) -> str:
    """Delete a Saturn Cloud resource.

    Args:
        resource_type: The resource type: workspace, job, or deployment.
        resource_name: The name of the resource to delete.
        owner_name: Owner name if the resource belongs to another user or a group.

    Returns:
        Confirmation message.
    """
    conn = get_connection()
    resource_id = resolve_resource_id(resource_type, resource_name, owner_name=owner_name)
    status_code = conn.delete(resource_type, resource_id)
    return f"Deleted {resource_type} '{resource_name}' (status {status_code})"


@mcp.tool()
def saturn_start_resource(
    resource_type: str,
    resource_name: str,
    owner_name: Optional[str] = None,
) -> str:
    """Start a stopped Saturn Cloud resource.

    Args:
        resource_type: The resource type: workspace, job, or deployment.
        resource_name: The name of the resource to start.
        owner_name: Owner name if the resource belongs to another user or a group.

    Returns:
        Confirmation with resource status.
    """
    conn = get_connection()
    resource_id = resolve_resource_id(resource_type, resource_name, owner_name=owner_name)
    result = conn.start(resource_type, resource_id)
    status = result.get("status", "unknown")
    return f"Started {resource_type} '{resource_name}' — status: {status}"


@mcp.tool()
def saturn_stop_resource(
    resource_type: str,
    resource_name: str,
    owner_name: Optional[str] = None,
) -> str:
    """Stop a running Saturn Cloud resource.

    Args:
        resource_type: The resource type: workspace, job, or deployment.
        resource_name: The name of the resource to stop.
        owner_name: Owner name if the resource belongs to another user or a group.

    Returns:
        Confirmation message.
    """
    conn = get_connection()
    resource_id = resolve_resource_id(resource_type, resource_name, owner_name=owner_name)
    conn.stop(resource_type, resource_id)
    return f"Stopped {resource_type} '{resource_name}'"


@mcp.tool()
def saturn_get_logs(
    resource_type: str,
    resource_name: str,
    pod_name: Optional[str] = None,
    source: Optional[str] = None,
    all_containers: bool = False,
    owner_name: Optional[str] = None,
) -> str:
    """Get logs for a Saturn Cloud resource.

    Args:
        resource_type: The resource type: workspace, job, or deployment.
        resource_name: The name of the resource.
        pod_name: Specific pod name (optional, defaults to latest).
        source: Log source: 'live' or 'historical' (optional, tries both).
        all_containers: If true, include init containers and sidecars.
        owner_name: Owner name if the resource belongs to another user or a group.

    Returns:
        Formatted log output.
    """
    conn = get_connection()
    logs = conn.get_logs(
        resource_type,
        resource_name,
        owner_name=owner_name,
        pod_name=pod_name,
        source=source,
        all_containers=all_containers,
    )
    return logs if logs else "No logs available."


@mcp.tool()
def saturn_schedule_job(
    job_name: str,
    cron_schedule: Optional[str] = None,
    disable: bool = False,
    owner_name: Optional[str] = None,
) -> str:
    """Set, update, or disable a cron schedule on a Saturn Cloud job.

    Args:
        job_name: The name of the job.
        cron_schedule: Cron expression (e.g. '0 */6 * * *'). Omit to keep current schedule.
        disable: If true, disable the schedule instead of enabling it.
        owner_name: Owner name if the job belongs to another user or a group.

    Returns:
        Confirmation with schedule details.
    """
    conn = get_connection()
    job_id = resolve_resource_id("job", job_name, owner_name=owner_name)
    result = conn.schedule(job_id, cron_schedule=cron_schedule, disable=disable)
    if disable:
        return f"Disabled schedule for job '{job_name}'"
    schedule_info = result.get("cron_schedule_options", {}).get("schedule", "unknown")
    return f"Scheduled job '{job_name}' with cron: {schedule_info}"


DEFAULT_SATURN_KEY_PATH = Path.home() / ".ssh" / "id_ed25519_saturn"


# Atlas answers 403 with this error_code when a workspace, job, deployment
# or Dask cluster token calls a route that needs a user (saturncloud/saturn#7271).
RESOURCE_TOKEN_NOT_ALLOWED = "TokenErrors.RESOURCE_TOKEN_NOT_ALLOWED"

RESOURCE_TOKEN_HELP = (
    "SSH key setup is not available with a Saturn resource's token. The "
    "SATURN_TOKEN that a workspace, job or deployment gets cannot manage SSH "
    "keys. Run SSH key setup from your own machine instead. Or set "
    "SATURN_TOKEN to a user API token yourself, which makes every Saturn "
    "tool act as you rather than as this resource."
)


def _ssh_key_api() -> SshPublicKeysApi:
    return SshPublicKeysApi(get_api_client())


async def _ssh_key_call(call: Awaitable[T]) -> T:
    """Await an SSH key API call, replacing Atlas's resource-token 403
    with instructions for the user."""
    try:
        return await call
    except ApiException as err:
        if err.status == 403 and RESOURCE_TOKEN_NOT_ALLOWED in (err.body or ""):
            raise RuntimeError(RESOURCE_TOKEN_HELP) from err
        raise


@mcp.tool()
async def saturn_ssh_key_list(identity: Optional[str] = None) -> str:
    """List SSH public keys registered with Saturn Cloud.

    Args:
        identity: Filter to keys owned by a specific user or group name.
            Omit to list keys for the calling user.

    Returns:
        JSON array of {id, name, identity, created_at}.
    """
    result = await _ssh_key_call(_ssh_key_api().list(identity=identity))
    return json.dumps([k.to_dict() for k in result.ssh_public_keys], indent=2, default=str)


@mcp.tool()
async def saturn_ssh_key_register(
    name: str,
    public_key: str,
    identity: Optional[str] = None,
) -> str:
    """Register an SSH public key with Saturn Cloud.

    Args:
        name: Human-readable name for the key (shown in the Saturn UI).
        public_key: The full public key string (e.g. 'ssh-ed25519 AAAA... comment').
        identity: User or group name the key should authenticate as.
            Omit to register against the calling user.

    Returns:
        JSON of the created key: {id, name, identity, created_at}.
    """
    body = SSHPublicKeyCreate(name=name, value=public_key.strip(), identity=identity)
    created = await _ssh_key_call(_ssh_key_api().create(ssh_public_key_create=body))
    return json.dumps(created.to_dict(), indent=2, default=str)


@mcp.tool()
async def saturn_ssh_key_delete(key_id: str) -> str:
    """Delete an SSH public key from Saturn Cloud by ID."""
    await _ssh_key_call(_ssh_key_api().delete(ssh_publickey_id=key_id))
    return f"Deleted SSH public key '{key_id}'"


@mcp.tool()
async def saturn_ssh_setup(identity: Optional[str] = None) -> str:
    """Set up SSH access to Saturn Cloud end-to-end.

    Idempotent. Ensures a Saturn-dedicated keypair exists locally at
    ~/.ssh/id_ed25519_saturn, then registers the public half with Saturn
    under the given identity if it's not already registered under the
    name 'claude-code-<hostname>'.

    Args:
        identity: User or group name to register the key against. Omit
            to register against the calling user.

    Returns:
        Plain-text summary describing what was done.
    """
    key_path = DEFAULT_SATURN_KEY_PATH
    pub_path = Path(str(key_path) + ".pub")
    actions: List[str] = []

    if not key_path.exists():
        ssh_dir = key_path.parent
        ssh_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        result = subprocess.run(
            [
                "ssh-keygen",
                "-t", "ed25519",
                "-N", "",
                "-C", f"saturn-cloud-{socket.gethostname()}",
                "-f", str(key_path),
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"ssh-keygen failed (exit {result.returncode}): "
                f"{(result.stderr or result.stdout).strip()}"
            )
        actions.append(f"generated new keypair at {key_path}")
    else:
        actions.append(f"reusing existing keypair at {key_path}")

    public_key = pub_path.read_text().strip()
    key_name = f"claude-code-{socket.gethostname()}"

    api = _ssh_key_api()
    existing = await _ssh_key_call(api.list(identity=identity, name=key_name))
    matching = [k for k in existing.ssh_public_keys if k.name == key_name]

    if matching:
        actions.append(f"key '{key_name}' already registered (id={matching[0].id})")
    else:
        body = SSHPublicKeyCreate(name=key_name, value=public_key, identity=identity)
        created = await _ssh_key_call(api.create(ssh_public_key_create=body))
        actions.append(
            f"registered '{key_name}' with Saturn"
            + (f" under identity '{identity}'" if identity else "")
            + f" (id={created.id})"
        )

    return "\n".join(actions)


@mcp.tool()
async def saturn_get_ssh_url(
    resource_type: str,
    resource_name: str,
    owner_name: Optional[str] = None,
) -> str:
    """Get the SSH URL of a running workspace or deployment.

    The SSH URL is server-populated once the resource is running with
    `start_ssh: true`. Use it as the target for SSH dispatch:
        ssh -i ~/.ssh/id_ed25519_saturn <ssh_url>

    Args:
        resource_type: 'workspace' or 'deployment'.
        resource_name: Name of the resource.
        owner_name: Owner (user or group) name. Required if the resource
            belongs to a user or group other than the current API token's
            user.

    Returns:
        The ssh_url string, or an error message if the resource isn't
        running or `start_ssh` isn't enabled.
    """
    client = get_api_client()
    rt = resource_type.lower()
    if rt == "workspace":
        api = WorkspacesApi(client)
        result = await api.list(owner_name=owner_name, name=resource_name)
        items = result.workspaces
    elif rt == "deployment":
        api = DeploymentsApi(client)
        result = await api.list(owner_name=owner_name, name=resource_name)
        items = result.deployments
    else:
        raise ValueError(f"resource_type must be 'workspace' or 'deployment', got {resource_type!r}")

    match = next((r for r in items if r.name == resource_name), None)
    if match is None:
        return f"No {rt} named {resource_name!r} found" + (f" for owner {owner_name!r}" if owner_name else "")

    ssh_url = getattr(match, "ssh_url", None)
    if not ssh_url:
        return (
            f"{rt} {resource_name!r} has no ssh_url "
            f"(status: {getattr(match, 'status', '?')}, "
            f"start_ssh: {getattr(match, 'start_ssh', '?')})"
        )
    return ssh_url


def main():
    mcp.run()


if __name__ == "__main__":
    main()
