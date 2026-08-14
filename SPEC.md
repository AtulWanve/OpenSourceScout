# OpenSourceScout — Design Spec (v2, planning)

> Status: **partially built.** Stage 0 (COLLECT — facts, LLM-free) is live:
> `scripts/scout.py` writes the fact corpus, `scripts/build_index.py` renders the
> derived index. The judging layer (interpretation) is specified here and being built.
> Rules live in [`criteria.yaml`](criteria.yaml); output shape in
> [`knowledge/repos/_TEMPLATE.md`](knowledge/repos/_TEMPLATE.md).

## 0. How it all fits — one assessment, then route, then a money gate

Everything the tool records or decides is one of these. When adding a new
criterion, ask "is it a fact, part of the worth-test, or a route?"

```
STAGE 0 · COLLECT (facts only, LLM-free, persistent)          ← scripts/scout.py
   repo/account → GitHub API + README → one resumable markdown note per repo = the
   FACT CORPUS. No interpretation here, no LLM. Solves discovery: no session re-fetches
   the same repo. Any consumer reads it — human, Obsidian, or any AI.
                          │  facts persist; judging is a SEPARATE later pass that
                          ▼  CONSUMES them and never edits them
LAYER 1 · ASSESS (facts + worthiness, ONE pass; output keeps them separate)
   facts:      category · features · ai_at_build/ai_at_run (categorization only) · license · liability
   worthiness: ≥1 payoff  +  passes standards  +  warrants investment  +  liability LOW
   verdict:    payoff[commercial|reputation|learning|strategic:product|strategic:capability] (judge-assigned)
                           │  outcome + facts feed the route
                           ▼
LAYER 2 · ROUTE   independent → too_big → adopt → merge → upstream_pr/simplify_fork → combined → rejected
                          │
                          ▼
FINAL · CAPITAL   launch must be free (else parked_capital); scale from revenue
                  → status: active | parked_capital
```

Key consequences:
- **Facts + worthiness are judged in one pass**, but the output note lists facts
  separately from the verdict — features/license/category get reused later
  (parts-bin, portfolio) no matter what the verdict was.
- **Payoff applies to EVERY disposition.** Adopted product tools record `strategic:product`;
  adopted pipeline tools record `strategic:capability`; both may apply when the tool serves
  both roles. `strategic:product` is the payoff a merge/combined candidate carries.
  `strategic:capability` upgrades your recurring build steps.
- **AI-ness is categorization only** — `ai_at_build`/`ai_at_run`/`emerging_class`
  and `durability` must NOT affect worthiness or routing, so non-AI products
  compete equally and aren't buried by the AI-runtime hype.
- **Liability, not domain, is the gate.** High = a wrong output causes legal/
  financial/physical harm or needs a license from day one → out. Safe tools in
  the same broad area (a budgeting UI, a workout logger) stay in.
- **Money is last.** Launch must be free (zero out-of-pocket); scaling comes from
  revenue. Can't launch free → `parked_capital`; each paid dependency becomes a
  mini-target — scout a free *and still-maintained* alternative, swap in, unpark.
- **Not developer-only.** Category seeds span non-dev domains too.

## 1. Purpose

Take a **GitHub public repo** or a **raw idea** and route it to one disposition:

- **independent** — worth doing AND within one-person-plus-agentic-AI scope → build it standalone.
- **adopt** — a complete, healthy tool you *use as-is* (don't build, don't fork, don't fold in) — in a product's workflow or your build pipeline. Ownership stays external; it remains a separate dependency with its code in its own repository, never folded into your project. Distinct from `merge` (its code folds into yours) and `independent` (it already exists).
- **too_big** — worth doing but needs a real team → defer / partner (not a merge).
- **merge** — folds into an existing project (one you already run): modify-fully or harvest-parts.
- **upstream_pr** — great core tech, terrible UX/complexity, but the codebase is manageable enough to contribute a fix directly.
- **simplify_fork** — great core tech, terrible UX, but their project is too rigid for a PR (requires license check to wrap or fork).
- **combined** — its feature(s) help cover a target when pooled with other (often rejected) single-feature repos.
- **rejected** — none of the above, *but retained* as feature-tagged inventory for future target-assembly.

It's a **routing decision, not a score.** Then a `status` (`active` |
`parked_capital`) records whether money — the last gate — blocks pursuing it now.

