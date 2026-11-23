# Saturn Cloud Recipe Reference

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


## Common Spec Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Resource name (unique per owner) |
| `owner` | string | No | Owner reference (e.g. `"primary-tenant/demo"`) |
| `description` | string | No | Human-readable description |
| `tags` | object (string → string) | No | Arbitrary labels |
| `image` | string | Yes | Image reference, e.g. `"saturncloud/saturn-python:2025.05.01"`. **Single string, not an object.** |
| `instance_type` | string or array of strings | Yes, unless `instance_type_config` is given | Full instance descriptor (e.g. `"nebius-cpu-d3-4vcpu-16gb"`). Use `saturn_list_instance_types` to enumerate. On a resource spec it may also be an ordered list of descriptors (tried in order when one has no capacity), and it is omitted when `instance_type_config` is given. |
| `instance_type_config` | string | No | Name of a recommended instance type configuration (e.g. `"shadeform-rtxpro6000-1gpu"`): an operator-defined, ordered list of instance types on one cluster. Use `saturn_list_instance_type_configs` to enumerate. **Give this or `instance_type`, never both.** |
| `environment_variables` | object (string → string) | No | Plain env vars. **Dict shape, not array.** |
| `working_directory` | string | No | Working directory inside the container |
| `extra_packages` | [ExtraPackagesRecipe](#extrapackagesrecipe) | No | Package install instructions |
| `start_script` | string | No | Shell script run on startup |
| `token_scope` | string | No | Saturn token scope; usually auto-set |
| `dask_cluster` | [DaskClusterAttachment](#daskclusterattachment) | No | Attached Dask cluster |
| `git_repositories` | array of [ExternalRepoAttachmentRecipe](#externalrepoattachmentrecipe) | No | Git repos to clone |
| `secrets` | array of [SecretAttachmentRecipe](#secretattachmentrecipe) | No | Secret attachments. **Separate from `environment_variables`.** |
| `shared_folders` | array of [SharedFolderAttachmentRecipe](#sharedfolderattachmentrecipe) | No | Shared-folder mounts |
| `start_dind` | bool | No | Enable Docker-in-Docker |
| `status` | enum (`"stopped"`, `"running"`) | No | Desired state |
| `use_spot_instance` | bool | No | Use spot/preemptible instance |

## Workspace-Only Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `ide` | enum (`"jupyter"`, `"rstudio"`) | No | IDE |
| `disk_space` | string | No | Persistent disk size (e.g. `"64Gi"`) |
| `auto_shutoff` | enum (`"1 hour"`, `"6 hours"`, `"24 hours"`, `"3 days"`, `"7 days"`, `"Never"`) | No | Auto-shutdown timeout |
| `start_ssh` | bool | No | Enable SSH access |
| `routes` | array of [WorkspaceRouteRecipe](#workspacerouterecipe) | No | HTTP route definitions |
| `viewers` | array of [ViewerRecipe](#viewerrecipe) | No | Embedded viewer configurations |
| `self_destruct` | bool | No | Delete on stop |

## Job-Only Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `command` | string | Yes | Shell command to execute |
| `scale` | int | No | Number of replicas (deployment) or parallel runs (job) |
| `schedule` | string | No | Cron expression |
| `concurrency_policy` | enum (`"Allow"`, `"Forbid"`, `"Replace"`) | No | Concurrency policy for scheduled jobs |
| `retries` | int | No | Number of retries on failure |

## Deployment-Only Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `command` | string | Yes | Shell command to execute |
| `scale` | int | No | Number of replicas (deployment) or parallel runs (job) |
| `start_ssh` | bool | No | Enable SSH access |
| `routes` | array of [DeploymentRouteRecipe](#deploymentrouterecipe) | No | HTTP route definitions |
| `viewers` | array of [ViewerRecipe](#viewerrecipe) | No | Embedded viewer configurations |

## Nested Objects

### ExtraPackagesRecipe

| Field | Type | Required | Description |
|---|---|---|---|
| `pip` | [ExtraPackagesRecipePip](#extrapackagesrecipepip) | No |  |
| `conda` | [ExtraPackagesRecipeConda](#extrapackagesrecipeconda) | No |  |
| `apt` | [ExtraPackagesRecipeApt](#extrapackagesrecipeapt) | No |  |
| `cran` | [ExtraPackagesRecipeApt](#extrapackagesrecipeapt) | No |  |
| `remotes` | [ExtraPackagesRecipeApt](#extrapackagesrecipeapt) | No |  |
| `bioconductor` | [ExtraPackagesRecipeApt](#extrapackagesrecipeapt) | No |  |

### ExtraPackagesRecipePip

| Field | Type | Required | Description |
|---|---|---|---|
| `install` | string | No | Space-separated package list |
| `requirements_txt` | string | No | Path to requirements file |

### ExtraPackagesRecipeConda

| Field | Type | Required | Description |
|---|---|---|---|
| `install` | string | No | Space-separated package list |
| `environment_yml` | string | No | Path to environment YAML |
| `use_mamba` | bool | No | Use mamba instead of conda |

### ExtraPackagesRecipeApt

| Field | Type | Required | Description |
|---|---|---|---|
| `install` | string | No | Space-separated package list |

### ExternalRepoAttachmentRecipe

| Field | Type | Required | Description |
|---|---|---|---|
| `url` | string | Yes | Git clone URL (SSH or HTTPS) |
| `path` | string | No | Mount/clone path inside container |
| `on_restart` | enum (`"preserve changes"`, `"reclone"`) | No | Restart policy for the working tree. Server normalizes to `"reclone"` for jobs and deployments. |
| `reference` | string | No | Branch, tag, or commit |
| `reference_type` | enum (`"branch"`, `"commit"`, `"tag"`) | No | What kind of reference |
| `public` | bool | No | Public repo (no auth required) |

### SharedFolderAttachmentRecipe

| Field | Type | Required | Description |
|---|---|---|---|
| `owner` | string | No | Owner reference (e.g. `"primary-tenant/demo"`) |
| `name` | string | Yes | Resource name (unique per owner) |
| `path` | string | No | Mount/clone path inside container |

### SecretAttachmentRecipe

| Field | Type | Required | Description |
|---|---|---|---|
| `location` | string | Yes | Env-var name (or file path if `attachment_type: file`) |
| `attachment_type` | enum (`"environment_variable"`, `"file"`) | Yes | How the secret is exposed |
| `description` | string | No | Human-readable description |
| `owner` | string | No | Owner reference (e.g. `"primary-tenant/demo"`) |
| `name` | string | No | Resource name (unique per owner) |

### DaskClusterAttachment

| Field | Type | Required | Description |
|---|---|---|---|
| `num_workers` | int | Yes | Number of workers |
| `scheduler` | [DaskClusterAttachmentScheduler](#daskclusterattachmentscheduler) | Yes | Scheduler config |
| `worker` | [DaskClusterAttachmentWorker](#daskclusterattachmentworker) | Yes | Worker config |
| `status` | enum (`"stopped"`, `"running"`) | No | Desired state |

### DaskClusterAttachmentScheduler

| Field | Type | Required | Description |
|---|---|---|---|
| `instance_type` | string | Yes | Full instance descriptor (e.g. `"nebius-cpu-d3-4vcpu-16gb"`). Use `saturn_list_instance_types` to enumerate. |

### DaskClusterAttachmentWorker

| Field | Type | Required | Description |
|---|---|---|---|
| `instance_type` | string | Yes | Full instance descriptor (e.g. `"nebius-cpu-d3-4vcpu-16gb"`). Use `saturn_list_instance_types` to enumerate. |
| `num_processes` | int | No | Processes per worker |
| `num_threads` | int | No | Threads per process |
| `use_spot_instances` | bool | No | Use spot for workers (note: plural, vs `use_spot_instance` on spec) |

### WorkspaceRouteRecipe

| Field | Type | Required | Description |
|---|---|---|---|
| `subdomain` | string | No | Custom subdomain |
| `container_port` | int | Yes | Port the service listens on |
| `visibility` | enum (`"org"`, `"owner"`) | No | Who can access the route |

### DeploymentRouteRecipe

| Field | Type | Required | Description |
|---|---|---|---|
| `subdomain` | string | No | Custom subdomain |
| `container_port` | int | Yes | Port the service listens on |
| `visibility` | enum (`"unauthenticated"`, `"account"`, `"org"`, `"owner"`) | No | Who can access the route |

### ViewerRecipe

| Field | Type | Required | Description |
|---|---|---|---|
| `identity` | string | Yes | Viewer identity |
| `route` | string | No | Route reference |

## Example Recipes

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


## Key Pitfalls

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

