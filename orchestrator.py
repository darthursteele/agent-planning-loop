#!/usr/bin/env python3
"""Alternates headless Claude Code / Codex CLI turns to draft-and-review a
plan written into Linear. See docs/specs/2026-08-08-agent-planning-loop-design.md.
"""
import argparse
import json
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

import yaml

VERDICT_RE = re.compile(r"<<<VERDICT>>>\s*(.*?)\s*<<<END_VERDICT>>>", re.DOTALL)

ROOT = Path(__file__).resolve().parent


class VerdictError(RuntimeError):
    pass


def load_config(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def render(template_text: str, **values) -> str:
    """Fill {placeholder} tokens and {if_x}...{end_if_x} blocks.

    Deliberately simple (no templating dependency) — blocks are kept purely
    linear/non-nested, which is all these prompts need.
    """
    text = template_text
    for key, cond in values.pop("_conditions", {}).items():
        start, end = f"{{if_{key}}}", f"{{end_if_{key}}}"
        pattern = re.compile(re.escape(start) + r"(.*?)" + re.escape(end), re.DOTALL)
        text = pattern.sub(lambda m: m.group(1) if cond else "", text)
    for key, val in values.items():
        text = text.replace(f"{{{key}}}", str(val))
    return text


def build_task_prompt(role: str, round_num: int, **ctx) -> str:
    path = ROOT / CONFIG["roles"][role]["task_prompt"]
    template = path.read_text()
    conditions = {
        "round_1": round_num == 1,
        "round_gt_1": round_num > 1,
    }
    return render(template, _conditions=conditions, round=round_num, **ctx)


def build_system_prompt(role: str) -> str:
    path = ROOT / CONFIG["roles"][role]["system_prompt"]
    return path.read_text()


def run_agent(role: str, task_prompt: str, log_dir: Path, round_num: int) -> dict:
    agent_name = CONFIG["roles"][role]["agent"]
    agent_cfg = CONFIG["agents"][agent_name]
    system_prompt = build_system_prompt(role)

    # Split the template into argv *before* substitution, then replace
    # whole-token placeholders. This avoids ever building a shell string out
    # of prompt text (which may contain quotes/newlines) and passing it
    # through shlex — each argv element is passed to the subprocess verbatim.
    argv = []
    for token in shlex.split(agent_cfg["command"]):
        if token == "{task_prompt}":
            argv.append(task_prompt)
        elif token == "{system_prompt}":
            argv.append(system_prompt)
        else:
            argv.append(token)
    timeout = agent_cfg.get("timeout_seconds", 1200)

    log_path = log_dir / f"round_{round_num}_{role}.log"
    print(f"[orchestrator] round {round_num}: running {role} ({agent_name})...")

    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        log_path.write_text(f"TIMEOUT after {timeout}s\nstdout so far:\n{exc.stdout or ''}\n")
        raise VerdictError(f"{role} ({agent_name}) timed out after {timeout}s")

    log_path.write_text(
        f"$ {argv}\n\n--- stdout ---\n{result.stdout}\n\n--- stderr ---\n{result.stderr}\n"
    )

    if result.returncode != 0:
        raise VerdictError(
            f"{role} ({agent_name}) exited {result.returncode}; see {log_path}"
        )

    return parse_verdict(result.stdout, role, log_path)


def parse_verdict(stdout: str, role: str, log_path: Path) -> dict:
    match = VERDICT_RE.search(stdout)
    if not match:
        raise VerdictError(
            f"{role}: no <<<VERDICT>>> block found in output; see {log_path}"
        )
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise VerdictError(f"{role}: verdict block is not valid JSON ({exc}); see {log_path}")


def format_findings(findings: list) -> str:
    if not findings:
        return "(none)"
    lines = []
    for f in findings:
        lines.append(f"- [{f.get('severity', '?')}] {f.get('summary', '')} ({f.get('location', '')})")
    return "\n".join(lines)


def run_loop(goal: str, run_id: str, max_rounds: int) -> int:
    log_dir = ROOT / "runs" / run_id
    log_dir.mkdir(parents=True, exist_ok=True)

    all_blocking = []  # (round, findings) for escalation
    round_num = 1
    linear_project_id = None
    reviewer_findings_text = ""
    author_summary = ""

    while True:
        author_prompt = build_task_prompt(
            "author",
            round_num,
            goal=goal,
            linear_project_id=linear_project_id or "",
            prev_round=round_num - 1,
            reviewer_findings=reviewer_findings_text,
        )
        author_verdict = run_agent("author", author_prompt, log_dir, round_num)
        linear_project_id = author_verdict.get("linear_project_id", linear_project_id)
        author_summary = author_verdict.get("summary_of_changes", "")

        reviewer_prompt = build_task_prompt(
            "reviewer",
            round_num,
            linear_project_id=linear_project_id or "",
            prev_round=round_num - 1,
            author_summary=author_summary,
        )
        reviewer_verdict = run_agent("reviewer", reviewer_prompt, log_dir, round_num)
        findings = reviewer_verdict.get("findings", [])
        blocking = [f for f in findings if f.get("severity") == "blocking"]
        all_blocking.append((round_num, blocking))

        if reviewer_verdict.get("verdict") == "approve" and not blocking:
            print(f"[orchestrator] approved after round {round_num}. Plan: {linear_project_id}")
            return 0

        if round_num >= max_rounds:
            escalate(linear_project_id, all_blocking, max_rounds, log_dir, round_num)
            return 1

        reviewer_findings_text = format_findings(findings)
        round_num += 1


def escalate(linear_project_id, all_blocking, max_rounds, log_dir: Path, round_num: int):
    print(f"[orchestrator] hit max_rounds ({max_rounds}) without approval. Escalating.")
    lines = []
    for r, blocking in reversed(all_blocking):
        if blocking:
            lines.append(f"Round {r}:\n" + format_findings(blocking))
    all_blocking_text = "\n\n".join(lines) or "(none recorded)"

    path = ROOT / CONFIG["escalation"]["task_prompt"]
    template = path.read_text()
    prompt = render(
        template,
        _conditions={},
        max_rounds=max_rounds,
        linear_project_id=linear_project_id or "(unknown)",
        all_blocking_findings=all_blocking_text,
    )
    try:
        run_agent("reviewer", prompt, log_dir, round_num=round_num + 1)
    except VerdictError as exc:
        print(f"[orchestrator] escalation call itself failed: {exc}", file=sys.stderr)

    print(f"[orchestrator] unresolved blocking findings:\n{all_blocking_text}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--goal", required=True, help="Plan goal / prompt for the author agent")
    parser.add_argument("--config", default=str(ROOT / "config.yaml"))
    parser.add_argument("--max-rounds", type=int, default=None)
    args = parser.parse_args()

    global CONFIG
    CONFIG = load_config(Path(args.config))
    max_rounds = args.max_rounds or CONFIG.get("loop", {}).get("max_rounds", 5)
    run_id = time.strftime("%Y%m%d-%H%M%S")

    try:
        sys.exit(run_loop(args.goal, run_id, max_rounds))
    except VerdictError as exc:
        print(f"[orchestrator] fatal: {exc}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