## 2. The funnel (the whole logic, in order)

```
              ┌───────────────────────────────────────────────┐
 candidate → │ 1. Worth doing AND solo+AI scope?              │─ yes → INDEPENDENT
              └───────────────────────────────────────────────┘
                        │ no
              ┌─────────▼─────────────────────────────────────┐
              │ 1b. Worth doing but too big (needs a team)?   │─ yes → TOO_BIG
              └─────────┬─────────────────────────────────────┘
                        │ no
              ┌─────────▼─────────────────────────────────────┐
              │ 1c. A complete tool you'd USE as-is?          │─ yes → ADOPT (unchanged; product or build-pipeline)
              └─────────┬─────────────────────────────────────┘
                        │ no
               ┌─────────▼─────────────────────────────────────┐
               │ 2. Folds into an existing project?             │─ yes → MERGE (modify-fully | harvest-parts)
               └─────────┬─────────────────────────────────────┘
                         │ no
               ┌─────────▼─────────────────────────────────────┐
               │ 3. Valuable core, terrible UX, but codebase   │─ yes → UPSTREAM_PR (fix it directly)
               │    is manageable enough to fix via PR?        │
               └─────────┬─────────────────────────────────────┘
                         │ no
               ┌─────────▼─────────────────────────────────────┐
               │ 3b. Valuable core, terrible UX, but a PR      │─ yes → SIMPLIFY_FORK (wrap/fork, license permitting)
               │     isn't viable — wrap or fork it?           │
               └─────────┬─────────────────────────────────────┘
                         │ no
               ┌─────────▼─────────────────────────────────────┐
               │ 4. Its features help cover a target,           │─ yes → COMBINED (build-kit toward target)
               │    pooled with other (rejected) repos?         │
               └─────────┬─────────────────────────────────────┘
                        │ no
                        ▼
                     REJECTED  (retained as feature-tagged inventory for future targets)

 ─────────────────────────────────────────────────────────────────────────────
 AFTER routing, for anything you'd pursue (independent / adopt / merge / combined):
              ┌───────────────────────────────────────────────┐
              │ Needs capital you can't spend now?             │─ yes → status: PARKED_CAPITAL
              └───────────────────────────────────────────────┘        (revisit when funded, OR when a
                        │ no                                             free alt to a paid dependency is found)
                        ▼
                     status: ACTIVE — go build
```

**"one person project" is redefined:** one person *orchestrating agentic AI*,
not one person alone — so the scope bar for `independent` is high. See
`criteria.yaml:definitions`.

**Never rejects on spoken language, programming language, or capital.** Language
is never a gate; capital is the *last* gate, never the first.

## 3. Who judges (idea vs repo)

| | **Idea** | **Repo** |
|---|---|---|
| Method | **AI is the direct judge** — no metric system | **Automate first, AI second** |
| Flow | LLM reads the idea + prior-art search → funnel | Pull GitHub metadata → run funnel on hard facts → escalate borderline/after a constraint to an agentic coding agent for a second opinion |
| Why | You can't score a raw idea in code without over-building | Metrics filter volume cheaply; AI adjudicates the calls that matter |

## 4. Targets, the parts bin, and the combination step (step 4)

The reject pool is **not a graveyard — it's a feature-tagged parts bin.** A simple
single-feature repo *should* fail `independent` (too small) and `merge` (nothing
to fold into yet); its value is as **inventory**.

Combination isn't blind pairing — it's **target-driven feature assembly:**

