# Kairos Simple Tutorial

Review date: 2026-05-18

## Daily Use

For now, the web app is available and active development is CLI-first. The CLI is the fastest way to track real work while Kairos is being built.

1. Open Today.
2. Follow the single Now action.
3. Answer the suggested reflection only if it helps today's direction.
4. Make sure the current 21-day Season is clear.
5. Write or confirm intention, must-win, and daily pact.
6. Choose only 1-3 commitments for the day.
7. Start Focus for the next task.
8. After the timer, record the block as complete, partial, or blocked.
9. If useful, record friction, quality, mood, and energy.
10. At the end of the day, write a shutdown note.
11. Once a week, open Review and check what should change.
12. Use Coach when you want the app to summarize your current state or suggest the next move.

## What Each Page Is For

| Page | Use it for | When to open it |
| --- | --- | --- |
| Today | Daily command center | Every morning and during work |
| Season | 21-day operating agreement | When choosing or adjusting the current primary track |
| Focus | Single-task execution | When starting a work block |
| Goals | Outcomes and next tasks | When creating or refining goals |
| Weekly | Realistic weekly capacity and goal allocation | Start of week |
| Areas | Life and career balance | Weekly or when priorities feel off |
| North Star | Long-term direction | Monthly or quarterly |
| Brain | Editable self-understanding and memory | When answering prompts or confirming memories |
| Research | Source-backed search, read, and save sessions | When learning something that should affect decisions |
| Review | Weekly learning and charts | End of week |
| Coach | Data-based guidance from Hugging Face or local fallback | When planning, reviewing, or diagnosing friction |

## Current Product Context

- Today shows the daily operating system first and keeps the time-block composer collapsed until needed.
- Season stores the current 21-day primary track, support track, constraints, paused goals, success evidence, and checkpoint notes.
- Focus puts the selected block and timer first, with target switching secondary.
- Goals keeps the create-goal form collapsed so active outcomes stay in view.
- Weekly supports capacity planning, goal allocation, and rollover.
- Review includes weekly charts for focus trend, area balance, goal progress, outcome mix, trigger patterns, and focus consistency.
- Areas works as a life scorecard with overview metrics first and editable area cards below.
- Brain stores editable profile fields, confirmed memories, memory candidates, saved research, raw answers, personal-brain observations/patterns, and a 156-question library.
- Research works as a lightweight Perplexity-style flow: ask a question, inspect sources, save the useful insight.
- Coach uses Hugging Face Inference Providers with the configured `HF_MODEL`, and falls back to local guidance if the provider is unavailable.

## Product Direction

Kairos is moving toward a behavior-first design:

- Today should show the chosen daily operating mode, selected/captured work, and evidence, not every control.
- Season should protect one primary track for 21 days.
- North Star should be read-first, not form-first.
- Weekly should prevent unrealistic planning.
- Review should teach one useful adjustment.
- Coach should appear where the user is stuck.

## CLI Workflow

The normal CLI loop is:

```powershell
kairos
kairos daily
kairos goal create
kairos goal add-task
kairos status
kairos season
kairos today
kairos today plan
kairos focus
```

The home screen shows season, discipline progress, XP-style completed minutes, today's completed goals/tasks, selected/captured work, and fast commands. The timer command runs in the terminal, plays an alert when the focus block ends, saves the focus result, and updates the task status.

Before tracking real work, run `kairos status` and confirm storage is MongoDB when working across machines.

References: `docs/README.md` for the documentation map and `docs/psychological_product_blueprint.md` for the behavior-first product model.

## Current Goal Category Map

| Goal | Category | Why |
| --- | --- | --- |
| Langchain | Learning | Skill-building goal for RAG models and agents. |
| FastAPI | Learning | Backend/application integration skill-building. |
| Langpraph | Learning | Agent orchestration skill-building. |
| CodeMitra | Career | Personal project that can become shipped proof of work and career capital. |

## Category Rules

- Career: shipped projects, job/business outcomes, portfolio proof, opportunity creation.
- Learning: courses, technical skills, practice projects, notes, demos.
- Health: exercise, sleep, food, energy, body maintenance.
- Money: income, budgeting, savings, investing, financial clarity.
- Relationships: family, friends, network, communication.
- Personal Systems: routines, environment, planning, discipline, automation.

## Recommended Weekly Rhythm

- Monday: choose weekly focus area, realistic capacity, and top goals.
- Daily morning: plan 1-3 commitments.
- During the day: run focus blocks.
- Daily evening: shutdown note.
- Sunday: review time by area and adjust next week.
