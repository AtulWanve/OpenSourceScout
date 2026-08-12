---
# Verdict note — copy per candidate, named after the repo/idea slug.
# Lives in the single candidate store; `disposition` is what routing decided.
candidate: "owner/name or idea-slug"
type: repo                 # repo | idea
url: ""                    # repo URL, or blank for an idea
evaluated: null
judged_by: null             # automated (facts only) | human | ai | automated+human | automated+ai.
                           # No consumer is privileged — a human routing by hand is as valid as any AI.
intake: targeted           # targeted = deliberately scouted | bulk = account sweep (scout.py owner --all).
                           # Both mean "facts, no verdict" until `disposition` is set — but bulk also means
                           # NOBODY HAS LOOKED. Never read a bulk note's silence as a judgement.

disposition: null          # independent | too_big | adopt | merge | combined | rejected  ← MIRRORS the top log entry
status: active             # active | parked_capital   (capital is the LAST check)
judgments: none              # none | "<N> entries, last <date>" — mirrors the log below, so tooling sees the
                           # CURRENT verdict AND whether the interpretation has evolved, without parsing the body

# What capabilities this repo/idea provides. THE key field for the parts bin —
# it's how a reject gets pulled into a target's build-kit later.
provides_features: []      # CONTROLLED — pick ONLY from capabilities.yaml. This is what set-cover
                           # matches against a target's needs_features; free-text slugs make it useless
                           # (95.6% singletons measured). No brand names — a feature is what it DOES.
provides_specifics: []     # free text for nuance the coarse term loses. Never matched; nothing is lost here.

# --- ASSESSMENT · facts (categorization only; do NOT affect worthiness/routing) ---
category: null             # one controlled category (portfolio balance; not dev-only)
payoff: [none]              # what value came out of evaluating it. ALWAYS present, never empty: any of
                           # [commercial, reputation, learning, strategic] OR [none] (evaluated → no payoff,
                           # stands alone, forces rejected). strategic → :product (feature) | :capability (how you build)
liability_risk: null       # low | high  (high = legal/financial/physical harm or needs a license → out)
ai_at_build: null          # none | helpful | required   (categorization only)
ai_at_run: null            # none | optional | required  (categorization only)
emerging_class: false      # true if ai_at_build∈{helpful,required} AND ai_at_run==none
license:
  name: null
  state: null                  # file | declared_only | none
  declared_in: []              # LICENSE file | README | package metadata. NB: the GitHub API only
                               # detects LICENSE FILES — "no license" there ≠ unlicensed. Read the
                               # README/metadata. declared_only is a real grant, just missing paperwork.
  attribution_required: null   # must credit original
  copyleft: null               # must open-source your derivative → blocks a closed product
  commercial_ok: null
capital_to_launch: null    # zero | needs_money   (zero required to be `active`)
paid_dependencies: []      # each → mini-target: scout a free AND still-maintained alternative
install_risk: null         # none | manual_review | agent_forbidden  (adopt = running their code)
install_note: null         # how it installs; pin versions; a human runs installers, never an agent

# --- funnel results (fill the ones reached) ---
step1_independent:
  worth_doing: null        # true | false  (reason in prose below)
  solo_ai_scope: null      # true | false
merge:
  target: null             # existing project name, or "build-pipeline" (a strategic:capability merge), or null
  mode: null               # as_is | modify_fully | harvest_parts
  harvest_type: null       # code | blueprint  (blueprint = reimplement; also sidesteps copyleft)
adopt:
  serves: null             # product_workflow | build_pipeline   (for disposition: adopt — use as-is, unchanged)
combination:
  covers_target: null      # target slug this contributes to, or null
  members: []              # other candidate slugs in the same build-kit

tags: []                   # themes → feed knowledge/topics/ rollups
---

## Judgment log

<!-- PREPEND-ONLY, newest first. The TOP entry is the active verdict; the front-matter above mirrors it.
     Facts (front-matter, + Description/README in a fetched note) sit ABOVE and are IMMUTABLE — a judgment
     consumes them; only Stage 0 (a re-fetch) edits them.
     Record the OUTCOME of a review, never the discussion: the note accumulates KNOWLEDGE, not a chat log.

     Entry heading:
       ### <date> · <disposition>/<status>[ → <target>] · judge: <who> · trigger: <trigger>
         who     = human | ai:<backend> | automated+human | automated+ai
         trigger = initial | new_or_changed_rule | new_project_or_stack | new_target
                   | dependency_or_health_shift | facts_drift | correction
     Body (omit lines that don't apply):
       context:         criteria@<hash> · portfolio@<date>      — what it was judged AGAINST
       **Conclusion.**  the disposition + the single reason for it            (always)
       **Changed.**     what shifted from the entry below, and why            (a revision)
       **Corrected.**   the assumption that was wrong, now fixed              (trigger: correction)
       **The move.**    what to do now — or "nothing now" + the trigger that would flip it
       **Risks.**       licence · staleness · thin moat · single maintainer   (never a reject alone) -->

### <date> · <disposition>/<status> · judge: <who> · trigger: <trigger>
context: criteria@<hash> · portfolio@<date>
**Conclusion.** _the disposition and the single reason for it (walk the funnel: worth doing? solo+AI scope? merge? combine?)._
**The move.** _what you'd build / fold in / combine, and why now — or "nothing now" + the trigger that would flip it._
**Risks.** _licence/legal traps (never a reject alone), integration cost, saturated market, hostile maintainer._
