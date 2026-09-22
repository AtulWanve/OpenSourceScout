# Identity

You are helping the user with the OpenSourceScout project, an open-source scouting framework.

# Folder Structure (The Map)
This project uses a strict Three-Layer Folder Architecture based on the Interpretable Context Methodology (ICM).

**CRITICAL ROUTING INSTRUCTION:** 
When the user gives you a task, you MUST first determine which "Room" (folder) it belongs to. You must then READ the `CONTEXT.md` in that folder BEFORE taking any action. If a task does not fit any room, ask the user before guessing.

- `/` — The Root Room. Route here for tasks involving root-level files such as CLAUDE.md, AGENTS.md, and README.md. Read `/CONTEXT.md` before taking action.
- `/setup` — The onboarding room. Route here if the user asks to "onboard", "setup", or configure their workspace constraints.
- `/scripts` — The Engine. Route here to write Python, modify the pipeline, or debug `scout.py`.
- `/prompts` — The Logic. Route here to edit AI instructions, backend json schemas, or LLM evaluation rules.
- `/knowledge` — The Database. Route here to view raw repository markdown files, edit targets, or rebuild indexes.
- `/inbox` — The Triage Room. Route here to review fetched repository digests and process pending intake items.
- `/investigations` — The Analyst Room. Route here when the user asks questions like "Find an alternative to X", "Do we have a repo that does Y?", or any query searching for processed repos. You MUST read its `CONTEXT.md` to learn how to search the `INDEX.md` files properly instead of grepping the whole project.
- `/.claude` — The Tooling Room. Route here to manage Claude Code specific settings, hooks, skills, or permission allowlists.
- `/Methodology` — The Library. Reference material on the ICM architecture.
- `/tests` — Test suite for the project scripts.

## Directory Map
```text
.
├── /.claude                     # Tooling Room
│   ├── CONTEXT.md
│   ├── session_debugging_log.md
│   └── settings.json
├── /inbox                       # Incoming repo digests
├── /investigations            # Analyst workspace
│   └── CONTEXT.md
├── /knowledge
│   ├── /daily                 # Daily sync logs
│   ├── /repos                 # Evaluated candidate notes
│   ├── /targets               # Build-kit target definitions
│   ├── /topics
│   ├── CONTEXT.md
│   ├── INDEX.md
│   ├── INDEX-features.md
│   └── INDEX-inventory.md
├── /Methodology               # Reference docs
├── /prompts                   # AI instructions
│   ├── CONTEXT.md
│   └── judge_worker.md
├── /scripts                   # Engine
│   ├── CONTEXT.md
│   ├── build_index.py
│   ├── judge_loop.py
│   ├── normalize_features.py
│   ├── optimize_prompt.py
│   ├── oss_config.py
│   ├── pack_repos.py
│   ├── run.py
│   └── scout.py
├── /setup                     # Onboarding
│   └── CONTEXT.md
├── /tests                     # Test suite
├── AGENTS.md                  # Non-Claude agent map
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

- `config.local.yaml` (Root) — Private user data. Holds your private portfolio (`existing_projects`), personal standards, and categories. The judge engine reads this alongside the public rules. (Git-ignored)
- `criteria.local.yaml` (Root) — Private rule overrides. Overrides public definitions in `criteria.yaml` without checking them into git. (Git-ignored)

## Rules
- Read this file first on every new task.
- NEVER gather metadata by hand; always use `python scripts/scout.py`.
- ALWAYS check for `CONTEXT.md` when entering a new folder.
- If you are lost or do not know how to proceed, re-read this Map.
- **SYNC RULE (Root):** Any time you modify this `CLAUDE.md` file, you MUST immediately review and update `AGENTS.md` to ensure structural consistency for non-Claude tools.
- **SYNC RULE (Map):** If you create, delete, or change the purpose of a subfolder, you MUST update the "Folder Structure (The Map)" in this file to reflect the change. Every active room must be on the Map.
- Ask clarifying questions before making assumptions
- When you are unsure, say so
- Adhere strictly to the project architecture and coding standards
- **TOOL RULE:** You MUST use the native SDK tools (`Read`, `Write`, `Edit`, `Grep`, `Glob`) for interacting with the file system. NEVER use `Bash` or `PowerShell` tools to run shell commands like `cat`, `grep`, `sed`, `awk`, `head`, `tail`, `echo`, or heredocs (`<<EOF`) for file operations. This is a strict user instruction for this project.

## Attribution Policy
- NEVER add `Co-Authored-By`, `Authored-By`, `Contributor`, `Co-Contributor`, or any similar attribution line referencing Claude, AI, or any AI tool in commit messages, PR descriptions, code comments, or any other output.
- NEVER mention, imply, or hint in any form (comments, docs, commit messages, PR bodies, changelogs, README badges, footers) that AI was used to assist with any task.
- All work should appear as solely human-authored.
