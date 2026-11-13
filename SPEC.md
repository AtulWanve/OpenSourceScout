# OpenSourceScout Design Specification

> Status: Stage 0 (collect: `scripts/scout.py`), Stage 1 (pack: `scripts/pack_repos.py`), Stage 2 (judge: `scripts/judge_loop.py`), and Stage 3 (index: `scripts/build_index.py`) are implemented. Unified runner (`scripts/run.py`) coordinates the pipeline.
> Rules live in [`criteria.yaml`](criteria.yaml); output note template lives in [`knowledge/repos/_TEMPLATE.md`](knowledge/repos/_TEMPLATE.md).

## 0. Architecture: assessment, routing, and capital verification

Every recorded attribute and decision belongs to one of three stages: a factual property, a worthiness check, or a routing disposition.

```
STAGE 0 · COLLECT (facts only, persistent)                    ← scripts/scout.py
   repo/account → GitHub API + README → one resumable note per repo = the
   FACT CORPUS. No interpretation or LLM dependencies. Any consumer can read it
   (human readers, Obsidian, or external tools).
                          │  facts persist; judging runs as a separate later pass
                          ▼  that consumes facts without editing them
LAYER 1 · ASSESS (facts + worthiness, one pass; output keeps them separate)
   facts:      category · features · ai_at_build/ai_at_run (descriptive tag) · license · liability
   worthiness: ≥1 payoff  +  passes standards  +  warrants investment  +  liability LOW
   verdict:    payoff[commercial|reputation|learning|strategic:product|strategic:capability]
                           │  outcome and facts feed the route
                           ▼
LAYER 2 · ROUTE   independent → too_big → adopt → merge → upstream_pr/simplify_fork → combined → rejected
                          │
                          ▼
FINAL · CAPITAL   launch must be free (else parked_capital); scale from revenue
                  → status: active | parked_capital
```

Key principles:
- Facts and worthiness are evaluated in one pass. Output notes store facts separately from verdicts so features, licenses, and categories can be queried across the portfolio regardless of disposition.
- Every disposition assigns a payoff. Adopted product tools record `strategic:product`. Adopted pipeline tools record `strategic:capability`. Merge and combination candidates carry `strategic:product`. Capability payoffs apply when upgrading recurring build steps.
- AI integration serves as a descriptive attribute (`ai_at_build`, `ai_at_run`, `emerging_class`, `durability`) and does not dictate worthiness or routing. Non-AI projects compete under the same criteria.
- Safety is governed by liability level. High liability projects (where incorrect outputs cause legal, financial, or physical harm, or require regulated licensing) are rejected. Low liability tools in the same domains remain eligible.
- Capital review occurs at the final step. Initial launch must require zero capital, with scale funded from revenue. Candidates with paid dependencies receive `parked_capital` status until free, maintained alternatives are identified.
- Category taxonomies span both developer tools and non-developer applications.

## 1. Purpose

Evaluate a GitHub repository or raw project concept and assign one disposition:

- `independent`: Viable and within solo developer scope using AI tools. Standalone build.
- `adopt`: Complete tool ready for immediate use in product or build workflows, maintained externally as a dependency.
- `too_big`: Valuable concept that exceeds solo scope and requires a dedicated team or external partner.
- `merge`: Folds into an existing project (`as_is`, `modify_fully`, or `harvest_parts`).
- `upstream_pr`: Useful core with friction or UI gaps that can be fixed directly via upstream pull request.
- `simplify_fork`: Useful core needing a simplified wrapper or API where an upstream pull request is unviable (license permitting).
- `combined`: Features fulfill a target product definition when grouped with other candidate repositories.
- `rejected`: Kept as feature-tagged inventory for future target matching.

The evaluation produces a routing decision rather than a numeric score. The status flag (`active` or `parked_capital`) records whether immediate pursuit is blocked by capital requirements.

## 2. Decision funnel

