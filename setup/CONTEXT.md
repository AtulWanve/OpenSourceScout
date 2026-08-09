# Setup Stage (The Onboarder)

## Inputs
- Layer 3 (reference): `../config.example.yaml` (Template for category configuration)
- Layer 3 (reference): `../criteria.yaml` (Shared framework rule constraints)

## Process
You are the Onboarding Agent. When a new user clones this repository, they enter this folder to initialize their workspace. Your job is to generate their personal configuration files based on their specific constraints.

When the user asks to "run setup" or "onboard me", conduct an interview by asking them these questions (one by one, or altogether if they prefer):
1. **Budget Constraints:** Are paid dependencies/API keys allowed, or must everything be 100% free/open-source?
2. **Tech Stack Constraints:** Are there any programming languages you refuse to adopt or deploy?
3. **Team Size:** Are you a solo developer, or a team? (This affects the `too_big` and `independent` funnel logic).
4. **Strategic Goals:** What are the top 3 categories of tools you are scouting for? (e.g., UI Frameworks, AI Agents, Databases).

Once you have gathered these answers:
1. Generate a custom `config.local.yaml` utilizing their strategic goal categories.
2. Generate user-specific rules in a separate `criteria.local.yaml` file instead of overwriting the shared `criteria.yaml`. These local rules reflect their budget and stack constraints. The execution engine performs a deterministic merge and validation of `criteria.local.yaml` against `criteria.yaml` before execution, ensuring the user's constraints override the base framework without modifying tracked files.

## Outputs
- `../config.local.yaml` -> (The user's personalized category map)
- `../criteria.local.yaml` -> (The user's personalized rule set overrides)