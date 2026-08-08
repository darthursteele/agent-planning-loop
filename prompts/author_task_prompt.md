Round: {round}

{if_round_1}
Goal:
{goal}

This is round 1. Create a new Linear Project to act as the epic for this
plan, write the plan into it, and create sub-issues for the individual pieces
of work.
{end_if_round_1}

{if_round_gt_1}
Linear project: {linear_project_id}

The reviewer looked at your round {prev_round} plan and returned:

{reviewer_findings}

Address every `blocking` finding. Use judgment on `minor`/`nit` findings.
Update the Linear project and its sub-issues directly.
{end_if_round_gt_1}