```
              ┌───────────────────────────────────────────────┐
 candidate → │ 1. Worth building and solo+AI scope?           │─ yes → INDEPENDENT
              └───────────────────────────────────────────────┘
                        │ no
              ┌─────────▼─────────────────────────────────────┐
              │ 1b. Worth doing but needs a larger team?      │─ yes → TOO_BIG
              └─────────┬─────────────────────────────────────┘
                        │ no
              ┌─────────▼─────────────────────────────────────┐
              │ 1c. Complete tool ready to use as-is?         │─ yes → ADOPT (product or build pipeline)
              └─────────┬─────────────────────────────────────┘
                        │ no
               ┌─────────▼─────────────────────────────────────┐
               │ 2. Folds into an existing project?            │─ yes → MERGE (modify-fully or harvest-parts)
               └─────────┬─────────────────────────────────────┘
                         │ no
               ┌─────────▼─────────────────────────────────────┐
               │ 3. Valuable core and addressable via PR?      │─ yes → UPSTREAM_PR
               └─────────┬─────────────────────────────────────┘
                         │ no
               ┌─────────▼─────────────────────────────────────┐
               │ 3b. Valuable core needing simplified wrapper? │─ yes → SIMPLIFY_FORK (license permitting)
               └─────────┬─────────────────────────────────────┘
                         │ no
               ┌─────────▼─────────────────────────────────────┐
               │ 4. Features fulfill target when pooled?       │─ yes → COMBINED (build kit toward target)
               └─────────┬─────────────────────────────────────┘
                        │ no
                        ▼
                     REJECTED (retained as feature-tagged inventory)

 ─────────────────────────────────────────────────────────────────────────────
 After routing, for active candidates (independent, adopt, merge, upstream_pr, simplify_fork, combined):
              ┌───────────────────────────────────────────────┐
              │ Needs capital that cannot be spent now?        │─ yes → status: PARKED_CAPITAL
              └───────────────────────────────────────────────┘        (revisit when funded or when a
                        │ no                                             free alternative is found)
                        ▼
                     status: ACTIVE (ready to build)
```

Solo developer scope assumes one developer working with AI tools, setting a high capability threshold for `independent`. See `criteria.yaml` for formal definitions.

Evaluation never rejects on programming language, spoken language, or capital. Capital is reviewed only during the final status check.

## 3. Evaluation methods (ideas vs. repositories)

| | Idea | Repository |
|---|---|---|
| Method | Direct LLM assessment | Automated metadata collection first, LLM evaluation second |
| Flow | LLM reads concept and prior art, then applies the funnel | Scripts pull GitHub metadata, evaluate concrete facts, and pass candidate data to the judge loop |
| Why | Raw ideas lack structured metrics and require direct reasoning | Metadata filters volume cheaply; LLM evaluation resolves nuanced criteria |

## 4. Targets, inventory, and combination

The reject pool acts as a feature-tagged inventory. Single-feature repositories that fail `independent` (too small) or `merge` (no active project match) are preserved as candidate inventory.

Combination uses target-driven feature assembly:

- A target is either a product target (such as an open alternative to a proprietary tool) or a build capability target (addressing internal pipeline gaps such as UI perception, schema generation, or runtime observability). Targets live in `knowledge/targets/` and define `needs_features`.
- Candidate repositories are tagged with `provides_features`.
- Assembly matches candidate features against target requirements to generate a build kit: covering repositories, coverage percentage, and remaining feature gaps.

Matching feature tags against explicit targets avoids combinatorial explosion. The match executes when a target is created or when a new feature is indexed, making the repository index queryable.

Re-validation: Rejections are provisional evaluations based on existing portfolio entries, targets, and criteria. When criteria change, affected candidate notes are re-evaluated. When a new stack, project, or target is added, queries run against candidate notes matching those attributes.

Merge modes: `modify_fully` adapts the full repository to an existing codebase; `harvest_parts` extracts specific components or routines.

## 4b. Strategy layer: payoff, AI categorization, and cost controls

Every note records an explicit payoff:
- Payoff: Every note records a payoff from `commercial`, `reputation`, `learning`, `strategic:product`, or `strategic:capability`. A value of `none` routes to `rejected`. `strategic:product` indicates value within an active project or target. `strategic:capability` indicates an improvement to a recurring build step.
- AI classification: Fields `ai_at_build`, `ai_at_run`, `emerging_class`, and `durability` describe how AI is used without penalizing or boosting evaluation scores.
- Resource management: Development prioritizes developer attention and focused LLM reasoning over unguided prompt generation.
- Liability assessment: Safety is determined by risk severity rather than application category. Regulated tools with direct safety or financial liability are rejected, while low-risk utilities in the same fields remain eligible.
- Categories: Category tags support portfolio strategy and distribution planning.

## 5. Directory structure: public framework and private data