- A **target** is either a **product-target** — a product you wish existed, usually
  *"an open alternative to [paywalled incumbent X]"* — OR a **build-capability
  target**: your own build pipeline, whose `needs_features` are your recurring
  build-step blind spots (ui-perception, schema-and-data, runtime-observability, …).
  Both live in `knowledge/targets/` and both carry a list of `needs_features`.
- Every candidate is tagged with `provides_features`.
- **Assembly = feature set-cover:** match pool repos (rejects included) onto a
  target's needs. Output a **build-kit** — which repo covers which feature, the
  coverage %, and the still-open gaps. That's a concrete shopping list, e.g.
  "6 single-feature repos → replaces one paywalled SaaS."

Why this beats brute force: with N rejects there are 2^N subsets, but you never
enumerate them — you match on feature tags toward a defined target. It runs
**when a target exists or gains a newly-covered feature**, not as a blind nightly
sweep. This is what makes the reject pool needing to be *queryable* (§5) pay off.

**Re-validation — a reject is provisional.** It was judged against the portfolio,
stacks, targets, and rules that existed *then*. The re-run scope depends on what
changed: **rule or criteria changes** (a new criterion, a modified standard) require
all rejects to be **re-run** (unless criteria carry version metadata that safely
identifies only the affected subset); **targeted changes** — a new stack, project,
target, or a dependency/health shift — re-run only the rejects tagged with the
matching attributes. The tags on each reject make this a targeted query, not a
blind re-sweep.

**Merge has two modes**: `modify_fully` (rework the
whole thing to fit) or `harvest_parts` (dismantle it, take only the useful
part). `harvest_parts` and target-assembly are cousins — both are about parts
rather than whole repos.

## 4b. Strategy layer — payoff, AI-as-category, and the real cost gate

`worth_doing` carries *why bother* — and deliberately keeps some things OUT of the decision:

- **Payoff** — what value came out of evaluating it; always recorded, never blank. A positive
  answer is ≥1 of `commercial | reputation | learning | strategic:product | strategic:capability`;
  the explicit `none` (evaluated → nothing useful) stands alone and forces `rejected`.
  No *positive* payoff ⇒ not worth your time. **`strategic:product`** measures usefulness
  *inside* an existing project/target — a shippable feature, the merge/combined payoff.
  **`strategic:capability`** upgrades your *means of production* — a recurring build step
  made faster/more accurate/less manual; it merges into your **build pipeline**, not a
  product. Capability value counts ONLY if it upgrades a build step you genuinely
  **repeat** — the bar that stops "it helps build something" from rescuing every reject.
- **AI-ness is categorization, not a merit.** `ai_at_build` / `ai_at_run` /
  `emerging_class` / `durability` are recorded but **do not decide** worthiness or
  routing — so non-AI products compete equally and AI-runtime products aren't
  penalized. `emerging_class` (build-with-AI / run-AI-free) is just a spotlight for
  that rising class.
- **The cost gate.** The scarce costs are **your time** and **strong-model
  reasoning** (a premium model) — NOT bulk build-tokens from cheap models. Spend
  build-tokens freely; the point is to convert cheap tokens now into durable assets.
- **Liability, not domain, gates safety.** High-liability/regulated work (harm on
  error, or needs a license day one) is out; safe tools in the same area stay in.
- **Category** is one controlled field for **portfolio strategy** — where to
  monetize vs. make a name — a different job from discovery tags/topics.

## 5. Directory structure — public framework vs. private data

The shape this took is **a shareable framework + your private working dataset**,
headed for a public repo. So the split that matters is public vs. private, done
with `.gitignore` — no file-shuffling:

