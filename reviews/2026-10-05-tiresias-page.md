# Review — Ask Tiresias page (PR #15)

Fresh-context adversarial reviewer, 2026-10-05. No HIGH findings in groening's code;
one **HIGH in the Tiresias library** (CTE-scope allowlist bypass), reproduced and
fixed in Tiresias v0.1.1 (EvanWAppel/tiresias#5) together with a locked-down DuckDB
instance. Deploy path, navigation (`position="hidden"` + page_link), guard probes,
schema tests and ~45 sampled docs all checked out.

| # | Sev | Finding | Disposition |
|---|-----|---------|-------------|
| H1 | HIGH | Library: CTE-scope allowlist bypass (file / excluded-table reads) | **Fixed in Tiresias v0.1.1**; bump the pin here after it is tagged |
| M1 | MED | Tree data is the Parks Tree Inventory, docs/config said street trees | **Fixed** (docs, blurb, example, planner note, gold wording) |
| M2 | MED | No check catches config/artifact drift at deploy | **Fixed**: `RUN tiresias check` after `dbt docs generate` |
| L1 | LOW | Embedding model downloads at first question | Open, as Elvis |
| L2 | LOW | Choropleth note dropped `request_type` for service requests | **Fixed** |
| L3 | LOW | Loose example guidance (column names, STR uniqueness, trees grain) | **Fixed** |
| L4 | LOW | Unpinned production dependencies | Pre-existing |
| L5 | LOW | Gold gaps (air, parks, UGB, adversarial cases) | Open; add after Evan reviews the gold set |
| L6 | LOW | `.dockerignore` lacks `.env` | Pre-existing; Railway builds from git |
