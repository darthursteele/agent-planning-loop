#!/usr/bin/env python3
"""Stub CLI used in place of `claude`/`codex` for orchestrator dry-run tests.

Deterministic script: as reviewer, requests changes (one blocking finding) on
round 1, approves from round 2 onward. As author, always reports success.
Role is inferred from the system prompt text; round is parsed from the task
prompt's "Round: N" line.
"""
import json
import re
import sys


def main():
    system_prompt = sys.argv[1] if len(sys.argv) > 1 else ""
    task_prompt = sys.argv[2] if len(sys.argv) > 2 else ""

    # Both prompts mention the *other* role by name (e.g. the reviewer
    # prompt says "your counterpart is an author agent"), so a plain
    # substring check is ambiguous. Each prompt's opening line is unique.
    role = "reviewer" if system_prompt.lstrip().startswith("You are the **reviewer**") else "author"

    match = re.search(r"Round:\s*(\d+)", task_prompt)
    round_num = int(match.group(1)) if match else 1

    if role == "author":
        verdict = {
            "role": "author",
            "round": round_num,
            "linear_project_id": "MOCK-PROJ-1",
            "status": "created" if round_num == 1 else "updated",
            "summary_of_changes": "addressed mock findings",
        }
    else:
        if round_num == 1:
            verdict = {
                "role": "reviewer",
                "round": round_num,
                "verdict": "request_changes",
                "findings": [
                    {
                        "severity": "blocking",
                        "summary": "mock blocking issue",
                        "location": "sub-issue-1",
                    }
                ],
            }
        else:
            verdict = {
                "role": "reviewer",
                "round": round_num,
                "verdict": "approve",
                "findings": [],
            }

    print("<<<VERDICT>>>")
    print(json.dumps(verdict))
    print("<<<END_VERDICT>>>")


if __name__ == "__main__":
    main()
