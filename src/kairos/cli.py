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
setup_app = typer.Typer(context_settings={"help_option_names": HELP_OPTION_NAMES}, help="Configure local launch helpers.", rich_markup_mode="rich")
config_app = typer.Typer(context_settings={"help_option_names": HELP_OPTION_NAMES}, help="Read and write Kairos user config.", rich_markup_mode="rich")

app.add_typer(goal_app, name="goal")
app.add_typer(goals_app, name="goals")
app.add_typer(today_app, name="today")
app.add_typer(season_app, name="season")
app.add_typer(focus_app, name="focus")
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
        ("goal list / goals list", "List goals"),
        ("today", "Show today"),
        ("today plan", "Choose commitments"),
        ("focus start", "Start a timer"),
        ("season", "Show current season"),
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
        ("start", "focus"): ["focus", "start"],
        ("add", "task"): ["goal", "task", "add"],
        ("create", "task"): ["goal", "task", "add"],
        ("new", "task"): ["goal", "task", "add"],
        ("create", "season"): ["season", "create"],
        ("new", "season"): ["season", "create"],
        ("set", "season"): ["season", "create"],
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
        ("6", "status", "Check progress and next action"),
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
    subparsers.add_parser("status", help="Show storage, season, today, focus, and next action.")
    subparsers.add_parser("doctor", help="Check install, config, storage, and launch health.")
    subparsers.add_parser("paths", help="Show important Kairos paths.")
    subparsers.add_parser("season", help="Show the current 21-day season.")

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
    """Show storage, season, today, focus, and next action."""
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


@app.command("daily")
def daily_command(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show questions without saving answers."),
) -> None:
    """Run the 3-5 question daily check-in."""
    run_daily_checkin(open_store(), dry_run=dry_run)


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
        task=task,
    )
    handle_goal(args, open_store())


@goal_app.command("task")
@goals_app.command("task")
def goal_task_command(
    action: str = typer.Argument("add", help="Task action. Currently only: add."),
    goal: Optional[int] = typer.Option(None, "--goal", help="Goal number from goals list."),
    goal_id: Optional[str] = typer.Option(None, "--goal-id", help="Goal id."),
    task: list[str] = typer.Option([], "--task", help="Task title. Repeat for multiple tasks."),
) -> None:
    """Manage tasks for a goal."""
    if action != "add":
        raise typer.BadParameter("task action must be add")
    args = SimpleNamespace(
        goal_command="task",
        goal_task_command=action,
        goal=goal,
        goal_id=goal_id,
        task=task,
    )
    handle_goal(args, open_store())


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
    return 2


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
    today_items = planned_work_items(goals, today_plan.items)
    focus_items = focus_candidates(goals)
    next_item = today_items[0] if today_items else (focus_items[0] if focus_items else None)
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
    summary.add_row("Plan", f"{len(today_items)}/3 commitments selected")
    summary.add_row("Next", next_item["title"] if next_item else "No active focus target")
    console.print(Panel(summary, title="Now", border_style="green"))

    done_today = format_done_today_summary(goals, today_sessions)
    console.print(
        Panel(
            done_today or "[dim]No completed focus logged today. Start with `focus`.[/dim]",
            title="Done Today",
            border_style="cyan",
        )
    )

    commands = Table(title="Fast Commands", header_style="bold cyan")
    commands.add_column("Need", style="bold")
    commands.add_column("Command", style="bold green")
    commands.add_column("Purpose")
    commands.add_row("Start", "focus", "Pick from available goals and log a block")
    commands.add_row("Plan", "today plan", "Choose one to three commitments")
    commands.add_row("Create", "goal create", "Add a goal and first tasks")
    commands.add_row("Extend", "add task", "Add tasks to an existing goal")
    commands.add_row("Review", "status", "Check progress, done work, and next target")
    commands.add_row("Guide", "quickstart", "Show the daily workflow")
    console.print(commands)
    console.print("[dim]Type `help` for all commands, or `exit` to leave Kairos.[/dim]")


