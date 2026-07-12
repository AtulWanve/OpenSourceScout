# Repo Judge — the GitHub repo track

You are evaluating one or more **GitHub repositories** against
[`criteria.yaml`](../criteria.yaml) and the private
[`config.local.yaml`](../config.local.yaml), then writing a verdict note per repo.

Method (from `criteria.yaml:judging.repo`): **automated first, AI second.**
Gather hard facts mechanically; then YOU apply judgment. Read `criteria.yaml` and
`config.local.yaml` in full before starting — they are the source of truth and
may have changed.

## Input

- A single repo: `owner/name` or a GitHub URL, **or**
- A batch: every non-empty line of `inbox/` (one `owner/name` / URL per line).

## Step 1 — Gather metadata (the automated pass)

Prefer the `gh` CLI (handles auth + rate limits); fall back to WebFetch of the
REST API or the repo page. Collect:

- `gh api repos/{owner}/{repo}` → `stargazers_count`, `forks_count`,
  `subscribers_count`, `license.spdx_id`, `pushed_at`, `archived`, `fork`,
  `open_issues_count`, `language`, `topics`, `description`, `homepage`
- `gh api repos/{owner}/{repo}/languages` → language breakdown
- Last commit / release recency → **months since `pushed_at`**
- Issues: rough open-vs-closed, and whether a `good first issue` label exists
- **README** (`gh api repos/{owner}/{repo}/readme` decoded, or the raw URL) —
  read it: this is what you extract `provides_features` and `paid_dependencies` from

If a fetch fails, record what you couldn't get and proceed — missing metadata is a
confidence caveat, not a reason to stop.

## Step 2 — Assess (facts + worthiness, one pass)

Fill the **facts** (they get reused later regardless of the verdict):

- `category` — one, from `config.local.yaml:categories` (not dev-only)
- `provides_features` — capabilities, **by what they DO, not the language**
- `payoff` — any of `[commercial, reputation, learning, strategic]`; **≥1 or it's out**
- `liability_risk` — `low`/`high` **by liability, not domain** (see the definition)
- `ai_at_build`, `ai_at_run`, `emerging_class` — **categorization only; never deciding**
- `license` — name + `attribution_required` + `copyleft` + `commercial_ok`
- `capital_to_launch` (`zero`/`needs_money`) + `paid_dependencies`

Then judge **worthiness** — *against each disposition as you walk the funnel*:
`≥1 payoff` + passes your `standards` + `warrants_investment` (your time + premium
reasoning, **not** build-tokens) + `liability_risk: low`.
`ai_*`, `durability`, and `capital` **do not decide**.

## Step 3 — Route (the funnel; first YES wins)

1. **independent** — worthy AND within `one_person_project` scope?
2. **too_big** — worthy but needs a team? → defer/partner (don't force a merge)
3. **merge** — folds into an `existing_project`? mode = `as_is | modify_fully |
   harvest_parts`; if the languages differ, set `harvest_type: blueprint`
   (reimplement — also sidesteps copyleft)
4. **combined** — do its features help cover a `target` when pooled with inventory?
5. **rejected** — none of the above → feature-tagged **inventory** (may also *seed* a new target)

Reminders: never reject on language, capital, or `ai_at_run`. A single-feature
repo *should* fail "independent" — that's correct; its value is as a part.

## Step 4 — Capital (last)

Can it **launch free**? If not → `status: parked_capital`, and turn each
`paid_dependency` into a mini-target: note "scout a free **and still-maintained**
alternative." Otherwise `status: active`.

## Step 5 — Emit

Write `knowledge/repos/{owner}__{name}.md` from
[`knowledge/repos/_TEMPLATE.md`](../knowledge/repos/_TEMPLATE.md): fill the
front-matter, then write the prose — **Verdict** (one line), **Reasoning** (walk
the funnel; justify each soft call), **The move**, **Risks/watch-outs**.
Append one line to `knowledge/daily/{YYYY-MM-DD}.md`:
`{owner}/{name} → {disposition}/{status} — {one-line why}`.

## Batch mode

Process each input, then print a summary: a table of `repo → disposition/status`,
plus **the AI-vs-non-AI balance of what you greenlit** (so AI-runtime candidates
don't crowd out non-AI ones). Flag any repo where missing metadata made the call
low-confidence and worth a manual look.

## Escalation

The above IS the AI second opinion. If a call is genuinely borderline, say so
explicitly in **Risks/watch-outs** and state what evidence would flip it, rather
than forcing a confident verdict.
