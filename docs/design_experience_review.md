# Kairos Design Experience Review

Role: Product Designer / UX Designer  
Review date: 2026-05-18  
Reviewed screens: Today, North Star, Season, Brain, Areas, Focus, Goals, Weekly, Review, Research, Coach on desktop and mobile.

## Executive Summary

Kairos has the right product shape: it is not just a timer, and it is not just a goal list. The current app already combines life direction, goal planning, daily planning, focus execution, and review evidence. That is the correct foundation for a personal discipline system.

The main design opportunity is to make the app feel like a guided behavioral operating system instead of a set of forms and dashboards. The current UI is functional and clear, but it puts too much responsibility on the user to know what to do next. The next design phase should reduce decision load, create stronger page hierarchy, and make each screen answer one question:

- Today: What should I do now?
- Season: What is protected for the next 21 days?
- Focus: What am I committing to for this block?
- Weekly: What is realistic this week?
- Goals: What outcome am I progressing?
- North Star: Why does this work matter?
- Areas: Which part of life needs attention?
- Review: What pattern is emerging, and what should change?
- Brain: What have I learned about myself?
- Research: What source-backed insight is worth keeping?
- Coach: Where am I stuck?

Current implementation note:

- Today is now built around a stronger "Now" section and a collapsed block composer.
- Focus centers the selected block and timer first.
- Goals keeps the create-goal form collapsed by default.
- Review now includes charts for focus, area balance, goal progress, outcome mix, and triggers.
- Areas now behaves as a scorecard with overview metrics first.
- Weekly now supports capacity planning, goal allocation, and rollover.
- Season is now the 21-day operating agreement and should be the main bridge between long-term direction and daily execution.
- Brain now leads with recommended questions and keeps the full 156-question library collapsed.
- Research now supports a source-backed search, read, save flow that feeds Brain memory.
- Coach uses Hugging Face Inference Providers and `Qwen/Qwen2.5-7B-Instruct-1M`, with local deterministic fallback when the provider is unavailable.

2026-05-18 Playwright audit:

- Today: usable as the daily command center; suggested reflection is visible and useful for slow, incremental Brain growth.
- Season: serviceable as the primary 21-day planning surface; checkpoint notes are correctly secondary.
- Brain: the top recommended questions now work better than a long intake; the full library should remain collapsed by default.
- Research: the flow is clear enough for local use, but the next iteration should make the source-backed answer and saved discussion feel closer to a Perplexity thread.
- Weekly and Review: dense but acceptable because they are weekly surfaces, not daily starting points.
- North Star: still more form-like than ideal; keep it as long-term direction and avoid making it compete with Season.

2026-05-15 gap-fix implementation:

- Today empty commitments now show direct Auto-plan and Choose manually actions.
- Weekly realism now exposes Auto-allocate this week before the raw allocation table.
- Review now starts with three decisions for next week, before charts and session detail.
- North Star now includes values, anti-vision, and Brain alignment notes.
- Brain questionnaire answers now synthesize into the editable Brain profile.
- Areas now has quick weekly target buttons so Review findings can become action.
- Goals now warns clearly when a selected goal has no next task.
- Research now has a visible search -> read -> save session flow.
- Coach now returns useful local guidance even when Hugging Face rejects the model/token.

2026-05-14 design decision:

The next design phase should simplify rather than expand. Today should become Now-first. North Star should become read-first. Review should lead with the lesson, not the dashboard. Weekly should guide realistic planning instead of behaving like a raw allocation sheet. Details are captured in `docs/psychological_product_blueprint.md`. Start with `docs/README.md` for the full documentation map.

## Current Flow Map

The current product flow is:

1. Define long-term direction in North Star.
2. Define life areas in Areas.
3. Create goals and tasks in Goals.
4. Select or auto-plan work in Today.
5. Start a timer in Focus.
6. Complete a block and record it.
7. Learn from completed sessions in Review.

This is a strong loop, but it is not yet visible enough to the user. A new user can land on Today and see metrics, a daily log, selected work, flow captures, queue, and available work, but the app must keep the chosen daily operating mode clear.

## What Works Well

- The left navigation is stable and simple.
- The Today page is correctly positioned as the main daily command center.
- The daily operating checklist is a good behavioral scaffold.
- The Focus page has a clear selected target and timer.
- Areas and North Star prevent the app from becoming only a task tracker.
- The mobile layout is usable and avoids horizontal overflow.
- The app uses restrained visual styling, which is appropriate for a productivity tool.

## Main Design Problems

### 1. Today Has Too Many Competing Starting Points

