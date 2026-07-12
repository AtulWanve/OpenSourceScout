---
# Verdict note — copy per candidate, named after the repo/idea slug.
# Lives in the single candidate store; `disposition` is what routing decided.
candidate: "owner/name or idea-slug"
type: repo                 # repo | idea
url: ""                    # repo URL, or blank for an idea
evaluated: 2026-07-11
judged_by: null            # automated | ai | automated+ai

disposition: rejected      # independent | too_big | merge | combined | rejected
status: active             # active | parked_capital   (capital is the LAST check)

# What capabilities this repo/idea provides. THE key field for the parts bin —
# it's how a reject gets pulled into a target's build-kit later.
provides_features: []      # e.g. [oauth-login, csv-export, webhook-dispatch]

# --- ASSESSMENT · facts (categorization only; do NOT affect worthiness/routing) ---
category: null             # one controlled category (portfolio balance; not dev-only)
payoff: []                 # any of [commercial, reputation, learning, strategic]; >=1 required
liability_risk: null       # low | high  (high = legal/financial/physical harm or needs a license → out)
ai_at_build: null          # none | helpful | required   (categorization only)
ai_at_run: null            # none | optional | required  (categorization only)
emerging_class: false      # true if ai_at_build∈{helpful,required} AND ai_at_run==none
license:
  name: null
  attribution_required: null   # must credit original
  copyleft: null               # must open-source your derivative → blocks a closed product
  commercial_ok: null
capital_to_launch: null    # zero | needs_money   (zero required to be `active`)
paid_dependencies: []      # each → mini-target: scout a free AND still-maintained alternative

# --- funnel results (fill the ones reached) ---
step1_independent:
  worth_doing: null        # true | false  (reason in prose below)
  solo_ai_scope: null      # true | false
merge:
  target: null             # existing project name, or null
  mode: null               # as_is | modify_fully | harvest_parts
  harvest_type: null       # code | blueprint  (blueprint = reimplement; also sidesteps copyleft)
combination:
  covers_target: null      # target slug this contributes to, or null
  members: []              # other candidate slugs in the same build-kit

tags: []                   # themes → feed knowledge/topics/ rollups
---

## Verdict

_One line: the disposition and the single reason for it._

## Reasoning

_Walk the funnel. Worth doing? Why. In solo+AI scope (per the definition)? Why.
If not independent — does it merge, into what, as-is or modified? If neither —
what rejected candidates might it combine with, and what gap does each fill?_

## The move

_If actionable: what you'd actually build / fold in / combine, and why now._

## Risks / watch-outs

_License/legal traps (never a reject, but note them), integration cost,
saturated market, hostile maintainer, etc._
