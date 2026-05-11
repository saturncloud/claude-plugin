"""Saturn Cloud MCP server for Claude Code."""

import json
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP
from saturn_client.core import ServerOptionTypes

from saturn_mcp.connection import get_connection, resolve_resource_id

mcp = FastMCP("saturn")


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
def saturn_delete_resource(resource_type: str, resource_name: str) -> str:
    """Delete a Saturn Cloud resource.

    Args:
        resource_type: The resource type: workspace, job, or deployment.
        resource_name: The name of the resource to delete.

    Returns:
        Confirmation message.
    """
    conn = get_connection()
    resource_id = resolve_resource_id(resource_type, resource_name)
    status_code = conn.delete(resource_type, resource_id)
    return f"Deleted {resource_type} '{resource_name}' (status {status_code})"


@mcp.tool()
def saturn_start_resource(resource_type: str, resource_name: str) -> str:
    """Start a stopped Saturn Cloud resource.

    Args:
        resource_type: The resource type: workspace, job, or deployment.
        resource_name: The name of the resource to start.

    Returns:
        Confirmation with resource status.
    """
    conn = get_connection()
    resource_id = resolve_resource_id(resource_type, resource_name)
    result = conn.start(resource_type, resource_id)
    status = result.get("status", "unknown")
    return f"Started {resource_type} '{resource_name}' — status: {status}"


@mcp.tool()
def saturn_stop_resource(resource_type: str, resource_name: str) -> str:
    """Stop a running Saturn Cloud resource.

    Args:
        resource_type: The resource type: workspace, job, or deployment.
        resource_name: The name of the resource to stop.

    Returns:
        Confirmation message.
    """
    conn = get_connection()
    resource_id = resolve_resource_id(resource_type, resource_name)
    conn.stop(resource_type, resource_id)
    return f"Stopped {resource_type} '{resource_name}'"


@mcp.tool()
def saturn_get_logs(
    resource_type: str,
    resource_name: str,
    pod_name: Optional[str] = None,
    source: Optional[str] = None,
    all_containers: bool = False,
) -> str:
    """Get logs for a Saturn Cloud resource.

    Args:
        resource_type: The resource type: workspace, job, or deployment.
        resource_name: The name of the resource.
        pod_name: Specific pod name (optional, defaults to latest).
        source: Log source: 'live' or 'historical' (optional, tries both).
        all_containers: If true, include init containers and sidecars.

    Returns:
        Formatted log output.
    """
    conn = get_connection()
    logs = conn.get_logs(
        resource_type,
        resource_name,
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
) -> str:
    """Set, update, or disable a cron schedule on a Saturn Cloud job.

    Args:
        job_name: The name of the job.
        cron_schedule: Cron expression (e.g. '0 */6 * * *'). Omit to keep current schedule.
        disable: If true, disable the schedule instead of enabling it.

    Returns:
        Confirmation with schedule details.
    """
    conn = get_connection()
    job_id = resolve_resource_id("job", job_name)
    result = conn.schedule(job_id, cron_schedule=cron_schedule, disable=disable)
    if disable:
        return f"Disabled schedule for job '{job_name}'"
    schedule_info = result.get("cron_schedule_options", {}).get("schedule", "unknown")
    return f"Scheduled job '{job_name}' with cron: {schedule_info}"


if __name__ == "__main__":
    mcp.run()
