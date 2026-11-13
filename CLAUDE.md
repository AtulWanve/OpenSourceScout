# Identity

You are helping the user with the OpenSourceScout project, an open-source scouting framework.

# Directory Structure
This project organizes context by directory with a `CONTEXT.md` file in each folder.

**TASK NAVIGATION:** 
When given a task, first determine which directory it belongs to. Read the `CONTEXT.md` in that folder BEFORE taking action. If a task does not fit any directory, ask the user before guessing.

- `/` - Root project files (`CLAUDE.md`, `AGENTS.md`, `README.md`, `CONTEXT.md`).
- `/setup` - Onboarding and workspace configuration.
- `/scripts` - Execution engine and Python pipeline scripts (`scout.py`, `build_index.py`).
- `/prompts` - Prompt templates, schemas, and evaluation rules.
- `/knowledge` - Repository notes, target definitions, and generated indexes.
- `/inbox` - Incoming repository digests pending review.
- `/investigations` - Repository research and capability searches (search `INDEX.md` files here rather than grepping the full repo).
- `/.claude` - Claude Code configuration, settings, and custom commands.
- `/.github` - GitHub Actions workflows and CI automation.
- `/docs` - Documentation, milestones, and planning notes.
- `/tests` - Test suite for scripts and tooling.

## Directory Structure
```text
.
├── /.claude                     # Tooling and configuration
│   ├── CONTEXT.md
│   ├── session_debugging_log.md
│   └── settings.json
├── /.github                     # GitHub workflows
│   ├── /workflows
│   │   ├── ci.yml
│   │   ├── codeql.yml
│   │   └── task-list-checker.yml
│   ├── CONTEXT.md
│   ├── ISSUE_TEMPLATE.md
│   └── pull_request_template.md
├── /docs                        # Documentation and milestones
│   ├── /milestones
│   │   ├── M0-foundation.md
│   │   └── M0.1-template-and-doc-updates.md
│   └── CONTEXT.md
├── /inbox                       # Incoming repo digests
│   └── CONTEXT.md
├── /investigations              # Repository research and analysis
│   └── CONTEXT.md
├── /knowledge                   # Repository notes and indexes
│   ├── /daily                   # Daily sweep logs
│   ├── /repos                   # Evaluated repo notes
│   ├── /targets                 # Build-kit target definitions
│   ├── CONTEXT.md
│   ├── INDEX.md
│   ├── INDEX-features.md
│   └── INDEX-inventory.md
├── /prompts                     # AI instructions
│   ├── CONTEXT.md
│   └── judge_worker.md
├── /scripts                     # Execution scripts
│   ├── CONTEXT.md
│   ├── build_index.py
│   ├── judge_loop.py
│   ├── optimize_prompt.py
│   ├── oss_config.py
│   ├── pack_repos.py
│   ├── run.py
│   └── scout.py
├── /setup                       # Onboarding
│   └── CONTEXT.md
├── /tests                       # Test suite
│   ├── CONTEXT.md
│   ├── test_config_and_indexing.py
│   ├── test_document_adoption.py
│   ├── test_opencode_backend.py
│   └── test_schemas_and_config.py
├── AGENTS.md                  # Cross-tool guidelines
├── CLAUDE.md                  # Project rules (this file)
├── CONTEXT.md                 # Root context
├── README.md                  # Project overview
├── REFERENCES.md
├── SPEC.md                    # Core architecture spec
├── capabilities.yaml          # Available features schema
├── config.example.yaml        # Template config
├── config.local.yaml          # User config (ignored)
├── criteria.yaml              # Public judge rules
└── criteria.local.yaml        # Private judge overrides (ignored)
```

- `config.local.yaml` (Root) - Private user data. Holds your private portfolio (`existing_projects`), personal standards, and categories. The judge engine reads this alongside the public rules. (Git-ignored)
- `criteria.local.yaml` (Root) - Private rule overrides. Overrides public definitions in `criteria.yaml` without checking them into git. (Git-ignored)

## Commands
- Test: `python -m pytest tests/`
- Run: `python scripts/run.py <target>`
- Scout: `python scripts/scout.py <target>`
- Index: `python scripts/build_index.py`

## Rules
- Read this file first on every new task.
- NEVER gather metadata by hand; always use `python scripts/scout.py`.
- ALWAYS check for `CONTEXT.md` when entering a new folder.
- If you are lost or do not know how to proceed, re-read this directory structure.
- **SYNC RULE (Root):** Any time you modify this `CLAUDE.md` file, you MUST immediately review and update `AGENTS.md` to ensure structural consistency for non-Claude tools.
- **SYNC RULE (Directory Structure):** If you create, delete, or change the purpose of a subfolder, you MUST update the "Directory Structure" in this file to reflect the change. Every active folder must be listed.
- Ask clarifying questions before making assumptions.
- When you are unsure, say so.
- Adhere strictly to the project architecture and coding standards.
- **TOOL RULE (FILE MODIFICATIONS):** You MUST use native SDK tools `Edit` (for existing files) and `Write` (for new files) to modify files. NEVER use shell commands (`sed`, `awk`, `echo >`, `Set-Content`, heredocs) to edit or write files. Standard shell commands for running tests or filesystem management (`Copy-Item`, `Move-Item`, `Remove-Item`) remain permitted per global rules.

## Attribution Policy
- NEVER add `Co-Authored-By`, `Authored-By`, `Contributor`, `Co-Contributor`, or any similar attribution line referencing Claude, AI, or any AI tool in commit messages, PR descriptions, code comments, or any other output.
- NEVER mention, imply, or hint in any form (comments, docs, commit messages, PR bodies, changelogs, README badges, footers) that AI was used to assist with any task. All work should appear as solely human-authored.
- **SCOPE (SPIRIT OVER LITERALISM):** This ban applies strictly to git commits, PR descriptions, code authorship metadata, and documentation. It never forbids building AI features, integrating AI APIs, or using terms like `ai_generated` or `llm` in business logic.
