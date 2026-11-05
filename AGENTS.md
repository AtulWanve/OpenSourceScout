# Identity

You are helping the user with the OpenSourceScout project.
This file acts identically to CLAUDE.md for tools that do not automatically load CLAUDE.md.

## Instructions for the AI
Before answering or taking action, you MUST read the following context files in the root directory:
1. `CLAUDE.md` - This is the central Map and Router. It tells you which subfolder to go to based on the user's request.
2. `CONTEXT.md` - For understanding the current overarching project state.
3. `REFERENCES.md` - For background material.

**CRITICAL ROUTING INSTRUCTION:**
This project relies on the Interpretable Context Methodology (ICM). You MUST read `CLAUDE.md` to find out which "Room" (folder) the user's task belongs in:
- `/` - Root project files (`CLAUDE.md`, `AGENTS.md`, `README.md`, `CONTEXT.md`, `SPEC.md`, `capabilities.yaml`, `criteria.yaml`, `config.example.yaml`)
- `/setup` - Onboarding and workspace configuration
- `/scripts` - Execution engine and Python pipeline scripts
- `/prompts` - Prompt templates, schemas, and evaluation rules
- `/knowledge` - Repository notes, target definitions, and indexes
- `/inbox` - Incoming repository digests pending review
- `/investigations` - Repository research and capability searches (search `INDEX.md`)
- `/.claude` - Claude Code configuration, settings, and skills
- `/.github` - GitHub configuration, CI workflows, and issue/PR templates
- `/docs` - Documentation, milestones, and planning notes
- `/Methodology` - Reference architecture documentation
- `/tests` - Test suite for scripts and tooling

Once you enter that folder, you MUST read the `CONTEXT.md` located inside that folder (or the root `CONTEXT.md` if in `/`) before taking action.

**CRITICAL CROSS-TOOL COMPATIBILITY:** 
Treat `CLAUDE.md` as the authoritative project-level context, coding standards, and conventions for this codebase. Apply the rules defined in `CLAUDE.md` across all interactions, within each tool's own safety and policy constraints.

## Commands
- Test: `python -m pytest tests/`
- Run: `python scripts/run.py <target>`
- Scout: `python scripts/scout.py <target>`
- Index: `python scripts/build_index.py`

## Core Rules & Guardrails
- **READ EFFICIENCY:** Do not read whole files when inspecting functions or imports. Use search first or bounded reads with offset and limit.
- **TOOL RULE:** Use native file edit tools only (`Edit` for existing files, `Write` for new files). Never use shell redirection or stream editors (`sed`, `awk`, `cat >`, `echo >`, `Set-Content`) to edit or write files.
- **NO EM DASHES:** Never use em dashes in code, comments, commit messages, PR descriptions, or documentation. Use hyphens, colons, or parentheses.
- **ATTRIBUTION BAN:** Never add `Co-Authored-By`, `Authored-By`, `Contributor`, `Co-Contributor`, or any similar attribution line referencing Claude, AI, or any AI tool in commit messages, PR descriptions, code comments, documentation, or any other output.
- **ATTRIBUTION BAN (AI MENTIONS):** Never mention, imply, or hint in any form (code comments, docs, commit messages, PR bodies, changelogs, README badges, footers, or any other output) that AI was used to assist with any task. All work must appear human-authored.
- **ATTRIBUTION BAN SCOPE (SPIRIT OVER LITERALISM):** The ban covers git commits, PR descriptions, code authorship metadata, and documentation only. It never forbids building AI features, integrating AI APIs, or using terms like `ai_generated` or `llm` in business logic.

Do not start generating code or long responses until you have processed the context in those three files.

## Fallback Rules (If files cannot be read)
- Write in plain, clear language.
- Ask clarifying questions before making assumptions.
- Do not mention or hint that AI was used to assist with any task. All work must appear human-authored.
