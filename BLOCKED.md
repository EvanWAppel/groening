# BLOCKED — what I need from Evan

> **Fleet repo (_system D-036, D-051, D-052):** groening's blockers live in Jira as *Needs Evan*
> tickets (component `groening`; file with `uv run --project ~/Documents/_system sys file-blocker`);
> `sys blockers` mirrors them into the todo dashboard. Two kinds stay here: `[sec]` blockers (the
> security dashboard counts them only here) and anything Jira must not hold — rosters, secrets,
> unpublished writing. Moved 2026-10-31: EA-42 (Review the Tiresias gold set and column-doc claims).


_Resolved 2026-09-27 (decision review, see `DECISIONS.md`): TOPIC-311 → find a
non-sensitive feed (no campsite data); custom domain → deferred. Neither waits on
you anymore._

_Resolved 2026-10-23 (blocker triage): license strings confirmed; dedicated
`groening` Anthropic workspace key ($10/month cap, $5 alert) set on Railway and
confirmed not personal; E7b follow-ups decided (Portland time, raise on unmapped
graffiti status), see `DECISIONS.md`._

- [x] 🔴 **Approve merging the `tiresias` PR** (merged as PR #15 on 2026-10-08) (merge = deploy on Railway). Safe before the key exists: without it the page only shows a notice.
- [x] 🟡 **Pick which topics fall back to a last-good snapshot when their source dies** — answered by Evan 2026-10-24: every candidate except `neighborhoods` (recorded in `DECISIONS.md`, 2026-10-24 entry). Implemented in the snapshot-fallback PR; nothing left to decide.
