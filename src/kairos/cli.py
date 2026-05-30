from __future__ import annotations

import argparse
from importlib.metadata import PackageNotFoundError, version
import os
import shlex
import shutil
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Optional
from typing import Sequence

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import typer

from .storage import (
    CurrentSeason,
    FocusSession,
    Goal,
    JsonStore,
    MongoStore,
    QUESTION_BANK,
    Task,
    TodayPlan,
    TodayPlanItem,
    create_store,
)


APP_NAME = "kairos"
DEFAULT_VERSION = "0.1.0"
console = Console()
HELP_OPTION_NAMES = ["-h", "--help"]
app = typer.Typer(
    add_completion=True,
    context_settings={"help_option_names": HELP_OPTION_NAMES},
    help="CLI-first Kairos workflow.",
    no_args_is_help=False,
    rich_markup_mode="rich",
)
goal_app = typer.Typer(context_settings={"help_option_names": HELP_OPTION_NAMES}, help="Create and list goals.", rich_markup_mode="rich")
goals_app = typer.Typer(context_settings={"help_option_names": HELP_OPTION_NAMES}, help="Alias for goal.", rich_markup_mode="rich")
today_app = typer.Typer(context_settings={"help_option_names": HELP_OPTION_NAMES}, help="Show or plan today's commitments.", rich_markup_mode="rich")
season_app = typer.Typer(context_settings={"help_option_names": HELP_OPTION_NAMES}, help="Show or create the current 21-day season.", rich_markup_mode="rich")
focus_app = typer.Typer(context_settings={"help_option_names": HELP_OPTION_NAMES}, help="Run and log focus sessions.", rich_markup_mode="rich")
task_app = typer.Typer(context_settings={"help_option_names": HELP_OPTION_NAMES}, help="Update and review tasks.", rich_markup_mode="rich")
brain_app = typer.Typer(context_settings={"help_option_names": HELP_OPTION_NAMES}, help="Sync and inspect Brain memory.", rich_markup_mode="rich")
setup_app = typer.Typer(context_settings={"help_option_names": HELP_OPTION_NAMES}, help="Configure local launch helpers.", rich_markup_mode="rich")
config_app = typer.Typer(context_settings={"help_option_names": HELP_OPTION_NAMES}, help="Read and write Kairos user config.", rich_markup_mode="rich")

app.add_typer(goal_app, name="goal")
app.add_typer(goals_app, name="goals")
app.add_typer(today_app, name="today")
app.add_typer(season_app, name="season")
app.add_typer(focus_app, name="focus")
app.add_typer(task_app, name="task")
app.add_typer(brain_app, name="brain")
app.add_typer(setup_app, name="setup")
app.add_typer(config_app, name="config")
LOCAL_ENV_KEYS = {
    "KAIROS_DATA_DIR",
    "KAIROS_MONGODB_COLLECTION",
    "KAIROS_MONGODB_DATABASE",
    "KAIROS_MONGODB_URI",
    "KAIROS_STORAGE",
    "KAIROS_VAULT_DIR",
}


def main(argv: Sequence[str] | None = None) -> int:
    configure_output()
    load_local_env()
    raw_args = list(sys.argv[1:] if argv is None else argv)
    raw_args = normalize_help_args(raw_args)
    if not raw_args:
        run_interactive(refresh_store(open_store()))
        return 0
    return run_typer(raw_args)


def run_typer(raw_args: list[str]) -> int:
    try:
        app(args=raw_args, prog_name="kairos", standalone_mode=False)
    except typer.Exit as exc:
        return int(exc.exit_code or 0)
    except typer.Abort:
        return 130
    except click.ClickException as exc:
        exc.show()
        return int(exc.exit_code)
    return 0


def run_interactive(store: JsonStore) -> None:
    store = run_startup_day_flow(store)
    print_home(store)
    while True:
        try:
            raw = input("\nkairos> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("")
            return
        if not raw:
            continue
        if raw in {"exit", "quit", "q"}:
            return
        if raw in {"help", "?"}:
            print_interactive_help()
            continue
        if raw in {"quickstart", "guide"}:
            print_quickstart()
            continue
        if raw in {"refresh", "reload", "sync", "home"}:
            store = refresh_store(open_store())
            print_home(store)
            continue
        try:
            args = shlex.split(raw)
        except ValueError as exc:
            print(f"Could not parse command: {exc}")
            continue
        if args and args[0] == "kairos":
            args = args[1:]
        args = normalize_help_args(args)
        args = normalize_interactive_args(args)
        try:
            exit_code = main(args)
            if exit_code:
                print(f"Command failed: {exit_code}")
        except SystemExit as exc:
            if exc.code not in {0, None}:
                print(f"Command failed: {exc}")


def print_interactive_help() -> None:
    table = Table(title="Kairos Commands", header_style="bold cyan")
    table.add_column("Command", style="bold")
    table.add_column("Purpose")
    rows = [
        ("status", "Show current state"),
        ("refresh / reload / home", "Reload storage and redraw command center"),
        ("quickstart", "Show the focus workflow guide"),
        ("daily", "Run daily check-in"),
        ("goal create / create goal", "Create a goal"),
        ("goal task add / add task", "Add tasks to an existing goal"),
        ("goal task status / update task", "Pick a task and set todo, doing, done, on hold, or blocked"),
        ("goal list / goals list", "List goals"),
        ("today", "Show today"),
        ("today plan", "Choose commitments"),
        ("today flow", "Use flow mode and record work as it happens"),
        ("today add / add flow", "Capture a work or personal task during flow mode"),
        ("focus start", "Start a timer"),
        ("task done / task hold / task block", "Update a task using a number or stable t:ref"),
        ("brain sync", "Write Brain markdown files into the vault"),
        ("shutdown", "Close the day and seed tomorrow"),
        ("season", "Show current season"),
        ("season update / update season", "Change season fields with a reason"),
        ("doctor", "Check install/config"),
        ("paths", "Show files and install paths"),
        ("config list", "Show config"),
        ("exit", "Leave Kairos"),
    ]
    for command, purpose in rows:
        table.add_row(command, purpose)
    console.print(table)


def normalize_interactive_args(args: list[str]) -> list[str]:
    if not args:
        return args
    normalized = [item.lower() for item in args]
    prefix_aliases = {
        ("create", "goal"): ["goal", "create"],
        ("new", "goal"): ["goal", "create"],
        ("add", "goal"): ["goal", "create"],
        ("list", "goal"): ["goal", "list"],
        ("list", "goals"): ["goals", "list"],
        ("show", "goals"): ["goals", "list"],
        ("show", "goal"): ["goal", "list"],
        ("plan", "today"): ["today", "plan"],
        ("flow", "today"): ["today", "flow"],
        ("go", "flow"): ["today", "flow"],
        ("add", "flow"): ["today", "add"],
        ("flow", "task"): ["today", "add"],
        ("add", "work"): ["today", "add", "--domain", "work"],
        ("add", "personal"): ["today", "add", "--domain", "personal"],
        ("start", "focus"): ["focus", "start"],
        ("add", "task"): ["goal", "task", "add"],
        ("create", "task"): ["goal", "task", "add"],
        ("new", "task"): ["goal", "task", "add"],
        ("update", "task"): ["goal", "task", "status"],
        ("set", "task"): ["goal", "task", "status"],
        ("complete", "task"): ["goal", "task", "status", "--status", "done"],
        ("finish", "task"): ["goal", "task", "status", "--status", "done"],
        ("hold", "task"): ["goal", "task", "status", "--status", "on_hold"],
        ("block", "task"): ["goal", "task", "status", "--status", "blocked"],
        ("shutdown", "day"): ["shutdown"],
        ("close", "day"): ["shutdown"],
        ("create", "season"): ["season", "create"],
        ("new", "season"): ["season", "create"],
        ("set", "season"): ["season", "create"],
        ("update", "season"): ["season", "update"],
        ("edit", "season"): ["season", "update"],
        ("change", "season"): ["season", "update"],
    }
    for prefix, mapped in prefix_aliases.items():
        if tuple(normalized[: len(prefix)]) == prefix:
            return mapped + args[len(prefix):]
    aliases = {
        ("goals",): ["goals", "list"],
        ("goal",): ["goal", "list"],
        ("focus",): ["focus", "start"],
    }
    mapped = aliases.get(tuple(normalized))
    if mapped is not None:
        return mapped
    return args


def normalize_help_args(args: list[str]) -> list[str]:
    return ["--help" if arg == "-help" else arg for arg in args]


def print_quickstart() -> None:
    table = Table(title="Quick Start", header_style="bold cyan")
    table.add_column("Step", justify="right", style="bold")
    table.add_column("Command", style="bold")
    table.add_column("What it does")
    rows = [
        ("1", "daily", "Answer 3-5 questions for today"),
        ("2", "goal create", "Create a goal and first tasks"),
        ("3", "goals list", "Review active goals and task numbers"),
        ("4", "today plan", "Choose 1-3 commitments for today"),
        ("5", "focus start", "Start the timer for the next commitment"),
        ("6", "status", "Check progress and completed work"),
    ]
    for row in rows:
        table.add_row(*row)
    console.print(table)
    console.print(
        Panel(
            "[bold]Fast path[/bold]\n"
            "goal create\n"
            "today plan\n"
            "focus start\n\n"
            "[bold]One-shot examples[/bold]\n"
            "kairos goal create --title \"Learn LangChain\" --category learning --priority P1 --task \"Watch lesson 1\"\n"
            "kairos today plan --items 1 --clear\n"
            "kairos focus start --target 1 --minutes 25",
            title="Examples",
            border_style="cyan",
        )
    )


def configure_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            continue


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kairos",
        description="CLI-first Kairos workflow over the same storage as the web app.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {package_version()}")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("home", help="Show the Kairos home screen.")
    subparsers.add_parser("status", help="Show storage, season, today, focus, and completed work.")
    subparsers.add_parser("doctor", help="Check install, config, storage, and launch health.")
    subparsers.add_parser("paths", help="Show important Kairos paths.")
    subparsers.add_parser("season", help="Show the current 21-day season.")
    shutdown = subparsers.add_parser("shutdown", help="Close the day and seed tomorrow.")
    shutdown.add_argument("--summary")
    shutdown.add_argument("--carry")
    shutdown.add_argument("--tomorrow")

    today = subparsers.add_parser("today", help="Show or plan today's commitments.")
    today_sub = today.add_subparsers(dest="today_command")
    today_sub.add_parser("show", help="Show today's commitments.")
    today_plan = today_sub.add_parser("plan", help="Choose one to three goals/tasks for today.")
    today_plan.add_argument("--items", help="Comma-separated candidate numbers to add, for example 1,3.")
    today_plan.add_argument("--clear", action="store_true", help="Clear today's plan before adding choices.")

    goal = subparsers.add_parser("goal", help="Create and list goals.")
    goal_sub = goal.add_subparsers(dest="goal_command", required=True)
    goal_sub.add_parser("list", help="List active goals and tasks.")
    goal_create = goal_sub.add_parser("create", help="Create a goal.")
    goal_create.add_argument("--title")
    goal_create.add_argument("--category", default="career")
    goal_create.add_argument("--priority", default="P3", choices=["P1", "P2", "P3", "P4", "P5"])
    goal_create.add_argument("--target-date")
    goal_create.add_argument("--notes")
    goal_create.add_argument("--task", action="append", default=[])
    goal_task = goal_sub.add_parser("task", help="Manage tasks for a goal.")
    goal_task_sub = goal_task.add_subparsers(dest="goal_task_command", required=True)
    goal_task_add = goal_task_sub.add_parser("add", help="Add one or more tasks to an existing goal.")
    goal_task_add.add_argument("--goal", type=int, help="Goal number from goals list.")
    goal_task_add.add_argument("--goal-id", help="Goal id.")
    goal_task_add.add_argument("--task", action="append", default=[], help="Task title. Repeat for multiple tasks.")
    goal_task_status = goal_task_sub.add_parser("status", help="Update task status.")
    goal_task_status.add_argument("--goal", type=int, help="Goal number from goals list.")
    goal_task_status.add_argument("--goal-id", help="Goal id.")
    goal_task_status.add_argument("--task-number", "--task-no", "--task", dest="task_number")
    goal_task_status.add_argument("--status")
    goal_task_status.add_argument("--reason")
    goal_task_status.add_argument("--review-date")

    task = subparsers.add_parser("task", help="Update task status quickly.")
    task.add_argument("action", nargs="?", default="status", help="status, done, hold, block, doing, or todo.")
    task.add_argument("--task-number", "--task-no", "--task", dest="task_number")
    task.add_argument("--goal", type=int, help="Goal number from goals list.")
    task.add_argument("--goal-id", help="Goal id.")
    task.add_argument("--status")
    task.add_argument("--reason")
    task.add_argument("--review-date")

    focus = subparsers.add_parser("focus", help="Run and log focus sessions.")
    focus_sub = focus.add_subparsers(dest="focus_command", required=True)
    focus_start = focus_sub.add_parser("start", help="Start a timer for a planned or active task.")
    focus_start.add_argument("--target", type=int, help="Candidate number from the focus list.")
    focus_start.add_argument("--minutes", type=int, help="Timer length. Defaults to app settings.")
    focus_start.add_argument("--no-timer", action="store_true", help="Skip countdown and log immediately.")
    focus_start.add_argument("--status", choices=["completed", "partial", "blocked"])
    focus_start.add_argument("--notes")
    focus_start.add_argument("--friction")

    daily = subparsers.add_parser("daily", help="Run the 3-5 question daily check-in.")
    daily.add_argument("--dry-run", action="store_true", help="Show questions without saving answers.")

    setup = subparsers.add_parser("setup", help="Configure local launch helpers.")
    setup_sub = setup.add_subparsers(dest="setup_command", required=True)
    setup_sub.add_parser("startup", help="Create a Windows startup launcher for kairos daily.")

    config = subparsers.add_parser("config", help="Read and write Kairos user config.")
    config_sub = config.add_subparsers(dest="config_command", required=True)
    config_sub.add_parser("list", help="List Kairos config values.")
    config_get = config_sub.add_parser("get", help="Get one config value.")
    config_get.add_argument("key")
    config_set = config_sub.add_parser("set", help="Set one config value in the Kairos user config.")
    config_set.add_argument("key")
    config_set.add_argument("value")
    return parser


