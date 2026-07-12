---
# A TARGET = a product you wish existed. The combination step assembles pool
# repos (rejects included) to cover its needs_features. Copy per target.
target: "open-alt-to-<paywalled-product>"
inspired_by: "<the paywalled/proprietary incumbent, if any>"
created: 2026-07-11

# The feature list the target needs. Matched against each candidate's
# `provides_features`. This is the "shopping list."
needs_features:
  - feature-a
  - feature-b
  - feature-c

# Filled by the assembler (step 3): which candidate covers which feature.
build_kit:
  # feature-a: owner/repo-1
  # feature-b: idea-slug-2
coverage: 0        # % of needs_features covered by the current build_kit
gaps: []           # needs_features still uncovered → what to go scout next
---

## Why this target

_The pain, who has it, and why the good solutions today are paywalled/closed —
i.e. why an assembled open alternative is worth it._

## Assembly notes

_How the collected repos fit together, integration friction, and the biggest
missing piece blocking a usable v1._
