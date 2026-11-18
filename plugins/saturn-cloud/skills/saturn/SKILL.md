---
name: saturn
description: >
  Use when helping users create, configure, or manage Saturn Cloud resources
  (workspaces, jobs, deployments). Provides recipe schema knowledge and best practices.
---

# Saturn Cloud

Saturn Cloud is a data science and ML platform. Users manage infrastructure through **recipes** — JSON resource definitions that describe workspaces, jobs, and deployments.

## Resource Types

| Type | Purpose | Key Traits |
|------|---------|------------|
| **Workspace** | Interactive dev environment (Jupyter, VS Code, RStudio) | Has an IDE, persistent disk, can be started/stopped |
| **Job** | Batch task (ETL, training, one-off scripts) | Has a command, can be cron-scheduled, runs to completion |
| **Deployment** | Long-running service (API, dashboard, app) | Has a command, exposes routes/ports, stays running |

## Recipe Structure

Every resource is defined by a recipe with two top-level fields:

```json
{
  "type": "workspace",
  "spec": {
    "name": "my-workspace",
    "owner": "user-name",
    "image": {"name": "saturncloud/saturn-python", "version": "2024.01.01"},
    "instance_type": "large",
    "disk_space": "64Gi",
    ...
  }
}
```

- `type` — one of `workspace`, `job`, `deployment`
- `spec` — all configuration fields for the resource

When you **read** a resource (via `saturn_get_resource`), it also includes a `state` field with `id`, `status`, `url`, etc. When **creating/updating** (via `saturn_apply_recipe`), omit `state`.

## Common Workflow

1. **List** resources with `saturn_list_resources` to see what exists
2. **Get** a specific resource with `saturn_get_resource` to see its full recipe
3. **Modify** the recipe dict as needed
4. **Apply** the modified recipe with `saturn_apply_recipe` to update it
5. **Start/Stop** with `saturn_start_resource` / `saturn_stop_resource`

To create a new resource from scratch, build a recipe dict and call `saturn_apply_recipe`.

To clone an existing resource, get it with `as_template=true`, modify `spec.name` (and `type` if changing resource type), then apply.

## Key Configuration Patterns

### Instance Types
Instance types are strings like `"large"`, `"xlarge"`, `"2xlarge"`, `"4xlarge"`, `"8xlarge"`, etc. GPU instances include `"g4dnxlarge"`, `"g5xlarge"`, `"p3.2xlarge"`, etc. The available options depend on the Saturn Cloud deployment.

### Git Repositories
```json
"git_repositories": [
  {
    "url": "git@github.com:org/repo.git",
    "path": "/home/jovyan/workspace/repo",
    "reference": "main",
    "reference_type": "branch",
    "on_restart": "preserve changes"
  }
]
```

**Always use SSH URLs (`git@github.com:org/repo.git`), not HTTPS.** Saturn Cloud authenticates to git hosts using the user's SSH keys — HTTPS URLs will fail to clone private repos because there's no PAT/credential flow wired up. This applies across the platform: workspaces, jobs, and deployments.

### Environment Variables

**Prefer `environment_variables` in the recipe over exporting in `start_script`.** Variables set this way are available to *every* process in the container (Jupyter kernels, SSH login shells, the start script itself, any service the user launches later). Exporting in `start_script` only affects the start_script's own shell — child processes the user spawns later won't see them.

Shape is a flat dict `{name: value}`, not an array:
```json
"environment_variables": {
  "API_BASE_URL": "https://api.example.com",
  "LOG_LEVEL": "info"
}
```

**Exception: use `start_script` when the value depends on shell expansion.** `environment_variables` values are stored literally — there is no envsubst, no `$HOME` interpolation, no command substitution. If you need to compute a value at start (e.g. `export FOO="$(hostname)-worker"` or `export PYTHONPATH="$HOME/extra:$PYTHONPATH"`), put it in `start_script` and also append it to `~/.profile` / `~/.bashrc` so interactive shells inherit it.

For secrets stored in Saturn's secret store, use the `secrets` field (see [recipe-reference.md](recipe-reference.md)), which mounts secret values as env vars without ever putting plaintext in the recipe.

### Extra Packages (pip)
```json
"extra_packages": {
  "pip": "pandas numpy scikit-learn"
}
```

### Start Script
```json
"start_script": "pip install -r requirements.txt && python setup.py"
```

### Command (Jobs & Deployments)
```json
"command": "python train.py --epochs 100"
```

#### Command pitfalls — read before applying any job/deployment

**1. The command runs via `exec`, not a shell.** Builtins (`cd`), operators (`&&`, `||`, `|`), redirects (`>`), and env-var expansion (`$VAR`) all fail with errors like `exec: cd: not found`. Use `working_directory` to set the cwd. If you genuinely need shell features, wrap with `bash -lc "..."`.