def package_version() -> str:
    try:
        return version(APP_NAME)
    except PackageNotFoundError:
        return DEFAULT_VERSION


@app.callback(invoke_without_command=True)
def cli_callback(
    ctx: typer.Context,
    version_flag: bool = typer.Option(False, "--version", help="Show Kairos version and exit."),
) -> None:
    if version_flag:
        console.print(f"kairos {package_version()}")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        print_home(open_store())
        raise typer.Exit()


@app.command("home")
def home_command() -> None:
    """Show the Kairos home screen."""
    print_home(refresh_store(open_store()))


@app.command("refresh")
def refresh_command() -> None:
    """Reload storage and show the Kairos command center."""
    print_home(refresh_store(open_store()))


@app.command("status")
def status_command() -> None:
    """Show storage, season, today, focus, and completed work."""
    print_status(open_store())


@app.command("doctor")
def doctor_command() -> None:
    """Check install, config, storage, and launch health."""
    print_doctor(open_store())


@app.command("paths")
def paths_command() -> None:
    """Show important Kairos paths."""
    print_paths()


@season_app.callback(invoke_without_command=True)
def season_callback(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        print_season(open_store())
        raise typer.Exit()


@season_app.command("show")
def season_show_command() -> None:
    """Show the current 21-day season."""
    print_season(open_store())


@season_app.command("create")
def season_create_command(
    title: Optional[str] = typer.Option(None, "--title", help="Season title."),
    goal: Optional[int] = typer.Option(None, "--goal", help="Goal number from goals list to validate."),
    goal_id: Optional[str] = typer.Option(None, "--goal-id", help="Goal id to validate."),
    primary: Optional[str] = typer.Option(None, "--primary", help="Primary track."),
    start_date: Optional[str] = typer.Option(None, "--start-date", help="Start date, YYYY-MM-DD."),
    end_date: Optional[str] = typer.Option(None, "--end-date", help="End date, YYYY-MM-DD."),
    daily_minimum: Optional[int] = typer.Option(None, "--daily-minimum", help="Daily minimum minutes."),
    weekly_target: Optional[int] = typer.Option(None, "--weekly-target", help="Weekly target minutes."),
    success: Optional[str] = typer.Option(None, "--success", help="Success criteria."),
    constraints: Optional[str] = typer.Option(None, "--constraints", help="Constraints."),
    paused: Optional[str] = typer.Option(None, "--paused", help="Paused goals."),
    review_question: Optional[str] = typer.Option(None, "--review-question", help="Day-21 review question."),
) -> None:
    """Create or replace the current 21-day season."""
    create_season(
        open_store(),
        title=title,
        goal_number=goal,
        goal_id=goal_id,
        primary=primary,
        start_date_text=start_date,
        end_date_text=end_date,
        daily_minimum=daily_minimum,
        weekly_target=weekly_target,
        success=success,
        constraints=constraints,
        paused=paused,
        review_question=review_question,
    )


@season_app.command("update")
def season_update_command(
    reason: Optional[str] = typer.Option(None, "--reason", help="Why this season is changing. Required."),
    title: Optional[str] = typer.Option(None, "--title", help="Season title."),
    goal: Optional[int] = typer.Option(None, "--goal", help="Goal number from goals list to validate."),
    goal_id: Optional[str] = typer.Option(None, "--goal-id", help="Goal id to validate."),
    primary: Optional[str] = typer.Option(None, "--primary", help="Primary track."),
    support: Optional[str] = typer.Option(None, "--support", help="Support track."),
    start_date: Optional[str] = typer.Option(None, "--start-date", help="Start date, YYYY-MM-DD."),
    end_date: Optional[str] = typer.Option(None, "--end-date", help="End date, YYYY-MM-DD."),
    daily_minimum: Optional[int] = typer.Option(None, "--daily-minimum", help="Daily minimum minutes."),
    weekly_target: Optional[int] = typer.Option(None, "--weekly-target", help="Weekly target minutes."),
    success: Optional[str] = typer.Option(None, "--success", help="Success criteria."),
    constraints: Optional[str] = typer.Option(None, "--constraints", help="Constraints."),
    paused: Optional[str] = typer.Option(None, "--paused", help="Paused goals."),
    review_question: Optional[str] = typer.Option(None, "--review-question", help="Day-21 review question."),
    status: Optional[str] = typer.Option(None, "--status", help="active, paused, completed, or cancelled."),
) -> None:
    """Update the current season and record why it changed."""
    update_season(
        open_store(),
        reason=reason,
        title=title,
        goal_number=goal,
        goal_id=goal_id,
        primary=primary,
        support=support,
        start_date_text=start_date,
        end_date_text=end_date,
        daily_minimum=daily_minimum,
        weekly_target=weekly_target,
        success=success,
        constraints=constraints,
        paused=paused,
        review_question=review_question,
        status=status,
    )


@app.command("daily")
def daily_command(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show questions without saving answers."),
) -> None:
    """Run the 3-5 question daily check-in."""
    run_daily_checkin(open_store(), dry_run=dry_run)


@app.command("shutdown")
def shutdown_command(
    summary: Optional[str] = typer.Option(None, "--summary", help="What happened today."),
    carry: Optional[str] = typer.Option(None, "--carry", help="What should be carried forward."),
    tomorrow: Optional[str] = typer.Option(None, "--tomorrow", help="First useful move for tomorrow."),
) -> None:
    """Close the day and seed tomorrow."""
    run_shutdown(open_store(), summary=summary, carry=carry, tomorrow=tomorrow)


@goal_app.command("list")
@goals_app.command("list")
def goal_list_command() -> None:
    """List active goals and tasks."""
    print_goal_list(open_store())


@goal_app.command("create")
@goals_app.command("create")
def goal_create_command(
    title: Optional[str] = typer.Option(None, "--title", help="Goal title."),
    category: str = typer.Option("career", "--category", help="Life area/category."),
    priority: str = typer.Option("P3", "--priority", help="Priority: P1-P5."),
    target_date: Optional[str] = typer.Option(None, "--target-date", help="Target date, YYYY-MM-DD."),
    notes: Optional[str] = typer.Option(None, "--notes", help="Goal notes."),
    task: list[str] = typer.Option([], "--task", help="Initial task. Repeat for multiple tasks."),
) -> None:
    """Create a goal."""
    if priority not in {"P1", "P2", "P3", "P4", "P5"}:
        raise typer.BadParameter("priority must be one of P1, P2, P3, P4, P5")
    args = SimpleNamespace(
        goal_command="create",
        title=title,
        category=category,
        priority=priority,
        target_date=target_date,
        notes=notes,
        task=task,
    )
    handle_goal(args, open_store())


@goal_app.command("add-task")
@goals_app.command("add-task")
def goal_add_task_command(
    goal: Optional[int] = typer.Option(None, "--goal", help="Goal number from goals list."),
    goal_id: Optional[str] = typer.Option(None, "--goal-id", help="Goal id."),
    task: list[str] = typer.Option([], "--task", help="Task title. Repeat for multiple tasks."),
) -> None:
    """Add one or more tasks to an existing goal."""
    args = SimpleNamespace(
        goal_command="task",
        goal_task_command="add",
        goal=goal,
        goal_id=goal_id,
        task_number=None,
        status=None,
        task=task,
    )
    handle_goal(args, open_store())


@goal_app.command("task")
@goals_app.command("task")
def goal_task_command(
    action: str = typer.Argument("add", help="Task action: add or status."),
    goal: Optional[int] = typer.Option(None, "--goal", help="Goal number from goals list."),
    goal_id: Optional[str] = typer.Option(None, "--goal-id", help="Goal id."),
    task_number: Optional[str] = typer.Option(None, "--task-number", "--task-no", help="Task number, for example 1.2."),
    status: Optional[str] = typer.Option(None, "--status", help="todo, doing, done, completed, on-hold, or blocked."),
    reason: Optional[str] = typer.Option(None, "--reason", help="Why this task changed status."),
    review_date: Optional[str] = typer.Option(None, "--review-date", help="Review date for held/blocked tasks."),
    task: list[str] = typer.Option([], "--task", help="Task title. Repeat for multiple tasks."),
) -> None:
    """Manage tasks for a goal."""
    normalized_action = normalize_task_action(action)
    if normalized_action not in {"add", "status"}:
        raise typer.BadParameter("task action must be add or status")
    args = SimpleNamespace(
        goal_command="task",
        goal_task_command=normalized_action,
        goal=goal,
        goal_id=goal_id,
        task_number=task_number,
        status=status,
        reason=reason,
        review_date=review_date,
        task=task,
    )
    handle_goal(args, open_store())


@task_app.command("status")
def task_status_command(
    task_number: Optional[str] = typer.Option(None, "--task-number", "--task-no", "--task", help="Task number or stable t:ref."),
    status: Optional[str] = typer.Option(None, "--status", help="todo, doing, done, on-hold, or blocked."),
    goal: Optional[int] = typer.Option(None, "--goal", help="Goal number from goals list."),
    goal_id: Optional[str] = typer.Option(None, "--goal-id", help="Goal id."),
    reason: Optional[str] = typer.Option(None, "--reason", help="Why this task changed status."),
    review_date: Optional[str] = typer.Option(None, "--review-date", help="Review date for held/blocked tasks."),
) -> None:
    """Update a task status."""
    update_task_status_from_cli(open_store(), goal, goal_id, task_number, status, reason, review_date)


@task_app.command("done")
def task_done_command(
    task_number: Optional[str] = typer.Option(None, "--task-number", "--task-no", "--task", help="Task number or stable t:ref."),
) -> None:
    """Mark a task done."""
    update_task_status_from_cli(open_store(), None, None, task_number, "done")


@task_app.command("hold")
def task_hold_command(
    task_number: Optional[str] = typer.Option(None, "--task-number", "--task-no", "--task", help="Task number or stable t:ref."),
    reason: Optional[str] = typer.Option(None, "--reason", help="Why this is on hold."),
    review_date: Optional[str] = typer.Option(None, "--review-date", help="Review date, YYYY-MM-DD."),
) -> None:
    """Put a task on hold."""
    update_task_status_from_cli(open_store(), None, None, task_number, "on_hold", reason, review_date)


@task_app.command("block")
def task_block_command(
    task_number: Optional[str] = typer.Option(None, "--task-number", "--task-no", "--task", help="Task number or stable t:ref."),
    reason: Optional[str] = typer.Option(None, "--reason", help="What is blocking this."),
    review_date: Optional[str] = typer.Option(None, "--review-date", help="Review date, YYYY-MM-DD."),
) -> None:
    """Mark a task blocked."""
    update_task_status_from_cli(open_store(), None, None, task_number, "blocked", reason, review_date)


@task_app.command("doing")
def task_doing_command(
    task_number: Optional[str] = typer.Option(None, "--task-number", "--task-no", "--task", help="Task number or stable t:ref."),
) -> None:
    """Mark a task in progress."""
    update_task_status_from_cli(open_store(), None, None, task_number, "in_progress")


@task_app.command("todo")
def task_todo_command(
    task_number: Optional[str] = typer.Option(None, "--task-number", "--task-no", "--task", help="Task number or stable t:ref."),
) -> None:
    """Move a task back to todo."""
    update_task_status_from_cli(open_store(), None, None, task_number, "todo")


@brain_app.command("sync")
def brain_sync_command() -> None:
    """Write Brain markdown files into the configured vault."""
    sync_brain_to_vault_cli(open_store())


@brain_app.command("rebuild")
def brain_rebuild_command() -> None:
    """Regenerate observations and inferred patterns from raw Kairos data."""
    rebuild_personal_brain_cli(open_store())


@brain_app.command("status")
def brain_status_command() -> None:
    """Show Brain answer/memory counts and vault path."""
    print_brain_status(open_store())


@today_app.callback(invoke_without_command=True)
def today_callback(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        print_today(open_store())
        raise typer.Exit()


@today_app.command("show")
def today_show_command() -> None:
    """Show today's commitments."""
    print_today(open_store())


@today_app.command("plan")
def today_plan_command(
    items: Optional[str] = typer.Option(None, "--items", help="Comma-separated candidate numbers, for example 1,3."),
    clear: bool = typer.Option(False, "--clear", help="Clear today's plan first."),
) -> None:
    """Choose one to three goals/tasks for today."""
    plan_today(open_store(), items, clear)


@today_app.command("flow")
def today_flow_command() -> None:
    """Use flow mode: pick focus targets as work happens."""
    store = open_store()
    set_today_plan_mode(store, "flow")
    print_today(store)


@today_app.command("add")
def today_add_command(
    title: Optional[str] = typer.Option(None, "--title", "-t", help="Task title."),
    domain: str = typer.Option("work", "--domain", help="work or personal."),
    category: str = typer.Option("career", "--category", "--area", help="Life area/category."),
    commit: bool = typer.Option(False, "--commit", help="Also add this task to today's planned commitments."),
    start: bool = typer.Option(False, "--start", help="Print the focus command to start this task next."),
) -> None:
    """Capture a flow-mode task with work/personal domain and category."""
    add_flow_task(open_store(), title=title, domain=domain, category=category, commit=commit, start=start)


@focus_app.command("start")
def focus_start_command(
    target: Optional[int] = typer.Option(None, "--target", help="Candidate number from the focus list."),
    minutes: Optional[int] = typer.Option(None, "--minutes", help="Timer length. Defaults to app settings."),
    no_timer: bool = typer.Option(False, "--no-timer", help="Skip countdown and log immediately."),
    status: Optional[str] = typer.Option(None, "--status", help="completed, partial, or blocked."),
    notes: Optional[str] = typer.Option(None, "--notes", help="What got done."),
    friction: Optional[str] = typer.Option(None, "--friction", help="Friction or blocker."),
) -> None:
    """Start a timer for a planned or active task."""
    if status is not None and status not in {"completed", "partial", "blocked"}:
        raise typer.BadParameter("status must be completed, partial, or blocked")
    args = SimpleNamespace(
        focus_command="start",
        target=target,
        minutes=minutes,
        no_timer=no_timer,
        status=status,
        notes=notes,
        friction=friction,
    )
    start_focus(open_store(), args)


@setup_app.command("startup")
def setup_startup_command() -> None:
    """Create a Windows startup launcher for kairos daily."""
    create_startup_launcher()


@config_app.command("list")
def config_list_command() -> None:
    """List Kairos config values."""
    handle_config(SimpleNamespace(config_command="list"))


@config_app.command("get")
def config_get_command(key: str) -> None:
    """Get one config value."""
    handle_config(SimpleNamespace(config_command="get", key=key))


@config_app.command("set")
def config_set_command(key: str, value: str) -> None:
    """Set one config value."""
    handle_config(SimpleNamespace(config_command="set", key=key, value=value))


def handle_goal(args: argparse.Namespace, store: JsonStore) -> int:
    if args.goal_command == "list":
        print_goal_list(store)
        return 0
    if args.goal_command == "create":
        interactive = args.title is None
        title = args.title or prompt_required("Goal title")
        category = args.category if not interactive else prompt_default("Area/category", args.category)
        priority = args.priority if not interactive else prompt_default("Priority", args.priority)
        target_date = args.target_date or (prompt_optional("Target date (YYYY-MM-DD, blank for none)") if interactive else "")
        notes = args.notes if args.notes is not None else (prompt_optional("Notes") if interactive else "")
        tasks = list(args.task)
        if not tasks and interactive:
            raw_tasks = prompt_optional("First tasks (comma-separated)")
            tasks = [item.strip() for item in raw_tasks.split(",") if item.strip()]
        goal = store.add_goal(title, category, priority, target_date or None, notes or "", tasks)
        print(f"Created goal: {goal.title}")
        if goal.tasks:
            print(f"Tasks: {len(goal.tasks)}")
        return 0
    if args.goal_command == "task" and args.goal_task_command == "add":
        add_tasks_to_goal(store, args.goal, args.goal_id, args.task)
        return 0
    if args.goal_command == "task" and args.goal_task_command == "status":
        update_task_status_from_cli(
            store,
            args.goal,
            args.goal_id,
            args.task_number,
            args.status,
            getattr(args, "reason", None),
            getattr(args, "review_date", None),
        )
        return 0
    return 2


def normalize_task_action(action: str) -> str:
    aliases = {
        "set": "status",
        "update": "status",
        "status": "status",
        "complete": "status",
        "finish": "status",
        "hold": "status",
        "block": "status",
    }
    return aliases.get(action.strip().lower(), action.strip().lower())


def add_tasks_to_goal(store: JsonStore, goal_number: int | None, goal_id: str | None, task_titles: list[str]) -> None:
    goals = sorted_goals([goal for goal in store.load_goals() if goal.status == "active"])
    if not goals:
        console.print("[yellow]No active goals yet. Create one with `goal create`.[/yellow]")
        return

    goal = resolve_goal_for_task_add(goals, goal_number, goal_id)
    if goal is None:
        console.print("[dim]Task add cancelled.[/dim]")
        return

    tasks = normalize_task_titles(task_titles)
    if not tasks:
        raw_tasks = prompt_optional("New tasks (comma-separated)")
        tasks = normalize_task_titles([raw_tasks])
    if not tasks:
        console.print("[yellow]No tasks added.[/yellow]")
        return

    added = [store.add_task(goal.id, task_title) for task_title in tasks]
    console.print(f"Added {len(added)} task(s) to [bold]{goal.title}[/bold]:")
    for task in added:
        console.print(f"- {task.title}")


def add_flow_task(
    store: JsonStore,
    title: str | None,
    domain: str,
    category: str,
    commit: bool = False,
    start: bool = False,
) -> Task:
    title = title or prompt_required("Task title")
    domain = normalize_flow_domain(domain)
    category = normalize_flow_category(category)
    goal = find_or_create_flow_goal(store, domain, category)
    task = store.add_task(goal.id, title)
    plan = store.load_today_plan()
    if plan.mode != "flow":
        set_today_plan_mode(store, "flow")
    if commit:
        store.add_today_plan_item(goal.id, task.id)
        set_today_plan_mode(store, "planned")
    console.print(
        f"[green]Captured {domain} task in {category}: {task.title}[/green]\n"
        f"[dim]Goal: {goal.title}[/dim]"
    )
    print_ascii_stamp("captured")
    if start:
        target_index = focus_target_index_for_today(store, goal.id, task.id)
        if target_index is not None:
            console.print(f"[bold]Start command:[/bold] kairos focus start --target {target_index}")
        else:
            console.print("[bold]Start command:[/bold] kairos focus")
    return task


def find_or_create_flow_goal(store: JsonStore, domain: str, category: str) -> Goal:
    title = flow_goal_title(domain, category)
    goals = store.load_goals()
    existing = next((goal for goal in goals if goal.status == "active" and goal.title == title), None)
    if existing is not None:
        return existing
    notes = (
        f"Flow capture bucket. Domain: {domain}. Category: {category}. "
        "Used for ad-hoc tasks captured during flexible days."
    )
    return store.add_goal(title, category, "P3", None, notes, [])


def flow_goal_title(domain: str, category: str) -> str:
    return f"Flow {domain.title()}: {category.replace('_', ' ').title()}"


def normalize_flow_domain(domain: str) -> str:
    normalized = domain.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "office": "work",
        "job": "work",
        "career": "work",
        "work": "work",
        "personal": "personal",
        "life": "personal",
        "home": "personal",
        "self": "personal",
    }
    mapped = aliases.get(normalized)
    if mapped is None:
        raise typer.BadParameter("domain must be work or personal")
    return mapped


def normalize_flow_category(category: str) -> str:
    normalized = category.strip().lower().replace("-", "_").replace(" ", "_")
    if not normalized:
        return "career"
    return normalized


def update_task_status_from_cli(
    store: JsonStore,
    goal_number: int | None,
    goal_id: str | None,
    task_number: str | None,
    raw_status: str | None,
    reason: str | None = None,
    review_date: str | None = None,
) -> None:
    tasks = task_status_candidates(store.load_goals())
    if not tasks:
        console.print("[yellow]No tasks found. Add one with `goal task add`.[/yellow]")
        return

    selected = resolve_task_for_status(tasks, goal_number, goal_id, task_number)
    if selected is None:
        console.print("[dim]Task status update cancelled.[/dim]")
        return

    status = normalize_task_status(raw_status or ask_task_status())
    if status is None:
        console.print("[dim]Task status update cancelled.[/dim]")
        return
    if status in {"blocked", "on_hold"}:
        reason = reason if reason is not None else prompt_optional("Reason")
        review_date = review_date if review_date is not None else prompt_optional("Review date (YYYY-MM-DD, blank for none)")

    goal, task, display_number = selected
    ref = task_ref(task)
    store.update_task_status(goal.id, task.id, status, reason or "", review_date or "")
    suffix = f" ({reason})" if reason else ""
    console.print(f"[green]Updated {display_number} ref {ref} {task.title} -> {status_label(status)}{suffix}[/green]")
    print_goal_list(store)


def task_status_candidates(goals: list[Goal]) -> list[tuple[Goal, Task, str]]:
    rows: list[tuple[Goal, Task, str]] = []
    active_goals = sorted_goals([goal for goal in goals if goal.status == "active"])
    for goal_index, goal in enumerate(active_goals, start=1):
        for task_index, task in enumerate(sorted_tasks(goal.tasks), start=1):
            rows.append((goal, task, f"{goal_index}.{task_index}"))
    return rows


def resolve_task_for_status(
    tasks: list[tuple[Goal, Task, str]],
    goal_number: int | None,
    goal_id: str | None,
    task_number: str | None,
) -> tuple[Goal, Task, str] | None:
    if task_number:
        normalized = task_number.strip()
        ref_match = task_by_ref(tasks, normalized)
        if ref_match is not None:
            return ref_match
        if "." in normalized:
            match = next((row for row in tasks if row[2] == normalized), None)
            if match is not None:
                return match
            raise SystemExit(f"Task not found: {task_number}")
        if goal_number is None and goal_id is None:
            match = task_by_flat_number(tasks, normalized)
            if match is not None:
                return match
            raise SystemExit(f"Task not found: {task_number}")

    scoped = tasks
    if goal_id:
        scoped = [row for row in tasks if row[0].id == goal_id]
    elif goal_number is not None:
        active_goals = sorted_goals([goal for goal in unique_goals_from_task_rows(tasks)])
        goal = resolve_goal_for_task_add(active_goals, goal_number, None)
        scoped = [row for row in tasks if goal is not None and row[0].id == goal.id]

    if task_number:
        try:
            task_index = int(task_number.strip())
        except ValueError:
            raise SystemExit(f"Invalid task number: {task_number}")
        if 1 <= task_index <= len(scoped):
            return scoped[task_index - 1]
        raise SystemExit(f"Task not found: {task_number}")

    print("Choose a task to update.")
    for index, (goal, task, display_number) in enumerate(tasks, start=1):
        print(f"{index}. {display_number} [{status_label(task.status)}] {goal.title}: {task.title}")
    choice = ask_single_choice("Task", 1, len(tasks))
    if choice is None:
        return None
    return tasks[choice - 1]


def unique_goals_from_task_rows(tasks: list[tuple[Goal, Task, str]]) -> list[Goal]:
    seen: set[str] = set()
    goals: list[Goal] = []
    for goal, _task, _display_number in tasks:
        if goal.id in seen:
            continue
        seen.add(goal.id)
        goals.append(goal)
    return goals


def task_by_flat_number(tasks: list[tuple[Goal, Task, str]], raw_number: str) -> tuple[Goal, Task, str] | None:
    try:
        index = int(raw_number)
    except ValueError:
        return None
    if 1 <= index <= len(tasks):
        return tasks[index - 1]
    return None


def task_by_ref(tasks: list[tuple[Goal, Task, str]], raw_ref: str) -> tuple[Goal, Task, str] | None:
    normalized = raw_ref.strip().lower()
    if normalized.startswith("t:"):
        normalized = normalized[2:]
    if not normalized:
        return None
    matches = [row for row in tasks if task_ref(row[1])[2:].lower().startswith(normalized) or row[1].id.lower().startswith(normalized)]
    if len(matches) == 1:
        return matches[0]
    return None


def ask_task_status() -> str:
    options = ["todo", "in_progress", "done", "on_hold", "blocked"]
    print("Choose status.")
    for index, status in enumerate(options, start=1):
        print(f"{index}. {status_label(status)}")
    choice = ask_single_choice("Status", 1, len(options))
    if choice is None:
        return ""
    return options[choice - 1]


def normalize_task_status(status: str) -> str | None:
    normalized = status.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "open": "todo",
        "todo": "todo",
        "to_do": "todo",
        "doing": "in_progress",
        "started": "in_progress",
        "start": "in_progress",
        "inprogress": "in_progress",
        "in_progress": "in_progress",
        "complete": "done",
        "completed": "done",
        "finish": "done",
        "finished": "done",
        "done": "done",
        "hold": "on_hold",
        "onhold": "on_hold",
        "on_hold": "on_hold",
        "paused": "on_hold",
        "blocked": "blocked",
        "block": "blocked",
    }
    mapped = aliases.get(normalized)
    if mapped is None:
        raise SystemExit("Status must be todo, doing, done, on-hold, or blocked.")
    return mapped


