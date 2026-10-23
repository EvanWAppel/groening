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
- [ ] 🟡 **Decide: should a single dead optional source fail the whole deploy?** — On ~2026-10-18 Metro retired the old UGB layer and every Railway build failed (`ValueError: ugb: no feature returned`) until the URL was repointed to the RLIS layer (fix/ugb-source PR). Today any one source going dark blocks *all* deploys, including security fixes. Making a topic optional is a design call, not a code tweak: it conflicts with CLAUDE.md "a fetch that returns zero rows should raise" / "do not hide errors", and dbt `stg_*`/`mart_*` plus the page would still need to handle a missing `raw.<topic>` table. Options: (a) keep fatal (status quo); (b) mark a set of topics optional so the build logs a `DROPPED topic …` warning (the existing `DROPPED_TOPICS` pattern), skips that dbt model, and the page shows a "source unavailable" notice; (c) fall back to the last good snapshot in `data/` (like `restaurant_inspections_raw.parquet`). Reply in `DECISIONS.md` or tell Claude which option, and for (b)/(c) which topics.