**2. Deployments must bind `0.0.0.0:8000`.** Saturn Cloud's deployment proxy is hard-wired to container port **8000**, and the service must listen on **`0.0.0.0`** (not `localhost`/`127.0.0.1`) so the proxy can reach it. Apply this everywhere you can:
   - For uvicorn: `python3 -m uvicorn app:app --host 0.0.0.0 --port 8000`
   - For mlflow ui/server: `mlflow ui --host 0.0.0.0 --port 8000 --allowed-hosts '*' --cors-allowed-origins '*'` (MLflow 3.x adds a security middleware that blocks non-localhost `Host` headers by default — `--allowed-hosts` is required to accept proxied requests)
   - For any other server: pass the equivalent host/port flags

   If you forget either: a service bound to `localhost` listens but the proxy can't connect; a service on a non-8000 port works only if you add a custom `route` matching that port, and even then Saturn auto-adds a redundant 8000 route that points at nothing.

**3. Verify the command, `working_directory`, and `git_repositories[].path` line up before applying.** This is the most common silent failure: the script the command points at isn't where it ends up on disk after the clone.

**4. Resources that need to call other Saturn services need an un-scoped `token_scope`.** By default Saturn auto-populates `token_scope` with a narrow value like `workspace:{self}:dask:write` — enough to talk to an attached Dask cluster, but **not** enough to call other deployments, list resources, or hit the Saturn API. If a workspace/job/deployment needs to reach out to another Saturn-managed service (e.g. a notebook calling a deployment endpoint, a job introspecting other resources), set `token_scope` explicitly to an un-scoped value. Forgetting this gets you 401/403s from the proxy that look like an auth bug but are actually scope.

Mental model: at job start, Saturn does (roughly) `git clone <url> <path>` for each entry in `git_repositories`, then `cd $working_directory && exec $command`. So before applying a recipe, walk through this checklist:

- Identify the script in the command (the arg after `python|python3|bash|sh|node|Rscript`).
- If it's a relative path: resolve it as `${working_directory}/${script}`. That path must exist inside one of the `git_repositories[].path` trees, with the script's location relative to the repo root preserved.
- If it's an absolute path: it must be under one of the `git_repositories[].path` trees.
- The git repo's `reference` (branch/tag/commit) must actually contain that file at that location — `git ls-tree` it on the user's local checkout if you're unsure.

**Concrete example.** Repo `saturncloud/examples` has `examples/data-science-analystics/cpu-data-versioning/ingest_taxi_dvc.py`. Two equivalent valid recipes:

```yaml
# A: working_directory at the script's parent, simple command
working_directory: /home/jovyan/workspace/examples/examples/data-science-analystics/cpu-data-versioning
command: python ingest_taxi_dvc.py
git_repositories:
  - url: git@github.com:saturncloud/examples.git
    path: /home/jovyan/workspace/examples
    reference: demo/saturn-data-pipeline

# B: working_directory at the repo root, relative path in command
working_directory: /home/jovyan/workspace/examples
command: python examples/data-science-analystics/cpu-data-versioning/ingest_taxi_dvc.py
git_repositories:
  - url: git@github.com:saturncloud/examples.git
    path: /home/jovyan/workspace/examples
    reference: demo/saturn-data-pipeline
```

Both resolve to the same script. The wrong recipe would be one where (e.g.) the command uses `python data-versioning/ingest.py` while `working_directory` is `/home/jovyan/workspace` and the clone path is `/home/jovyan/workspace/examples` — the path math doesn't reach the file.

### Dask Cluster (attached distributed compute)
```json
"dask_cluster": {
  "num_workers": 3,
  "instance_type": "xlarge",
  "scheduler_instance_type": "large",
  "use_spot_instances": true
}
```

### Routes (Deployments & Workspaces)
```json
"routes": [
  {"container_port": 8000, "visibility": "public", "path_prefix": "/api"}
]
```

### Cron Scheduling (Jobs)
Use `saturn_schedule_job` to set a cron schedule: `saturn_schedule_job(job_name="nightly-etl", cron_schedule="0 2 * * *")`.

### SSH Access
Use `saturn_ssh_setup` to create a local keypair at `~/.ssh/id_ed25519_saturn` and register it, then `saturn_get_ssh_url` for the target (the resource needs `start_ssh: true` and must be running).

**Inside a Saturn workspace, job or deployment, the SSH key tools need a user API token.** There, `SATURN_TOKEN` is the resource's own token, and Saturn Cloud refuses it on the SSH key and secrets APIs with 403 `TokenErrors.RESOURCE_TOKEN_NOT_ALLOWED`. No `token_scope` changes this. If an SSH key tool fails with that message, tell the user to create a user API token (click their name in the sidebar, then Access Keys, then API Tokens), export it as `SATURN_USER_TOKEN`, and restart Claude Code. Do not try to work around it with the resource token or by calling the API directly.

## Tips

- Use `as_template=true` when getting a resource you want to clone or modify — it strips the state and IDs.
- Jobs and deployments require a `command` field; workspaces do not.
- Workspaces have `ide` (e.g., `"jupyter"`, `"vscode"`) and `disk_space`; jobs and deployments do not.
- When unsure about available fields, refer to `recipe-reference.md` for the full schema.

For full recipe schema details, see [recipe-reference.md](recipe-reference.md).