def status_label(status: str) -> str:
    labels = {
        "todo": "todo",
        "in_progress": "doing",
        "done": "done",
        "on_hold": "on hold",
        "blocked": "blocked",
    }
    return labels.get(status, status)


def task_ref(task: Task) -> str:
    compact_id = task.id[5:] if task.id.startswith("task-") else task.id
    return f"t:{compact_id[:6]}"


def format_task_row(goal_index: int, task_index: int, task: Task) -> str:
    parts = [f"{goal_index}.{task_index}", f"ref {task_ref(task)}", task.title, f"[{status_label(task.status)}]"]
    if task.status_reason:
        parts.append(f"- {task.status_reason}")
    if task.review_date:
        parts.append(f"(review {task.review_date})")
    return " ".join(parts)


def resolve_goal_for_task_add(goals: list[Goal], goal_number: int | None, goal_id: str | None) -> Goal | None:
    if goal_id:
        goal = find_goal_by_id(goals, goal_id)
        if goal is None:
            raise SystemExit(f"Goal not found: {goal_id}")
        return goal
    if goal_number is not None:
        if goal_number < 1 or goal_number > len(goals):
            raise SystemExit(f"Invalid goal number: {goal_number}")
        return goals[goal_number - 1]

    console.print("Choose goal to add tasks:")
    for index, goal in enumerate(goals, start=1):
        console.print(f"{index}. [{goal.priority}] {goal.title}")
    choice = ask_single_choice("Goal", 1, len(goals))
    if choice is None:
        return None
    return goals[choice - 1]


