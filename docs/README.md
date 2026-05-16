# Kairos Documentation Map

Review date: 2026-05-16

This folder documents the current product direction for Kairos. The docs should be read as one connected product system, not as separate feature notes.

## Start Here

1. `psychological_product_blueprint.md` is the source of truth for the behavior-first product model.
2. `kairos_cognitive_mirror_build_spec.md` is the main build document for the evolved mirror / coach / plan product.
3. `implementation_roadmap.md` translates the blueprint into build phases and acceptance criteria.
4. `product_discipline_audit.md` explains the product loops, discipline mechanisms, gaps, and redundancy decisions.
5. `design_experience_review.md` explains the screen-by-screen UX direction from the Playwright audit.
6. Feature docs explain specific subsystems:
   - `indistractable_integration.md`
   - `timeboxed_day_planner.md`
   - `hugging_face_coach.md`
7. `user_tutorial.md` is the user-facing operating guide.

## Shared Product Language

| Term | Meaning |
| --- | --- |
| Today | Daily command center. It should answer: what should I do now? |
| Focus | Execution mode for one block. It should reduce choice and protect traction. |
| Weekly | Planning surface for realistic capacity, goal allocation, rollover, and weekly pact. |
| Review | Learning surface for planned vs actual, friction, area balance, and next adjustment. |
| North Star | Read-first direction: identity, season focus, 90-day outcomes, priorities. |
| Areas | Life and career balance scorecard. |
| Goals | Outcomes and next actions, not a generic task dump. |
| Coach | Contextual assistant that suggests, never judges or commands. |

Use `Review` in product language. The technical route may still be `/history` until routing cleanup, but docs and UI should treat the page as Review.

## Current Product Decisions

- Kairos is a single-user behavioral operating system for time management, career compounding, and life balance.
- The app should reduce decision load at the moment of action.
- Today should be Now-first.
- Weekly should prevent fantasy planning by starting with realistic capacity.
- Review should lead with one lesson and one adjustment before detailed charts.
- Misses are data, not failure.
- Coach should be grounded in Kairos data, embedded where decisions happen, and fall back to local guidance when the provider is unavailable.
- Brain and Research should feed the local memory layer without turning the product into a generic note app.
- More features are less important than clearer loops.

## Core Loop

1. North Star and Areas define what matters.
2. Goals turn direction into outcomes.
3. Weekly turns outcomes into realistic capacity commitments.
4. Today turns the week into one next action.
5. Focus turns the action into timed execution.
6. Check-in captures result, friction, quality, mood, and energy when useful.
7. Review turns evidence into the next adjustment.

## Documentation Maintenance Rule

When a product decision changes, update these docs in order:

1. `psychological_product_blueprint.md` for the principle.
2. `kairos_cognitive_mirror_build_spec.md` for the product system.
3. `implementation_roadmap.md` for the build impact.
4. `product_discipline_audit.md` for product loop and redundancy impact.
5. `design_experience_review.md` for screen behavior.
6. Any feature-specific doc affected by the decision.
