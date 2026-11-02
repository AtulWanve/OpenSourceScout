# Prompts

## Inputs
- `../capabilities.yaml`: Allowed capability tags
- `../config.local.yaml`: Configured categories
- Injected repo data at runtime (facts, README, description)

## Process
Guidelines for prompt templates used by the evaluation pipeline:
- Keep prompts structured around five standard sections: Identity, Task, Context, Constraints, and Output Format.
- Prompt the model to return valid, parseable JSON or structured Markdown.
- Only use keys, slugs, and categories defined in the project YAML files.

## Outputs
- `judge_worker.md`: Prompt template for judge evaluation JSON output