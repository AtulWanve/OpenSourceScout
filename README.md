# OpenSourceScout

A decision framework for scouting GitHub repos (and ideas) as a **solo builder
working with agentic AI**. Point it at a repo; it tells you whether to build on
it independently, fold it into an existing project, harvest parts of it, save it
as inventory for later, or pass — and why.

It is not a scorer. It **routes**.

## The model — Assess → Route → Capital

```
ASSESS   facts + worthiness, in one pass
           facts:      category · payoff · features · ai_at_build/run · license · liability
           worthiness: ≥1 payoff  +  passes your standards  +  warrants your time  +  liability LOW
                       │
ROUTE      independent → too_big → merge → combined → rejected
                       │
CAPITAL    launch must be free (else parked_capital); scale from revenue
                       → status: active | parked_capital
```

- **independent** — worth doing AND within one-person-plus-AI scope → build it.
- **too_big** — worth doing but needs a team → defer / partner.
- **merge** — folds into an existing project: `as_is` · `modify_fully` · `harvest_parts`.
- **combined** — its features help cover a **target** when pooled with other repos.
- **rejected** — retained as feature-tagged **inventory** (supply *and* inspiration for future targets).

Guiding rules: never reject on spoken/programming language or on capital;
AI-ness is a *category tag*, never a merit; money is the **last** gate, never the
first. Full rules in [`criteria.yaml`](criteria.yaml); design in [`SPEC.md`](SPEC.md).

## Repo track (start here)

You feed it a repo; it gathers GitHub metadata, runs the funnel, and writes a
verdict note. The instructions the judge follows are in
[`prompts/repo-judge.md`](prompts/repo-judge.md).

Drop repos to evaluate (one `owner/name` or URL per line) into `inbox/`, or pass
them directly to the judge.

## Layout

```
criteria.yaml            the shareable rules (public framework)
SPEC.md                  design + rationale
prompts/repo-judge.md    how the repo track evaluates a candidate
knowledge/repos/         verdict notes  (PRIVATE — git-ignored; _TEMPLATE.md is tracked)
knowledge/targets/       wish-list products to assemble toward (PRIVATE)
knowledge/{topics,daily} rollups + run logs (PRIVATE)
config.local.yaml        your portfolio, standards, categories (PRIVATE — git-ignored)
```

**Public framework vs. private data.** The rules, spec, prompts, and templates
are shareable. Your portfolio, the repos you're weighing, and your verdicts are
not — they live in git-ignored paths (see [`.gitignore`](.gitignore)). Copy
`config.local.yaml` and fill it in before first use.

> Status: framework complete; repo track ready to run. Idea track is planned.