def normalize_task_titles(values: list[str]) -> list[str]:
    tasks: list[str] = []
    for value in values:
        tasks.extend(item.strip() for item in value.split(",") if item.strip())
    return tasks


def handle_today(args: argparse.Namespace, store: JsonStore) -> int:
    if args.today_command in {None, "show"}:
        print_today(store)
        return 0
    if args.today_command == "plan":
        plan_today(store, args.items, args.clear)
        return 0
    if args.today_command == "flow":
        set_today_plan_mode(store, "flow")
        print_today(store)
        return 0
    if args.today_command == "add":
        add_flow_task(
            store,
            title=getattr(args, "title", None),
            domain=getattr(args, "domain", "work"),
            category=getattr(args, "category", "career"),
            commit=getattr(args, "commit", False),
            start=getattr(args, "start", False),
        )
        return 0
    return 2


def handle_focus(args: argparse.Namespace, store: JsonStore) -> int:
    if args.focus_command == "start":
        start_focus(store, args)
        return 0
    return 2


def handle_daily(args: argparse.Namespace, store: JsonStore) -> int:
    run_daily_checkin(store, dry_run=args.dry_run)
    return 0


def handle_setup(args: argparse.Namespace) -> int:
    if args.setup_command == "startup":
        create_startup_launcher()
        return 0
    return 2


def handle_config(args: argparse.Namespace) -> int:
    values = read_user_config()
    if args.config_command == "list":
        if not values:
            print(f"No config yet. Config path: {user_env_path()}")
            return 0
        for key in sorted(values):
            print(f"{key}={display_config_value(key, values[key])}")
        return 0
    if args.config_command == "get":
        value = values.get(args.key)
        if value is None:
            raise SystemExit(f"Config key not set: {args.key}")
        print(display_config_value(args.key, value))
        return 0
    if args.config_command == "set":
        key = args.key.strip()
        if key not in LOCAL_ENV_KEYS:
            allowed = ", ".join(sorted(LOCAL_ENV_KEYS))
            raise SystemExit(f"Unsupported config key: {key}\nAllowed keys: {allowed}")
        values[key] = args.value
        write_user_config(values)
        os.environ[key] = args.value
        print(f"Set {key}")
        return 0
    return 2


def load_local_env() -> None:
    ensure_user_config_dir()
    env_path = configured_env_path()
    if env_path is None:
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().removeprefix("export ").strip()
        if key not in LOCAL_ENV_KEYS or key in os.environ:
            continue
        os.environ[key] = value.strip().strip('"').strip("'")


def configured_env_path() -> Path | None:
    explicit = os.environ.get("KAIROS_ENV_FILE", "").strip()
    if explicit:
        path = Path(explicit).expanduser()
        return path if path.exists() else None
    for candidate in [user_config_dir() / ".env", project_root() / ".env"]:
        if candidate.exists():
            return candidate
    return None


def user_env_path() -> Path:
    return user_config_dir() / ".env"


def read_user_config() -> dict[str, str]:
    path = user_env_path()
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().removeprefix("export ").strip()
        if key in LOCAL_ENV_KEYS:
            values[key] = value.strip().strip('"').strip("'")
    return values


def write_user_config(values: dict[str, str]) -> None:
    user_config_dir().mkdir(parents=True, exist_ok=True)
    lines = [f"{key}={values[key]}" for key in sorted(values)]
    user_env_path().write_text("\n".join(lines) + "\n", encoding="utf-8")


def display_config_value(key: str, value: str) -> str:
    if "TOKEN" in key or "KEY" in key or "URI" in key:
        return mask_secret(value)
    return value


def mask_secret(value: str) -> str:
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


def ensure_user_config_dir() -> None:
    user_config_dir().mkdir(parents=True, exist_ok=True)


def user_config_dir() -> Path:
    return Path(os.environ.get("KAIROS_HOME", Path.home() / ".kairos")).expanduser().resolve()


def open_store() -> JsonStore:
    return create_store(default_data_dir())


def refresh_store(store: JsonStore) -> JsonStore:
    store.load_goals()
    store.load_sessions()
    store.load_today_plan()
    store.load_current_season()
    store.load_settings()
    return store


