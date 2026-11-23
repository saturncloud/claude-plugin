"""Generate skills/saturn/recipe-reference.md from saturn-api Pydantic models.

The structural parts (top-level layout, common spec table, per-resource-type
delta tables, nested-object tables) are derived from the OpenAPI-generated
models. The narrative parts (intro, examples, pitfalls) live as static
templates below — they're hard to derive from models and tend to be the place
human judgment matters.

Run:
    python scripts/generate_recipe_reference.py > skills/saturn/recipe-reference.md

Requires saturn-api importable on sys.path (e.g. install it, or add the local
checkout to PYTHONPATH).
"""
from __future__ import annotations

import enum
import sys
import typing
from typing import Any, get_args, get_origin

from saturn_api.models.deployment_recipe import DeploymentRecipe
from saturn_api.models.deployment_route_recipe import DeploymentRouteRecipe
from saturn_api.models.deployment_spec import DeploymentSpec
from saturn_api.models.dask_cluster_attachment import DaskClusterAttachment
from saturn_api.models.dask_cluster_attachment_scheduler import DaskClusterAttachmentScheduler
from saturn_api.models.dask_cluster_attachment_worker import DaskClusterAttachmentWorker
from saturn_api.models.external_repo_attachment_recipe import ExternalRepoAttachmentRecipe
from saturn_api.models.extra_packages_recipe import ExtraPackagesRecipe
from saturn_api.models.extra_packages_recipe_apt import ExtraPackagesRecipeApt
from saturn_api.models.extra_packages_recipe_conda import ExtraPackagesRecipeConda
from saturn_api.models.extra_packages_recipe_pip import ExtraPackagesRecipePip
from saturn_api.models.job_recipe import JobRecipe
from saturn_api.models.job_spec import JobSpec
from saturn_api.models.secret_attachment_recipe import SecretAttachmentRecipe
from saturn_api.models.shared_folder_attachment_recipe import SharedFolderAttachmentRecipe
from saturn_api.models.viewer_recipe import ViewerRecipe
from saturn_api.models.workspace_recipe import WorkspaceRecipe
from saturn_api.models.workspace_route_recipe import WorkspaceRouteRecipe
from saturn_api.models.workspace_spec import WorkspaceSpec


# ---------------------------------------------------------------------------
# Type rendering
# ---------------------------------------------------------------------------

def _unwrap(annotation: Any) -> Any:
    """Strip Optional[] and Annotated[] wrappers, return the inner type."""
    origin = get_origin(annotation)
    if origin is typing.Union:
        non_none = [a for a in get_args(annotation) if a is not type(None)]
        if len(non_none) == 1:
            return _unwrap(non_none[0])
    if origin is typing.Annotated or str(origin) == "typing.Annotated":
        return _unwrap(get_args(annotation)[0])
    return annotation


def _is_optional(annotation: Any) -> bool:
    if get_origin(annotation) is typing.Union:
        return type(None) in get_args(annotation)
    return False


def render_type(annotation: Any) -> str:
    """Render a Pydantic field annotation into a human-readable type label."""
    inner = _unwrap(annotation)
    origin = get_origin(inner)

    if origin is typing.Literal:
        choices = ", ".join(f"`\"{c}\"`" for c in get_args(inner))
        return f"enum ({choices})"
    if origin is list or origin is typing.List:
        item = render_type(get_args(inner)[0])
        return f"array of {item}"
    if origin is dict or origin is typing.Dict:
        k, v = get_args(inner)
        return f"object ({render_type(k)} → {render_type(v)})"
    if isinstance(inner, type) and issubclass(inner, enum.Enum):
        choices = ", ".join(f"`\"{m.value}\"`" for m in inner)
        return f"enum ({choices})"
    if hasattr(inner, "__name__"):
        name = inner.__name__
        # RootModel-wrapped scalars (e.g. ImageTagReference) — render as string
        if hasattr(inner, "model_fields") and set(inner.model_fields.keys()) == {"root"}:
            return "string"
        # Nested Pydantic model
        if hasattr(inner, "model_fields"):
            return f"[{name}](#{slug(name)})"
        if name == "str":
            return "string"
        if name == "int":
            return "int"
        if name == "bool":
            return "bool"
        if name == "float":
            return "float"
        return f"`{name}`"
    return f"`{inner!r}`"


