# Kairos Product Discipline Audit

Role: Product Leader / Behavioral Product Manager  
Review date: 2026-05-18

## Product Thesis

Kairos should help one person build discipline by connecting long-term direction to daily execution. The product should make it easier to choose the right work, start when motivation is low, finish with evidence, and review patterns without shame.

The best version of Kairos is not a generic todo app. It is a personal operating system for time management, career growth, and life balance.

2026-05-14 update:

The product direction is now behavior-first. Kairos should reduce decision load at the point of action, guide the user through small loops, and treat missed plans as information. The central reference for this direction is `docs/psychological_product_blueprint.md`; the full documentation map is `docs/README.md`.

2026-05-18 update:

The primary operating track is now 21 days, not 90 days. Season is the active planning layer between North Star and Today. Brain and Research are memory layers that should improve Season, Today, Review, and Coach over repeated use.

## Behavioral Product Doctrine

Kairos should be designed around six behavior principles:

- One moment, one question.
- Reduce choice at the point of action.
- Make starting smaller when motivation is low.
- Treat misses as data, not failure.
- Reinforce identity before metrics.
- Adapt the next prompt to the user's current state.

This means the app should not expose every useful control at once. It should decide what is relevant for the current moment and progressively reveal the rest.

## Current Feature Inventory

| Feature | Functionality | How It Helps Discipline | Current Maturity | Next Improvement |
| --- | --- | --- | --- | --- |
| Today dashboard | Shows daily score, streak, active goals, planned tasks, focus minutes, and blocks. | Creates daily visibility and makes discipline measurable. | Good foundation | Make it action-first and state-aware. |
| Daily discipline log | Captures intention, must-win, and shutdown. | Encourages morning clarity and evening closure. | Useful but form-heavy | Split into morning setup and evening shutdown. |
| Operating checklist | Tracks intention, must-win, plan, focus block, shutdown. | Converts discipline into a concrete daily checklist. | Strong | Add explanations and progress states. |
| Today's queue | Holds 1-3 planned work items. | Prevents overplanning and forces prioritization. | Strong | Add ordering, drag/reorder, and "commit for today". |
| Available work | Lists active goal tasks that can be added to today. | Gives the user a menu of meaningful work. | Useful | Add filters by priority, area, and due date. |
| Auto-plan | Adds up to three focus candidates to today. | Reduces planning friction when the user feels stuck. | Basic | Make rules visible and favor P1/overdue/neglected areas. |
| Next focus | Highlights one recommended focus target. | Reduces decision fatigue and helps the user start. | Strong | Make it the dominant top action on Today. |
| Season | Stores the 21-day primary track, support track, success evidence, constraints, paused goals, and checkpoint notes. | Turns broad ambition into a short validation cycle with clear tradeoffs. | Implemented | Drive Today auto-plan and Review evidence directly from Season. |
| Focus timer | Runs a single-task timer with start, pause, reset, and complete. | Converts intention into timed execution. | Good | Add result capture and distraction logging. |
| Complete focus block | Records minutes and marks selected task done. | Creates evidence of progress and rewards completion. | Good | Support partial completion and blocked outcomes. |
| Goals | Creates goals with category, priority, target date, notes, and tasks. | Converts ambitions into executable projects. | Good | Add goal health, next action, and weekly commitment. |
| Task status | Supports todo, doing, done, and blocked. | Makes work state visible and reduces hidden ambiguity. | Good | Add blocked reason and unblock next step. |
| North Star | Stores long-term direction, identity, values, anti-vision, and priorities. | Connects daily work to identity and long-term direction. | Strong concept | Keep it read-first and let Season carry the current 21-day operating decision. |
| Life areas | Tracks Career, Learning, Health, Money, Relationships, and Personal Systems. | Prevents career-only productivity and supports balanced growth. | Strong concept | Add weekly area budgets and attention warnings. |
| Area weekly target minutes | Lets each area define expected weekly focus time. | Encourages intentional time allocation. | Basic | Compare target versus actual and recommend rebalancing. |
| Area score | Rates each life area from 1-10. | Builds self-awareness and exposes neglected areas. | Basic | Trend score over time and prompt weekly reflection. |
| Review | Shows weekly charts, completed sessions, planned vs actual, area balance, goal progress, triggers, and reflection prompts. | Turns behavior into learning and adjustment. | Implemented, needs sharper top insight | Lead with planned vs actual, main friction, best goal, neglected area, and suggested adjustment. |
| Brain | Stores questionnaire answers, editable profile fields, confirmed memories, memory candidates, and saved research. | Builds a local cognitive mirror and improves personalization. | Implemented | Add forget/delete controls and more pattern summaries. |
| Research | Source-backed search, read/save sessions backed by local SearXNG. | Keeps useful search findings attached to goals, areas, questions, and Brain memory. | Implemented | Make sessions feel closer to a Perplexity-style answer thread. |
| Coach | Contextual guidance from Hugging Face or local fallback. | Reduces friction at the moment of action. | Implemented, resilient | Add embedded prompts on decision-heavy screens. |
| Access key | Optional simple personal protection for hosted use. | Keeps a personal app private without multi-user complexity. | Practical | Document deployment setup clearly. |
| MongoDB support | Allows cloud persistence across machines. | Enables continuity from any device. | Practical | Add backup/export and connection health display. |

## Discipline Mechanisms Already Present

Kairos already includes several strong behavior design mechanisms:

- Commitment: Today's queue asks the user to pick 1-3 tasks.
- Clarity: Daily intention and must-win reduce vague effort.
- Single-tasking: Focus mode narrows attention to one target.
- Evidence: Completed sessions become review evidence.
- Identity: North Star asks who the user is becoming.
- Balance: Areas make life and career visible together.
- Feedback: Score and streak create immediate feedback.