def default_data_dir() -> Path:
    configured = os.environ.get("KAIROS_DATA_DIR", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return (user_config_dir() / "data").resolve()


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def print_home(store: JsonStore) -> None:
    goals = store.load_goals()
    sessions = store.load_sessions()
    today_plan = store.load_today_plan()
    season = store.load_current_season()
    today_sessions = sessions_for_today(sessions)
    today_items = planned_work_items(goals, today_plan.items, season)
    flow_items = today_flow_items(goals) if today_plan.mode == "flow" else []
    focus_items = focus_candidates(goals)
    flexible_day = today_plan.mode == "flow"
    today_minutes = sum(session.duration_seconds for session in today_sessions) // 60
    completed_minutes = sum(session.duration_seconds for session in today_sessions if session.status == "completed") // 60
    week_minutes = focus_minutes_this_week(sessions)
    daily_target = season.daily_minimum_minutes or 0

    print_session_header()
    console.print(
        Panel(
            "[bold cyan]KAIROS COMMAND CENTER[/bold cyan]\n"
            "[dim](⌐■_■)  choose one target, finish one block, leave evidence[/dim]",
            border_style="cyan",
        )
    )

    summary = Table.grid(padding=(0, 2))
    summary.add_column(style="bold cyan", no_wrap=True)
    summary.add_column()
    summary.add_row("Season", season_status(season))
    summary.add_row("Discipline", f"{progress_bar(today_minutes, daily_target)} {format_minutes(today_minutes)} / {format_minutes(daily_target)}")
    summary.add_row("XP", f"+{completed_minutes} today | {week_minutes} this week")
    summary.add_row("Plan", today_plan_label_for_plan(goals, today_plan, season))
    season_nudge = season_session_nudge(season, today_sessions)
    if season_nudge:
        summary.add_row("Season pact", season_nudge)
    console.print(Panel(summary, title="Now", border_style="green"))

    done_today = format_done_today_summary(goals, today_sessions)
    empty_done_message = (
        "[dim]No completed focus logged today. Choose commitments with `today plan` or use `focus` in flow mode.[/dim]"
        if not today_items and focus_items and not flexible_day
        else "[dim]No completed focus logged today. Start with `focus`.[/dim]"
    )
    console.print(
        Panel(
            done_today or empty_done_message,
            title="Done Today",
            border_style="cyan",
        )
    )
    other_logged = format_non_completed_today_summary(goals, today_sessions)
    if other_logged:
        console.print(Panel(other_logged, title="Logged Today", border_style="yellow"))

    commands = Table(title="Fast Commands", header_style="bold cyan")
    commands.add_column("Need", style="bold")
    commands.add_column("Command", style="bold green")
    commands.add_column("Purpose")
    if today_items:
        commands.add_row("Start", "focus", "Pick from today's commitments and log a block")
        commands.add_row("Plan", "today plan", "Adjust today's one to three commitments")
    elif flexible_day:
        commands.add_row("Start", "focus", "Pick any available task and record the block")
        commands.add_row("Capture", "today add", "Add a work or personal task into flow mode")
        commands.add_row("Plan", "today plan", "Switch from flow mode to one to three commitments")
    else:
        commands.add_row("Plan", "today plan", "Choose one to three commitments")
        commands.add_row("Start", "focus", "Start after today's commitments are chosen")
    commands.add_row("Create", "goal create", "Add a goal and first tasks")
    commands.add_row("Extend", "add task", "Add tasks to an existing goal")
    commands.add_row("Update", "task done --task t:xxxxxx", "Use stable task refs from goal list")
    commands.add_row("Close", "shutdown", "Review today and seed tomorrow")
    commands.add_row("Review", "status", "Check progress and completed work")
    commands.add_row("Guide", "quickstart", "Show the daily workflow")
    console.print(commands)
    console.print("[dim]Type `help` for all commands, or `exit` to leave Kairos.[/dim]")


def print_status(store: JsonStore) -> None:
    goals = store.load_goals()
    sessions = store.load_sessions()
    today_plan = store.load_today_plan()
    season = store.load_current_season()
    today_items = planned_work_items(goals, today_plan.items, season)
    flow_items = today_flow_items(goals) if today_plan.mode == "flow" else []
    focus_items = focus_candidates(goals)
    flexible_day = today_plan.mode == "flow"
    today_sessions = sessions_for_today(sessions)
    today_minutes = sum(session.duration_seconds for session in today_sessions) // 60
    season_goal = find_goal_by_id(goals, season.goal_id)
    season_minutes = season_focus_minutes_today(today_sessions, season.goal_id)

    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold cyan")
    table.add_column()
    table.add_row("Storage", storage_label(store))
    table.add_row("Data", str(default_data_dir()))
    table.add_row("Season", season_status(season))
    if season_goal is not None:
        target = f" / {season.daily_minimum_minutes} min" if season.daily_minimum_minutes else ""
        table.add_row("Season goal", f"{season_goal.title} ({season_minutes} min today{target})")
    season_nudge = season_session_nudge(season, today_sessions)
    if season_nudge:
        table.add_row("Season pact", season_nudge)
    table.add_row("Today", f"{today_plan_label_for_plan(goals, today_plan, season)}, {format_minutes(today_minutes)} focused")
    if flow_items:
        table.add_row("Captured flow", format_item_titles(flow_items, limit=3))
    done_today = format_done_today_summary(goals, today_sessions)
    if done_today:
        table.add_row("Done today", done_today)
    other_logged = format_non_completed_today_summary(goals, today_sessions)
    if other_logged:
        table.add_row("Logged today", other_logged)
    elif today_sessions and not done_today:
        table.add_row("Logged today", format_session_summary(goals, today_sessions))
    console.print(Panel(table, title="Kairos Status", border_style="cyan"))


def print_doctor(store: JsonStore) -> None:
    print("(⌐■_■) Kairos Doctor")
    print(f"Version: {package_version()}")
    print(f"Python: {sys.executable}")
    print(f"Command: {shutil.which('kairos') or 'not found on PATH'}")
    print(f"Package: {Path(__file__).resolve()}")
    print(f"Home: {user_config_dir()}")
    print(f"Config: {configured_env_path() or 'not found'}")
    print(f"Data: {default_data_dir()}")
    print(f"Storage: {storage_label(store)}")
    try:
        store.load_goals()
        store.load_today_plan()
        store.load_current_season()
        print("Storage check: ok")
    except Exception as exc:
        print(f"Storage check: failed ({exc})")
    print(f"Startup launcher: {startup_launcher_status()}")


def print_paths() -> None:
    print("Kairos Paths")
    print(f"Home: {user_config_dir()}")
    print(f"Config: {user_env_path()}")
    print(f"Data: {default_data_dir()}")
    print(f"Command: {shutil.which('kairos') or 'not found on PATH'}")
    print(f"Package: {Path(__file__).resolve()}")
    if os.name == "nt":
        print(f"Startup: {startup_launcher_path()}")


def print_goal_list(store: JsonStore) -> None:
    goals = sorted_goals(store.load_goals())
    active = [goal for goal in goals if goal.status == "active"]
    if not active:
        console.print(Panel("No active goals yet.\n\nCreate one with: [bold]goal create[/bold]", title="Active Goals"))
        return
    table = Table(title="Active Goals", header_style="bold cyan")
    table.add_column("#", justify="right", style="bold")
    table.add_column("Priority")
    table.add_column("Goal")
    table.add_column("Area")
    table.add_column("Due")
    table.add_column("Open Tasks")
    for index, goal in enumerate(active, start=1):
        tasks = [task for task in sorted_tasks(goal.tasks) if task.status != "done"]
        task_text = "\n".join(format_task_row(index, task_index, task) for task_index, task in enumerate(tasks, start=1))
        table.add_row(str(index), goal.priority, goal.title, goal.category, goal.target_date or "", task_text or "-")
    console.print(table)


def print_today(store: JsonStore) -> None:
    goals = store.load_goals()
    today_plan = store.load_today_plan()
    season = store.load_current_season()
    items = planned_work_items(goals, today_plan.items, season)
    flow_items = today_flow_items(goals) if today_plan.mode == "flow" else []
    focus_items = focus_candidates(goals)
    print(date.today().strftime("Today: %A, %d %b %Y"))
    print(f"Mode: {today_mode_label(today_plan.mode)}")
    print(f"Plan: {today_plan_label_for_plan(goals, today_plan, season)}")
    if not items:
        print("Commitments: none set")
    else:
        print("Carried commitments:" if today_plan.mode == "flow" else "Commitments:")
        for index, item in enumerate(items, start=1):
            print(f"{index}. {item['title']}")
    if flow_items:
        print("Captured today:")
        for index, item in enumerate(flow_items, start=1):
            print(f"{index}. {item['title']}")


def plan_today(store: JsonStore, raw_items: str | None, clear_first: bool) -> TodayPlan:
    goals = store.load_goals()
    season = store.load_current_season()
    candidates = commitment_candidates(goals, season)
    if not candidates:
        print("No active focus targets. Create a goal first:")
        print("kairos goal create")
        return store.load_today_plan()

    if clear_first:
        store.clear_today_plan()

    print("Choose 1-3 commitments for today.")
    for index, item in enumerate(candidates, start=1):
        marker = f" [{item['marker']}]" if item.get("marker") else ""
        print(f"{index}. {item['title']}{marker}")

    choices = parse_choice_numbers(raw_items)
    if not choices:
        choices = ask_choice_numbers("Numbers", 1, min(3, len(candidates)))
    if choices is None:
        console.print("[dim]Today planning cancelled.[/dim]")
        return store.load_today_plan()

    plan = store.load_today_plan()
    for choice in choices[:3]:
        if choice < 1 or choice > len(candidates):
            print(f"Skipping invalid choice: {choice}")
            continue
        item = candidates[choice - 1]
        plan = store.add_today_plan_item(item["goal_id"], item["task_id"] or None)
    if planned_work_items(goals, store.load_today_plan().items, season):
        set_today_plan_mode(store, "planned")

    print_today(store)
    return plan


def run_startup_day_flow(store: JsonStore) -> JsonStore:
    if not sys.stdin.isatty():
        return store
    first_open_today = not daily_log_exists_for_today(store)
    if first_open_today:
        console.print(
            Panel(
                "[bold]Today check-in[/bold]\n"
                "First open for this date. Answer the Brain prompts, then choose how to run the day.",
                border_style="green",
            )
        )
        run_daily_checkin(store, dry_run=False, show_today_after=False)
        store = refresh_store(open_store())

    today_plan = store.load_today_plan()
    if today_plan.items or today_plan.mode == "flow":
        return store
    if not focus_candidates(store.load_goals()):
        return store
    if not first_open_today:
        return store
    console.print(
        Panel(
            "[bold]Choose today's operating mode[/bold]\n"
            "Pick three commitments for a deliberate day, or go with the flow and record work as it happens.",
            border_style="green",
        )
    )
    mode = ask_day_mode()
    if mode == "planned":
        plan_today(store, raw_items=None, clear_first=True)
    elif mode == "flow":
        set_today_plan_mode(store, "flow")
        console.print("[green]Flow mode set. Use `focus` to pick any task and record the block.[/green]")
    return refresh_store(open_store())


def daily_log_exists_for_today(store: JsonStore) -> bool:
    today = date.today().isoformat()
    return any(log.log_date == today for log in store.load_daily_logs())


def ask_day_mode() -> str | None:
    options = [
        ("planned", "Pick 1-3 tasks for today"),
        ("flow", "Go with the flow and record tasks as they happen"),
    ]
    for index, (_mode, label) in enumerate(options, start=1):
        print(f"{index}. {label}")
    choice = ask_single_choice("Mode", 1, len(options))
    if choice is None:
        return None
    return options[choice - 1][0]


def set_today_plan_mode(store: JsonStore, mode: str) -> TodayPlan:
    plan = store.load_today_plan()
    plan.mode = mode
    store.save_today_plan(plan)
    return plan


def today_plan_label(items: list[dict[str, str]], mode: str) -> str:
    if mode == "flow" and not items:
        return "flow mode"
    if mode == "flow":
        return f"flow mode, {len(items)}/3 commitments selected"
    return f"{len(items)}/3 commitments selected"


def today_plan_label_for_plan(goals: list[Goal], plan: TodayPlan, season: CurrentSeason | None) -> str:
    counts = today_plan_counts(goals, plan, season)
    selected = counts["selected"]
    active = counts["active"]
    done = counts["done"]
    held = counts["on_hold"]
    blocked = counts["blocked"]
    missing = counts["missing"]
    details = []
    if done:
        details.append(f"{done} done")
    if active:
        details.append(f"{active} active")
    if held:
        details.append(f"{held} on hold")
    if blocked:
        details.append(f"{blocked} blocked")
    if missing:
        details.append(f"{missing} unavailable")
    suffix = f" ({', '.join(details)})" if details else ""
    if plan.mode == "flow" and selected == 0:
        return "flow mode"
    if plan.mode == "flow":
        return f"flow mode, {selected}/3 carried{suffix}"
    return f"{selected}/3 commitments selected{suffix}"


def today_plan_counts(goals: list[Goal], plan: TodayPlan, season: CurrentSeason | None) -> dict[str, int]:
    counts = {"selected": len(plan.items), "active": 0, "done": 0, "on_hold": 0, "blocked": 0, "missing": 0}
    by_goal = {goal.id: goal for goal in goals}
    for item in plan.items:
        if is_season_plan_item(item):
            season_item = season_focus_item(goals, season)
            if season_item is None:
                counts["missing"] += 1
            else:
                counts["active"] += 1
            continue
        goal = by_goal.get(item.goal_id)
        if goal is None or goal.status != "active":
            counts["missing"] += 1
            continue
        if not item.task_id:
            counts["active"] += 1
            continue
        task = next((task for task in goal.tasks if task.id == item.task_id), None)
        if task is None:
            counts["missing"] += 1
            continue
        if task.status in {"todo", "in_progress"}:
            counts["active"] += 1
        elif task.status in {"done", "on_hold", "blocked"}:
            counts[task.status] += 1
        else:
            counts["missing"] += 1
    return counts


def today_mode_label(mode: str) -> str:
    if mode == "flow":
        return "flow"
    if mode == "planned":
        return "planned"
    return "not chosen"


def print_season(store: JsonStore) -> None:
    season = store.load_current_season()
    goal = find_goal_by_id(store.load_goals(), season.goal_id)
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold cyan")
    table.add_column()
    table.add_row("Title", season.title or "Not set")
    table.add_row("Goal", goal.title if goal else season.primary_track or "Not linked")
    table.add_row("Status", season.status)
    table.add_row("Dates", f"{season.start_date} to {season.end_date} ({season_day_label(season)})")
    table.add_row("Why now", season.primary_track or "Not set")
    table.add_row("Daily minimum", f"{season.daily_minimum_minutes} min")
    table.add_row("Weekly target", f"{season.weekly_target_minutes} min")
    table.add_row("Success", season.success_criteria or "Not set")
    if season.change_log:
        latest = season.change_log[-1]
        table.add_row("Last change", f"{latest.get('changed_at', '')} | {latest.get('reason', '')}")
    console.print(Panel(table, title="Current Season", border_style="cyan"))


def create_season(
    store: JsonStore,
    title: str | None = None,
    goal_number: int | None = None,
    goal_id: str | None = None,
    primary: str | None = None,
    start_date_text: str | None = None,
    end_date_text: str | None = None,
    daily_minimum: int | None = None,
    weekly_target: int | None = None,
    success: str | None = None,
    constraints: str | None = None,
    paused: str | None = None,
    review_question: str | None = None,
) -> CurrentSeason:
    interactive = title is None and sys.stdin.isatty()
    today = date.today()
    default_start = today.isoformat()
    default_end = (today + timedelta(days=20)).isoformat()
    current = store.load_current_season()
    goals = [goal for goal in sorted_goals(store.load_goals()) if goal.status == "active"]
    selected_goal = resolve_season_goal(goals, goal_number, goal_id, current.goal_id, interactive)

    default_title = f"{selected_goal.title} validation" if selected_goal else current.title or "21-day goal validation"
    title = title if title is not None else prompt_default("Season title", default_title)
    primary = primary if primary is not None else prompt_optional("Why this goal now?") if interactive else current.primary_track
    start_date_text = start_date_text or (prompt_default("Start date", current.start_date or default_start) if interactive else current.start_date or default_start)
    end_date_text = end_date_text or (prompt_default("End date", current.end_date or default_end) if interactive else current.end_date or default_end)
    daily_minimum = daily_minimum if daily_minimum is not None else (prompt_int_default("Daily minimum minutes", current.daily_minimum_minutes or 25) if interactive else current.daily_minimum_minutes)
    weekly_target = weekly_target if weekly_target is not None else (prompt_int_default("Weekly target minutes", current.weekly_target_minutes or 300) if interactive else current.weekly_target_minutes)
    success = success if success is not None else (prompt_optional("Success criteria") if interactive else current.success_criteria)
    constraints = constraints if constraints is not None else (prompt_optional("Constraints") if interactive else current.constraints)
    paused = paused if paused is not None else (prompt_optional("Paused goals") if interactive else current.paused_goals)
    review_question = review_question if review_question is not None else (
        prompt_default("Day-21 review question", current.review_question or "Continue, adjust, or pause?") if interactive else current.review_question
    )

    start = parse_date(start_date_text or default_start, today)
    end = parse_date(end_date_text or default_end, start + timedelta(days=20))
    if end < start:
        end = start + timedelta(days=20)

    season = CurrentSeason(
        title=(title or "").strip(),
        goal_id=selected_goal.id if selected_goal else (goal_id or current.goal_id or "").strip(),
        primary_track=(primary or "").strip(),
        support_track="",
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        daily_minimum_minutes=max(0, int(daily_minimum or 0)),
        weekly_target_minutes=max(0, int(weekly_target or 0)),
        success_criteria=(success or "").strip(),
        constraints=(constraints or "").strip(),
        paused_goals=(paused or "").strip(),
        review_question=(review_question or "").strip(),
        day_7_review=current.day_7_review,
        day_14_review=current.day_14_review,
        day_21_review=current.day_21_review,
        final_decision=current.final_decision,
        status=current.status or "active",
    )
    store.save_current_season(season)
    console.print("[green]Saved current season.[/green]")
    print_season(store)
    return season


def update_season(
    store: JsonStore,
    reason: str | None = None,
    title: str | None = None,
    goal_number: int | None = None,
    goal_id: str | None = None,
    primary: str | None = None,
    support: str | None = None,
    start_date_text: str | None = None,
    end_date_text: str | None = None,
    daily_minimum: int | None = None,
    weekly_target: int | None = None,
    success: str | None = None,
    constraints: str | None = None,
    paused: str | None = None,
    review_question: str | None = None,
    status: str | None = None,
) -> CurrentSeason:
    current = store.load_current_season()
    goals = [goal for goal in sorted_goals(store.load_goals()) if goal.status == "active"]
    interactive = (
        reason is None
        and title is None
        and goal_number is None
        and goal_id is None
        and primary is None
        and support is None
        and start_date_text is None
        and end_date_text is None
        and daily_minimum is None
        and weekly_target is None
        and success is None
        and constraints is None
        and paused is None
        and review_question is None
        and status is None
        and sys.stdin.isatty()
    )

    if interactive:
        print_season(store)
        reason = prompt_required("Reason for season change")
        title = prompt_default("Season title", current.title)
        primary = prompt_default("Primary track", current.primary_track)
        support = prompt_default("Support track", current.support_track)
        start_date_text = prompt_default("Start date", current.start_date)
        end_date_text = prompt_default("End date", current.end_date)
        daily_minimum = prompt_int_default("Daily minimum minutes", current.daily_minimum_minutes)
        weekly_target = prompt_int_default("Weekly target minutes", current.weekly_target_minutes)
        success = prompt_default("Success criteria", current.success_criteria)
        constraints = prompt_default("Constraints", current.constraints)
        paused = prompt_default("Paused goals", current.paused_goals)
        review_question = prompt_default("Day-21 review question", current.review_question)
        status = prompt_default("Status", current.status)

    reason = (reason or "").strip()
    if not reason:
        raise typer.BadParameter("season update requires --reason")

    selected_goal = None
    if goal_id or goal_number is not None:
        selected_goal = resolve_season_goal(goals, goal_number, goal_id, current.goal_id, interactive=False)

    updates: dict[str, object] = {}
    add_update(updates, "title", current.title, title)
    add_update(updates, "goal_id", current.goal_id, selected_goal.id if selected_goal else goal_id if goal_id is not None else None)
    add_update(updates, "primary_track", current.primary_track, primary)
    add_update(updates, "support_track", current.support_track, support)
    add_update(updates, "start_date", current.start_date, start_date_text)
    add_update(updates, "end_date", current.end_date, end_date_text)
    add_update(updates, "daily_minimum_minutes", current.daily_minimum_minutes, daily_minimum)
    add_update(updates, "weekly_target_minutes", current.weekly_target_minutes, weekly_target)
    add_update(updates, "success_criteria", current.success_criteria, success)
    add_update(updates, "constraints", current.constraints, constraints)
    add_update(updates, "paused_goals", current.paused_goals, paused)
    add_update(updates, "review_question", current.review_question, review_question)
    add_update(updates, "status", current.status, normalize_season_status(status) if status is not None else None)

    if not updates:
        console.print("[yellow]No season fields changed.[/yellow]")
        return current

    if "start_date" in updates or "end_date" in updates:
        start = parse_date(str(updates.get("start_date", current.start_date)), parse_date(current.start_date, date.today()))
        end = parse_date(str(updates.get("end_date", current.end_date)), parse_date(current.end_date, start))
        if end < start:
            raise typer.BadParameter("end date must be on or after start date")

    before = {key: getattr(current, key) for key in updates}
    for key, value in updates.items():
        setattr(current, key, value)
    current.change_log.append(
        {
            "changed_at": timestamp_now(),
            "reason": reason,
            "fields": ", ".join(sorted(updates)),
            "before": {key: str(value) for key, value in before.items()},
            "after": {key: str(value) for key, value in updates.items()},
        }
    )
    store.save_current_season(current)
    console.print(f"[green]Updated season: {', '.join(sorted(updates))}[/green]")
    print_season(store)
    return current


def add_update(updates: dict[str, object], key: str, current_value: object, new_value: object | None) -> None:
    if new_value is None:
        return
    value = new_value.strip() if isinstance(new_value, str) else new_value
    if value != current_value:
        updates[key] = value


def normalize_season_status(status: str) -> str:
    normalized = status.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "active": "active",
        "resume": "active",
        "paused": "paused",
        "pause": "paused",
        "on_hold": "paused",
        "completed": "completed",
        "done": "completed",
        "cancelled": "cancelled",
        "canceled": "cancelled",
        "cancel": "cancelled",
    }
    mapped = aliases.get(normalized)
    if mapped is None:
        raise typer.BadParameter("status must be active, paused, completed, or cancelled")
    return mapped


