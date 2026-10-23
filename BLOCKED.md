# BLOCKED — what I need from Evan

_Resolved 2026-09-27 (decision review, see `DECISIONS.md`): TOPIC-311 → find a
non-sensitive feed (no campsite data); custom domain → deferred. Neither waits on
you anymore._

_Resolved 2026-10-23 (blocker triage): license strings confirmed; dedicated
`groening` Anthropic workspace key ($10/month cap, $5 alert) set on Railway and
confirmed not personal; E7b follow-ups decided (Portland time, raise on unmapped
graffiti status), see `DECISIONS.md`._

- [ ] 🟡 **Review the Tiresias gold set and column-doc claims** — skim `evals/tiresias_gold.yaml` (25 drafted questions: are the "answer" ones answerable and the "abstain" ones not?) and check the 14 claims in `TIRESIAS.md` → "Column-doc claims to check against the data". Edit `models/marts/schema.yml` directly or note corrections for Claude.
- [x] 🔴 **Approve merging the `tiresias` PR** (merged as PR #15 on 2026-10-08) (merge = deploy on Railway). Safe before the key exists: without it the page only shows a notice.
