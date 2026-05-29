# Kairos Implementation Roadmap

Role: Product Manager / Technical Lead  
Review date: 2026-05-18

Current status: the core local redesign is implemented for Today, Season, Focus, Goals, Review, Areas, Weekly, Research, Brain, and Coach. The app now uses static CSS/JS assets, Review includes charts and a focus heatmap, Weekly supports capacity planning and rollover, Season manages the current 21-day operating agreement, Research supports SearXNG-backed read/save sessions, Brain stores confirmed memories and memory candidates, and Coach can call Hugging Face Inference Providers with `Qwen/Qwen2.5-7B-Instruct-1M` plus a local fallback.

Update 2026-05-29: the CLI loop now supports first-open daily check-in, planned vs flow day mode, stable task refs, task status reasons, shutdown, ASCII evidence stamps, and a personal-brain rebuild/sync flow. Brain now has raw answers plus generated observations and inferred patterns with confidence, evidence count, recency, and contradiction notes.

Update 2026-05-18: Kairos has moved from a 90-day planning assumption to a 21-day primary track. `/season` now has a persisted CurrentSeason model, day progress, daily and weekly minute targets, checkpoint notes, suggested season defaults, and actions to apply empty fields or update North Star/Areas from the current direction. Today surfaces a state-aware reflection. Brain now leads with recommended questions, keeps the full 156-question bank collapsed as a library, and separates confirmed memories from candidates. Research stores source-backed sessions and can save selected insights into Brain memory. Playwright smoke covers Today, Season, Brain, Research, Weekly, Review, Goals, Areas, Focus, North Star, Coach, and mobile Today.

Update 2026-05-15: Kairos now has the first local Brain vertical slice. The app includes Brain profile storage, a psychological question engine, saved search memory, optional SearXNG search, Coach brain context, and Obsidian vault sync for Brain and Research notes.

Update 2026-05-15: implemented the first gap-fix pass after full-page Playwright review. Today now has an explicit Auto-plan empty-state action, Weekly has a top-level auto-allocation action in the realism guide, Review leads with three decisions for next week, North Star captures values/anti-vision/Brain alignment notes, Brain answers synthesize into the editable profile, Areas has quick target actions, Goals warns when a goal has no next task, Research has a session flow, and Coach falls back to deterministic local guidance when Hugging Face is unavailable or rejects the token/model.

## Goal

Use the current Kairos foundation to build a practical personal discipline system that works across machines, supports MongoDB persistence, and helps the user improve time management, career growth, and life balance.

## Guiding Decisions

- Keep the app single-user.
- Keep authentication simple with optional personal access key.
- Treat Obsidian as the canonical readable memory for the personal brain.
- Store raw answers separately from Kairos-generated summaries.
- Use psychological questionnaires for self-understanding and personalization, not diagnosis.
- Keep Today as the main daily workspace.
- Keep Season as the 21-day operating agreement.
- Build CLI-first for the next development phase and keep the terminal loop reliable for real daily use.
- Keep the CLI and web app on the same storage abstractions.
- Avoid building a generic task manager.
- Prefer small, complete behavior loops over many disconnected features.
- Use Playwright screenshots and smoke tests after every meaningful UI change.
- Keep Weekly, Review, Research, Brain, and Coach in the smoke screenshot sweep.
- Optimize for psychological ease: reduce visible decisions at the moment of action.
- Treat misses as data, not failure.
- Prefer state-aware daily operating modes over dashboards.
- Make planning realistic before making tracking more detailed.

## 2026-05-14 Product Direction Decision

Kairos should now move from "feature-complete personal OS" toward "guided behavioral operating system." The next work should simplify and sequence the experience rather than add more panels.

Reference blueprint: `docs/psychological_product_blueprint.md`.

Documentation map: start with `docs/README.md`. The blueprint defines the product psychology, this roadmap defines build order, and the audit/design docs define product and UX tradeoffs.

Core loop:

1. Direction: North Star and Areas define values.
2. Season: choose the protected 21-day primary track, support track, constraints, and paused goals.
3. Weekly commitment: Plan Week sets realistic capacity and goal allocation.
4. Today: choose planned mode or flow mode, then record evidence.
5. Focus: execute one block with a pact.
6. Brain and Research: capture durable patterns and source-backed insights.
7. Review: learn what happened and adjust the system.

Design rule:

Every screen should answer one primary question. If a section does not help the user decide or act in that moment, it should be collapsed, moved lower, or merged.

## Phase 1: Improve The Core Daily Flow

Objective: Make Kairos easier to use every day without thinking.

Tasks:

- Redesign Today around a state-aware "Now" section.
- Make Today's queue a numbered commitment list.
- Move available work below the commitment area and reduce its visual priority.
- Split daily discipline into morning setup and evening shutdown.
- Add inline success messages after save, plan, and complete actions.
- Add confirmation before clearing today's plan.
- Improve empty states for no goals, no tasks, no plan, and no sessions.