def slug(s: str) -> str:
    return s.lower().replace("_", "-").replace(" ", "-")


# ---------------------------------------------------------------------------
# Field tables
# ---------------------------------------------------------------------------

# Hand-written one-liners for fields whose Pydantic description isn't enough
# to be useful in the docs. Anything not listed gets a default empty cell.
DESCRIPTIONS: dict[str, str] = {
    "name": "Resource name (unique per owner)",
    "owner": "Owner reference (e.g. `\"primary-tenant/demo\"`)",
    "description": "Human-readable description",
    "tags": "Arbitrary labels",
    "image": "Image reference, e.g. `\"saturncloud/saturn-python:2025.05.01\"`. **Single string, not an object.**",
    "instance_type": "Full instance descriptor (e.g. `\"nebius-cpu-d3-4vcpu-16gb\"`). Use `saturn_list_instance_types` to enumerate. On a resource spec it may also be an ordered list of descriptors (tried in order when one has no capacity), and it is omitted when `instance_type_config` is given.",
    "instance_type_config": "Name of a recommended instance type configuration (e.g. `\"shadeform-rtxpro6000-1gpu\"`): an operator-defined, ordered list of instance types on one cluster. Use `saturn_list_instance_type_configs` to enumerate. **Give this or `instance_type`, never both.**",
    "environment_variables": "Plain env vars. **Dict shape, not array.**",
    "working_directory": "Working directory inside the container",
    "extra_packages": "Package install instructions",
    "start_script": "Shell script run on startup",
    "token_scope": "Saturn token scope; usually auto-set",
    "dask_cluster": "Attached Dask cluster",
    "git_repositories": "Git repos to clone",
    "secrets": "Secret attachments. **Separate from `environment_variables`.**",
    "shared_folders": "Shared-folder mounts",
    "start_dind": "Enable Docker-in-Docker",
    "status": "Desired state",
    "use_spot_instance": "Use spot/preemptible instance",
    "command": "Shell command to execute",
    "scale": "Number of replicas (deployment) or parallel runs (job)",
    "schedule": "Cron expression",
    "concurrency_policy": "Concurrency policy for scheduled jobs",
    "retries": "Number of retries on failure",
    "ide": "IDE",
    "disk_space": "Persistent disk size (e.g. `\"64Gi\"`)",
    "auto_shutoff": "Auto-shutdown timeout",
    "start_ssh": "Enable SSH access",
    "routes": "HTTP route definitions",
    "viewers": "Embedded viewer configurations",
    "self_destruct": "Delete on stop",
    # Nested-type field descriptions
    "url": "Git clone URL (SSH or HTTPS)",
    "path": "Mount/clone path inside container",
    "reference": "Branch, tag, or commit",
    "reference_type": "What kind of reference",
    "on_restart": "Restart policy for the working tree. Server normalizes to `\"reclone\"` for jobs and deployments.",
    "public": "Public repo (no auth required)",
    "location": "Env-var name (or file path if `attachment_type: file`)",
    "attachment_type": "How the secret is exposed",
    "container_port": "Port the service listens on",
    "visibility": "Who can access the route",
    "subdomain": "Custom subdomain",
    "num_workers": "Number of workers",
    "scheduler": "Scheduler config",
    "worker": "Worker config",
    "num_processes": "Processes per worker",
    "num_threads": "Threads per process",
    "use_spot_instances": "Use spot for workers (note: plural, vs `use_spot_instance` on spec)",
    "install": "Space-separated package list",
    "requirements_txt": "Path to requirements file",
    "environment_yml": "Path to environment YAML",
    "use_mamba": "Use mamba instead of conda",
    "identity": "Viewer identity",
    "route": "Route reference",
}


