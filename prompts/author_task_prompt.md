Round: {round}

Original goal:

{goal}

{if_round_1}
This is Round 1.

Create a new Linear Project to act as the epic for this implementation plan.

Write the Project description as the scope ledger required by your system
instructions:

- Goal
- Success criteria
- In scope
- Non-goals
- Constraints
- Assumptions
- Delivery sequence

Then create the minimum set of independently actionable sub-issues needed to
achieve the success criteria.

Before creating each sub-issue, identify the success criterion it serves.
Exclude speculative hardening, generalized infrastructure, retrospective
cleanup, and future extensibility unless the original goal explicitly requires
them.

Use existing architecture and seams where practical. Keep acceptance criteria
and verification proportionate to the goal.
{end_if_round_1}

{if_round_gt_1}
Linear project:

{linear_project_id}

The reviewer returned these Round {prev_round} findings:

{reviewer_findings}

This is a revision round, not a new comprehensive planning round.

For every blocking finding:

1. Compare it with the original goal and current scope ledger.
2. Classify it as `accept`, `narrow`, or `reject`.
3. If accepted, make the smallest sufficient correction.
4. If narrowed, revise the requirement to express the intended smaller
   guarantee without adding the reviewer’s broader mechanism.
5. If rejected, do not modify the plan for that finding; record the concrete
   scope or evidence reason in your final summary.

For minor findings and nits, make only changes that remain inside the current
scope and do not materially expand implementation or verification work.

After editing, reconcile repeated contracts across the active Project and
sub-issues. Remove superseded wording.

Do not:

- add a new subsystem merely to satisfy an overbroad interpretation;
- convert optional hardening into an acceptance criterion;
- expand into historical or already-completed work unless it directly blocks
  the goal;
- increase test scope beyond representative coverage without an explicit
  requirement;
- assume every reviewer-proposed implementation is mandatory.

In your final summary, report the dispositions and call out any net scope
change.
{end_if_round_gt_1}

Use Linear directly for all plan updates. End with the required machine-parsed author verdict block.