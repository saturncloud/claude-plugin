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
    "url": "https://github.com/org/repo.git",
    "path": "/home/jovyan/workspace/repo",
    "reference": "main",
    "reference_type": "branch",
    "on_restart": "preserve changes"
  }
]
```

### Secrets (Environment Variables)
```json
"environment_variables": [
  {"variable": "MY_SECRET", "secret_name": "my-secret"}
]
```

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

## Tips

- Use `as_template=true` when getting a resource you want to clone or modify — it strips the state and IDs.
- Jobs and deployments require a `command` field; workspaces do not.
- Workspaces have `ide` (e.g., `"jupyter"`, `"vscode"`) and `disk_space`; jobs and deployments do not.
- When unsure about available fields, refer to `recipe-reference.md` for the full schema.

For full recipe schema details, see [recipe-reference.md](recipe-reference.md).