def field_row(name: str, field: Any) -> str:
    type_str = render_type(field.annotation)
    required = "Yes" if field.is_required() else "No"
    desc = DESCRIPTIONS.get(name, "")
    return f"| `{name}` | {type_str} | {required} | {desc} |"


def field_table(model: type, exclude: set[str] = frozenset()) -> str:
    rows = ["| Field | Type | Required | Description |", "|---|---|---|---|"]
    for name, field in model.model_fields.items():
        if name in exclude:
            continue
        rows.append(field_row(name, field))
    return "\n".join(rows)


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def common_field_names() -> list[str]:
    ws = set(WorkspaceSpec.model_fields)
    job = set(JobSpec.model_fields)
    dep = set(DeploymentSpec.model_fields)
    common = ws & job & dep
    # preserve workspace order for stable output
    return [name for name in WorkspaceSpec.model_fields if name in common]


def fields_only_in(spec: type) -> list[str]:
    """Fields on `spec` that are not common to all three specs."""
    common = set(common_field_names())
    return [name for name in spec.model_fields if name not in common]


def render_common_table() -> str:
    common = common_field_names()
    rows = ["| Field | Type | Required | Description |", "|---|---|---|---|"]
    # Use WorkspaceSpec as the source of field metadata for common fields.
    for name in common:
        rows.append(field_row(name, WorkspaceSpec.model_fields[name]))
    return "\n".join(rows)


def render_specific_table(spec: type) -> str:
    only = fields_only_in(spec)
    if not only:
        return "_(none)_"
    rows = ["| Field | Type | Required | Description |", "|---|---|---|---|"]
    for name in only:
        rows.append(field_row(name, spec.model_fields[name]))
    return "\n".join(rows)


NESTED_MODELS: list[type] = [
    ExtraPackagesRecipe,
    ExtraPackagesRecipePip,
    ExtraPackagesRecipeConda,
    ExtraPackagesRecipeApt,
    ExternalRepoAttachmentRecipe,
    SharedFolderAttachmentRecipe,
    SecretAttachmentRecipe,
    DaskClusterAttachment,
    DaskClusterAttachmentScheduler,
    DaskClusterAttachmentWorker,
    WorkspaceRouteRecipe,
    DeploymentRouteRecipe,
    ViewerRecipe,
]


def render_nested_section(model: type) -> str:
    return f"### {model.__name__}\n\n{field_table(model)}"


# ---------------------------------------------------------------------------
# Static narrative
# ---------------------------------------------------------------------------

HEADER = """# Saturn Cloud Recipe Reference

> **Auto-generated** from `saturn-api` Pydantic models.
> Run `python scripts/generate_recipe_reference.py > skills/saturn/recipe-reference.md` to refresh.
> Hand edits to the structural tables will be overwritten — edit the templates and field descriptions in `scripts/generate_recipe_reference.py` instead.

Complete schema reference for Saturn Cloud resource recipes.

## Top-Level Structure

```yaml
schema_version: "2025.10.01"   # optional; included in API responses
type: workspace                # workspace | job | deployment
spec:
  name: my-resource
  ...
state:                         # response-only; omit when applying
  id: ...
  status: stopped
```
"""

