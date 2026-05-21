# Kairos Psychological Product Blueprint

Role: Product Leader / Product Designer / Behavioral Systems Designer  
Review date: 2026-05-18  
Inputs: Playwright audit of Today, North Star, Areas, Focus, Goals, Weekly, Review, Coach; existing product docs; behavioral design references.

Related docs:

- `docs/README.md` explains the documentation map and reading order.
- `docs/implementation_roadmap.md` translates this blueprint into build phases.
- `docs/product_discipline_audit.md` tracks product loops, gaps, and redundancy decisions.
- `docs/design_experience_review.md` captures the screen-level UX review.

## Product Thesis

Kairos should help one person become more consistent by reducing decision load, making intention visible, making starting easier, and turning misses into useful feedback.

The app should not feel like a productivity dashboard that asks the user to manage many controls. It should feel like a calm discipline coach that answers:

- What matters?
- What should I do now?
- What might pull me away?
- What did I learn?
- What should change next time?

The strongest version of Kairos is not a generic task manager. It is a behavioral operating system for time management, career compounding, and life balance.

Current operating decision:

- Kairos should use a 21-day Season as the active planning layer.
- North Star holds long-term direction; Season decides what is protected now.
- The app should not reintroduce a 90-day planning layer until the 21-day loop has real usage evidence.

## Local Brain Direction

Kairos should become a local cognitive mirror, not a hidden black-box profile. The product should help the user remember what they said matters, notice repeated patterns, and make better commitments. It should not claim to be an identical copy of the person or diagnose them.

Implementation principles:

- Obsidian is the readable long-term memory.
- App storage indexes the memory for fast planning, review, coaching, and search.
- Raw answers stay separate from generated summaries.
- Every durable memory must be visible, editable, and deletable.
- The best prompt is usually one question at the right moment, not a long form.
- Psychological questionnaires should deepen self-understanding while avoiding clinical claims.
- The full question bank should remain available as a library, but daily use should show only a small set of relevant questions.

The initial Brain model should capture:

- Identity and North Star.
- Values and anti-vision.
- Current state, struggles, constraints, and energy patterns.
- Autonomy, competence, and relatedness signals.
- Focus triggers, pacts, mood, energy, and quality.
- Saved search interests from local SearXNG flow.

Question types should include:

- Likert: Strongly disagree to Strongly agree.
- Frequency: Never to Always.
- Ranking: values, areas, goals, and blockers.
- Choice: competing needs or likely patterns.
- Open reflection: raw narrative context.
- Post-session check-ins: quality, mood, energy, trigger, pact.

Safe questionnaire sources:

- IPIP public-domain personality item pool for personality-style trait depth.
- WHO-5-inspired wellbeing check-ins, clearly marked as non-diagnostic.
- Self-Determination Theory-inspired autonomy, competence, and relatedness prompts.
- Nir Eyal-inspired internal/external trigger reflection.

## Behavioral Foundations

Kairos should borrow from these models without becoming a rigid copy of any one system.

### 1. Indistractable-Inspired Traction Model

Core idea for Kairos:

- A distraction can only be identified after the user defines intended traction.
- The app must ask what the time is for before judging whether the user drifted.
- Internal triggers matter as much as external triggers.
- Pacts should protect a block before motivation drops.

Product implication:

- Every focus block needs a planned target.
- Completion should ask what happened, not just whether the task is done.
- Review should show trigger patterns without shame.
- Timeboxing should exist to define intent, not to punish deviations.

### 2. Fogg Behavior Model

BJ Fogg's behavior model frames behavior as requiring motivation, ability, and prompt at the same moment.

Product implication:

- When motivation is low, Kairos should increase ability by making the next step smaller.
- Prompts should be state-aware: "Plan today", "Start first block", "Close the day".
- The app should not rely on willpower. It should design the next action so it feels easy enough to start.

### 3. Implementation Intentions

Implementation intentions use if-then planning: if a specific cue occurs, then a specific action follows.

Product implication:

- "I will study LangChain" is too vague.
- "At 07:45, start a 25-minute LangChain block and write notes" is executable.
- Today and Weekly should convert goals into time/place/action commitments.
- Focus pacts should use simple if-then wording:
  - If I want to check my phone, then I wait 10 minutes.
  - If I feel unclear, then I write the next question.
  - If energy is low, then I start with 5 minutes.

### 4. Self-Determination Theory

Long-term discipline is more stable when the user experiences autonomy, competence, and relatedness.

Product implication:

- Autonomy: user chooses the week focus and the day plan; the app suggests, not commands.
- Competence: Review should show progress, learning, and realistic improvement.
- Relatedness: Relationships and health should remain visible so the app does not become career-only pressure.

### 5. GTD-Inspired Trusted System

GTD separates capture, clarify, organize, reflect, and engage.

