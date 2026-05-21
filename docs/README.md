# Kairos Documentation Map

Review date: 2026-05-18

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
| Season | 21-day operating agreement. It should answer: what is protected now, what supports it, and what is paused? |
| Focus | Execution mode for one block. It should reduce choice and protect traction. |
| Weekly | Planning surface for realistic capacity, goal allocation, rollover, and weekly pact. |
| Review | Learning surface for planned vs actual, friction, area balance, and next adjustment. |
| North Star | Read-first long-term direction: identity, values, anti-vision, yearly direction, and priorities. |
| Areas | Life and career balance scorecard. |
| Goals | Outcomes and next actions, not a generic task dump. |
| Brain | Editable cognitive mirror: profile, confirmed memories, memory candidates, saved research, and question engine. |
| Research | Source-backed search, read, and save workflow that feeds Brain memory. |
| Coach | Contextual assistant that suggests, never judges or commands. |

Use `Review` in product language. The technical route may still be `/history` until routing cleanup, but docs and UI should treat the page as Review.

## Current Product Decisions

- Kairos is a single-user behavioral operating system for time management, career compounding, and life balance.
- The app should reduce decision load at the moment of action.
- Today should be Now-first.
- The primary planning track is 21 days, not 90 days.
- Season should be the bridge between North Star, Goals, Areas, Today, and Review.
- Active development should move CLI-first while keeping the web app as the visual/reference interface.
- The CLI must write to the same storage layer as the web app so daily use creates real product data while Kairos is being built.
- Weekly should prevent fantasy planning by starting with realistic capacity.
- Review should lead with one lesson and one adjustment before detailed charts.
- Misses are data, not failure.
- Coach should be grounded in Kairos data, embedded where decisions happen, and fall back to local guidance when the provider is unavailable.
- Brain and Research should feed the local memory layer without turning the product into a generic note app.
- Research should behave like a lightweight Perplexity-style flow: ask, read source-backed results, save the durable insight.
- The question engine should ask high-signal questions over time, with the full bank kept as a collapsible library.
- More features are less important than clearer loops.

## Core Loop

1. North Star and Areas define long-term direction and balance.
2. Goals turn direction into outcomes.
3. Season chooses the protected 21-day primary track, support track, constraints, and paused goals.
4. Weekly turns the season into realistic capacity commitments.
5. Today turns the week into one next action.
6. Focus turns the action into timed execution.
7. Brain and Research capture durable patterns and source-backed insights.
8. Review turns evidence into the next adjustment.

## CLI-First Workflow

The CLI is now the active daily operating surface. It writes to the same storage as the web app and should be used while the product is being built.

| Command | Purpose |
| --- | --- |
| `kairos` / `kairos home` | Open the command center with season, discipline progress, XP, completed work, and next action. |
| `kairos status` | Confirm storage mode, current season, today's commitments, focus minutes, completed work, and next action. |
| `kairos season` | Create or update the current 21-day operating agreement. |
| `kairos today` | Show the current day, commitments, and next focus target. |
| `kairos today plan` | Choose 1-3 commitments from active goal tasks. |
| `kairos goal create` | Create goals with priority, category, target date, notes, and first tasks. |
| `kairos goal add-task` / `add task` | Add tasks to an existing goal whenever the goal needs more concrete next steps. |
| `kairos focus` / `kairos focus start` | Run a terminal timer, save the result, and update task status when completed, partial, or blocked. |
| `kairos daily` | Ask daily reflection questions and save useful answers to Brain. |

Research, Coach, and full Review CLI commands should come after this daily loop stays reliable in real use.

## Documentation Maintenance Rule

When a product decision changes, update these docs in order:

1. `psychological_product_blueprint.md` for the principle.
2. `kairos_cognitive_mirror_build_spec.md` for the product system.
3. `implementation_roadmap.md` for the build impact.
4. `product_discipline_audit.md` for product loop and redundancy impact.
5. `design_experience_review.md` for screen behavior.
6. Any feature-specific doc affected by the decision.