EXAMPLES = """## Example Recipes

### Workspace

```yaml
type: workspace
spec:
  name: cpu-interactive
  owner: primary-tenant/demo
  image: saturncloud/saturn-python:2025.05.01
  instance_type: nebius-cpu-d3-4vcpu-16gb
  ide: jupyter
  disk_space: 300Gi
  auto_shutoff: 6 hours
  git_repositories:
    - url: git@github.com:saturncloud/examples.git
      path: /home/jovyan/workspace/examples
      reference: main
      reference_type: branch
      on_restart: preserve changes
  shared_folders:
    - name: test-data
      owner: primary-tenant/demo
      path: /home/jovyan/shared/demo/test-data
```

### Job

```yaml
type: job
spec:
  name: nyc-taxi-ingest
  owner: primary-tenant/demo
  image: saturncloud/saturn-python:2025.05.01
  instance_type: nebius-cpu-d3-4vcpu-16gb
  command: cd examples/data-science-analystics/cpu-data-versioning && python ingest_taxi_dvc.py
  extra_packages:
    pip:
      install: dvc>=3.67
  environment_variables:
    SHARED_STORAGE: /home/jovyan/shared/demo/test-data
  git_repositories:
    - url: git@github.com:saturncloud/examples.git
      path: /home/jovyan/workspace/examples
      reference: demo/saturn-data-pipeline
      reference_type: branch
      on_restart: reclone
  shared_folders:
    - name: test-data
      owner: primary-tenant/demo
      path: /home/jovyan/shared/demo/test-data
```

### Deployment

```yaml
type: deployment
spec:
  name: prediction-api
  owner: primary-tenant/demo
  image: saturncloud/saturn-python:2025.05.01
  instance_type: nebius-cpu-d3-4vcpu-16gb
  command: python3 -m uvicorn serve:app --host 0.0.0.0 --port 8000
  scale: 1
  routes:
    - container_port: 8000
      visibility: org
  environment_variables:
    MODEL_PATH: /home/jovyan/shared/models/latest
```
"""

PITFALLS = """## Key Pitfalls

- `image` is a **string**, not `{name, version}`.
- `instance_type` is the **full descriptor**, not a size keyword (use `saturn_list_instance_types`).
- Where the installation offers a **recommended configuration** (`saturn_list_instance_type_configs`), prefer `instance_type_config: <name>` over a single `instance_type`: it starts at whichever listed site has stock. Give one or the other, never both; a dumped recipe shows `instance_type_config` and no `instance_type`.
- `environment_variables` is a **dict**, not a list of `{variable, value}` objects.
- `extra_packages.pip` is an **object** `{install, requirements_txt}`, not a space-separated string.
- `secrets` is a **separate array**, not embedded in `environment_variables`.
- `schema_version` is at the **top level** alongside `type`, not inside `spec`.
- For **jobs**, the server normalizes `git_repositories[].on_restart` to `"reclone"`.
- Deployment scaling is `scale`, not `replicas`.
- IDE values are `"jupyter"` or `"rstudio"` only — VS Code is configured via image, not as an IDE value.
- `command` runs via `exec`, **not a shell** — shell builtins like `cd`, `&&`, `||`, pipes, redirects, and env-var expansion will fail with `exec: cd: not found` (or similar). Use `working_directory` to set the cwd. If you genuinely need shell features, wrap with `bash -lc "..."`.
- **Deployments must bind `0.0.0.0:8000`.** Saturn Cloud's deployment proxy is hard-wired to container port `8000`, and the service must listen on `0.0.0.0` (not `localhost`/`127.0.0.1`). Anything else is silently broken: a `localhost` bind isn't reachable by the proxy; a non-8000 port works only with a custom `route`, and Saturn still auto-adds a redundant port-8000 route that points at nothing. For MLflow 3.x specifically, also add `--allowed-hosts '*'` and `--cors-allowed-origins '*'` so its security middleware accepts proxied requests.
- **Resources that need to call other Saturn services need an un-scoped `token_scope`.** Default `token_scope` auto-populates to a narrow value like `workspace:{self}:dask:write` — enough for Dask, not enough to call other deployments or hit the Saturn API. Set `token_scope` explicitly to the un-scoped value when a resource needs to reach beyond itself.
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    out = []
    out.append(HEADER)

    out.append("## Common Spec Fields\n\n" + render_common_table())
    out.append("## Workspace-Only Fields\n\n" + render_specific_table(WorkspaceSpec))
    out.append("## Job-Only Fields\n\n" + render_specific_table(JobSpec))
    out.append("## Deployment-Only Fields\n\n" + render_specific_table(DeploymentSpec))

    nested = "\n\n".join(render_nested_section(m) for m in NESTED_MODELS)
    out.append("## Nested Objects\n\n" + nested)

    out.append(EXAMPLES)
    out.append(PITFALLS)

    sys.stdout.write("\n\n".join(out) + "\n")


if __name__ == "__main__":
    main()
