# OpenSourceScout

A decision framework for scouting GitHub repos (and ideas) as a **solo builder
working with agentic AI**. Point it at a repo; it tells you whether to build on
it independently, fold it into an existing project, harvest parts of it, save it
as inventory for later, or pass, and why.

It is not a scorer. It **routes**.

## The model: Assess -> Route -> Capital

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

- **independent**: worth doing AND within one-person-plus-AI scope -> build it.
- **too_big**: worth doing but needs a team -> defer / partner.
- **adopt**: complete, healthy tool to use as-is (in product workflow or build pipeline).
- **merge**: folds into an existing project: `as_is` · `modify_fully` · `harvest_parts`.
- **upstream_pr**: valuable core with friction or UX gaps you can fix via PR.
- **simplify_fork**: valuable core needing a simpler wrapper or API where PR is unviable.
- **combined**: its features help cover a **target** when pooled with other repos.
- **rejected**: retained as feature-tagged **inventory** (supply and inspiration for future targets).

Guiding rules: never reject on spoken/programming language or on capital;
AI-ness is a *category tag*, never a merit; money is the **last** gate, never the
first. Full rules in [`criteria.yaml`](criteria.yaml); design in [`SPEC.md`](SPEC.md).

## Quickstart

Run test suite:
```bash
python -m pytest tests/
```

Scout a repository:
```bash
python scripts/scout.py <owner/repo>
```

Rebuild search index:
```bash
python scripts/build_index.py
```

## Repo track (start here)

You feed it a repo; it gathers GitHub metadata, runs the funnel, and writes a
verdict note. The instructions the judge follows are in
[`prompts/judge_worker.md`](prompts/judge_worker.md).

Drop repos to evaluate (one `owner/name` or URL per line) into `inbox/`, or pass
them directly to the judge.

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

**Public framework vs. private data.** The rules, spec, prompts, and templates
are shareable. Your portfolio, the repos you're weighing, and your verdicts are
not - they live in git-ignored paths (see [`.gitignore`](.gitignore)). Copy
`config.example.yaml` to `config.local.yaml` to add your private portfolio and categories.
If omitted, the framework automatically falls back to `config.example.yaml` for zero-config operation.

> Status: framework complete; repo track ready to run. Idea track is planned.
