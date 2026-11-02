# Setup

## Inputs
- `../config.example.yaml`: Base template for local configuration
- `../criteria.yaml`: Default evaluation criteria and rules

## Process
This folder handles initial workspace setup. Use it to generate local configuration files tailored to a user's workflow and criteria.

When onboarding a user (e.g., when asked to "run setup" or "onboard me"), ask these questions to gather their preferences:
1. **Budget Constraints:** Are paid dependencies/API keys allowed, or must everything be 100% free/open-source?
2. **Tech Stack Constraints:** Are there any programming languages you refuse to adopt or deploy?
3. **Team Size:** Are you a solo developer or a team? (This affects the `too_big` and `independent` evaluation checks).
4. **Target Categories:** What are the top 3 tool categories you want to scout? (e.g., UI Frameworks, AI Agents, Databases).

Once you have gathered these answers:
1. Generate `config.local.yaml` with their selected categories.
2. Save custom budget and stack rules in `criteria.local.yaml` instead of editing `criteria.yaml`. The pipeline automatically merges `criteria.local.yaml` over `criteria.yaml` at runtime, keeping tracked files clean.

## Outputs
- `../config.local.yaml`: User's local category configuration
- `../criteria.local.yaml`: User's local criteria overrides