Product implication:

- Kairos needs a small inbox/capture path later, but not a large task manager.
- Goals should hold clarified outcomes and next actions.
- Today should only show what is ready to engage.
- Review should be the reflection mechanism.

### 6. WOOP / Mental Contrasting

WOOP asks for wish, outcome, obstacle, and plan.

Product implication:

- Weekly planning should ask not only "What do I want?" but "What will block this?"
- The plan should produce a pact for the obstacle.
- This fits naturally into weekly planning and focus check-in.

## Psychological Design Principles

### Principle 1: One Moment, One Question

Each screen should answer one user question.

| Screen | Primary question |
| --- | --- |
| Today | What should I do now? |
| Focus | What am I doing for this block? |
| Weekly | What is realistic this week? |
| Review | What happened and what should change? |
| Goals | What outcome am I moving and what is the next action? |
| Areas | Is my life balanced enough? |
| North Star | Why does this matter? |
| Coach | Where am I stuck and what is the next move? |

### Principle 2: Reduce Choice at the Point of Action

Planning can support many options. Execution should not.

Today should show one recommended next action. Focus should show one selected target. Backlog and target switching should be secondary.

### Principle 3: Make Starting Smaller

Discipline usually fails at initiation, not at abstract desire.

Kairos should support:

- Start 5 minutes.
- Resume next block.
- Do the smallest next action.
- Clarify task if unclear.
- Convert blocked work into a next question.

### Principle 4: Treat Misses as Data

The app must avoid shame language.

Use:

- "What pulled you away?"
- "What made this block harder?"
- "What should change next time?"

Avoid:

- "Failed"
- "Bad score"
- "You missed"
- punitive streak framing

### Principle 5: Identity Before Metrics

Metrics help, but identity sustains.

North Star and daily pact should reinforce:

- "I am someone who plans before reacting."
- "I start small when resistance is high."
- "I keep promises to myself by adjusting the system."

### Principle 6: Make the System Adaptive

The app should not assume every day is the same.

Kairos should adapt based on:

- no plan yet
- planned but no focus
- focus completed
- energy low
- repeated blocked sessions
- overcommitted weekly plan
- neglected life area

## Desired User Loops

### Daily Loop

1. Open Today.
2. See one "Now" action.
3. Set or confirm intention, must-win, and day pact.
4. Commit to 1-3 tasks.
5. Start the first focus block.
6. Complete block with result, friction, energy, mood, and quality if useful.
7. Continue next block or close the day.
8. Shutdown asks what happened, what carries forward, and what to change tomorrow.

### Focus Loop

1. Select one target.
2. Write a block commitment.
3. Choose pact if a known trigger is likely.
4. Start timer.
5. Record complete, partial, or blocked.
6. Capture friction and emotional state.
7. Decide next: next block, clarify, break, or shutdown.

### Weekly Loop

1. Review last week: planned vs actual, strongest goal, neglected area, main friction.
2. Choose one focus area of the week.
3. Set realistic capacity.
4. Allocate capacity to top goals.
5. Rollover missed work intentionally, not automatically as guilt.
6. Define one weekly pact.

### Career Compounding Loop

1. Choose career direction.
2. Pick skill or project.
3. Define proof of work.
4. Allocate weekly focus.
5. Ship or document evidence.
6. Review progress weekly.

### Life Balance Loop

1. Score areas weekly or monthly.
2. Choose focus area.
3. Set target minutes or action.
4. Track actual investment.
5. Adjust next week.

## Proposed Information Architecture

Keep all current pages for now, but change their meaning:

| Nav item | Product role | Long-term direction |
| --- | --- | --- |
| Today | Daily command center | Keep |
| Focus | Execution mode | Keep |
| Goals | Outcomes and next actions | Keep |
| Weekly | Weekly plan editor | Rename to Plan Week later |
| Review | Learning and adjustment | Keep |
| Areas | Life balance scorecard | Keep |
| North Star | Read-first direction | Keep, less frequent use |
| Coach | Contextual assistant | Keep, but also embed into pages |

Recommended mobile nav later:

- Today
- Focus
- Goals
- Review
- More

Put North Star, Areas, Weekly, Coach under More or link contextually.

## Redesign Decisions

### Decision 1: Today Becomes "Now First"

Today should not show the full operating system at once.

Future layout:

1. Now card: one state-aware action.
2. Today Plan: committed tasks.
3. Focus progress: compact.
4. Morning setup or Shutdown depending on time/state.
5. Schedule/timebox collapsed by default.
6. Backlog collapsed unless no plan exists.

What to remove from the first screen:

- full timeboxed schedule
- full daily discipline form
- full backlog
- all template controls

### Decision 2: Combine Checklist and Daily Discipline

The operating checklist and discipline form are the same loop expressed twice.

Future design:

