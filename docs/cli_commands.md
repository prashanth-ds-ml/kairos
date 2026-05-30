# Kairos CLI Commands

Kairos is installed as a user-level terminal tool. You can run these from any folder:

```powershell
kairos
```

That opens the interactive Kairos session. Inside it, type commands without the `kairos` prefix:

```text
kairos> quickstart
kairos> daily
kairos> goal create
kairos> add task
kairos> goals list
kairos> create season
kairos> today plan
kairos> focus
kairos> exit
```

For one-shot status without entering the session:

```powershell
kairos status
```

## Install On A New Machine

Prerequisites:

- Python 3.10 or newer
- Git
- Optional: MongoDB if you want the same Kairos data across machines

Clone Kairos:

```powershell
git clone https://github.com/prashanth-ds-ml/kairos.git
cd kairos
```

Create a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

On macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the CLI:

```powershell
python -m pip install --upgrade pip
python -m pip install -e .
```

Verify it:

```powershell
kairos --version
kairos doctor
kairos paths
```

Run it:

```powershell
kairos
```

If the shell cannot find `kairos`, check whether Python can run it and where user scripts are installed:

```powershell
python -m kairos.cli --version
python -m site --user-base
```

Add the Python scripts directory under that user base to `PATH`. On Windows it is usually similar to:

```powershell
C:\Users\<you>\AppData\Roaming\Python\Python312\Scripts
```

Use local JSON storage on one machine:

```powershell
kairos config set KAIROS_STORAGE json
```

Use MongoDB for the same data on multiple machines:

```powershell
kairos config set KAIROS_STORAGE mongodb
kairos config set KAIROS_MONGODB_URI "<your MongoDB URI>"
kairos config set KAIROS_MONGODB_DATABASE kairos
kairos config set KAIROS_MONGODB_COLLECTION state
```

Config and local fallback data live here on Windows:

```powershell
C:\Users\<you>\.kairos
```

On macOS or Linux:

```bash
~/.kairos
```

Update an existing install:

```powershell
git pull
python -m pip install -e . --upgrade
```

## Quick Guide

Start Kairos:

```powershell
kairos
```

On the first interactive open of a new day, Kairos starts with today check-in, saves the daily log, then asks whether you want to pick one to three commitments or go with the flow and record tasks as they happen. Daily check-in uses a mixed question set: stable open check-in prompts plus coverage-aware rotating open, choice, frequency, ranking, and agree/disagree questions from the Brain question bank. Each saved answer keeps the question id and timestamp so repeated answers can be compared over time.

Inside Kairos, use this normal flow:

```text
kairos> quickstart
kairos> daily
kairos> goal create
kairos> add task
kairos> goals list
kairos> today plan
kairos> focus
kairos> status
kairos> exit
```

Create a goal:

```text
kairos> goal create
```

Then answer the prompts:

```text
Goal title: Learn LangChain
Area/category [career]: learning
Priority [P3]: P1
Target date (YYYY-MM-DD, blank for none): 2026-06-01
Notes:
First tasks (comma-separated): Watch lesson 1, Make notes, Build small demo
```

Plan today's commitments:

```text
kairos> today plan
```

Pick one to three numbers from the list.

Start a focus session:

```text
kairos> focus start
```

Pick the target number. Kairos runs the timer, then asks what happened and saves the focus session.

Create or update the 21-day season:

```text
kairos> create season
```

Then choose one active goal to validate and answer the prompts for why this goal now, dates, daily minimum, weekly target, success criteria, constraints, paused goals, and review question.

Fast one-shot examples from any terminal:

```powershell
kairos goal create --title "Learn LangChain" --category learning --priority P1 --task "Watch lesson 1" --task "Make notes"
kairos goal add-task --goal 1 --task "Build small demo" --task "Write notes"
kairos goal task add --goal 1 --task "Review docs,ship example"
kairos season create --goal 2 --title "MongoDB exam season" --primary "Validate real commitment to MongoDB certification" --daily-minimum 45 --weekly-target 420
kairos today plan --items 1 --clear
kairos focus start --target 1 --minutes 25
```

