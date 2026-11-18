# Saturn Cloud plugin for Claude Code

A [Claude Code](https://claude.com/claude-code) plugin that lets Claude manage [Saturn Cloud](https://saturncloud.io) resources — workspaces, jobs, and deployments — directly from a Claude Code session.

The plugin bundles two pieces:

- **MCP server** (`src/saturn_mcp/`) — exposes Saturn Cloud's API as tools Claude can call (list/get/apply recipes, start/stop resources, schedule jobs, fetch logs, list instance types).
- **Skill** (`skills/saturn/`) — gives Claude recipe schema knowledge and conventions so it can author and edit recipes correctly without trial and error.

## Install

The plugin is published in the local marketplace defined by `.claude-plugin/marketplace.json`. From a Claude Code session, add the marketplace and install:

```
/plugin marketplace add /path/to/this/repo
/plugin install saturn-cloud@saturn-local
```

The MCP server runs out of `.venv`, so create it first:

```sh
uv sync
```

## Configure

The MCP server reads these environment variables (see `.mcp.json`):

| Variable | Description |
|----------|-------------|
| `SATURN_BASE_URL` | Your Saturn Cloud installation URL (e.g. `https://app.community.saturnenterprise.io`) |
| `SATURN_TOKEN` | A user API token. Create one in Saturn Cloud: click your name in the sidebar, then **Access Keys**, then **API Tokens**. |
| `SATURN_USER_TOKEN` | Optional. A user API token for the SSH key tools only. Set it when running inside a Saturn resource (see below). |

Set these in your shell before launching Claude Code, or in your Claude Code MCP config.

### Running inside a Saturn workspace, job or deployment

Saturn sets `SATURN_BASE_URL` and `SATURN_TOKEN` in every resource, so the plugin works there without setup. That `SATURN_TOKEN` is the resource's own token, though, and Saturn Cloud refuses it on the SSH key and secrets APIs. A resource token must not be able to create a credential that outlives the resource.

So inside a resource the SSH key tools (`saturn_ssh_setup`, `saturn_ssh_key_list`, `saturn_ssh_key_register`, `saturn_ssh_key_delete`) need a user API token. Create one as described above and export it as `SATURN_USER_TOKEN` before starting Claude Code. The SSH key tools use it, and the other tools keep using the resource's `SATURN_TOKEN`. Without it, the SSH key tools fail with a message that says what to do. You can instead set `SATURN_TOKEN` itself to the user token, but then every tool acts as you rather than as the resource.

## What's in this repo

```
.claude-plugin/marketplace.json   Local marketplace entry
plugin.json                       Plugin manifest
.mcp.json                         MCP server registration
src/saturn_mcp/                   MCP server (FastMCP + saturn-client)
skills/saturn/                    Skill: SKILL.md + recipe-reference.md
scripts/generate_recipe_reference.py  Regenerates skills/saturn/recipe-reference.md from saturn-client
pyproject.toml / uv.lock          Python packaging
```

## Available tools

Once installed, Claude can call:

- `saturn_list_resources` — list workspaces, jobs, and deployments
- `saturn_get_resource` — fetch a resource's full recipe
- `saturn_apply_recipe` — create or update a resource from a recipe
- `saturn_delete_resource` — delete a resource
- `saturn_start_resource` / `saturn_stop_resource` — control runtime state
- `saturn_schedule_job` — set a cron schedule on a job
- `saturn_get_logs` — fetch logs for a resource
- `saturn_list_instance_types` — list available compute sizes
- `saturn_ssh_setup` — create a local SSH keypair and register it with Saturn Cloud
- `saturn_ssh_key_list` / `saturn_ssh_key_register` / `saturn_ssh_key_delete` — manage registered SSH public keys
- `saturn_get_ssh_url` — get the SSH URL of a running workspace or deployment

## Updating the recipe reference

`skills/saturn/recipe-reference.md` is generated from the `saturn-client` schema. To regenerate after a `saturn-client` upgrade:

```sh
uv run python scripts/generate_recipe_reference.py
```

## License

See [LICENSE](LICENSE).
