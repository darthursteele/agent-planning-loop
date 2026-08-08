# Agent Planning Loop — Design

Date: 2026-08-08

## Purpose

A lightweight framework in which Claude Code and Codex collaborate on a software
project plan: one agent authors the plan (as a Linear Project acting as an
"epic," with sub-issues), the other critiques it, and they iterate until the
plan is approved or a safety cap is hit. Coordination happens through a
synchronous orchestrator process, not through the agents talking to each other
directly or through polling.

## Architecture

A standalone Python CLI (`orchestrator.py`) alternates headless invocations of
the `claude` and `codex` CLIs. Each invocation blocks until the agent
finishes; the orchestrator never calls Linear itself — each agent uses its own
Linear MCP access to read and write the plan and sub-issues. The orchestrator's
only job is to route prompts in, and parse each agent's final structured
verdict out.

## Components

```
agent-planning-loop/
  orchestrator.py        # main loop: alternates author/reviewer calls, parses verdicts, decides stop/continue
  config.yaml             # per-agent invocation command templates, max_rounds, per-call timeout
  prompts/
    author_system_prompt.md    # durable operating instructions for the author role
    reviewer_system_prompt.md  # durable operating instructions for the reviewer role
    author_task_prompt.md      # per-round task template: goal, Linear ref, reviewer's prior findings
    reviewer_task_prompt.md    # per-round task template: Linear ref, round number, verdict schema
    escalation_task_prompt.md  # used when safety cap is hit
  runs/                   # gitignored — per-run logs (full stdout/stderr per call)
  tests/
    mock_agent.py          # stub CLI replacement that prints canned verdict JSON, for dry-run testing
    test_orchestrator.py
  README.md
```

## Roles

Fixed per run, configurable at kickoff: one agent is "author," the other is
"reviewer." Default: Claude Code = author, Codex = reviewer. Which physical
CLI plays which role is set in `config.yaml` per run, not hardcoded.

## System prompts vs. task prompts

Two distinct layers, both role-specific:

- **System prompt** (`author_system_prompt.md` / `reviewer_system_prompt.md`):
  loaded on *every* call for that role, via each CLI's system-prompt mechanism
  (e.g. Claude Code's `--append-system-prompt`, Codex's equivalent). Durable
  instructions on *how* to work:
  - Use subagents to handle independent sub-issues in parallel, to conserve
    the top-level agent's context.
  - When delegating to a subagent for a given sub-issue, pick a model sized to
    that sub-issue's complexity (lighter model for small/mechanical sub-issues,
    strongest model for architecturally significant ones), using the CLI's
    native per-subagent model override.
  - How to read/write the Linear plan (project = epic, sub-issues = tasks).
  - How to emit the verdict block (see below) as the last thing printed.

- **Task prompt** (`author_task_prompt.md` / `reviewer_task_prompt.md`):
  built fresh each round with the *what* — the goal (round 1) or the other
  agent's prior findings/summary (later rounds), plus the Linear project ID.

## Data flow (per round)

1. **Round 1**: orchestrator runs the author CLI with the goal description
   (system prompt + task prompt with the goal). The author creates the Linear
   Project (epic) + sub-issues, writes the plan, and ends its output with a
   delimited JSON verdict block:
   ```
   <<<VERDICT>>>
   {"role":"author","round":1,"linear_project_id":"...","status":"created"}
   <<<END_VERDICT>>>
   ```
2. Orchestrator extracts everything between the fixed delimiters (parsing
   doesn't depend on the CLI's own output formatting) and gets
   `linear_project_id`.
3. Orchestrator runs the reviewer CLI with the `linear_project_id` and round
   number. Reviewer reads the plan via its own Linear MCP tools, leaves
   comments, and ends with:
   ```
   <<<VERDICT>>>
   {"role":"reviewer","round":1,"verdict":"request_changes","findings":[{"severity":"blocking","summary":"...","location":"..."}]}
   <<<END_VERDICT>>>
   ```
4. If `verdict == "approve"` and no `blocking` findings → **done**, success
   exit.
5. Otherwise, if `round >= max_rounds` → **escalate** (see below), exit
   non-zero.
6. Otherwise, increment round, run the author CLI again with the reviewer's
   `findings` included in the task prompt text (this is the direct
   agent-to-agent handoff channel, mediated by the orchestrator — not just
   Linear comments), and repeat from step 3.

## Verdict schema

Always the last thing each agent prints, wrapped in `<<<VERDICT>>>` /
`<<<END_VERDICT>>>` delimiters.

- Author: `{role, round, linear_project_id, status: "created"|"updated", summary_of_changes?}`
- Reviewer: `{role, round, verdict: "approve"|"request_changes", findings: [{severity: "blocking"|"minor"|"nit", summary, location}]}`

## Stop condition

Approve with zero `blocking` findings, or a safety cap (default 5 rounds,
configurable in `config.yaml`). Severity tagging lets the reviewer flag
nitpicks without blocking convergence, while still surfacing them for human
visibility in the final plan.

## Escalation

On hitting the cap without approval, the orchestrator makes one more agent
call — the reviewer, using `escalation_task_prompt.md` — asking it to post a
summary comment on the Linear epic tagging the user, listing all outstanding
blocking findings across rounds. The orchestrator then exits non-zero with a
local summary printed to the terminal.

## Operational note: headless tool approval

Both CLIs need to be configured so Linear MCP tool calls don't hang waiting on
interactive approval, since there's no human present during a run. Exact flags
depend on installed CLI versions, so `config.yaml` holds the full invocation
command as a template (not hardcoded in `orchestrator.py`) so it can be
adjusted without touching code.

## Testing

`tests/mock_agent.py` is a stub CLI (prints canned verdict JSON) that
`config.yaml` can point at instead of the real CLIs, so loop/parsing/
escalation logic can be tested without spending real agent calls. A real
smoke-test run on a toy planning task is the final validation step before
relying on this for real work.
