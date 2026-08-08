This planning loop hit its round cap ({max_rounds} rounds) without reaching
approval on Linear project {linear_project_id}.

Post a comment on the Linear project summarizing every outstanding `blocking`
finding across all rounds, and tag the user so they know the loop stopped and
needs a human decision. Do not attempt further plan changes yourself.

Outstanding blocking findings, most recent round first:

{all_blocking_findings}

End your turn with a verdict block:

<<<VERDICT>>>
{"role":"reviewer","round":"escalation","verdict":"escalated"}
<<<END_VERDICT>>>
