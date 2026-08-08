# agent-planning-loop

Two-agent (Claude Code + Codex) planning loop: one agent authors an
implementation plan into Linear (as a Project acting as an epic, with
sub-issues), the other reviews it, and they iterate until the reviewer
approves with no blocking findings or a safety cap is hit.

Design doc: [`docs/specs/2026-08-08-agent-planning-loop-design.md`](docs/specs/2026-08-08-agent-planning-loop-design.md)

## How it works

A Python orchestrator (`orchestrator.py`) synchronously alternates headless
CLI calls: run the author, parse its verdict, run the reviewer, parse its
verdict, repeat. Neither agent talks to the other directly — the orchestrator
relays each round's findings/summary into the next agent's task prompt. Both
agents use their own Linear MCP access directly; the orchestrator never calls
Linear itself.

Each agent gets two layers of instructions:
- A **system prompt** (`prompts/author_system_prompt.md` /
  `reviewer_system_prompt.md`), loaded on every call for that role. Durable
  operating instructions: use subagents for independent sub-issues, match
  subagent model to sub-issue complexity, how to read/write Linear, how to
  emit the verdict block.
- A **task prompt** (`prompts/author_task_prompt.md` /
  `reviewer_task_prompt.md`), rebuilt each round with the goal (round 1) or
  the other agent's findings/summary (later rounds).

## Setup

```bash
pip install -r requirements.txt
```

Before running against the real CLIs, check `config.yaml` — the `claude` and
`codex` command templates include non-interactive/auto-approve flags that
need to match your installed CLI versions (so Linear MCP tool calls don't
hang waiting on interactive approval with no human present).

## Usage

```bash
python3 orchestrator.py --goal "Design a plan for <your project>"
```

Logs for every round (full stdout/stderr per agent call) are written to
`runs/<timestamp>/`.

Options:
- `--max-rounds N` — override `loop.max_rounds` from `config.yaml` (default 5).
- `--config path.yaml` — use an alternate config (e.g. for the mock dry-run
  setup in `tests/config.mock.yaml`).

## Testing

Dry-run the loop logic against a scripted stub agent (no real CLI calls):

```bash
python3 -m pytest tests/ -v
# or
python3 tests/test_orchestrator.py
```