def print_status(store: JsonStore) -> None:
    goals = store.load_goals()
    sessions = store.load_sessions()
    today_plan = store.load_today_plan()
    today_items = planned_work_items(goals, today_plan.items)
    focus_items = focus_candidates(goals)
    next_item = today_items[0] if today_items else (focus_items[0] if focus_items else None)
    today_sessions = sessions_for_today(sessions)
    today_minutes = sum(session.duration_seconds for session in today_sessions) // 60
    season = store.load_current_season()
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
    table.add_row("Today", f"{len(today_items)}/3 commitments, {format_minutes(today_minutes)} focused")
    done_today = format_done_today_summary(goals, today_sessions)
    if done_today:
        table.add_row("Done today", done_today)
    elif today_sessions:
        table.add_row("Logged today", format_session_summary(goals, today_sessions))
    table.add_row("Next", next_item["title"] if next_item else "No active focus target")
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
        task_text = "\n".join(f"{index}.{task_index} {task.title} [{task.status}]" for task_index, task in enumerate(tasks, start=1))
        table.add_row(str(index), goal.priority, goal.title, goal.category, goal.target_date or "", task_text or "-")
    console.print(table)


def print_today(store: JsonStore) -> None:
    goals = store.load_goals()
    today_plan = store.load_today_plan()
    items = planned_work_items(goals, today_plan.items)
    focus_items = focus_candidates(goals)
    print(date.today().strftime("Today: %A, %d %b %Y"))
    if not items:
        print("Commitments: none set")
    else:
        print("Commitments:")
        for index, item in enumerate(items, start=1):
            print(f"{index}. {item['title']}")
    next_item = items[0] if items else (focus_items[0] if focus_items else None)
    print(f"Next: {next_item['title'] if next_item else 'No active focus target'}")


def plan_today(store: JsonStore, raw_items: str | None, clear_first: bool) -> TodayPlan:
    goals = store.load_goals()
    candidates = focus_candidates(goals)
    if not candidates:
        print("No active focus targets. Create a goal first:")
        print("kairos goal create")
        return store.load_today_plan()

    if clear_first:
        store.clear_today_plan()

    print("Choose 1-3 commitments for today.")
    for index, item in enumerate(candidates, start=1):
        print(f"{index}. {item['title']}")

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

    print_today(store)
    return plan


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
    planned = planned_work_items(goals, today_plan.items)
    candidates = focus_targets_with_season(goals, planned, season)
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
    print(f"Starting: {target['title']} ({minutes} min)")
    if not args.no_timer:
        run_timer(minutes)
        alert()

    should_prompt_result = args.status is None and args.notes is None and args.friction is None
    status = args.status or (prompt_default("Result [completed/partial/blocked]", "completed") if should_prompt_result else "completed")
    if status not in {"completed", "partial", "blocked"}:
        status = "completed"
    notes = args.notes if args.notes is not None else (prompt_optional("What got done?") if should_prompt_result else "")
    friction = args.friction if args.friction is not None else (prompt_optional("Friction or blocker") if should_prompt_result else "")
    note_parts = [f"Result: {notes}" if notes else "", f"Friction: {friction}" if friction else ""]
    session = store.add_session(
        target["goal_id"],
        target["task_id"] or None,
        minutes * 60,
        status,
        notes=" | ".join(part for part in note_parts if part),
    )
    if target["task_id"]:
        if status == "completed":
            store.update_task_status(target["goal_id"], target["task_id"], "done")
        elif status == "partial":
            store.update_task_status(target["goal_id"], target["task_id"], "in_progress")
        elif status == "blocked":
            store.update_task_status(target["goal_id"], target["task_id"], "blocked")
    print(f"Logged {format_minutes(session.duration_seconds // 60)}: {status}")


