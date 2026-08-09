# Knowledge Stage (The Database)

## Inputs
- Layer 4 (working): `repos/*.md` (Raw repository notes)
- Layer 3 (reference): `targets/*.md` (Business/strategic goals)

## Process
You are operating in the state persistence layer. This is where the results of the pipeline live.
- Notes in `repos/` are the canonical record and source of truth.
- Do not manually edit the `INDEX` files. If the data is incorrect, apply "Semantic Debugging": fix the source note in `repos/` or fix the prompt in `../prompts/`.
- Once the source is fixed, trigger the rebuild process.

## Outputs
- `INDEX.md` -> (Rendered human-readable view)
- `INDEX-inventory.md` -> (Rendered human-readable view)
- `INDEX-features.md` -> (Rendered human-readable view)