Show version:

```powershell
kairos --version
```

Show the top-level home screen:

```powershell
kairos home
```

`kairos` and `kairos home` show the command center: season, discipline progress, XP-style completed minutes, today's plan count, completed work for today, and fast commands.

At startup, Kairos refreshes the configured storage before drawing the command center. In an interactive session, redraw the latest state without restarting:

```text
kairos> refresh
```

One-shot equivalent:

```powershell
kairos refresh
```

## Daily Use

Show current storage, season, today's commitments, focus minutes, and completed work grouped by priority/goal/task:

```powershell
kairos status
```

Check install, config, storage, command path, and startup status:

```powershell
kairos doctor
```

Show important paths:

```powershell
kairos paths
```

Run the daily 3-5 question check-in:

```powershell
kairos daily
```

Preview today's daily questions without saving answers:

```powershell
kairos daily --dry-run
```

The bank includes personality, identity, values, motivation, planning, focus, energy, emotion, learning, decision style, situation simulation, stress defaults, communication style, boundaries, constraint preferences, and belief evolution. Answers are saved into Kairos Brain storage as raw timestamped records. To write the readable markdown brain into the vault:

```powershell
kairos brain status
kairos brain rebuild
kairos brain sync
```

`kairos brain rebuild` regenerates the personal-brain layer from raw data: observations, inferred patterns, evidence counts, confidence, recency, and contradictions. The sync writes files such as `vault/10 Brain/Personal Brain.md`, `Questionnaire History.md`, `Profile.md`, `Current State.md`, and `Confirmed Memories.md`.

Kairos prints small ASCII stamps when tasks are captured, focus blocks are logged, the day is closed, or the Brain is rebuilt. Set `KAIROS_NO_ART=1` to hide these stamps in scripts.

Show today's commitments:

```powershell
kairos today
```

Plan 1-3 commitments for today:

```powershell
kairos today plan
```

The current 21-day season appears at the top of the pick list, even if it is not linked to a normal goal task yet. This keeps the protected season visible and makes it easy to log at least one season block.

Use flow mode when the day is uncertain and you want to choose focus targets as work happens:

```powershell
kairos today flow
```

Capture an ad-hoc flow task:

```powershell
kairos today add --title "Reply to client escalation" --domain work --category career
kairos today add --title "Book doctor appointment" --domain personal --category health
kairos today add --title "Pay credit card bill" --domain personal --category money --start
```

Flow tasks are stored under reusable goals such as `Flow Work: Career` or `Flow Personal: Health`, so category and work/personal context remain visible in focus and review. Use `--commit` if the task should also become one of today's planned commitments.

In flow mode, `kairos today` separates carried commitments from tasks captured today.

Clear today's plan and choose new commitments:

```powershell
kairos today plan --clear
```

Choose commitments by number without prompts:

```powershell
kairos today plan --items 1,2 --clear
```

## Goals

List active goals and unfinished tasks:

```powershell
kairos goal list
```

Create a goal interactively:

```powershell
kairos goal create
```

Create a goal with flags:

```powershell
kairos goal create --title "Build Kairos CLI" --category career --priority P1 --task "Create goal command" --task "Run focus timer"
```

Add tasks to an existing goal interactively:

```powershell
kairos goal add-task
```

Inside the interactive shell, the natural alias is:

```text
kairos> add task
```

Add tasks to a goal by number:

```powershell
kairos goal add-task --goal 7 --task "Make PRD" --task "Write documentation"
```

Comma-separated task input is also supported:

```powershell
kairos goal task add --goal 7 --task "Test samples,write blog,release on GitHub"
```

Update task status:

```powershell
kairos goal task status
kairos goal task status --task-number 1.2 --status completed
kairos goal task status --goal 1 --task-number 2 --status on-hold
kairos task done --task t:30a619
kairos task hold --task t:30a619 --reason "Waiting for client" --review-date 2026-05-30
kairos task block --task t:30a619 --reason "Need API access"
```

Inside the interactive shell, natural aliases also work:

```text
kairos> update task
kairos> complete task
kairos> hold task
```

Supported task statuses are `todo`, `doing`, `done`, `on-hold`, and `blocked`. `completed` is accepted as an alias for `done`. `kairos goal list` shows both the current display number and a stable `t:xxxxxx` task reference; prefer the stable reference when updating a task after statuses have changed.

Close the day:

```powershell
kairos shutdown
kairos shutdown --summary "Finished the release notes" --carry "Waiting on review" --tomorrow "Start with tests"
```

## Focus Timer

Start a focus timer for a planned or active task:

```powershell
kairos focus start
```

Start a 25-minute focus timer for target number 1:

```powershell
kairos focus start --target 1 --minutes 25
```

The default timer uses one compact updating line to keep PowerShell history clean. Set `KAIROS_BIG_TIMER=1` to use the large full-screen ASCII countdown.

Log focus without running the countdown:

```powershell
kairos focus start --target 1 --minutes 25 --no-timer --status completed --notes "Finished the task"
```

Allowed focus statuses:

```powershell
completed
partial
blocked
```

## Season

Show current 21-day season:

```powershell
kairos season
```

Create or replace the current 21-day season. A season validates one goal by putting time into it and collecting evidence about whether it is real commitment or only an emotional spike:

```powershell
kairos season create
```

Pick a goal by number without prompts:

```powershell
kairos season create --goal 2 --title "MongoDB exam season" --daily-minimum 45 --weekly-target 420
```

Update the current season with a reason:

```powershell
kairos season update --reason "Exam date moved" --end-date 2026-06-25
kairos season update --reason "Daily minimum was unrealistic" --daily-minimum 35 --weekly-target 245
kairos season update --reason "Primary evidence changed" --goal 2 --primary "Validate ESE prep through daily evidence"
```

Inside the interactive shell:

```text
kairos> update season
kairos> edit season
```

Every update stores a change entry with timestamp, reason, changed fields, and before/after values.

Natural aliases inside the interactive shell:

```text
kairos> create season
kairos> new season
kairos> set season
```

When a season has a linked goal, `kairos focus start` shows the season goal first.

## Startup

Create a Windows startup launcher that opens Kairos daily check-in when the laptop starts:

```powershell
kairos setup startup
```

## Config

List config values from `C:\Users\prash\.kairos\.env`:

```powershell
kairos config list
```

Get one config value:

```powershell
kairos config get KAIROS_STORAGE
```

Set one config value:

```powershell
kairos config set KAIROS_STORAGE mongodb
kairos config set KAIROS_MONGODB_DATABASE kairos
kairos config set KAIROS_MONGODB_COLLECTION state
```

Supported config keys:

```powershell
KAIROS_DATA_DIR
KAIROS_MONGODB_COLLECTION
KAIROS_MONGODB_DATABASE
KAIROS_MONGODB_URI
KAIROS_STORAGE
KAIROS_VAULT_DIR
```

## Installation And Update

Install Kairos as a user-level CLI from the repo:

```powershell
cd C:\Users\prash\projects\kairos
python -m pip install --user .
```

After code changes, reinstall/update the user-level command:

```powershell
cd C:\Users\prash\projects\kairos
python -m pip install --user . --upgrade
```

Kairos independent config and local fallback data live here:

```powershell
C:\Users\prash\.kairos
```

The global launcher currently lives here:

```powershell
C:\Users\prash\.local\bin\kairos.cmd
```

## Useful Help

Show all top-level commands:

```powershell
kairos --help
kairos -h
kairos -help
```

Show help for a command group:

```powershell
kairos goal --help
kairos today --help
kairos focus --help
```

Show help for focus start:

```powershell
kairos focus start --help
```