```
OpenSourceScout/
├─ README.md                       PUBLIC   what it is + how to run the repo track
├─ SPEC.md                         PUBLIC   design + rationale
├─ criteria.yaml                   PUBLIC   the rules (no private project names)
├─ capabilities.yaml               PUBLIC   controlled feature vocabulary
├─ config.example.yaml             PUBLIC   config template (copy to config.local.yaml)
├─ .env.example                    PUBLIC   env template (GITHUB_TOKEN)
├─ prompts/judge_worker.md         PUBLIC   the judge prompt used by judge_loop.py
├─ knowledge/repos/_TEMPLATE.md    PUBLIC   the note schema (real notes below are ignored)
├─ knowledge/targets/_TEMPLATE.md  PUBLIC
├─ scripts/                        PUBLIC   pipeline scripts (scout.py, judge_loop.py, build_index.py, etc.)
├─ .gitignore
│
├─ config.local.yaml               PRIVATE  your portfolio, standards, categories
├─ knowledge/repos/*               PRIVATE  verdict notes
├─ knowledge/{targets,topics,daily}/*  PRIVATE
├─ knowledge/INDEX*.md             PRIVATE  generated indexes (features → candidates)
├─ inbox/*                         PRIVATE  repos queued to evaluate
└─ project_enhancement_ideas.md    PRIVATE  orphan brainstorm — git-ignored
```

Three model-level choices behind this:
1. **One candidate store, `disposition` in front-matter** — don't shuffle files
   between status folders; a candidate's route can change.
2. **A generated Markdown index** (`knowledge/INDEX*.md`) so the combination step (§4)
   can query features without walking every note. Derived view — markdown notes stay the source.
3. **Judgments are append-only history, not one overwrite.** A verdict was made against
   the portfolio/criteria/targets that existed *then* (§4 re-validation), so re-judging
    **keeps** the prior verdict instead of erasing it. The note body carries a dated
    judgment log where each entry records the **outcome** of a review — what changed,
    which assumption was corrected, the new conclusion — plus the criteria version or
    hash and the relevant portfolio, target, dependency, health, and fact/context
    revision identifiers — never the discussion that produced it (**knowledge, not
    chat logs**). Re-judging fires on a context change (§4) *or* on a
   **correction** — the prior read was simply wrong and got challenged; interpretation is
   expected to evolve. Front-matter mirrors the *current* (latest) verdict for tooling.
   Facts are never written by a judge — immutability is about *who writes*, not about facts
   being frozen; Stage 0 re-fetches refresh them, and a facts-drift is itself a re-judge cause.

## 6. Decisions still open

1. **GitHub access — RESOLVED.** `scripts/scout.py` calls the REST API directly
   (stdlib, no `gh` CLI, no LLM). Anonymous 60/hr, or 5000/hr with `GITHUB_TOKEN`
   (env or `.env`). The old "judge falls back to WebFetch in-session" path is gone —
   hand-fetching was the token-burn/hallucination source Stage 0 exists to remove.
2. **Index storage — RESOLVED.** Implemented as generated Markdown files (`knowledge/INDEX*.md`), regenerated by `scripts/build_index.py`.
3. **Combination cadence** — on demand when a target exists (not a blind sweep).
4. **LICENSE** — none yet; pick one before going public (an OSS-scout should ship OSS).

## 7. Build phases

- **Phase 0:** framework — funnel, definitions, schema, public/private split. ✅
- **Phase 1: repo track** — Stage 0 fetch (`scripts/scout.py`, LLM-free) + the note
  schema + [`prompts/judge_worker.md`](prompts/judge_worker.md) for the judging pass. ✅
- **Phase 2 (partial):** judging layer — `judge_loop.py` + `judge_worker.md` built;
  append-only log working. Prompt alignment with `_TEMPLATE.md` fields in progress.
- **Phase 3 (partial):** feature vocabulary (`capabilities.yaml`) + `normalize_features.py`
  + derived indexes (`scripts/build_index.py`) built; the target assembler (set-cover,
  step 4 combined) is next.
- **Phase 4 (partial):** account-sweep intake + daily logs built; GitHub search/trending
  intake and topic rollups pending.
- **Pending:** idea track — a judge routes a raw idea down the same funnel.