- Checklist rows become interactive.
- Clicking Intention opens its field.
- Clicking Must-win opens its field.
- Clicking Daily pact opens pact field.
- Shutdown appears later or after focus.

This reduces form fatigue and keeps progress visible.

### Decision 3: Focus Has Modes

Focus should not show both focus recording and activity logging at equal weight.

Future design:

- Segmented control: Focus / Activity.
- Focus mode shows selected task, timer, commitment, result.
- Activity mode shows activity type, minutes, energy/mood note.

### Decision 4: Weekly Planning Should Guide Realism

Weekly should not be a raw spreadsheet.

Future design:

1. Capacity first: "How many real focus hours are available?"
2. Auto-suggest allocation from priority, due dates, area targets, and rollover.
3. Show warning if plan exceeds capacity.
4. Show "health/personal systems underfunded" if relevant.
5. Notes hidden behind expansion.

### Decision 5: Review Should Lead With Learning

Review should answer:

- Did I do what I planned?
- What pulled me away?
- What should change next week?

Future top cards:

- Planned vs actual.
- Best goal.
- Neglected area.
- Main friction.
- Suggested adjustment.

Detailed charts should stay below.

### Decision 6: North Star Becomes Read-First

North Star should feel like direction, not setup admin.

Future layout:

- Identity statement.
- Current 21-day season focus.
- Longer-term outcomes and priorities.
- Top 3 priorities.
- Edit button.
- Review cadence.

### Decision 7: Coach Becomes Contextual

Coach should remain a page, but its highest value is contextual.

Add small coach actions:

- Today: "Help me choose the next block."
- Focus: "Help me unblock this task."
- Weekly: "Suggest a realistic plan."
- Review: "Explain this week."
- Goals: "Break this goal into next actions."

## Redundancy To Remove

| Redundant pair | Keep | Merge/remove |
| --- | --- | --- |
| Today checklist + Daily discipline form | Checklist as interactive system | Hide form fields inline |
| Today commitments + Backlog | Today Plan | Backlog collapsed inside plan |
| Area actual vs target + Area balance in Review | One Area Balance section | Merge duplicate charts/lists |
| Focus form + Activity form visible together | Mode switch | Hide inactive mode |
| Weekly raw allocation + Goals progress separate | Keep both, but link | Show weekly target on goal detail |
| Coach page only | Contextual coach prompts | Add embedded coach actions |

## Data Model Implications

Needed or recommended models:

- WeeklyPlan: already added.
- WeeklyReview: reflection fields should persist separately from daily logs.
- AreaFocus: one weekly focus area.
- GoalEvidence: proof of work links or notes for career compounding.
- DistractionLog: optional lightweight record when user abandons a block.
- UserState: onboarding completed, preferred schedule, low-energy defaults.

## Design Tone

Kairos should feel:

- calm
- practical
- non-judgmental
- direct
- private
- momentum-oriented

Kairos should not feel:

- gamified in a childish way
- punitive
- data-heavy before action-heavy
- like a generic todo app
- like a therapy app

## Product Copy Rules

Use:

- "Start small."
- "What is this time for?"
- "What pulled you away?"
- "Adjust the system."
- "Choose one next block."
- "Protect traction."

Avoid:

- "You failed."
- "Bad day."
- "Catch up."
- "You are behind."
- "Fix yourself."

## First-Run Setup

The app needs onboarding later. First-run should take under 10 minutes.

1. Choose current 21-day season focus.
2. Score six life areas.
3. Create 1-3 active goals.
4. Choose weekly capacity.
5. Plan today with one task.
6. Start first 5-minute block.

The first session should produce action, not only configuration.

## Sources Reviewed

- Nir Eyal / Indistractable public materials: https://www.nirandfar.com/wp-content/uploads/2025/02/Indistractable_Lesson_Plan_for_Educators_07152020.pdf
- BJ Fogg Behavior Model: https://www.behaviormodel.org/
- Implementation intentions overview from NCI: https://cancercontrol.cancer.gov/brp/research/constructs/implementation-intentions
- GTD official overview: https://gettingthingsdone.com/what-is-gtd/
- Self-Determination Theory overview: https://www.urmc.rochester.edu/MediaLibraries/URMCMedia/community-health/programs-services/documents/SDT-Visual-Summary-120221.pdf
- WOOP handout: https://ggie.berkeley.edu/wp-content/uploads/2025/06/WOOP-Handout.pdf

## Build Priority From This Blueprint

1. Simplify Today into a true Now-first command center.
2. Make checklist and discipline form one interactive loop.
3. Redesign Weekly as guided capacity planning.
4. Redesign Review top section around learning and adjustment.
5. Make North Star read-first.
6. Add contextual Coach prompts.
7. Add first-run setup.
8. Add career evidence/proof-of-work tracking.