Today shows the Now banner, metrics, checklist, commitments, a long timeboxed day, discipline form, and backlog. These are useful, but the visual hierarchy still asks the user to process too much before acting:

- First: choose today's 1-3 commitments.
- Then: start the next block.
- Later: close the day.

Recommended change:

Create a stronger top section called "Now" with the user's chosen operating mode. If no mode is chosen, the primary decision is planned day versus flow day. If work is selected, the surface should show selected/captured work and completed evidence without forcing a recommended next item.

New design requirement:

Collapse the full timeboxed schedule and backlog by default on mobile. The first screen should show the Now action, compact progress, and the committed plan.

### 2. Metrics Are Useful But Too Prominent

The six metrics occupy a large area before the user sees the actual work. This makes the app feel analytical before it feels actionable.

Recommended change:

Keep Score and Streak prominent, but compress the other metrics into a compact weekly progress strip. The top of Today should prioritize operating mode and evidence, not reporting.

### 3. Forms Make the App Feel Heavy

North Star, Areas, Goals, and Daily Discipline are mostly full forms. Forms are necessary, but the current design makes reflection feel like admin work.

Recommended change:

Use read-first, edit-on-demand sections. For example, Areas should first show the area score, desired state, weekly target, progress, and recommendation. The edit fields can appear after clicking "Edit".

North Star should especially become read-first. The identity statement, values, anti-vision, yearly direction, and priorities should be the main surface. Editing should be secondary. The current 21-day operating layer belongs in Season.

### 4. Focus Target Selection Is Too Long

The Focus page lists every available task above or beside the timer. On mobile, the user must scroll past a long list before reaching the timer. This weakens the focus experience.

Recommended change:

On Focus, show the selected target first. Put target switching behind a compact "Change target" panel or dropdown. Once the user enters Focus, the timer should dominate the screen.

### 5. Review Is Too Long

Review now contains useful analytics, but it risks becoming a long report. It needs a sharper top section that explains what to change.

Recommended change:

Lead with:

- Planned vs actual.
- Main friction.
- Best goal.
- Neglected area.
- Suggested adjustment for next week.

Keep detailed charts below.

### 6. Mobile Navigation Uses Too Much First-Screen Space

On mobile, the nav wraps into two rows and consumes significant vertical space. It is usable, but it pushes daily content down.

Recommended change:

Move mobile navigation to a compact bottom tab bar with Today, Focus, Goals, Review, More. Keep North Star and Areas under More, or expose them from Today when needed.

## Page-Level Recommendations

## Today

Current purpose: daily planning, planned/flow mode, available work, captured work, completed evidence, and daily reflection.

Recommended design direction:

- Make Today the only screen the user needs during a normal day.
- Add a top "Now" module with state-aware action.
- Merge Today's operating checklist and Daily Discipline form.
- Group content into Morning, Work, Shutdown.
- Move available work inside the Today Plan section and collapse it unless the queue is empty.
- Show planned tasks as numbered commitments: 1, 2, 3.
- Make "Auto-plan" explain what it selected after it runs.
- Add a "Why this matters" link from each task to its goal and life area.

Suggested Today layout:

1. Now: daily mode, selected/captured work, evidence summary.
2. Daily score: score, streak, focus minutes.
3. Today's commitments: 1-3 tasks.
4. Daily discipline: intention, must-win, shutdown.
5. Available work: only when adding or replanning.
6. Review: today timeline and notes.

## Focus

Current purpose: choose target, run timer, complete block.

Recommended design direction:

- Make the timer the hero of the page.
- Display selected task, goal, area, and reason.
- Add a pre-focus commitment prompt: "What will be true when this block is done?"
- Add end-of-block result capture: completed, partial, blocked, distraction reason.
- Move target selection into a secondary panel.

Suggested Focus layout:

1. Selected task and goal context.
2. Timer and controls.
3. Completion form.
4. Change target drawer.
5. Today's completed blocks.

## Goals

Current purpose: create goals, add tasks, update statuses.

Recommended design direction:

- Separate creating a goal from managing an existing goal.
- Add progress indicators by task completion and focus time.
- Add clearer priority meaning: P1 should mean "must move this week", not just a label.
- Add "next action" as a first-class field.
- Add goal health: no next task, overdue, no focus this week, too many active goals.

## North Star

Current purpose: long-term direction and identity.

Recommended design direction:

- Keep it calm and reflective.
- Show saved direction in a read-first format.
- Add prompts that connect to career and life outcomes.
- Add "current season" as the bridge between long-term vision and weekly planning.
- Add a quarterly reset/review date.