Acceptance criteria:

- A user landing on Today can immediately tell the next best action.
- If no tasks are planned, "Plan today" is the dominant action.
- If tasks are planned, "Start focus" is the dominant action.
- If a focus block is completed, completed work is visible as evidence and unfinished work remains in the selected/captured lists.
- Mobile Today shows the first meaningful action within the first screen.

Testing:

- Playwright desktop and mobile screenshots for Today.
- Smoke test for creating a plan, starting focus, completing a block, and returning to Today.

Status:

- Implemented locally.
- Today is now the main command center, shows a state-aware reflection, and the block composer is collapsed by default.

## Phase 1.5: Build The 21-Day Season Loop

Objective: Make the user's current primary track explicit enough to guide Today, Weekly, Review, Brain, and Coach.

Implemented:

- Added persisted CurrentSeason storage for JSON and MongoDB.
- Added `/season` with start/end dates, day progress, daily minimum, weekly target, success criteria, constraints, paused goals, and day 7/14/21 checkpoint notes.
- Added suggested season defaults from active goals and Brain context.
- Added actions to apply empty fields and update Direction/Areas from the current season.
- Added Season panels on Today and Review.

Next improvements:

- Use Season as the default filter for Today auto-plan.
- Add explicit Day 7, Day 14, and Day 21 review flows.
- Show season evidence in Review before detailed analytics.
- Add a "pause or continue" decision at the end of Day 21.

## Phase 0: Local Brain And Question Engine

Objective: Build Kairos into a local cognitive mirror that understands the user's North Star, values, current state, struggles, energy patterns, search interests, and recurring behavior patterns.

Implemented:

- Added `/brain` with editable Brain Profile fields for identity, values, anti-vision, current state, strengths, struggles, energy patterns, and motivation notes.
- Added a reusable 156-question bank with Likert, frequency, ranking, choice, and open-response prompts, including situation simulation, decision rules, stress defaults, communication style, boundaries, constraint preferences, and belief evolution.
- Added answer persistence for raw questionnaire responses.
- Added personal-brain rebuild from raw answers, logs, and focus sessions into observations and inferred patterns.
- Added `/research` with optional local SearXNG search through `KAIROS_SEARXNG_URL`.
- Saved source-backed research sessions and selected durable insights by default.
- Added confirmed Brain memories and memory candidates from answers and research.
- Added Obsidian sync into `vault/10 Brain` and `vault/20 Research`.
- Extended Coach context with confirmed Brain profile, recent answers, and saved research.

Next improvements:

- Add delete/forget controls for Brain answers, memories, saved research, and research sessions.
- Add scoring summaries for public-domain or permission-safe instruments such as IPIP traits and Kairos-native wellbeing/self-determination inspired prompts.
- Add more contextual one-question prompts after missed plans, blocked sessions, repeated distractions, and weekly review.

Acceptance criteria:

- The user can answer one useful question without completing a long intake.
- The user can inspect and edit every durable memory in Obsidian.
- Coach uses Brain context without inventing facts or clinical labels.

## Phase 2: Redesign Focus Mode

Objective: Make focus feel calm, direct, and execution-oriented.

Tasks:

- Put selected target and timer first.
- Move target selection into a secondary "Change target" panel.
- Add a pre-focus commitment field.
- Add completion result options: complete, partial, blocked.
- Add optional distraction/friction tags.
- Keep manual minutes editing for real-world accuracy.

Acceptance criteria:

- On mobile, the timer appears before the long target list.
- The user can complete a focus block without losing context.
- Partial and blocked sessions can be recorded without falsely marking a task done.

Testing:

- Playwright timer interaction test.
- Completion test for complete, partial, and blocked states.
- Mobile screenshot check for timer visibility.

Status:

- Implemented locally.
- Focus now centers the selected target, timer, and block result controls.

## Phase 3: Build Weekly Review

Objective: Turn tracking into learning.

Tasks:

- Keep product language as Review. The technical route may remain `/history` until routing cleanup.
- Add weekly summary cards:
  - Total focus minutes.
  - Blocks completed.
  - Days planned.
  - Shutdowns completed.
  - Best goal.
  - Neglected area.
- Add sessions grouped by day.
- Add area breakdown for the current week.
- Add weekly reflection fields:
  - Biggest win.
  - Main friction.
  - What to change next week.
  - Next week's focus area.

Acceptance criteria:

- Review explains what happened this week without manually reading every session.
- The user can write a weekly reflection.
- The app can identify an underfunded area when target minutes are set.

Testing:

- Storage tests for weekly review data.
- Playwright screenshots for Review with and without sessions.

Status:

- Implemented locally.
- Review now includes weekly charts and reflection prompts.

