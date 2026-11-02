# Knowledge Base

## Inputs
- `repos/*.md`: Raw repository notes and evaluations
- `targets/*.md`: Build-kit target definitions
- `daily/*.md`: Daily sweep activity logs

## Process
This directory stores pipeline outputs and repository notes:
- Notes in `repos/` are the source of truth.
- Do not manually edit the `INDEX` files. If data is incorrect, fix the source note in `repos/` or update the prompt in `../prompts/`.
- Once the source note or prompt is fixed, rebuild the indexes.

## Outputs
- `INDEX.md`: Main repository overview index
- `INDEX-inventory.md`: Repository inventory index
- `INDEX-features.md`: Capability and feature mapping index