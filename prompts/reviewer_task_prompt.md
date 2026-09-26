Round: {round}

Original goal:

{goal}

Linear project:

{linear_project_id}

{if_round_gt_1}
The author addressed the Round {prev_round} findings and supplied this summary:

{author_summary}
{end_if_round_gt_1}

## Review assignment

Review the current Linear plan against the original goal and the Project’s
declared scope.

Start by identifying the current scope ledger from the Project description:

- Goal
- Success criteria
- In scope
- Non-goals
- Constraints
- Active implementation sub-issues

Treat that ledger as the boundary of the review.

{if_round_1}
This is the comprehensive plan-review round. Review all active in-scope
sub-issues, their contracts, and their dependency sequence.

Focus on whether the minimum proposed plan can achieve the goal. Do not expand
the plan with adjacent hardening, generalized infrastructure, retrospective
cleanup, or optional improvements.
{end_if_round_1}

{if_round_gt_1}
This is a delta-review round.

Perform these steps:

1. Verify each prior blocking finding against the revised Linear descriptions.
2. Carry forward any prior finding that remains unresolved.
3. Review the author’s changes and the direct contracts those changes affect.
4. Check whether a revision introduced a new contradiction in a core in-scope
   path.

Introduce a new blocking finding only if the latest revision created it or if
it proves the core goal still cannot work. Do not reopen unchanged peripheral
areas or raise the quality bar for an already sufficient mechanism.
{end_if_round_gt_1}

Use the finding admission test from your system instructions before writing any
Linear comment.

Use subagents only for independent in-scope angles, and give them the same
scope and non-goals.

Leave admitted findings as Linear comments. Approve when there are no blocking
findings, even if minor findings remain.

End with the required machine-parsed verdict block.