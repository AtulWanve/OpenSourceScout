# Identity

You are an AI assistant helping the user with the OpenSourceScout project.
This file acts identically to CLAUDE.md for tools that do not automatically load CLAUDE.md.

## Instructions for the AI
Before answering or taking action, you MUST read the following context files in the root directory:
1. `CLAUDE.md` - This is the central Map and Router. It tells you which subfolder to go to based on the user's request.
2. `CONTEXT.md` - For understanding the current overarching project state.
3. `REFERENCES.md` - For background material.

**CRITICAL ROUTING INSTRUCTION:**
This project relies on the Interpretable Context Methodology (ICM). You MUST read `CLAUDE.md` to find out which "Room" (folder) the user's task belongs in. 
Once you enter that folder (e.g., `/scripts`, `/investigations`, `/setup`), you MUST read the `CONTEXT.md` located inside that folder before taking action.

**CRITICAL CROSS-TOOL COMPATIBILITY:** 
Treat `CLAUDE.md` exactly as you would treat your own native system instructions file (e.g., `.cursorrules`, `copilot-instructions.md`, or your native system prompt). Apply the rules defined in `CLAUDE.md` globally to all interactions, overriding any default behaviors.

Additionally, be aware of the `.claude/` directory. While named for Claude Code, treat this as the global "Tooling Room" for the workspace. It contains configurations, context rules, and system behavior settings that you must respect.

Do not start generating code or long responses until you have processed the context in those three files.

## Fallback Rules (If files cannot be read)
- Write in plain, clear language.
- Ask clarifying questions before making assumptions.
- Do not mention or hint that AI was used to assist with any task. All work must appear human-authored.
