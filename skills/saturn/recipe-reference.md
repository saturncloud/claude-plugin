# Saturn Cloud Recipe Reference

Complete schema reference for Saturn Cloud resource recipes.

## Top-Level Structure

```json
{
  "type": "<resource_type>",
  "spec": { ... }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | `"workspace"`, `"job"`, or `"deployment"` |
| `spec` | object | Yes | Resource configuration (see below) |
| `state` | object | Read-only | Present when reading resources; contains `id`, `status`, `url`, etc. |

## Spec Fields

### Common Fields (all resource types)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | string | required | Resource name (unique per owner) |
| `owner` | string | current user | Owner username |
| `description` | string | `""` | Human-readable description |
| `image` | object | required | Docker image (see Image below) |
| `instance_type` | string | required | Compute instance size |
| `extra_packages` | object | `null` | Additional packages to install (see Extra Packages) |
| `start_script` | string | `""` | Shell script to run on startup |
| `environment_variables` | array | `[]` | Environment variables / secrets (see Environment Variables) |
| `git_repositories` | array | `[]` | Git repos to clone (see Git Repositories) |
| `shared_folders` | array | `[]` | Shared folder mounts |
| `dask_cluster` | object | `null` | Dask cluster config (see Dask Cluster) |
| `auto_shutoff` | string | `"1 hour"` | Auto-shutdown timeout |
| `working_directory` | string | `"/home/jovyan/workspace"` | Working directory |

### Workspace-Only Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `ide` | string | `"jupyter"` | IDE: `"jupyter"`, `"vscode"`, `"rstudio"` |
| `disk_space` | string | `"16Gi"` | Persistent disk size: `"16Gi"`, `"64Gi"`, `"256Gi"`, `"512Gi"`, `"1Ti"` |
| `start_dind` | bool | `false` | Enable Docker-in-Docker |
| `start_ssh` | bool | `false` | Enable SSH access |

### Job-Only Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `command` | string | required | Shell command to execute |
| `start_dind` | bool | `false` | Enable Docker-in-Docker |
| `backoff_limit` | int | `0` | Number of retries on failure |
| `concurrency_policy` | string | `"Forbid"` | `"Allow"`, `"Forbid"`, `"Replace"` — for scheduled jobs |

### Deployment-Only Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `command` | string | required | Shell command to run the service |
| `routes` | array | `[]` | HTTP route definitions (see Routes) |
| `viewers` | array | `[]` | Embedded viewer configurations |
| `replicas` | int | `1` | Number of replicas |

## Nested Objects

### Image

```json
{
  "name": "saturncloud/saturn-python",
  "version": "2024.01.01"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Image repository name |
| `version` | string | Image tag/version |

### Extra Packages

```json
{
  "pip": "package1 package2",
  "conda": "package1 package2",
  "apt": "package1 package2"
}
```

All fields are optional space-separated package strings.

### Environment Variables

```json
[
  {"variable": "KEY", "value": "plain-text-value"},
  {"variable": "KEY", "secret_name": "saturn-secret-name"}
]
```

Use `value` for non-sensitive values. Use `secret_name` to reference a Saturn Cloud secret.

### Git Repositories

```json
[
  {
    "url": "https://github.com/org/repo.git",
    "path": "/home/jovyan/workspace/repo",
    "reference": "main",
    "reference_type": "branch",
    "on_restart": "preserve changes"
  }
]
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `url` | string | required | Git clone URL |
| `path` | string | auto | Clone destination path |
| `reference` | string | `"main"` | Branch, tag, or commit |
| `reference_type` | string | `"branch"` | `"branch"`, `"tag"`, `"commit"` |
| `on_restart` | string | `"preserve changes"` | `"preserve changes"`, `"reset to reference"` |

### Dask Cluster

```json
{
  "num_workers": 3,
  "instance_type": "xlarge",
  "scheduler_instance_type": "large",
  "use_spot_instances": false
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `num_workers` | int | required | Number of Dask workers |
| `instance_type` | string | required | Worker instance type |
| `scheduler_instance_type` | string | same as workers | Scheduler instance type |
| `use_spot_instances` | bool | `false` | Use spot/preemptible instances for workers |
| `num_processes` | int | `1` | Processes per worker |
| `num_threads` | int | auto | Threads per process |

### Routes

```json
[
  {
    "container_port": 8000,
    "visibility": "public",
    "path_prefix": "/api"
  }
]
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `container_port` | int | required | Port the service listens on |
| `visibility` | string | `"org"` | `"public"`, `"org"`, `"owner"` |
| `path_prefix` | string | `"/"` | URL path prefix |

## Example Recipes

### Workspace

```json
{
  "type": "workspace",
  "spec": {
    "name": "my-workspace",
    "image": {"name": "saturncloud/saturn-python", "version": "2024.01.01"},
    "instance_type": "large",
    "disk_space": "64Gi",
    "ide": "jupyter",
    "auto_shutoff": "1 hour",
    "git_repositories": [
      {
        "url": "https://github.com/myorg/myrepo.git",
        "path": "/home/jovyan/workspace/myrepo",
        "reference": "main",
        "reference_type": "branch",
        "on_restart": "preserve changes"
      }
    ],
    "extra_packages": {"pip": "pandas scikit-learn"},
    "start_script": "cd /home/jovyan/workspace/myrepo && pip install -e ."
  }
}
```

### Job

```json
{
  "type": "job",
  "spec": {
    "name": "nightly-etl",
    "image": {"name": "saturncloud/saturn-python", "version": "2024.01.01"},
    "instance_type": "xlarge",
    "command": "python /home/jovyan/workspace/etl/run.py",
    "auto_shutoff": "6 hours",
    "git_repositories": [
      {
        "url": "https://github.com/myorg/etl-pipeline.git",
        "path": "/home/jovyan/workspace/etl",
        "reference": "main",
        "reference_type": "branch"
      }
    ],
    "environment_variables": [
      {"variable": "DATABASE_URL", "secret_name": "database-url"}
    ]
  }
}
```

### Deployment

```json
{
  "type": "deployment",
  "spec": {
    "name": "prediction-api",
    "image": {"name": "saturncloud/saturn-python", "version": "2024.01.01"},
    "instance_type": "xlarge",
    "command": "uvicorn app:app --host 0.0.0.0 --port 8000",
    "routes": [
      {"container_port": 8000, "visibility": "public"}
    ],
    "replicas": 2,
    "auto_shutoff": "never",
    "extra_packages": {"pip": "fastapi uvicorn"},
    "environment_variables": [
      {"variable": "MODEL_PATH", "value": "/home/jovyan/workspace/model.pkl"}
    ]
  }
}
```

## State Object (read-only)

When reading a resource, the recipe includes a `state` field:

```json
{
  "state": {
    "id": "abc123",
    "status": "running",
    "url": "https://app.saturn.io/...",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T12:00:00Z"
  }
}
```

Possible `status` values: `"pending"`, `"running"`, `"stopping"`, `"stopped"`, `"error"`.
