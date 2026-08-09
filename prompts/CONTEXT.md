# Prompts Stage (The Logic)

## Inputs
- Layer 3 (reference): `../capabilities.yaml` (Controlled vocabulary)
- Layer 3 (reference): `../config.local.yaml` (Allowed categories)
- Layer 4 (working): Injected data at runtime (facts, readme, description)

## Process
You are designing the "Smart Mad Libs" templates (the Layer 3 AI tools).
- When writing or modifying prompts here, you must use the strict 5-part structure: Identity, Task, Context, Constraints, and Output Format.
- Enforce strict constraints on the AI to output deterministic JSON or structured Markdown.
- Never invent keys, slugs, or categories; route strictly by the rules in the Layer 3 YAML files.

## Outputs
- `judge_worker.md` -> (Backend JSON contract)
- `repo-judge.md` -> (Human-readable Markdown note contract)