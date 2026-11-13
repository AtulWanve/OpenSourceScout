# OpenSourceScout

OpenSourceScout evaluates GitHub repositories and project ideas for solo developers using AI tools. Given a repository, it recommends whether to build on it independently, merge it into an existing project, harvest components, save it as inventory for later reference, or pass.

## Evaluation workflow: assess, route, capital

```
ASSESS   facts + worthiness, in one pass
           facts:      category · payoff · features · ai_at_build/run · license · liability
           worthiness: ≥1 payoff  +  passes your standards  +  warrants your time  +  liability LOW
                       │
ROUTE      independent → too_big → adopt → merge → upstream_pr → simplify_fork → combined → rejected
                       │
CAPITAL    launch must be free (else parked_capital); scale from revenue
                       → status: active | parked_capital
```

- `independent`: Viable and within solo developer scope with AI tools.
- `too_big`: Valuable, but requires a larger team or partner.
- `adopt`: Complete tool ready for immediate use in product or build workflows.
- `merge`: Combines with an existing project (`as_is`, `modify_fully`, or `harvest_parts`).
- `upstream_pr`: Useful core with friction or UI gaps addressable via upstream pull request.
- `simplify_fork`: Useful core needing a simplified wrapper or API where an upstream pull request is unviable.
- `combined`: Features fulfill a target product definition when grouped with other repositories.
- `rejected`: Kept as feature-tagged inventory for future targets.

Core rules:
- Do not reject candidates based on programming language, spoken language, or required capital.
- Treat AI integration as a descriptive category tag rather than an evaluation merit.
- Review capital requirements at the final capital stage rather than during initial assessment.

Full rules are in [`criteria.yaml`](criteria.yaml); architecture details are in [`SPEC.md`](SPEC.md).

## Quickstart

Run test suite:
```bash
python -m pytest tests/
```

Scout a repository:
```bash
python scripts/scout.py OWNER/REPO
```

Rebuild search index:
```bash
python scripts/build_index.py
```

## Repository evaluation

Pass a repository to the pipeline to collect GitHub metadata, evaluate it against criteria, and generate a verdict note. Evaluation prompt instructions are defined in [`prompts/judge_worker.md`](prompts/judge_worker.md).

Place repository targets (one `owner/name` or URL per line) into `inbox/`, or pass them directly to the judge runner.

## Layout

```
criteria.yaml            the shareable rules (public framework)
SPEC.md                  design + rationale
prompts/judge_worker.md  how the repo track evaluates a candidate
knowledge/repos/         verdict notes  (PRIVATE (git-ignored; _TEMPLATE.md is tracked))
knowledge/targets/       wish-list products to assemble toward (PRIVATE)
knowledge/daily/         run logs (PRIVATE)
config.example.yaml      template configuration (tracked baseline)
config.local.yaml        your portfolio, standards, categories (PRIVATE (git-ignored))
```

### Public framework and private data

Framework rules, specifications, prompt templates, and schema configurations are public. Private data (such as project portfolios, candidate evaluations, and local notes) remains in git-ignored paths listed in [`.gitignore`](.gitignore).

Copy `config.example.yaml` to `config.local.yaml` to configure private portfolio definitions and categories. When `config.local.yaml` is absent, scripts fall back to `config.example.yaml` for zero-config execution.

> Status: fact collection live (scripts/scout.py + build_index.py); judging and verdict workflow in progress. Idea track is planned.
