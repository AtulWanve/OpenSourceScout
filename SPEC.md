# OpenSourceScout — Design Spec (v2, planning)

> Status: **plan only, nothing built yet.** Describes *what* the tool does and
> *how the pieces fit*, so we pick a form factor before writing code.
> Rules live in [`criteria.yaml`](criteria.yaml); output shape in
> [`knowledge/repos/_TEMPLATE.md`](knowledge/repos/_TEMPLATE.md).

## 0. How it all fits — one assessment, then route, then a money gate

Everything the tool records or decides is one of these. When adding a new
criterion, ask "is it a fact, part of the worth-test, or a route?"

```
LAYER 1 · ASSESS (facts + worthiness, ONE pass; output keeps them separate)
   facts:      category · payoff[commercial|reputation|learning|strategic] · features
               · ai_at_build/ai_at_run (categorization only) · license · liability
   worthiness: ≥1 payoff  +  passes standards  +  warrants investment  +  liability LOW
               (judged AGAINST a disposition, not once globally)
                          │  outcome + facts feed the route
                          ▼
LAYER 2 · ROUTE   independent → too_big → merge → combined → rejected
                          │
                          ▼
FINAL · CAPITAL   launch must be free (else parked_capital); scale from revenue
                  → status: active | parked_capital
```

Key consequences:
- **Facts + worthiness are judged in one pass**, but the output note lists facts
  separately from the verdict — features/license/category get reused later
  (parts-bin, portfolio) no matter what the verdict was.
- **Payoff applies to EVERY disposition.** `strategic` (usefulness to an existing
  project or a target) is the payoff a merge/combined candidate carries.
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
- **too_big** — worth doing but needs a real team → defer / partner (not a merge).
- **merge** — folds into an existing project (one you already run): as-is, modify-fully, or harvest-parts.
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
             │ 1b. Worth doing but too big (needs a team)?    │─ yes → TOO_BIG
             └─────────┬─────────────────────────────────────┘
                       │ no
             ┌─────────▼─────────────────────────────────────┐
             │ 2. Folds into an existing project?             │─ yes → MERGE (as-is | modify-fully | harvest-parts)
             └─────────┬─────────────────────────────────────┘
                       │ no
             ┌─────────▼─────────────────────────────────────┐
             │ 3. Its features help cover a target,           │─ yes → COMBINED (build-kit toward target)
             │    pooled with other (rejected) repos?         │
             └─────────┬─────────────────────────────────────┘
                       │ no
                       ▼
                    REJECTED  (retained as feature-tagged inventory for future targets)

 ─────────────────────────────────────────────────────────────────────────────
 AFTER routing, for anything you'd pursue (independent / merge / combined):
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

## 4. Targets, the parts bin, and the combination step (step 3)

The reject pool is **not a graveyard — it's a feature-tagged parts bin.** A simple
single-feature repo *should* fail `independent` (too small) and `merge` (nothing
to fold into yet); its value is as **inventory**.

Combination isn't blind pairing — it's **target-driven feature assembly:**

- A **target** = a product you wish existed, usually *"an open alternative to
  [paywalled incumbent X]"*, with a list of `needs_features`. Lives in `knowledge/targets/`.
- Every candidate is tagged with `provides_features`.
- **Assembly = feature set-cover:** match pool repos (rejects included) onto a
  target's needs. Output a **build-kit** — which repo covers which feature, the
  coverage %, and the still-open gaps. That's a concrete shopping list, e.g.
  "6 single-feature repos → replaces one paywalled SaaS."

Why this beats brute force: with N rejects there are 2^N subsets, but you never
enumerate them — you match on feature tags toward a defined target. It runs
**when a target exists or gains a newly-covered feature**, not as a blind nightly
sweep. This is what makes the reject pool needing to be *queryable* (§5) pay off.

**Merge has three modes** (step 2), not two: `as_is`, `modify_fully` (rework the
whole thing to fit), or `harvest_parts` (dismantle it, take only the useful
part). `harvest_parts` and target-assembly are cousins — both are about parts
rather than whole repos.

## 4b. Strategy layer — payoff, AI-as-category, and the real cost gate

`worth_doing` carries *why bother* — and deliberately keeps some things OUT of the decision:

- **Payoff** — ≥1 of `commercial | reputation | learning | strategic`. No payoff ⇒
  not worth your time. `strategic` (usefulness to an existing project/target) is
  the payoff a merge/combined candidate carries.
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
├─ criteria.yaml                   PUBLIC   the rules (no private project names)
├─ SPEC.md                         PUBLIC   design + rationale
├─ prompts/repo-judge.md           PUBLIC   the repo track
├─ knowledge/repos/_TEMPLATE.md    PUBLIC   the note schema (real notes below are ignored)
├─ knowledge/targets/_TEMPLATE.md  PUBLIC
├─ .gitignore
│
├─ config.local.yaml               PRIVATE  your portfolio, standards, categories
├─ knowledge/repos/*               PRIVATE  verdict notes
├─ knowledge/{targets,topics,daily,combinations}/*   PRIVATE
├─ inbox/*                         PRIVATE  repos queued to evaluate
├─ index/                          PRIVATE  generated parts-bin index (features → candidates)
└─ project_enhancement_ideas.md    PRIVATE  orphan brainstorm — git-ignored; consider deleting
```

Two model-level choices behind this:
1. **One candidate store, `disposition` in front-matter** — don't shuffle files
   between status folders; a candidate's route can change.
2. **A generated `index/`** (JSONL) so the combination step (§4) can query
   features without walking every note.

## 6. Decisions still open

1. **GitHub access** — `gh` CLI is **not installed** here. Either install + `gh auth
   login` (5000 req/hr, needed for volume), or the judge falls back to WebFetch of
   the REST API (anonymous, ~60 req/hr — fine for a handful at a time).
2. **Index storage** — JSONL (simple, Git-friendly) vs. SQLite. *Lean: JSONL.*
3. **Combination cadence** — on demand when a target exists (not a blind sweep).
4. **LICENSE** — none yet; pick one before going public (an OSS-scout should ship OSS).

## 7. Build phases

- **Phase 0:** framework — funnel, definitions, schema, public/private split. ✅
- **Phase 1 (now): repo track** — [`prompts/repo-judge.md`](prompts/repo-judge.md):
  feed a repo → gather GitHub metadata → run the funnel → write a note. ← ready to run
- **Phase 2:** idea track — AI judges a raw idea down the same funnel.
- **Phase 3:** the parts-bin `index/` + target assembler (step 3), on demand.
- **Phase 4:** batch intake from GitHub search/trending; topic rollups; daily logs.