def run_daily_checkin(store: JsonStore, dry_run: bool = False) -> None:
    print_logo()
    questions = daily_questions(store)
    print("Daily check-in")
    print("Answer briefly. Blank is fine if a question is not useful today.")
    answers: dict[str, str] = {}
    for question in questions:
        if dry_run:
            print(f"- {question['prompt']}")
            continue
        answer = prompt_optional(question["prompt"])
        answers[question["id"]] = answer
        if answer:
            store.add_brain_reflection(
                prompt=question["prompt"],
                answer_text=answer,
                construct=question["construct"],
                section="Daily CLI check-in",
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
    print_today(store)


def daily_questions(store: JsonStore) -> list[dict[str, str]]:
    season = store.load_current_season()
    today_plan = store.load_today_plan()
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
        },
    ]
    if not today_plan.items:
        questions.append(
            {
                "id": "plan_gap",
                "prompt": "What one task should be protected before the day gets noisy?",
                "construct": "planning_friction",
            }
        )
    elif not season.title.strip() and not season.primary_track.strip():
        questions.append(
            {
                "id": "season_gap",
                "prompt": "What should the current 21-day season be testing?",
                "construct": "season_clarity",
            }
        )
    else:
        questions.append(
            {
                "id": "energy",
                "prompt": "What energy level are you starting with, and when should deep work happen?",
                "construct": "energy",
            }
        )
    questions.append(
        {
            "id": "minimum",
            "prompt": "What is the smallest version of success that still counts today?",
            "construct": "daily_minimum",
        }
    )
    return questions[:5]


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


def planned_work_items(goals: list[Goal], plan_items: list[TodayPlanItem]) -> list[dict[str, str]]:
    by_goal = {goal.id: goal for goal in goals}
    items: list[dict[str, str]] = []
    for plan_item in plan_items:
        goal = by_goal.get(plan_item.goal_id)
        if goal is None or goal.status != "active":
            continue
        task = next((item for item in goal.tasks if item.id == plan_item.task_id), None)
        if plan_item.task_id and (task is None or task.status not in {"todo", "in_progress"}):
            continue
        title = goal.title if task is None else f"{goal.title}: {task.title}"
        items.append({"goal_id": goal.id, "task_id": task.id if task else "", "title": title})
    return items


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


def focus_targets_with_season(
    goals: list[Goal],
    planned: list[dict[str, str]],
    season: CurrentSeason,
) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    season_goal = find_goal_by_id(goals, season.goal_id)
    if season_goal is not None and season_goal.status == "active":
        task = next((task for task in sorted_tasks(season_goal.tasks) if task.status in {"todo", "in_progress"}), None)
        title = season_goal.title if task is None else f"{season_goal.title}: {task.title}"
        candidates.append(
            {
                "goal_id": season_goal.id,
                "task_id": task.id if task else "",
                "title": title,
                "marker": f"season | {season_day_label(season)} | min {season.daily_minimum_minutes or 0}m",
            }
        )
    elif season.title.strip() or season.primary_track.strip():
        title = season.primary_track.strip() or season.title.strip()
        candidates.append(
            {
                "goal_id": "",
                "task_id": "",
                "title": title,
                "marker": f"season | {season_day_label(season)} | unlinked | min {season.daily_minimum_minutes or 0}m",
            }
        )
    seen = {(item["goal_id"], item["task_id"]) for item in candidates}
    for item in planned or focus_candidates(goals):
        key = (item["goal_id"], item["task_id"])
        if key in seen:
            continue
        copied = dict(item)
        copied["marker"] = "planned" if item in planned else "available"
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
    status_order = {"in_progress": 0, "todo": 1, "blocked": 2, "done": 3}
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


def run_timer(minutes: int) -> None:
    remaining = minutes * 60
    while remaining > 0:
        mins, secs = divmod(remaining, 60)
        print(f"\r{mins:02d}:{secs:02d}", end="", flush=True)
        time.sleep(1)
        remaining -= 1
    print("\r00:00")


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