The project separates framework code from local working datasets through `.gitignore`:

```text
OpenSourceScout/
├── /.claude/                     PUBLIC   tooling configuration and custom commands
├── /.github/                     PUBLIC   CI workflows and templates
├── /docs/                        PUBLIC   milestones and documentation
├── /prompts/                     PUBLIC   evaluation prompt templates
│   └── judge_worker.md
├── /scripts/                     PUBLIC   pipeline execution scripts
│   ├── build_index.py
│   ├── judge_loop.py
│   ├── optimize_prompt.py
│   ├── oss_config.py
│   ├── pack_repos.py
│   ├── run.py
│   └── scout.py
├── /setup/                       PUBLIC   workspace setup guidelines
├── /tests/                       PUBLIC   automated test suite
├── AGENTS.md                     PUBLIC   cross-tool guidelines
├── CLAUDE.md                     PUBLIC   project rules and directory map
├── CONTEXT.md                    PUBLIC   root context
├── README.md                     PUBLIC   overview and quickstart
├── REFERENCES.md                 PUBLIC   architecture references
├── SPEC.md                       PUBLIC   design and architecture specification
├── capabilities.yaml             PUBLIC   controlled feature vocabulary
├── config.example.yaml           PUBLIC   configuration template
├── criteria.yaml                 PUBLIC   default evaluation rules
├── .gitignore
│
├── config.local.yaml             PRIVATE  custom portfolio and criteria overrides (git-ignored)
├── criteria.local.yaml           PRIVATE  custom criteria overrides (git-ignored)
├── /inbox/                       PRIVATE  queued repository digests (git-ignored)
├── /investigations/              PRIVATE  research workspace (git-ignored)
├── /knowledge/                   PRIVATE  notes, targets, daily logs, indexes (git-ignored)
│   ├── /daily/                   PRIVATE  sweep activity logs
│   ├── /repos/                   PRIVATE  verdict notes (_TEMPLATE.md tracked)
│   ├── /targets/                 PRIVATE  target definitions (_TEMPLATE.md tracked)
│   ├── INDEX.md                  PRIVATE  main repository index
│   ├── INDEX-features.md         PRIVATE  feature and capability index
│   └── INDEX-inventory.md        PRIVATE  inventory index
├── /Methodology/                 PRIVATE  local reference architecture guides (git-ignored)
└── project_enhancement_ideas.md  PRIVATE  brainstorm notes (git-ignored)
```

Core structural choices:
1. One candidate store, disposition in frontmatter: Avoid moving files across status folders; dispositions update within the note frontmatter.
2. Generated index files (`knowledge/INDEX*.md`): The index builder parses candidate notes to allow feature lookups without scanning every markdown file.
3. Append-only judgment logs: Notes preserve historical evaluation records. Each entry records review date, outcome, modified assumptions, and criteria version. Context updates or factual corrections add new entries to the log while frontmatter reflects the latest verdict. Factual metadata from Stage 0 is refreshed independently of subjective verdicts.

## 6. Project decisions

1. GitHub access (Resolved): `scripts/scout.py` queries the GitHub REST API directly using standard library utilities without LLMs or CLI wrappers. Rate limits: 60 requests/hour unauthenticated, or 5,000 requests/hour with `GITHUB_TOKEN`.
2. Index storage (Resolved): Implemented as generated markdown index files (`knowledge/INDEX*.md`) regenerated by `scripts/build_index.py`.
3. Combination cadence: Triggered on demand when a target product definition exists or gains a newly covered feature.
4. License: Open-source license selection planned prior to public release.

## 7. Implementation phases

- Phase 0 (Complete): Framework rules, definitions, schemas, configuration cascading, and public/private separation.
- Phase 1 (Complete): Metadata fetch (`scripts/scout.py`), code evidence packing (`scripts/pack_repos.py`), note schemas, and prompt template (`prompts/judge_worker.md`).
- Phase 2 (Complete): Judge loop (`scripts/judge_loop.py`) with backend support (OpenCode and Claude), append-only evaluation logs, and CLI runner (`scripts/run.py`).
- Phase 3 (In Progress): Feature vocabulary (`capabilities.yaml`), index generation (`scripts/build_index.py`), and target feature set-cover matching.
- Phase 4 (In Progress): Account intake sweeps and daily activity logs (`knowledge/daily/`).
- Planned: Raw project idea evaluation track.