## Phase 4: Upgrade Areas Into A Life Scoreboard

Objective: Help the user excel across life and career, not only finish tasks.

Tasks:

- Convert area cards to read-first scorecards.
- Hide edit forms behind an Edit action.
- Show weekly target versus actual minutes.
- Add status labels: healthy, attention, neglected.
- Add one recommended action per area.
- Add "focus area of the week".

Acceptance criteria:

- Areas can be scanned in under 10 seconds.
- The weakest or most neglected area is obvious.
- Area updates do not make the page feel like a wall of forms.

Testing:

- Screenshot tests at desktop and mobile widths.
- Data tests for area weekly minutes.

Status:

- Implemented locally.
- Areas now behave as a life scorecard instead of a form-heavy page.

## Phase 5: Add Career Growth Track

Objective: Convert time management into visible career progress.

Tasks:

- Add a Career page or Career section under Areas.
- Track target role/direction.
- Track skills being built.
- Track projects to ship.
- Track proof of work links or notes.
- Link career goals to weekly focus blocks.
- Add a weekly career commitment.

Acceptance criteria:

- The user can see what career capability they are building.
- Focus sessions can be connected to skills or shipped projects.
- Weekly Review includes career progress.

Testing:

- CRUD tests for career track data.
- UI tests for adding skill, project, and evidence item.

## Phase 6: Production And Deployment Hardening

Objective: Make the hosted app reliable for personal use from any machine.

Tasks:

- Document MongoDB environment variables clearly.
- Add app startup validation for storage mode.
- Add visible storage health on a settings/status page.
- Add export backup for all personal data.
- Add import restore later if needed.
- Ensure access key is required in hosted mode.
- Add Render/free-hosting deployment checklist.

Acceptance criteria:

- The app can run locally with JSON storage.
- The app can run hosted with MongoDB storage.
- The user can verify which storage mode is active.
- The user can export data before making risky changes.

Testing:

- Local JSON smoke test.
- MongoDB connection test when credentials are configured.
- Deployment checklist verification.

## Phase 7: Insight And Coaching Layer

Objective: Help the user improve behavior over time.

Tasks:

- Add friction trends.
- Add energy trend.
- Add planning accuracy.
- Add focus consistency heatmap.
- Add suggestions based on patterns.
- Add optional AI-assisted weekly planning later.

Acceptance criteria:

- The app can identify repeat blockers.
- The app can show whether planning is improving.
- Suggestions are tied to actual behavior, not generic advice.

Testing:

- Unit tests for insight calculations.
- Seeded-data screenshot tests.

## Technical Refactor Recommendations

The current Flask single-file UI is acceptable for fast iteration, but it will become harder to maintain as the product grows.

Recommended refactors:

- Move HTML rendering into templates.
- Move CSS into a static stylesheet.
- Move JavaScript into a static file.
- Add service functions for weekly summaries and score calculations.
- Add focused tests for scoring, planning, area minutes, and review summaries.
- Keep storage abstractions stable so JSON and MongoDB both work.

## Immediate Next Build Order

1. Keep `kairos` / `kairos home` as the command center: season, discipline progress, XP, completed work, selected/captured work, and fast commands.
2. Keep `kairos status` accurate: storage mode, MongoDB/JSON status, current season, today's commitments, focus minutes, completed goal/task work, and logged partial/blocked work.
3. Keep `kairos season` able to create or update the 21-day operating agreement.
4. Keep `kairos today plan` able to choose 1-3 commitments from active goal tasks.
5. Keep `kairos goal create` and `kairos goal add-task` fast enough for real goal maintenance during work.
6. Keep `kairos focus` / `kairos focus start` reliable: terminal countdown, focus-end alert, result save, and task status update.
7. Add later CLI review commands only after the daily loop remains stable in real use.
8. Use Kairos daily while building so Today, Focus, Research, and Brain accumulate real data.
9. Tighten Season-driven auto-plan so Today favors the protected 21-day primary track.
10. Add Day 7, Day 14, and Day 21 Season review decisions.
11. Improve Research into a fuller Perplexity-style session: source list, answer, read view, save memory, and revisit thread.
12. Add delete/forget controls for Brain memories, answers, saved research, and research sessions.

## Risk Notes

- Too many features can make the app feel like a chore. Build loops, not screens.
- Streaks can motivate but can also create pressure. Keep score useful, not punishing.
- Career growth should be tied to shipped proof, not only learning hours.
- Mobile matters because the user wants access from any machine and likely quick check-ins from phone-sized screens.
- MongoDB should remain infrastructure, not product complexity. The user should not have to think about databases during daily use.

## Definition Of Done For Future UI Changes

Every future UI change should include:

- Desktop screenshot review.
- Mobile screenshot review.
- At least one Playwright flow test.
- Empty state check.
- Data persistence check.
- Clear next action on the page.
