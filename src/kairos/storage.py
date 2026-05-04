from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

TASK_STATUSES = {"todo", "in_progress", "done", "blocked"}


def timestamp() -> str:
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class Task:
    id: str
    title: str
    status: str = "todo"
    estimate_minutes: int | None = None
    created_at: str = field(default_factory=timestamp)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        return cls(
            id=data["id"],
            title=data["title"],
            status=data.get("status", "todo"),
            estimate_minutes=data.get("estimate_minutes"),
            created_at=data.get("created_at", timestamp()),
        )


@dataclass
class Goal:
    id: str
    title: str
    category: str
    priority: str
    target_date: str | None = None
    status: str = "active"
    notes: str = ""
    created_at: str = field(default_factory=timestamp)
    tasks: list[Task] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Goal":
        return cls(
            id=data["id"],
            title=data["title"],
            category=data.get("category", "General"),
            priority=data.get("priority", "P3"),
            target_date=data.get("target_date"),
            status=data.get("status", "active"),
            notes=data.get("notes", ""),
            created_at=data.get("created_at", timestamp()),
            tasks=[Task.from_dict(item) for item in data.get("tasks", [])],
        )


@dataclass
class FocusSession:
    id: str
    goal_id: str
    task_id: str | None
    started_at: str
    duration_seconds: int
    session_type: str = "pomodoro"
    status: str = "completed"
    notes: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FocusSession":
        return cls(
            id=data["id"],
            goal_id=data["goal_id"],
            task_id=data.get("task_id"),
            started_at=data["started_at"],
            duration_seconds=data["duration_seconds"],
            session_type=data.get("session_type", "pomodoro"),
            status=data.get("status", "completed"),
            notes=data.get("notes", ""),
        )


@dataclass
class AppSettings:
    pomodoro_minutes: int = 25
    short_break_minutes: int = 5
    long_break_minutes: int = 15
    sessions_before_long_break: int = 4

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppSettings":
        return cls(
            pomodoro_minutes=data.get("pomodoro_minutes", 25),
            short_break_minutes=data.get("short_break_minutes", 5),
            long_break_minutes=data.get("long_break_minutes", 15),
            sessions_before_long_break=data.get("sessions_before_long_break", 4),
        )


@dataclass
class TodayPlanItem:
    goal_id: str
    task_id: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TodayPlanItem":
        return cls(
            goal_id=data["goal_id"],
            task_id=data.get("task_id"),
        )


@dataclass
class TodayPlan:
    plan_date: str
    items: list[TodayPlanItem] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TodayPlan":
        return cls(
            plan_date=data.get("plan_date", datetime.now().date().isoformat()),
            items=[TodayPlanItem.from_dict(item) for item in data.get("items", [])],
        )


class JsonStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.goals_path = data_dir / "goals.json"
        self.sessions_path = data_dir / "sessions.json"
        self.settings_path = data_dir / "settings.json"
        self.today_plan_path = data_dir / "today_plan.json"
        self._ensure_files()

    def _ensure_files(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if not self.goals_path.exists():
            self.goals_path.write_text("[]\n", encoding="utf-8")
        if not self.sessions_path.exists():
            self.sessions_path.write_text("[]\n", encoding="utf-8")
        if not self.settings_path.exists():
            self.save_settings(AppSettings())
        if not self.today_plan_path.exists():
            self.save_today_plan(TodayPlan(plan_date=datetime.now().date().isoformat()))

    def _read_json(self, path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return default
        return json.loads(raw)

    def _write_json(self, path: Path, data: Any) -> None:
        path.write_text(f"{json.dumps(data, indent=2)}\n", encoding="utf-8")

    def load_goals(self) -> list[Goal]:
        payload = self._read_json(self.goals_path, [])
        return [Goal.from_dict(item) for item in payload]

    def save_goals(self, goals: list[Goal]) -> None:
        self._write_json(self.goals_path, [asdict(goal) for goal in goals])

    def load_sessions(self) -> list[FocusSession]:
        payload = self._read_json(self.sessions_path, [])
        return [FocusSession.from_dict(item) for item in payload]

    def save_sessions(self, sessions: list[FocusSession]) -> None:
        self._write_json(self.sessions_path, [asdict(session) for session in sessions])

    def load_settings(self) -> AppSettings:
        payload = self._read_json(self.settings_path, {})
        return AppSettings.from_dict(payload)

    def save_settings(self, settings: AppSettings) -> None:
        self._write_json(self.settings_path, asdict(settings))

    def load_today_plan(self) -> TodayPlan:
        payload = self._read_json(self.today_plan_path, {})
        plan = TodayPlan.from_dict(payload)
        today = datetime.now().date().isoformat()
        if plan.plan_date != today:
            plan = TodayPlan(plan_date=today)
            self.save_today_plan(plan)
        return plan

    def save_today_plan(self, plan: TodayPlan) -> None:
        self._write_json(self.today_plan_path, asdict(plan))

    def add_today_plan_item(self, goal_id: str, task_id: str | None) -> TodayPlan:
        plan = self.load_today_plan()
        item = TodayPlanItem(goal_id=goal_id, task_id=task_id)
        if any(existing.goal_id == item.goal_id and existing.task_id == item.task_id for existing in plan.items):
            return plan
        plan.items.append(item)
        self.save_today_plan(plan)
        return plan

    def remove_today_plan_item(self, goal_id: str, task_id: str | None) -> TodayPlan:
        plan = self.load_today_plan()
        plan.items = [
            item
            for item in plan.items
            if not (item.goal_id == goal_id and item.task_id == task_id)
        ]
        self.save_today_plan(plan)
        return plan

    def clear_today_plan(self) -> TodayPlan:
        plan = TodayPlan(plan_date=datetime.now().date().isoformat())
        self.save_today_plan(plan)
        return plan

    def _merge_tasks(
        self,
        existing_tasks: list[Task],
        task_titles: list[str],
    ) -> list[Task]:
        remaining_tasks = list(existing_tasks)
        merged_tasks: list[Task] = []

        for task_title in task_titles:
            match = next(
                (task for task in remaining_tasks if task.title == task_title),
                None,
            )
            if match is None:
                merged_tasks.append(Task(id=f"task-{uuid4().hex[:8]}", title=task_title))
                continue
            merged_tasks.append(match)
            remaining_tasks.remove(match)

        return merged_tasks

    def add_goal(
        self,
        title: str,
        category: str,
        priority: str,
        target_date: str | None,
        notes: str,
        task_titles: list[str] | None = None,
    ) -> Goal:
        goals = self.load_goals()
        goal = Goal(
            id=f"goal-{uuid4().hex[:8]}",
            title=title,
            category=category,
            priority=priority,
            target_date=target_date,
            notes=notes,
            tasks=[
                Task(id=f"task-{uuid4().hex[:8]}", title=task_title)
                for task_title in (task_titles or [])
            ],
        )
        goals.append(goal)
        self.save_goals(goals)
        return goal

    def update_goal(
        self,
        goal_id: str,
        title: str,
        category: str,
        priority: str,
        target_date: str | None,
        notes: str,
        task_titles: list[str] | None = None,
    ) -> Goal:
        goals = self.load_goals()
        for goal in goals:
            if goal.id != goal_id:
                continue
            goal.title = title
            goal.category = category
            goal.priority = priority
            goal.target_date = target_date
            goal.notes = notes
            if task_titles is not None:
                goal.tasks = self._merge_tasks(goal.tasks, task_titles)
            self.save_goals(goals)
            return goal
        raise ValueError(f"Goal not found: {goal_id}")

    def add_task(self, goal_id: str, title: str) -> Task:
        goals = self.load_goals()
        for goal in goals:
            if goal.id == goal_id:
                task = Task(id=f"task-{uuid4().hex[:8]}", title=title)
                goal.tasks.append(task)
                self.save_goals(goals)
                return task
        raise ValueError(f"Goal not found: {goal_id}")

    def rename_task(self, goal_id: str, task_id: str, title: str) -> None:
        goals = self.load_goals()
        for goal in goals:
            if goal.id != goal_id:
                continue
            for task in goal.tasks:
                if task.id == task_id:
                    task.title = title
                    self.save_goals(goals)
                    return
            raise ValueError(f"Task not found: {task_id}")
        raise ValueError(f"Goal not found: {goal_id}")

    def delete_task(self, goal_id: str, task_id: str) -> None:
        goals = self.load_goals()
        for goal in goals:
            if goal.id != goal_id:
                continue
            updated_tasks = [task for task in goal.tasks if task.id != task_id]
            if len(updated_tasks) == len(goal.tasks):
                raise ValueError(f"Task not found: {task_id}")
            goal.tasks = updated_tasks
            self.save_goals(goals)
            return
        raise ValueError(f"Goal not found: {goal_id}")

    def update_goal_status(self, goal_id: str, status: str) -> None:
        goals = self.load_goals()
        for goal in goals:
            if goal.id == goal_id:
                goal.status = status
                self.save_goals(goals)
                return
        raise ValueError(f"Goal not found: {goal_id}")

    def delete_goal(self, goal_id: str) -> None:
        goals = self.load_goals()
        updated_goals = [goal for goal in goals if goal.id != goal_id]
        if len(updated_goals) == len(goals):
            raise ValueError(f"Goal not found: {goal_id}")
        self.save_goals(updated_goals)

    def update_task_status(self, goal_id: str, task_id: str, status: str) -> None:
        if status not in TASK_STATUSES:
            raise ValueError(f"Invalid task status: {status}")
        goals = self.load_goals()
        for goal in goals:
            if goal.id != goal_id:
                continue
            for task in goal.tasks:
                if task.id == task_id:
                    task.status = status
                    self.save_goals(goals)
                    return
            raise ValueError(f"Task not found: {task_id}")
        raise ValueError(f"Goal not found: {goal_id}")

    def add_session(
        self,
        goal_id: str,
        task_id: str | None,
        duration_seconds: int,
        status: str,
        session_type: str = "pomodoro",
        notes: str = "",
    ) -> FocusSession:
        sessions = self.load_sessions()
        session = FocusSession(
            id=f"session-{uuid4().hex[:8]}",
            goal_id=goal_id,
            task_id=task_id,
            started_at=timestamp(),
            duration_seconds=duration_seconds,
            session_type=session_type,
            status=status,
            notes=notes,
        )
        sessions.append(session)
        self.save_sessions(sessions)
        return session