These mechanisms are directionally correct. The next product work should strengthen the loop around them.

## Product Gaps

### 0. Too Much Is Visible At Once

The largest current risk is not missing functionality. It is cognitive overload. Today, Review, and Weekly contain useful pieces, but they sometimes ask the user to plan, edit, review, execute, and diagnose at the same time.

Recommended product correction:

- Today becomes a Now-first command center.
- Season becomes the 21-day operating agreement.
- Weekly becomes guided capacity planning.
- Review leads with one lesson and one adjustment.
- North Star becomes read-first.
- Coach appears contextually where decisions happen.
- Brain and Research stay in the memory layer instead of becoming generic note surfaces.

Why it matters:

Discipline is fragile when the user is tired, uncertain, or emotionally avoidant. The app should lower activation energy, not make the user operate a cockpit.

### 1. Weekly Review Needs A Sharper Learning Loop

Discipline is built daily, but corrected weekly. The current app now has Review, charts, planned-vs-actual metrics, and reflection prompts. The remaining issue is focus: Review should lead with the lesson before showing the full analytics report.

Recommended improvement:

Review should lead with:

- Planned vs actual.
- Best goal.
- Neglected area.
- Main friction.
- Suggested adjustment.

Why it matters:

This turns raw tracking into learning. Review should help the user make one better plan, not force them to interpret every chart manually.

### 2. No Time Budget

Areas have weekly target minutes, but Today does not use them strongly yet.

Recommended feature:

Add weekly time budgets by area and goal. Show "planned versus actual" and warn when Career, Learning, Health, or Personal Systems are underfunded.

Why it matters:

Time management becomes real when time is allocated before it is spent.

### 3. No Friction Capture

When a user does not focus, the app does not ask why.

Recommended feature:

Add quick friction tags:

- Low energy.
- Unclear task.
- Too big.
- Distraction.
- Avoidance.
- Blocked dependency.
- Environment issue.

Why it matters:

Discipline improves when recurring blockers become visible. This avoids treating every missed session as a character problem.

### 4. No Career Growth Track

The user wants to excel in life and career. Current goals can support career, but there is no explicit career development model.

Recommended feature:

Add Career Track:

- Target role or business direction.
- Skills to build.
- Projects to ship.
- Proof of work.
- Weekly career commitment.
- Portfolio/evidence log.

Why it matters:

This turns time management into career compounding, not just productivity.

### 5. No Onboarding

The app assumes the user understands the system.

Recommended feature:

Add a first-run setup:

1. Write one-year direction.
2. Score life areas.
3. Create 1-3 active goals.
4. Choose today's first task.
5. Start first focus block.

Why it matters:

The first session should produce momentum immediately.

### 6. No Review of Plan Quality

The app records whether tasks were planned, but not whether the plan was realistic.

Recommended feature:

At shutdown, ask:

- Did I complete the must-win?
- Was the plan too much, too little, or right-sized?
- What should I carry forward?

Why it matters:

The user learns how to plan better, not just work harder.

## Recommended Product Loops

## Daily Loop

1. Morning: choose intention, must-win, and 1-3 tasks.
2. Work: start next focus block.
3. Completion: record result and actual minutes.
4. Shutdown: capture outcome, carry forward unfinished work, close the day.

Updated product requirement:

Today should show only the next relevant step in this loop. It should not show every loop component at equal weight.

## Weekly Loop

1. Review focus time by area and goal.
2. Identify strongest and weakest area.
3. Choose one weekly focus area.
4. Set time budgets.
5. Pick top goals for the week.

## Career Growth Loop

1. Choose skill or project.
2. Break into visible deliverables.
3. Focus consistently.
4. Record shipped proof.
5. Review progress weekly.

## Life Balance Loop

1. Score each area.
2. Set desired state.
3. Set weekly time target.
4. Track actual focus.
5. Flag neglected areas.

## Feature Priorities

## Must Build Next

- Now-first Today command center.
- Interactive operating checklist that replaces the separate Daily Discipline form.
- Guided Weekly planning with capacity realism.
- Review top insight: planned vs actual, main friction, suggested adjustment.
- Contextual Coach prompts.

## Should Build After

- First-run setup.
- North Star read-first redesign.
- Friction and energy trend summaries.
- Career Track page.
- Goal health warnings.
- Career evidence / proof-of-work log.

## Later

- Reminders and notifications.
- Calendar integration.
- Import/export.
- Mobile install/PWA polish.
- AI-assisted weekly planning.

## Product Quality Bar

Kairos should be judged by these questions:

- Did the user know what to do next?
- Did the app reduce decision fatigue?
- Did the app help the user start work?
- Did the app make progress visible?
- Did the app help the user learn from misses?
- Did the app connect today's work to life and career direction?
- Did the app make the next step smaller when resistance was high?
- Did the app avoid shaming the user for misses?
- Did the app help the user make a realistic plan instead of an aspirational one?

If a feature does not help one of these outcomes, it should be delayed.

## Redundancy Decisions

| Current overlap | Decision |
| --- | --- |
| Today operating checklist + Daily Discipline form | Merge into one interactive checklist/form. |
| Today commitments + Backlog | Merge into one Today Plan section with backlog collapsed. |
| Focus recording + Activity logging visible together | Replace with Focus/Activity mode switch. |
| Review area chart + Review area balance list | Combine into one Area Balance section. |
| Weekly allocation separate from Goals | Keep Weekly as editor, but show weekly target/actual on Goals. |
| Coach page isolated from work surfaces | Keep page, add contextual coach actions. |
