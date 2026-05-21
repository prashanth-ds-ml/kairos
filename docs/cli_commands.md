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

## Quick Guide

Start Kairos:

```powershell
kairos
```

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

`kairos` and `kairos home` show the command center: season, discipline progress, XP-style completed minutes, today's plan count, next focus target, completed work for today, and fast commands.

## Daily Use

Show current storage, season, today's commitments, focus minutes, completed work grouped by priority/goal/task, and next action:

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

Show today's commitments and next focus target:

```powershell
kairos today
```

Plan 1-3 commitments for today:

```powershell
kairos today plan
```

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

## Focus Timer

Start a focus timer for a planned or active task:

```powershell
kairos focus start
```

Start a 25-minute focus timer for target number 1:

```powershell
kairos focus start --target 1 --minutes 25
```

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
