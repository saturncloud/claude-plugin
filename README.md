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

Claude Code starts the MCP server with `uvx` (see `.mcp.json`), which needs
[uv](https://docs.astral.sh/uv/) 0.9.17 or later. The launch only takes package
releases that are at least 7 days old (`--exclude-newer "7 days"`), so a release
that is hijacked and pulled within days never reaches your machine.

For development, `uv sync` creates `.venv` with the same 7-day cooldown.

## Configure

The MCP server reads two environment variables (see `.mcp.json`):

| Variable | Description |
|----------|-------------|
| `SATURN_BASE_URL` | Your Saturn Cloud installation URL (e.g. `https://app.community.saturnenterprise.io`) |
| `SATURN_TOKEN` | API token from **Settings → API Tokens** in Saturn Cloud |

Set these in your shell before launching Claude Code, or in your Claude Code MCP config.

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

## Updating the recipe reference

`skills/saturn/recipe-reference.md` is generated from the `saturn-client` schema. To regenerate after a `saturn-client` upgrade:

```sh
uv run python scripts/generate_recipe_reference.py
```

## License

See [LICENSE](LICENSE).