def timestamp_now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def resolve_season_goal(
    goals: list[Goal],
    goal_number: int | None,
    goal_id: str | None,
    current_goal_id: str,
    interactive: bool,
) -> Goal | None:
    if goal_id:
        match = find_goal_by_id(goals, goal_id)
        if match is None:
            raise SystemExit(f"Goal not found: {goal_id}")
        return match
    if goal_number is not None:
        if goal_number < 1 or goal_number > len(goals):
            raise SystemExit(f"Goal number must be between 1 and {len(goals)}")
        return goals[goal_number - 1]
    current = find_goal_by_id(goals, current_goal_id)
    if current is not None and not interactive:
        return current
    if not interactive:
        return current
    if not goals:
        console.print("[yellow]No active goals yet. Create a goal first with `create goal`.[/yellow]")
        return None
    console.print("Choose the goal this season will validate:")
    for index, goal in enumerate(goals, start=1):
        console.print(f"{index}. [{goal.priority}] {goal.title}")
    choice = ask_single_choice("Season goal", 1, len(goals))
    if choice is None:
        raise SystemExit("Season setup cancelled.")
    return goals[choice - 1]


def find_goal_by_id(goals: list[Goal], goal_id: str) -> Goal | None:
    if not goal_id:
        return None
    return next((goal for goal in goals if goal.id == goal_id), None)


def start_focus(store: JsonStore, args: argparse.Namespace) -> None:
    goals = store.load_goals()
    season = store.load_current_season()
    today_plan = store.load_today_plan()
    planned = planned_work_items(goals, today_plan.items, season)
    flow_items = today_flow_items(goals) if today_plan.mode == "flow" else []
    candidates = focus_targets_with_season(goals, planned, season, flow_items)
    if not candidates:
        print("No focus target available. Create a goal first:")
        print("kairos goal create")
        return

    print("Focus targets")
    for index, item in enumerate(candidates, start=1):
        marker = item.get("marker") or ("planned" if item in planned else "available")
        print(f"{index}. {item['title']} [{marker}]")

    choice = args.target or ask_single_choice("Target", 1, len(candidates))
    if choice is None:
        console.print("[dim]Focus cancelled.[/dim]")
        return
    if choice < 1 or choice > len(candidates):
        raise SystemExit(f"Invalid target: {choice}")
    target = candidates[choice - 1]

    settings = store.load_settings()
    minutes = max(1, args.minutes or settings.pomodoro_minutes)
    print_focus_banner(target["title"], minutes)
    if not args.no_timer:
        run_timer(minutes, target["title"])
        alert()

    should_prompt_result = args.status is None and args.notes is None and args.friction is None
    status = args.status or (prompt_default("Result [completed/partial/blocked]", "completed") if should_prompt_result else "completed")
    if status not in {"completed", "partial", "blocked"}:
        status = "completed"
    notes = args.notes if args.notes is not None else (prompt_optional("What got done?") if should_prompt_result else "")
    friction = args.friction if args.friction is not None else (prompt_optional("Friction or blocker") if should_prompt_result else "")
    note_parts = [f"Result: {notes}" if notes else "", f"Friction: {friction}" if friction else ""]
    session = store.add_session(
        "" if target["goal_id"] == "__season__" else target["goal_id"],
        None if target["task_id"] in {"", "__season__"} else target["task_id"],
        minutes * 60,
        status,
        notes=" | ".join(part for part in note_parts if part),
    )
    if target["task_id"] and target["task_id"] != "__season__":
        if status == "completed":
            store.update_task_status(target["goal_id"], target["task_id"], "done")
        elif status == "partial":
            store.update_task_status(target["goal_id"], target["task_id"], "in_progress")
        elif status == "blocked":
            store.update_task_status(target["goal_id"], target["task_id"], "blocked")
    print_ascii_stamp("done" if status == "completed" else "logged")
    print(f"Logged {format_minutes(session.duration_seconds // 60)}: {status}")


def run_daily_checkin(store: JsonStore, dry_run: bool = False, show_today_after: bool = True) -> None:
    print_logo()
    questions = daily_questions(store)
    print("Daily check-in")
    print("Answer briefly. Blank is fine if a question is not useful today.")
    answers: dict[str, str] = {}
    for question in questions:
        if dry_run:
            print(format_question_preview(question))
            continue
        answer = ask_question_response(question)
        answers[str(question["id"])] = answer
        if answer:
            if question.get("question_id"):
                store.add_brain_answer(question["question_id"], answer)
            else:
                store.add_brain_reflection(
                    prompt=question["prompt"],
                    answer_text=answer,
                    construct=question["construct"],
                    section="Daily CLI check-in",
                    question_id=str(question["id"]),
                    response_type=str(question.get("response_type", "open")),
                )

    if dry_run:
        return

    today_log = store.load_daily_log()
    intention = answers.get("intention") or today_log.intention
    must_win = answers.get("must_win") or today_log.must_win
    derailment = answers.get("derailment") or today_log.pact
    score = daily_score(intention, must_win, derailment)
    store.save_daily_log(today_log.log_date, intention, must_win, today_log.shutdown, score, derailment)
    print("Saved daily check-in.")
    if show_today_after:
        print_today(store)