North Star should not be a daily form. It should be an identity reminder and long-term alignment surface. Season should carry the current 21-day operating decision.

## Season

Current purpose: choose the protected 21-day track, support track, constraints, paused goals, evidence, and checkpoint rhythm.

Recommended design direction:

- Keep the top decision summary visible.
- Keep edit fields available but secondary to the operating agreement.
- Use Day 7, Day 14, and Day 21 checkpoints as decision moments.
- Make Season the default source for Today auto-plan and Review evidence.
- Avoid adding a 90-day planning layer until the 21-day loop is working from real usage data.

Suggested Season layout:

1. Current season summary: day, primary track, support track, next action.
2. Evidence: focus minutes, daily minimum, weekly target, progress.
3. Decision controls: apply suggested fields, update direction, pause/continue.
4. Edit season details.
5. Checkpoint notes.

## Brain

Current purpose: local cognitive mirror and question engine.

Recommended design direction:

- Show recommended questions first.
- Keep the full question bank collapsed as a library.
- Separate confirmed memories from candidate memories.
- Make every durable memory editable and forgettable.
- Avoid clinical or identity-fixed labels.

## Research

Current purpose: source-backed search, read, save memory.

Recommended design direction:

- Treat every search as a research session.
- Keep source list, synthesized answer, selected source, and saved memory together.
- Save only durable insight, not raw noise.
- Make previous research sessions searchable and reusable by Brain and Coach.

## Areas

Current purpose: score life areas and define desired states.

Recommended design direction:

- Turn area cards into scorecards instead of edit forms.
- Show target versus actual focus minutes for the current week.
- Add visual status: healthy, needs attention, neglected.
- Add recommended action per area.
- Allow one active focus area for the week.

Avoid making every area equally urgent. If all six cards say "Needs target", the user receives noise. The system should identify one area to attend to next.

## Review

Current purpose: turn completed work into learning.

Recommended design direction:

- Add charts and summaries.
- Make it useful for weekly reflection.
- Show patterns, not only records.

Rename in mental model to Review everywhere. The route may remain `/history` technically, but product language should be Review.

## Weekly

Current purpose: weekly capacity and goal allocation.

Recommended design direction:

- Rename conceptually to Plan Week.
- Ask for realistic capacity before showing allocation.
- Auto-suggest plan from priority, due dates, rollover, and area targets.
- Warn when plan exceeds capacity.
- Hide notes/details until expanded.
- Show one weekly pact.

Weekly planning should prevent fantasy planning. It should help the user choose what not to do.

## Visual Design Recommendations

- Keep the restrained blue and neutral palette, but add semantic colors for status: green for done, amber for attention, red for blocked/neglected.
- Reduce large metric cards on Today and increase prominence of operating mode, selected/captured work, and evidence.
- Use icons for repetitive actions like start, complete, remove, review, and edit.
- Tighten vertical spacing on dense pages like Today and Goals.
- Use progressive disclosure for editing fields.
- Use consistent button hierarchy:
  - Primary: one main action per section.
  - Secondary: navigation or low-risk action.
  - Destructive/clearing: visually quieter but clearly labeled.
- Add empty states with direct actions, not just explanatory text.

## Interaction Improvements

- Add state-aware Today actions:
  - No plan: "Plan my day".
  - Planned but no focus: "Start first block".
  - Focus done: "Continue with next task".
  - End of day: "Close the day".
- Add inline success feedback after saving logs, planning work, or completing focus.
- Add keyboard-friendly focus flow: start timer, pause, complete block.
- Add confirmation for clearing today's plan.
- Add filters for available work by area and priority.
- Add quick add task from Today.

## Accessibility Notes

- The current color contrast appears mostly acceptable, especially in primary text and buttons.
- Some small uppercase labels may be difficult to read for long sessions.
- Focus states exist for inputs but should also be strong for links and buttons.
- Mobile tap targets are generally usable, but action buttons inside dense lists should be more consistent.
- The app should support reduced motion if future animations are added.

## Highest Priority Design Changes

1. Simplify Today into a Now-first command center.
2. Merge Today checklist and Daily Discipline into one interactive loop.
3. Make Weekly a guided realistic planning flow.
4. Redesign Review's top section around the lesson and next adjustment.
5. Convert North Star to read-first display.
6. Add contextual Coach actions where decisions happen.
7. Add stronger empty states and success states.

## Design Principle Going Forward

Kairos should not ask "What data do you want to enter?" It should ask "What decision do you need to make now?" Every screen should reduce ambiguity and make disciplined action easier.
