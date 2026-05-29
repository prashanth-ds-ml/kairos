# Kairos + Indistractable Product Model

Kairos keeps the original life-management structure and adds an Indistractable-inspired behavior layer.

## Existing Kairos Layer

This answers: What matters?

- North Star: long-term direction.
- Areas: life and career balance.
- Goals: outcomes to pursue.
- Today: 1-3 daily commitments.
- Timeboxed day: planned traction, breaks, admin, personal, and buffer blocks.
- Focus: execution block.
- Review: weekly learning.

## Indistractable Layer

This answers: Why do I get pulled away, and what pact protects traction?

- Daily pact: one rule that protects today's traction.
- Internal trigger: discomfort that may cause avoidance.
- External trigger: environment or interruption that may pull attention.
- Focus pact: commitment for one block.
- Outcome: complete, partial, or blocked.
- Weekly trigger review: patterns across the week.

## Product Principle

Kairos should not replace goals with trigger tracking. It should connect them:

1. Values and areas define what matters.
2. Goals turn values into outcomes.
3. Today turns goals into planned traction.
4. Timeboxing gives each kind of traction a place in the day.
5. Focus turns traction into timed execution.
6. Trigger logging turns distraction into data.
7. Review turns data into a better system.

## 2026-05-14 Design Decision

Kairos should apply the Indistractable model through progressive guidance, not by exposing every concept at once.

Current risk:

- Today can show too much planning, tracking, timeboxing, and backlog at the same time.
- Focus can show both focus recording and activity logging at once.
- Review can become a long analytics report instead of a short learning loop.

Updated product direction:

- Today defines intended traction through planned mode or flow mode, then records evidence.
- Focus protects one block with a pact.
- Activity is a separate mode, not a second form competing with Focus.
- Weekly defines realistic traction before the week starts.
- Review asks whether the user did what they planned and what should change.

## Indistractable UX Mapping

| Indistractable idea | Kairos implementation |
| --- | --- |
| Master internal triggers | Focus check-in and Review friction patterns |
| Make time for traction | Weekly plan and timeboxed day |
| Hack back external triggers | External trigger logging and pact suggestions |
| Prevent distraction with pacts | Daily pact, focus pact, weekly pact |
| Identity | North Star and read-first identity statement |

## Copy Rule

Use "traction" to describe intended action. Use "distraction" only after the user has defined what the time was for.

Do not use shame language. A missed plan means the system learned something.

## Public Positioning

Use this wording when writing about the project:

"Kairos is a personal discipline system inspired by the idea that time management is also discomfort management. It combines life areas, goals, daily planning, focus blocks, internal/external trigger logging, pacts, and weekly review."

Avoid implying endorsement from Nir Eyal unless he explicitly gives it. Use language like "inspired by" and link to his book or public work.

## Related Docs

- `docs/README.md`
- `docs/psychological_product_blueprint.md`
- `docs/timeboxed_day_planner.md`
