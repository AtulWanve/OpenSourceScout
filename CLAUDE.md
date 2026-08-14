# Identity

You are helping the user with the OpenSourceScout project, an open-source scouting framework.

# Folder Structure (The Map)
This project uses a strict Three-Layer Folder Architecture based on the Interpretable Context Methodology (ICM).

**CRITICAL ROUTING INSTRUCTION:** 
When the user gives you a task, you MUST first determine which "Room" (folder) it belongs to. You must then READ the `CONTEXT.md` in that folder BEFORE taking any action. If a task does not fit any room, ask the user before guessing.

- `/setup` — The onboarding room. Route here if the user asks to "onboard", "setup", or configure their workspace constraints.
- `/scripts` — The Engine. Route here to write Python, modify the pipeline, or debug `scout.py`.
- `/prompts` — The Logic. Route here to edit AI instructions, backend json schemas, or LLM evaluation rules.
- `/knowledge` — The Database. Route here to view raw repository markdown files, edit targets, or rebuild indexes.
- `/inbox` — The Triage Room. Route here to review fetched repository digests and process pending intake items.
- `/investigations` — The Analyst Room. Route here when the user asks questions like "Find an alternative to X" or "Do we have a repo that does Y?".
- `/.claude` — The Tooling Room. Route here to manage Claude Code specific settings, hooks, skills, or permission allowlists.
- `/Methodology` — The Library. Reference material on the ICM architecture.
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
- **TOOL RULE:** ALWAYS prefer the native SDK tools (`Read`, `Write`, `Edit`, `Grep`, `Glob`) for interacting with the file system. Do NOT use `Bash` or `PowerShell` tools to run shell commands like `cat`, `grep`, `head`, `tail`, `echo`, or heredocs (`<<EOF`) for file operations unless explicitly requested or if the native tools fail.

## Attribution Policy
- NEVER add `Co-Authored-By`, `Authored-By`, `Contributor`, `Co-Contributor`, or any similar attribution line referencing Claude, AI, or any AI tool in commit messages, PR descriptions, code comments, or any other output.
- NEVER mention, imply, or hint in any form (comments, docs, commit messages, PR bodies, changelogs, README badges, footers) that AI was used to assist with any task.
- All work should appear as solely human-authored.
