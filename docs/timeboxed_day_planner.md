# Timeboxed Day Planner

Kairos now supports a simple Indistractable-style timeboxed planner on Today.

## Purpose

The planner answers: What is this time for?

Instead of only keeping a task list, you define the shape of the day:

- Day start time.
- Day end time.
- Traction blocks.
- Breaks.
- Admin blocks.
- Personal blocks.
- Buffer blocks.

## How To Use It

1. Open Today.
2. Set the day start and end time.
3. Add blocks for the day before execution starts.
4. Attach a block to a goal or task when it is goal-driven work.
5. Use non-goal blocks for lunch, walks, admin, messages, shutdown, or recovery.
6. During the day, use Focus for the current traction block.

## Block Types

| Type | Meaning |
| --- | --- |
| Traction | Planned goal-aligned work. |
| Break | Intentional recovery. |
| Admin | Email, messages, planning, maintenance. |
| Personal | Health, relationships, errands, life commitments. |
| Buffer | Flexible space for overruns and transition time. |

## Product Rule

The timebox is not meant to be perfect. It is meant to make distraction easier to detect.

If something happens during a block that was not planned, ask:

- Was this traction or distraction?
- What internal trigger made me want to switch?
- What external trigger pulled me away?
- What pact would protect this block next time?

## 2026-05-14 UX Decision

The timeboxed day is useful, but it should not dominate Today.

Design direction:

- Today should show the chosen operating mode, selected/captured work, and completed evidence first.
- The full schedule should be collapsed by default on mobile.
- Template controls should be secondary.
- The user should not have to manage 13 blocks before starting one focus block.
- The schedule should be used to define intent, not to create pressure.

The planner should answer "What is this time for?" It should not become the main task manager.

## Psychological Rule

When the user is tired, the schedule should make starting easier:

- show current or next block
- show one Start action
- allow "start 5 minutes"
- allow quick reschedule without guilt
- move unfinished work into Review or Weekly rollover intentionally

## Related Docs

- `docs/README.md`
- `docs/psychological_product_blueprint.md`
- `docs/indistractable_integration.md`
