# Project Snapshot

## Product

Kairos is a personal discipline system for time management, career growth, and life balance. It helps the user:

- define life direction and active areas
- convert goals into weekly and daily commitments
- run focused work blocks and activity sessions
- capture quality, mood, energy, and friction
- review planned vs actual behavior without shame
- improve planning discipline over time

## Current Application Structure

- **Today**: daily command center and Now action
- **North Star**: identity, season focus, 90-day outcomes, priorities
- **Areas**: life and career balance scorecard
- **Focus**: focus/activity timer and session completion
- **Goals**: outcomes, tasks, and progress
- **Weekly**: capacity planning, goal allocation, and rollover backlog
- **Review**: weekly learning, planned vs actual, charts, heatmap, sessions
- **Brain**: questionnaire-backed local cognitive mirror and Obsidian sync
- **Research**: local SearXNG-backed search memory and read/save flow
- **Coach**: Hugging Face powered contextual guidance with local fallback

## Current Strengths

- Strong core loop: direction -> weekly plan -> today -> focus -> check-in -> review.
- JSON and Mongo storage paths are supported.
- Weekly planning, rollover, Review metrics, decision-first summary, and heatmap are implemented.
- Brain answers synthesize into editable profile fields.
- Research now has a visible search-read-save flow.
- Today and Focus already have stronger hierarchy than the original utility layout.
- The app has a clear psychological product direction.

## Current Weaknesses

- Today still risks showing too many useful things at equal weight.
- Weekly is functional but should become more guided and realism-aware.
- Review has charts, but the top section should explain the lesson more directly.
- North Star and Areas should stay read-first instead of form-heavy.
- Coach is useful as a page, but should be embedded where decisions happen and remain useful when Hugging Face is unavailable.

## Success Definition

Kairos succeeds when the user can open it while tired or uncertain and still know the next useful action within seconds.

The product should make discipline easier by reducing decision load, making starting smaller, and treating misses as data.

## Related Notes

- [[01 Overview/Documentation Map]]
- [[02 Strategy/Strategy Index]]
- [[05 Reference/Shared Product Language]]