def run_shutdown(store: JsonStore, summary: str | None = None, carry: str | None = None, tomorrow: str | None = None) -> None:
    goals = store.load_goals()
    sessions = sessions_for_today(store.load_sessions())
    today_plan = store.load_today_plan()
    season = store.load_current_season()
    today_log = store.load_daily_log()
    if summary is None:
        console.print(Panel(format_done_today_summary(goals, sessions) or "No focus sessions logged today.", title="Done Today"))
        summary = prompt_optional("What actually happened today?")
    if carry is None:
        carry = prompt_optional("What should be carried forward or cleaned up?")
    if tomorrow is None:
        tomorrow = prompt_optional("First useful move tomorrow?")

    parts = []
    if summary:
        parts.append(f"Summary: {summary}")
    if carry:
        parts.append(f"Carry: {carry}")
    if tomorrow:
        parts.append(f"Tomorrow: {tomorrow}")
    shutdown_text = " | ".join(parts)
    score = daily_score(today_log.intention, today_log.must_win, today_log.pact)
    store.save_daily_log(
        today_log.log_date,
        today_log.intention,
        today_log.must_win,
        shutdown_text,
        score,
        today_log.pact,
    )

    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold cyan")
    table.add_column()
    table.add_row("Focused", format_minutes(sum(session.duration_seconds for session in sessions) // 60))
    table.add_row("Plan", today_plan_label_for_plan(goals, today_plan, season))
    season_nudge = season_session_nudge(season, sessions)
    if season_nudge:
        table.add_row("Season", season_nudge)
    if carry:
        table.add_row("Carry", carry)
    if tomorrow:
        table.add_row("Tomorrow", tomorrow)
    console.print(Panel(table, title="Day Closed", border_style="green"))
    print_ascii_stamp("closed")


def sync_brain_to_vault_cli(store: JsonStore) -> None:
    store.sync_brain_to_vault(store.load_north_star(), store.load_life_areas(), store.load_goals())
    console.print(f"[green]Synced Brain markdown to:[/green] {store.vault_dir / '10 Brain'}")
    console.print(f"[dim]Personal brain: {store.vault_dir / '10 Brain' / 'Personal Brain.md'}[/dim]")
    console.print(f"[dim]Question history: {store.vault_dir / '10 Brain' / 'Questionnaire History.md'}[/dim]")


def rebuild_personal_brain_cli(store: JsonStore) -> None:
    observations, patterns = store.rebuild_personal_brain()
    console.print(
        Panel(
            f"Observations: {len(observations)}\nPatterns: {len(patterns)}\n\n"
            "Raw answers remain unchanged; this layer can be regenerated.",
            title="Personal Brain Rebuilt",
            border_style="green",
        )
    )
    print_ascii_stamp("brain")


def print_brain_status(store: JsonStore) -> None:
    answers = store.load_brain_answers()
    memories = store.load_brain_memories()
    observations = store.load_brain_observations()
    patterns = store.load_brain_patterns()
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold cyan")
    table.add_column()
    table.add_row("Answers", str(len(answers)))
    table.add_row("Observations", str(len(observations)))
    table.add_row("Patterns", str(len(patterns)))
    table.add_row("Memories", str(len(memories)))
    table.add_row("Vault", str(store.vault_dir))
    table.add_row("Markdown", str(store.vault_dir / "10 Brain" / "Questionnaire History.md"))
    console.print(Panel(table, title="Brain Status", border_style="cyan"))


def daily_questions(store: JsonStore) -> list[dict[str, str]]:
    season = store.load_current_season()
    today_plan = store.load_today_plan()
    answers = store.load_brain_answers()
    questions = [
        {
            "id": "intention",
            "prompt": "What kind of person do you want to practice being today?",
            "construct": "identity_practice",
        },
        {
            "id": "must_win",
            "prompt": "What is today's must-win?",
            "construct": "daily_minimum",
        },
        {
            "id": "derailment",
            "prompt": "What is most likely to derail you today?",
            "construct": "execution_friction",
            "response_type": "open",
            "options": [],
        },
    ]
    for question in questions:
        question.setdefault("response_type", "open")
        question.setdefault("options", [])
    selected_ids = scheduled_daily_question_ids(season, today_plan, answers, limit=2)
    questions.extend(question_bank_prompt(question_id) for question_id in selected_ids)
    return questions[:5]


def scheduled_daily_question_ids(
    season: CurrentSeason,
    today_plan: TodayPlan,
    answers: list[object],
    limit: int = 2,
) -> list[str]:
    candidates = daily_rotation_candidates(season, today_plan)
    selected: list[str] = []
    first = pick_rotating_questions(candidates, answers, limit=1)
    selected.extend(first)
    remaining = [question_id for question_id in candidates if question_id not in selected]
    first_type = question_response_type(selected[0]) if selected else ""
    if first_type == "open":
        remaining = [question_id for question_id in remaining if question_response_type(question_id) != "open"] + [
            question_id for question_id in remaining if question_response_type(question_id) == "open"
        ]
    else:
        remaining = [question_id for question_id in remaining if question_response_type(question_id) == "open"] + [
            question_id for question_id in remaining if question_response_type(question_id) != "open"
        ]
    selected.extend(pick_rotating_questions(remaining, answers, limit=max(0, limit - len(selected))))
    return selected[:limit]


def daily_rotation_candidates(season: CurrentSeason, today_plan: TodayPlan) -> list[str]:
    high_value_sections = [
        "Situation Simulation",
        "Preference Under Constraint",
        "Decision Rules",
        "Stress Defaults",
        "Communication Style",
        "Boundaries",
        "Belief Evolution",
        "Planning Accuracy",
        "Focus Patterns",
        "Energy",
        "Emotional Patterns",
        "Learning Style",
        "Decision Style",
        "Self Honesty",
        "Motivation",
        "Values",
        "Wellbeing",
        "Distraction",
    ]
    candidates = [
        str(question["id"])
        for section in high_value_sections
        for question in QUESTION_BANK
        if question.get("section") == section and question.get("priority", "medium") in {"high", "medium"}
    ]
    contextual_ids = [
        "planning_05",
        "planning_01",
        "season_primary_02",
        "focus_04",
        "energy_02",
        "emotion_03",
    ]
    typed_ids = [
        "autonomy",
        "competence",
        "wellbeing_recent",
        "internal_trigger_frequency",
        "energy_01",
        "emotion_01",
        "values_rank",
        "learning_01",
    ]
    if not today_plan.items:
        contextual_ids.insert(0, "planning_01")
    if not season.title.strip() and not season.primary_track.strip():
        contextual_ids.insert(0, "season_primary_01")
    else:
        contextual_ids.insert(0, "season_primary_02")
        contextual_ids.insert(1, "focus_04")
    return unique_question_ids(contextual_ids + typed_ids + candidates)


def unique_question_ids(question_ids: list[str]) -> list[str]:
    unique_ids: list[str] = []
    for question_id in question_ids:
        if question_id not in unique_ids:
            unique_ids.append(question_id)
    return unique_ids


def pick_rotating_questions(question_ids: list[str], answers: list[object], limit: int) -> list[str]:
    unique_ids = unique_question_ids(question_ids)

    last_seen: dict[str, str] = {}
    for answer in answers:
        question_id = getattr(answer, "question_id", "")
        if question_id in unique_ids:
            last_seen[question_id] = max(last_seen.get(question_id, ""), getattr(answer, "created_at", ""))

    def sort_key(question_id: str) -> tuple[int, str]:
        return (1 if question_id in last_seen else 0, last_seen.get(question_id, ""))

    return sorted(unique_ids, key=sort_key)[:limit]


def question_response_type(question_id: str) -> str:
    question = next((item for item in QUESTION_BANK if item["id"] == question_id), None)
    if question is None:
        return "open"
    return str(question.get("response_type", "open"))


def question_bank_prompt(question_id: str) -> dict[str, str | list[str]]:
    question = next((item for item in QUESTION_BANK if item["id"] == question_id), None)
    if question is None:
        return {
            "id": question_id,
            "prompt": "What is useful for Kairos to remember today?",
            "construct": "reflection",
            "response_type": "open",
            "options": [],
        }
    return {
        "id": question["id"],
        "question_id": question["id"],
        "prompt": question["prompt"],
        "construct": question["construct"],
        "response_type": question["response_type"],
        "options": question.get("options", []),
    }


def format_question_preview(question: dict[str, object]) -> str:
    response_type = str(question.get("response_type", "open"))
    options = question.get("options") or []
    if options:
        return f"- [{response_type}] {question['prompt']} ({', '.join(str(option) for option in options)})"
    return f"- [{response_type}] {question['prompt']}"


def ask_question_response(question: dict[str, object]) -> str:
    response_type = str(question.get("response_type", "open"))
    options = [str(option) for option in question.get("options", [])]
    prompt = str(question["prompt"])
    if response_type in {"likert", "frequency", "choice"} and options:
        return ask_option_response(prompt, options)
    if response_type == "ranking" and options:
        return ask_ranking_response(prompt, options)
    return prompt_optional(prompt)


def ask_option_response(prompt: str, options: list[str]) -> str:
    if not sys.stdin.isatty():
        return ""
    print(prompt)
    for index, option in enumerate(options, start=1):
        print(f"{index}. {option}")
    choice = ask_single_choice("Answer", 1, len(options))
    if choice is None:
        return ""
    return options[choice - 1]


def ask_ranking_response(prompt: str, options: list[str]) -> str:
    if not sys.stdin.isatty():
        return ""
    print(prompt)
    for index, option in enumerate(options, start=1):
        print(f"{index}. {option}")
    raw = input("Rank top choices, comma-separated (blank to skip): ").strip()
    choices = parse_choice_numbers(raw)
    ranked = [options[choice - 1] for choice in choices if 1 <= choice <= len(options)]
    return ", ".join(ranked)


def create_startup_launcher() -> None:
    if os.name != "nt":
        raise SystemExit("Startup launcher setup is currently implemented for Windows only.")
    launcher = startup_launcher_path()
    launcher.parent.mkdir(parents=True, exist_ok=True)
    kairos_command = shutil.which("kairos") or str(Path(sys.executable).with_name("kairos.exe"))
    command = f'@echo off\r\n"{kairos_command}" daily\r\npause\r\n'
    launcher.write_text(command, encoding="utf-8")
    print(f"Created startup launcher: {launcher}")


def startup_launcher_path() -> Path:
    if os.name != "nt":
        return user_config_dir() / "Kairos Daily.cmd"
    return Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "Kairos Daily.cmd"


def startup_launcher_status() -> str:
    if os.name != "nt":
        return "not supported"
    path = startup_launcher_path()
    return f"installed ({path})" if path.exists() else "not installed"


def storage_label(store: JsonStore) -> str:
    requested = os.environ.get("KAIROS_STORAGE", "mongodb").strip().lower()
    if isinstance(store, MongoStore):
        database = os.environ.get("KAIROS_MONGODB_DATABASE", "kairos")
        collection = os.environ.get("KAIROS_MONGODB_COLLECTION", "state")
        return f"MongoDB ({database}.{collection})"
    if requested not in {"json", "local"}:
        return "JSON local (MongoDB unavailable)"
    return "JSON local"


def season_status(season: CurrentSeason) -> str:
    title = season.title.strip() or season.primary_track.strip()
    if not title:
        return "Not set"
    return f"{title} | {season_day_label(season)}"


def season_day_label(season: CurrentSeason) -> str:
    start = parse_date(season.start_date, date.today())
    end = parse_date(season.end_date, start)
    if end < start:
        end = start
    today = date.today()
    total_days = max(1, (end - start).days + 1)
    if today < start:
        return f"starts in {(start - today).days} days"
    if today > end:
        return "review due"
    return f"day {(today - start).days + 1} of {total_days}"


def parse_date(value: str, fallback: date) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return fallback


def sessions_for_today(sessions: list[FocusSession]) -> list[FocusSession]:
    today = date.today()
    items: list[FocusSession] = []
    for session in sessions:
        if session.status not in {"completed", "partial", "blocked"} or session.session_type != "pomodoro":
            continue
        try:
            if datetime.fromisoformat(session.started_at).date() == today:
                items.append(session)
        except ValueError:
            continue
    return items


def focus_minutes_this_week(sessions: list[FocusSession]) -> int:
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    minutes = 0
    for session in sessions:
        if session.status != "completed" or session.session_type != "pomodoro":
            continue
        try:
            session_date = datetime.fromisoformat(session.started_at).date()
        except ValueError:
            continue
        if week_start <= session_date <= today:
            minutes += session.duration_seconds // 60
    return minutes


def season_focus_minutes_today(sessions: list[FocusSession], goal_id: str) -> int:
    if not goal_id:
        return 0
    return sum(session.duration_seconds for session in sessions if session.goal_id == goal_id) // 60


def season_session_nudge(season: CurrentSeason, today_sessions: list[FocusSession]) -> str:
    if not season.title.strip() and not season.primary_track.strip() and not season.goal_id:
        return ""
    if season.goal_id:
        minutes = season_focus_minutes_today(today_sessions, season.goal_id)
    else:
        minutes = sum(session.duration_seconds for session in today_sessions if not session.goal_id) // 60
    minimum = season.daily_minimum_minutes or 25
    if minutes >= minimum:
        return f"{format_minutes(minutes)} logged for season today; target met"
    if minutes > 0:
        return f"{format_minutes(minutes)} / {format_minutes(minimum)} logged; season block still under target"
    return f"Protect at least one season block today ({minimum} min target)"


def format_session_summary(goals: list[Goal], sessions: list[FocusSession]) -> str:
    recent = sorted(sessions, key=lambda session: session.started_at)[-3:]
    parts = []
    for session in recent:
        parts.append(
            f"{session_title(goals, session)} ({format_minutes(session.duration_seconds // 60)}, {session.status})"
        )
    remaining = len(sessions) - len(recent)
    suffix = f" +{remaining} earlier" if remaining > 0 else ""
    return "; ".join(parts) + suffix


def format_done_today_summary(goals: list[Goal], sessions: list[FocusSession]) -> str:
    completed = [session for session in sessions if session.status == "completed"]
    if not completed:
        return ""

    grouped: dict[tuple[str, str | None], int] = {}
    latest_started: dict[tuple[str, str | None], str] = {}
    for session in completed:
        key = (session.goal_id, session.task_id)
        grouped[key] = grouped.get(key, 0) + session.duration_seconds
        latest_started[key] = max(latest_started.get(key, ""), session.started_at)

    rows: list[str] = []
    for key, seconds in sorted(grouped.items(), key=lambda item: latest_started.get(item[0], "")):
        goal_id, task_id = key
        goal = find_goal_by_id(goals, goal_id)
        priority = f"[{goal.priority}] " if goal is not None else ""
        title = session_title_by_ids(goals, goal_id, task_id)
        rows.append(f"{priority}{title} ({format_minutes(seconds // 60)})")
    return "\n".join(rows)


def format_non_completed_today_summary(goals: list[Goal], sessions: list[FocusSession]) -> str:
    sessions = [session for session in sessions if session.status != "completed"]
    if not sessions:
        return ""
    rows = []
    for session in sorted(sessions, key=lambda item: item.started_at):
        title = session_title(goals, session)
        rows.append(f"{title} ({format_minutes(session.duration_seconds // 60)}, {session.status})")
    return "\n".join(rows)


def session_title(goals: list[Goal], session: FocusSession) -> str:
    return session_title_by_ids(goals, session.goal_id, session.task_id)


def session_title_by_ids(goals: list[Goal], goal_id: str, task_id: str | None) -> str:
    goal = find_goal_by_id(goals, goal_id)
    if goal is None:
        return "Unlinked focus"
    task = next((task for task in goal.tasks if task.id == task_id), None)
    if task is None:
        return goal.title
    return f"{goal.title}: {task.title}"


def planned_work_items(
    goals: list[Goal],
    plan_items: list[TodayPlanItem],
    season: CurrentSeason | None = None,
) -> list[dict[str, str]]:
    by_goal = {goal.id: goal for goal in goals}
    items: list[dict[str, str]] = []
    for plan_item in plan_items:
        if is_season_plan_item(plan_item):
            season_item = season_focus_item(goals, season)
            if season_item is not None:
                items.append(season_item)
            continue
        goal = by_goal.get(plan_item.goal_id)
        if goal is None or goal.status != "active":
            continue
        task = next((item for item in goal.tasks if item.id == plan_item.task_id), None)
        if plan_item.task_id and (task is None or task.status not in {"todo", "in_progress"}):
            continue
        title = goal.title if task is None else f"{goal.title}: {task.title}"
        items.append({"goal_id": goal.id, "task_id": task.id if task else "", "title": title})
    return items


def is_season_plan_item(plan_item: TodayPlanItem) -> bool:
    return plan_item.goal_id == "__season__" or plan_item.task_id == "__season__"


def season_focus_item(goals: list[Goal], season: CurrentSeason | None) -> dict[str, str] | None:
    if season is None:
        return None
    season_title = (season.title or season.primary_track).strip()
    if not season_title and not season.goal_id:
        return None
    linked_goal = find_goal_by_id(goals, season.goal_id)
    if linked_goal is not None and linked_goal.status == "active":
        task = next((task for task in sorted_tasks(linked_goal.tasks) if task.status in {"todo", "in_progress"}), None)
        title = linked_goal.title if task is None else f"{linked_goal.title}: {task.title}"
        return {
            "goal_id": linked_goal.id,
            "task_id": task.id if task else "",
            "title": title,
            "marker": f"season | {season_day_label(season)} | min {season.daily_minimum_minutes or 0}m",
        }
    if not season_title:
        return None
    return {
        "goal_id": "__season__",
        "task_id": "__season__",
        "title": f"Season: {season_title}",
        "marker": f"season | {season_day_label(season)} | min {season.daily_minimum_minutes or 0}m",
    }


def focus_candidates(goals: list[Goal]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for goal in sorted_goals([goal for goal in goals if goal.status == "active"]):
        tasks = [task for task in sorted_tasks(goal.tasks) if task.status in {"todo", "in_progress"}]
        if not tasks:
            items.append({"goal_id": goal.id, "task_id": "", "title": goal.title})
            continue
        for task in tasks:
            items.append({"goal_id": goal.id, "task_id": task.id, "title": f"{goal.title}: {task.title}"})
    return items


def focus_target_index_for_today(store: JsonStore, goal_id: str, task_id: str | None = None) -> int | None:
    goals = store.load_goals()
    season = store.load_current_season()
    today_plan = store.load_today_plan()
    planned = planned_work_items(goals, today_plan.items, season)
    flow_items = today_flow_items(goals) if today_plan.mode == "flow" else []
    candidates = focus_targets_with_season(goals, planned, season, flow_items)
    normalized_task_id = task_id or ""
    for index, item in enumerate(candidates, start=1):
        if item["goal_id"] == goal_id and item["task_id"] == normalized_task_id:
            return index
    return None


def today_flow_items(goals: list[Goal]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    today_iso = date.today().isoformat()
    for goal in sorted_goals([goal for goal in goals if goal.status == "active" and goal.title.startswith("Flow ")]):
        tasks = [
            task
            for task in sorted_tasks(goal.tasks)
            if task.status in {"todo", "in_progress"} and task.created_at[:10] == today_iso
        ]
        for task in tasks:
            items.append({"goal_id": goal.id, "task_id": task.id, "title": f"{goal.title}: {task.title}"})
    return items


def format_item_titles(items: list[dict[str, str]], limit: int = 3) -> str:
    visible = [item["title"] for item in items[:limit]]
    if len(items) > limit:
        visible.append(f"+{len(items) - limit} more")
    return "; ".join(visible)


def commitment_candidates(goals: list[Goal], season: CurrentSeason) -> list[dict[str, str]]:
    candidates = focus_candidates(goals)
    season_item = season_focus_item(goals, season)
    if season_item is None:
        return candidates
    season_first = []
    others = []
    for item in candidates:
        if item["goal_id"] == season_item["goal_id"] and item["task_id"] == season_item["task_id"]:
            copied = dict(item)
            copied["marker"] = "season"
            season_first.append(copied)
        else:
            others.append(item)
    if not season_first:
        season_first.append(season_item)
    return season_first + others


def focus_targets_with_season(
    goals: list[Goal],
    planned: list[dict[str, str]],
    season: CurrentSeason,
    flow_items: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    season_item = season_focus_item(goals, season)
    if season_item is not None:
        candidates.append(season_item)
    seen = {(item["goal_id"], item["task_id"]) for item in candidates}
    base_items = planned or focus_candidates(goals)
    for item in [*base_items, *(flow_items or [])]:
        key = (item["goal_id"], item["task_id"])
        if key in seen:
            continue
        copied = dict(item)
        copied["marker"] = "planned" if item in planned else "captured" if item in (flow_items or []) else "available"
        candidates.append(copied)
        seen.add(key)
    return candidates


def sorted_goals(goals: list[Goal]) -> list[Goal]:
    priority_order = {"P1": 0, "P2": 1, "P3": 2, "P4": 3, "P5": 4}
    return sorted(
        goals,
        key=lambda goal: (
            priority_order.get(goal.priority, 99),
            goal.target_date or "9999-12-31",
            goal.created_at,
        ),
    )


def sorted_tasks(tasks: list[Task]) -> list[Task]:
    status_order = {"in_progress": 0, "todo": 1, "on_hold": 2, "blocked": 3, "done": 4}
    return sorted(tasks, key=lambda task: (status_order.get(task.status, 99), task.created_at))


def format_minutes(minutes: int) -> str:
    if minutes < 60:
        return f"{minutes} min"
    hours, remainder = divmod(minutes, 60)
    if remainder == 0:
        return f"{hours}h"
    return f"{hours}h {remainder}m"


def progress_bar(value: int, target: int, width: int = 20) -> str:
    if target <= 0:
        return "\\[" + "-" * width + "]"
    filled = min(width, max(0, round((value / target) * width)))
    return "\\[" + "#" * filled + "-" * (width - filled) + "]"


def print_logo() -> None:
    logo = "(⌐■_■) KAIROS"
    try:
        print(logo)
    except UnicodeEncodeError:
        print("(cool) KAIROS")


ASCII_STAMPS = {
    "captured": [
        "+----------------+",
        "|  TASK STORED   |",
        "+----------------+",
    ],
    "done": [
        "+----------------+",
        "| EVIDENCE SAVED |",
        "+----------------+",
    ],
    "logged": [
        "+----------------+",
        "|  BLOCK LOGGED  |",
        "+----------------+",
    ],
    "closed": [
        "+----------------+",
        "|   DAY CLOSED   |",
        "+----------------+",
    ],
    "brain": [
        "+----------------+",
        "|  BRAIN UPDATED |",
        "+----------------+",
    ],
}


def print_ascii_stamp(name: str) -> None:
    if os.environ.get("KAIROS_NO_ART", "").strip().lower() in {"1", "true", "yes"}:
        return
    lines = ASCII_STAMPS.get(name)
    if not lines:
        return
    for line in lines:
        print(line)


def print_session_header() -> None:
    table = Table.grid(padding=(0, 1))
    table.add_column(style="bold cyan")
    table.add_column()
    table.add_row("version:", package_version())
    table.add_row("home:", str(user_config_dir()))
    table.add_row("storage:", os.environ.get("KAIROS_STORAGE", "mongodb"))
    table.add_row("refreshed:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    table.add_row("directory:", str(Path.cwd()))
    console.print(
        Panel(
            table,
            title=f"(⌐■_■) >_ Kairos ({package_version()})",
            title_align="left",
            border_style="cyan",
        )
    )


def prompt_required(label: str) -> str:
    if not sys.stdin.isatty():
        raise SystemExit(f"Missing required value: {label}")
    while True:
        try:
            value = input(f"{label}: ").strip()
        except EOFError:
            raise SystemExit(f"Missing required value: {label}")
        if value:
            return value
        print("Required.")


def prompt_optional(label: str) -> str:
    if not sys.stdin.isatty():
        return ""
    try:
        return input(f"{label}: ").strip()
    except EOFError:
        return ""


def prompt_default(label: str, default: str) -> str:
    if not sys.stdin.isatty():
        return default
    try:
        value = input(f"{label} [{default}]: ").strip()
    except EOFError:
        return default
    return value or default


def prompt_int_default(label: str, default: int) -> int:
    if not sys.stdin.isatty():
        return default
    while True:
        raw = input(f"{label} [{default}]: ").strip()
        if not raw:
            return default
        try:
            return int(raw)
        except ValueError:
            print("Enter a number.")


def parse_choice_numbers(raw_items: str | None) -> list[int]:
    if not raw_items:
        return []
    choices: list[int] = []
    for item in raw_items.split(","):
        try:
            choices.append(int(item.strip()))
        except ValueError:
            continue
    return choices


EXIT_WORDS = {"0", "q", "quit", "exit", "cancel", "back"}


def ask_choice_numbers(label: str, minimum: int, maximum: int) -> list[int] | None:
    if not sys.stdin.isatty():
        return None
    while True:
        raw = input(f"{label} ({minimum}-{maximum}, comma-separated, 0 to cancel): ").strip()
        if raw.lower() in EXIT_WORDS:
            return None
        choices = parse_choice_numbers(raw)
        if minimum <= len(choices) <= maximum:
            return choices
        print(f"Choose between {minimum} and {maximum} items.")


def ask_single_choice(label: str, minimum: int, maximum: int) -> int | None:
    if not sys.stdin.isatty():
        return None
    while True:
        raw = input(f"{label} ({minimum}-{maximum}, 0 to cancel): ").strip()
        if raw.lower() in EXIT_WORDS:
            return None
        try:
            choice = int(raw)
        except ValueError:
            print("Enter a number.")
            continue
        if minimum <= choice <= maximum:
            return choice
        print(f"Choose a number from {minimum} to {maximum}.")


BIG_DIGITS = {
    "0": [" ### ", "#   #", "#   #", "#   #", " ### "],
    "1": ["  #  ", " ##  ", "  #  ", "  #  ", " ### "],
    "2": [" ### ", "#   #", "   # ", "  #  ", "#####"],
    "3": ["#### ", "    #", " ### ", "    #", "#### "],
    "4": ["#   #", "#   #", "#####", "    #", "    #"],
    "5": ["#####", "#    ", "#### ", "    #", "#### "],
    "6": [" ### ", "#    ", "#### ", "#   #", " ### "],
    "7": ["#####", "    #", "   # ", "  #  ", "  #  "],
    "8": [" ### ", "#   #", " ### ", "#   #", " ### "],
    "9": [" ### ", "#   #", " ####", "    #", " ### "],
    ":": ["     ", "  #  ", "     ", "  #  ", "     "],
}


def print_focus_banner(title: str, minutes: int) -> None:
    console.print(
        Panel(
            f"[bold]Target[/bold]\n{title}\n\n[bold]Timer[/bold]\n{minutes} min",
            title="Focus Block",
            border_style="green",
        )
    )


def run_timer(minutes: int, title: str = "") -> None:
    remaining = minutes * 60
    total_seconds = max(1, minutes * 60)
    use_big_timer = os.environ.get("KAIROS_BIG_TIMER", "").strip().lower() in {"1", "true", "yes"}
    if title and not use_big_timer:
        print(f"FOCUS: {title[:72]}")
    while remaining > 0:
        mins, secs = divmod(remaining, 60)
        timer_text = f"{mins:02d}:{secs:02d}"
        if sys.stdout.isatty() and use_big_timer:
            print("\033[2J\033[H", end="")
            if title:
                print(f"FOCUS: {title[:72]}")
            print("")
            for line in render_big_timer(timer_text):
                print(line)
            print("\nCtrl+C to stop the block early.")
        else:
            elapsed = total_seconds - remaining
            print(f"\r{timer_text} {timer_progress_bar(elapsed, total_seconds)}  Ctrl+C to stop", end="", flush=True)
        time.sleep(1)
        remaining -= 1
    if sys.stdout.isatty() and use_big_timer:
        print("\033[2J\033[H", end="")
        for line in render_big_timer("00:00"):
            print(line)
    else:
        print(f"\r00:00 {timer_progress_bar(total_seconds, total_seconds)}  complete          ")


def render_big_timer(value: str) -> list[str]:
    rows = ["", "", "", "", ""]
    for character in value:
        glyph = BIG_DIGITS.get(character, BIG_DIGITS[":"])
        for index, line in enumerate(glyph):
            rows[index] += line + "  "
    border = "+" + "-" * max(len(row) for row in rows) + "+"
    return [border] + [f"|{row.ljust(len(border) - 2)}|" for row in rows] + [border]


def timer_progress_bar(elapsed: int, total: int, width: int = 24) -> str:
    filled = min(width, max(0, round((elapsed / max(1, total)) * width)))
    return "[" + "#" * filled + "-" * (width - filled) + "]"


def alert() -> None:
    print("\a", end="", flush=True)
    if os.name == "nt":
        try:
            import winsound

            winsound.MessageBeep()
        except RuntimeError:
            pass


def daily_score(intention: str, must_win: str, pact: str) -> int:
    score = 0
    if intention.strip():
        score += 30
    if must_win.strip():
        score += 40
    if pact.strip():
        score += 30
    return score


if __name__ == "__main__":
    raise SystemExit(main())
