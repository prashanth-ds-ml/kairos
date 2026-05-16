from __future__ import annotations

from datetime import date, datetime
from typing import Any

from PySide6.QtCore import QObject, Property, Signal, Slot

from .storage import FocusSession, Goal, JsonStore, Task, TodayPlan, TodayPlanItem


PRIORITY_LEVELS = ["P1", "P2", "P3", "P4", "P5"]
PRIORITY_ORDER = {priority: index for index, priority in enumerate(PRIORITY_LEVELS)}


def parse_target_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def format_target_date(value: str | None) -> str:
    parsed = parse_target_date(value)
    if parsed is None:
        return "No target date"
    return parsed.strftime("%d %b %Y")


def target_date_sort_key(value: str | None) -> tuple[int, str]:
    return (0, value) if value else (1, "9999-12-31")


def target_date_badge(value: str | None) -> str:
    parsed = parse_target_date(value)
    if parsed is None:
        return "No target date"
    today = date.today()
    if parsed < today:
        return f"Overdue | {format_target_date(value)}"
    if parsed == today:
        return "Due today"
    delta_days = (parsed - today).days
    if delta_days <= 3:
        return f"Due in {delta_days} day{'s' if delta_days != 1 else ''}"
    return f"Due {format_target_date(value)}"


def actionable_task(task: Task) -> bool:
    return task.status in {"todo", "in_progress"}


def task_status_sort_key(task: Task) -> int:
    return {
        "in_progress": 0,
        "todo": 1,
        "blocked": 2,
        "done": 3,
    }.get(task.status, 99)


def sorted_goals(goals: list[Goal]) -> list[Goal]:
    return sorted(
        goals,
        key=lambda goal: (
            PRIORITY_ORDER.get(goal.priority, 99),
            target_date_sort_key(goal.target_date),
            goal.category.lower(),
            goal.created_at,
        ),
    )


def active_execution_order(goals: list[Goal]) -> dict[str, int]:
    return {
        goal.id: index
        for index, goal in enumerate(
            sorted_goals([goal for goal in goals if goal.status == "active"]),
            start=1,
        )
    }


def priority_display(goal: Goal, execution_order: dict[str, int]) -> str:
    active_rank = execution_order.get(goal.id)
    if active_rank is None:
        return goal.priority
    return f"#{active_rank} | {goal.priority}"


def find_goal(goals: list[Goal], goal_id: str) -> Goal | None:
    return next((goal for goal in goals if goal.id == goal_id), None)


def find_task(goal: Goal, task_id: str | None) -> Task | None:
    if task_id is None:
        return None
    return next((task for task in goal.tasks if task.id == task_id), None)


def planned_focus_candidates(goals: list[Goal], today_plan: TodayPlan) -> list[tuple[Goal, Task | None]]:
    candidates: list[tuple[Goal, Task | None]] = []
    for item in today_plan.items:
        goal = find_goal(goals, item.goal_id)
        if goal is None or goal.status != "active":
            continue
        task = find_task(goal, item.task_id)
        if item.task_id is not None and (task is None or not actionable_task(task)):
            continue
        candidates.append((goal, task))
    return candidates


def choose_next_focus(goals: list[Goal], today_plan: TodayPlan) -> tuple[Goal | None, Task | None]:
    planned_candidates = planned_focus_candidates(goals, today_plan)
    if planned_candidates:
        planned_candidates.sort(
            key=lambda item: (
                PRIORITY_ORDER.get(item[0].priority, 99),
                target_date_sort_key(item[0].target_date),
                0 if item[1] is not None and item[1].status == "in_progress" else 1,
                task_status_sort_key(item[1]) if item[1] is not None else 99,
            ),
        )
        return planned_candidates[0]

    active_goals = sorted_goals([goal for goal in goals if goal.status == "active"])
    for goal in active_goals:
        tasks = sorted(goal.tasks, key=task_status_sort_key)
        next_task = next((task for task in tasks if actionable_task(task)), None)
        if next_task is not None:
            return goal, next_task

    if active_goals:
        return active_goals[0], None
    return None, None


def completed_focus_sessions(sessions: list[FocusSession]) -> list[FocusSession]:
    return [
        session
        for session in sessions
        if session.status == "completed" and session.session_type == "pomodoro"
    ]


def sessions_on_date(sessions: list[FocusSession], target: date) -> list[FocusSession]:
    items: list[FocusSession] = []
    for session in completed_focus_sessions(sessions):
        try:
            started = datetime.fromisoformat(session.started_at).date()
        except ValueError:
            continue
        if started == target:
            items.append(session)
    return items


class KairosController(QObject):
    changed = Signal()

    def __init__(self, store: JsonStore) -> None:
        super().__init__()
        self.store = store
        self.goals: list[Goal] = []
        self.sessions: list[FocusSession] = []
        self.today_plan = TodayPlan(plan_date=date.today().isoformat())
        self._active_goal_count = 0
        self._planned_today_text = "0/3"
        self._focus_minutes = 0
        self._today_focus_minutes = 0
        self._today_focus_sessions = 0
        self._suggestion_title = "Nothing is ready yet"
        self._suggestion_meta = "Add an active goal with at least one actionable task."
        self._can_start_focus = False
        self._planned_items: list[dict[str, Any]] = []
        self._available_items: list[dict[str, Any]] = []
        self._focus_target = "No focus target selected"
        self._focus_goal_id: str | None = None
        self._focus_task_id: str | None = None
        self._focus_items: list[dict[str, Any]] = []
        self._selected_focus_index = 0
        self._goal_items: list[dict[str, Any]] = []
        self._selected_goal_index = 0
        self._selected_goal: dict[str, Any] = {}
        self._selected_goal_tasks: list[dict[str, Any]] = []
        self._session_items: list[dict[str, Any]] = []
        self._open_task_count = 0
        self._done_task_count = 0
        self._blocked_task_count = 0
        self._completed_goal_count = 0
        self._recent_focusLabel = "No sessions yet"
        self._pomodoro_minutes = 25
        self._short_break_minutes = 5
        self._long_break_minutes = 15
        self.refresh()

    @Property(str, notify=changed)
    def todayLabel(self) -> str:
        return date.today().strftime("%A, %d %b %Y")

    @Property(int, notify=changed)
    def activeGoalCount(self) -> int:
        return self._active_goal_count

    @Property(str, notify=changed)
    def plannedTodayText(self) -> str:
        return self._planned_today_text

    @Property(int, notify=changed)
    def focusMinutes(self) -> int:
        return self._focus_minutes

    @Property(int, notify=changed)
    def todayFocusMinutes(self) -> int:
        return self._today_focus_minutes

    @Property(int, notify=changed)
    def todayFocusSessions(self) -> int:
        return self._today_focus_sessions

    @Property(str, notify=changed)
    def suggestionTitle(self) -> str:
        return self._suggestion_title

    @Property(str, notify=changed)
    def suggestionMeta(self) -> str:
        return self._suggestion_meta

    @Property(bool, notify=changed)
    def canStartFocus(self) -> bool:
        return self._can_start_focus

    @Property("QVariantList", notify=changed)
    def plannedItems(self) -> list[dict[str, Any]]:
        return self._planned_items

    @Property("QVariantList", notify=changed)
    def availableItems(self) -> list[dict[str, Any]]:
        return self._available_items

    @Property(str, notify=changed)
    def focusTarget(self) -> str:
        return self._focus_target

    @Property("QVariantList", notify=changed)
    def focusItems(self) -> list[dict[str, Any]]:
        return self._focus_items

    @Property(int, notify=changed)
    def selectedFocusIndex(self) -> int:
        return self._selected_focus_index

    @Property("QVariantList", notify=changed)
    def goalItems(self) -> list[dict[str, Any]]:
        return self._goal_items

    @Property(int, notify=changed)
    def selectedGoalIndex(self) -> int:
        return self._selected_goal_index

    @Property("QVariantMap", notify=changed)
    def selectedGoal(self) -> dict[str, Any]:
        return self._selected_goal

    @Property("QVariantList", notify=changed)
    def selectedGoalTasks(self) -> list[dict[str, Any]]:
        return self._selected_goal_tasks

    @Property("QVariantList", notify=changed)
    def sessionItems(self) -> list[dict[str, Any]]:
        return self._session_items

    @Property(int, notify=changed)
    def openTaskCount(self) -> int:
        return self._open_task_count

    @Property(int, notify=changed)
    def doneTaskCount(self) -> int:
        return self._done_task_count

    @Property(int, notify=changed)
    def blockedTaskCount(self) -> int:
        return self._blocked_task_count

    @Property(int, notify=changed)
    def completedGoalCount(self) -> int:
        return self._completed_goal_count

    @Property(str, notify=changed)
    def recentFocusLabel(self) -> str:
        return self._recent_focusLabel

    @Property(int, notify=changed)
    def pomodoroMinutes(self) -> int:
        return self._pomodoro_minutes

    @Property(int, notify=changed)
    def shortBreakMinutes(self) -> int:
        return self._short_break_minutes

    @Property(int, notify=changed)
    def longBreakMinutes(self) -> int:
        return self._long_break_minutes

    @Slot()
    def refresh(self) -> None:
        self.goals = self.store.load_goals()
        self.sessions = self.store.load_sessions()
        self.today_plan = self.store.load_today_plan()
        settings = self.store.load_settings()
        self._pomodoro_minutes = settings.pomodoro_minutes
        self._short_break_minutes = settings.short_break_minutes
        self._long_break_minutes = settings.long_break_minutes

        active_goals = [goal for goal in self.goals if goal.status == "active"]
        planned_candidates = planned_focus_candidates(self.goals, self.today_plan)
        completed_sessions = completed_focus_sessions(self.sessions)
        today_sessions = sessions_on_date(self.sessions, date.today())
        total_minutes = sum(session.duration_seconds for session in completed_sessions) // 60
        today_minutes = sum(session.duration_seconds for session in today_sessions) // 60
        all_tasks = [task for goal in self.goals for task in goal.tasks]

        self._active_goal_count = len(active_goals)
        self._planned_today_text = f"{len(planned_candidates)}/3"
        self._focus_minutes = total_minutes
        self._today_focus_minutes = today_minutes
        self._today_focus_sessions = len(today_sessions)
        self._open_task_count = len([task for task in all_tasks if task.status in {"todo", "in_progress"}])
        self._done_task_count = len([task for task in all_tasks if task.status == "done"])
        self._blocked_task_count = len([task for task in all_tasks if task.status == "blocked"])
        self._completed_goal_count = len([goal for goal in self.goals if goal.status == "completed"])

        suggested_goal, suggested_task = choose_next_focus(self.goals, self.today_plan)
        if suggested_goal is None:
            self._suggestion_title = "Nothing is ready yet"
            self._suggestion_meta = "Add an active goal with at least one actionable task."
            self._can_start_focus = False
        elif suggested_task is None:
            self._suggestion_title = suggested_goal.title
            self._suggestion_meta = (
                f"{target_date_badge(suggested_goal.target_date)} | "
                f"{suggested_goal.category} | Goal-level focus"
            )
            self._can_start_focus = True
        else:
            self._suggestion_title = f"{suggested_goal.title}: {suggested_task.title}"
            self._suggestion_meta = (
                f"{target_date_badge(suggested_goal.target_date)} | "
                f"{suggested_goal.category} | {suggested_task.status.replace('_', ' ')}"
            )
            self._can_start_focus = True

        self._planned_items = self._build_planned_items(planned_candidates)
        self._available_items = self._build_available_items(active_goals)
        previous_focus_key = (
            (self._focus_goal_id, self._focus_task_id)
            if self._focus_goal_id is not None
            else (
                suggested_goal.id if suggested_goal is not None else None,
                suggested_task.id if suggested_task is not None else None,
            )
        )
        self._focus_items = self._build_focus_items(active_goals)
        self._selected_focus_index = self._find_focus_index(previous_focus_key)
        self._goal_items = self._build_goal_items()
        self._session_items = self._build_session_items()
        if self._selected_goal_index >= len(self._goal_items):
            self._selected_goal_index = max(0, len(self._goal_items) - 1)
        self._set_selected_goal_from_index()
        self._recent_focusLabel = self._session_items[0]["title"] if self._session_items else "No sessions yet"
        self.changed.emit()

    @Slot(int)
    def addAvailableItem(self, index: int) -> None:
        if index < 0 or index >= len(self._available_items):
            return
        if len(self.today_plan.items) >= 3:
            return
        item = self._available_items[index]
        self.today_plan.items.append(TodayPlanItem(goal_id=item["goalId"], task_id=item["taskId"]))
        self.store.save_today_plan(self.today_plan)
        self.refresh()

    @Slot(int)
    def removePlannedItem(self, index: int) -> None:
        if index < 0 or index >= len(self._planned_items):
            return
        item = self._planned_items[index]
        self.today_plan.items = [
            plan_item
            for plan_item in self.today_plan.items
            if not (plan_item.goal_id == item["goalId"] and plan_item.task_id == item["taskId"])
        ]
        self.store.save_today_plan(self.today_plan)
        self.refresh()

    @Slot()
    def clearTodayPlan(self) -> None:
        self.today_plan.items = []
        self.store.save_today_plan(self.today_plan)
        self.refresh()

    @Slot()
    def autoPlanToday(self) -> None:
        active_goals = [goal for goal in self.goals if goal.status == "active"]
        planned = {(item.goal_id, item.task_id) for item in self.today_plan.items}
        candidates = self._build_focus_items(active_goals)
        for item in candidates:
            if len(self.today_plan.items) >= 3:
                break
            key = (item["goalId"], item["taskId"])
            if key in planned:
                continue
            self.today_plan.items.append(TodayPlanItem(goal_id=item["goalId"], task_id=item["taskId"]))
            planned.add(key)
        self.store.save_today_plan(self.today_plan)
        self.refresh()

    @Slot()
    def startFocus(self) -> None:
        selected_item = self._selected_focus_item()
        if selected_item is None:
            self._apply_suggested_focus()
        else:
            self._apply_focus_item(selected_item)
        self.changed.emit()

    @Slot()
    def startSuggestedFocus(self) -> None:
        self._apply_suggested_focus()
        self.changed.emit()

    @Slot(int)
    def selectFocusTarget(self, index: int) -> None:
        if index < 0 or index >= len(self._focus_items):
            return
        self._selected_focus_index = index
        self._apply_focus_item(self._focus_items[index])
        self.changed.emit()

    def _apply_focus_item(self, item: dict[str, Any]) -> None:
        self._focus_target = item["title"]
        self._focus_goal_id = item["goalId"]
        self._focus_task_id = item["taskId"]

    def _apply_suggested_focus(self) -> None:
        suggested_goal, suggested_task = choose_next_focus(self.goals, self.today_plan)
        if suggested_goal is None:
            self._focus_target = "No focus target selected"
            self._focus_goal_id = None
            self._focus_task_id = None
            return
        self._focus_goal_id = suggested_goal.id
        self._focus_task_id = suggested_task.id if suggested_task else None
        self._focus_target = (
            suggested_goal.title
            if suggested_task is None
            else f"{suggested_goal.title}: {suggested_task.title}"
        )
        self._selected_focus_index = self._find_focus_index((self._focus_goal_id, self._focus_task_id))

    def _selected_focus_item(self) -> dict[str, Any] | None:
        if not self._focus_items:
            return None
        if self._selected_focus_index < 0 or self._selected_focus_index >= len(self._focus_items):
            self._selected_focus_index = 0
        return self._focus_items[self._selected_focus_index]

    def _find_focus_index(self, focus_key: tuple[str | None, str | None]) -> int:
        for index, item in enumerate(self._focus_items):
            if (item["goalId"], item["taskId"]) == focus_key:
                self._apply_focus_item(item)
                return index
        if self._focus_items:
            self._apply_focus_item(self._focus_items[0])
        else:
            self._focus_target = "No focus target selected"
            self._focus_goal_id = None
            self._focus_task_id = None
        return 0

    @Slot(int)
    def selectGoal(self, index: int) -> None:
        if index < 0 or index >= len(self._goal_items):
            return
        self._selected_goal_index = index
        self._set_selected_goal_from_index()
        self.changed.emit()

    @Slot(str, str, str, str, str, str)
    def createGoal(
        self,
        title: str,
        category: str,
        priority: str,
        target_date: str,
        notes: str,
        task_lines: str,
    ) -> None:
        title = title.strip()
        if not title:
            return
        tasks = [line.strip() for line in task_lines.splitlines() if line.strip()]
        self.store.add_goal(
            title=title,
            category=category.strip() or "General",
            priority=priority.strip() or "P3",
            target_date=target_date.strip() or None,
            notes=notes.strip(),
            task_titles=tasks,
        )
        self._selected_goal_index = len(self.store.load_goals()) - 1
        self.refresh()

    @Slot(str, str, str, str, str)
    def updateSelectedGoal(self, title: str, category: str, priority: str, target_date: str, notes: str) -> None:
        if not self._selected_goal:
            return
        title = title.strip()
        if not title:
            return
        self.store.update_goal(
            self._selected_goal["id"],
            title,
            category.strip() or "General",
            priority.strip() or "P3",
            target_date.strip() or None,
            notes.strip(),
        )
        self.refresh()

    @Slot()
    def deleteSelectedGoal(self) -> None:
        if not self._selected_goal:
            return
        self.store.delete_goal(self._selected_goal["id"])
        self._selected_goal_index = max(0, self._selected_goal_index - 1)
        self.refresh()

    @Slot(str)
    def addTaskToSelectedGoal(self, title: str) -> None:
        if not self._selected_goal:
            return
        title = title.strip()
        if not title:
            return
        self.store.add_task(self._selected_goal["id"], title)
        self.refresh()

    @Slot(int, str)
    def updateSelectedTaskStatus(self, index: int, status: str) -> None:
        if not self._selected_goal or index < 0 or index >= len(self._selected_goal_tasks):
            return
        task = self._selected_goal_tasks[index]
        self.store.update_task_status(self._selected_goal["id"], task["id"], status)
        self.refresh()

    @Slot(int)
    def deleteSelectedTask(self, index: int) -> None:
        if not self._selected_goal or index < 0 or index >= len(self._selected_goal_tasks):
            return
        task = self._selected_goal_tasks[index]
        self.store.delete_task(self._selected_goal["id"], task["id"])
        self.refresh()

    @Slot(str)
    def updateSelectedGoalStatus(self, status: str) -> None:
        if not self._selected_goal:
            return
        self.store.update_goal_status(self._selected_goal["id"], status)
        self.refresh()

    @Slot(int, str)
    def completeFocusSession(self, duration_minutes: int, session_type: str) -> None:
        if self._focus_goal_id is None:
            suggested_goal, suggested_task = choose_next_focus(self.goals, self.today_plan)
            if suggested_goal is None:
                return
            self._focus_goal_id = suggested_goal.id
            self._focus_task_id = suggested_task.id if suggested_task else None
            self._focus_target = (
                suggested_goal.title
                if suggested_task is None
                else f"{suggested_goal.title}: {suggested_task.title}"
            )
        self.store.add_session(
            self._focus_goal_id,
            self._focus_task_id,
            max(1, duration_minutes) * 60,
            "completed",
            session_type=session_type or "pomodoro",
        )
        if session_type == "pomodoro" and self._focus_task_id:
            try:
                self.store.update_task_status(self._focus_goal_id, self._focus_task_id, "done")
            except ValueError:
                pass
        self.refresh()

    def _build_planned_items(self, planned_candidates: list[tuple[Goal, Task | None]]) -> list[dict[str, Any]]:
        execution_order = active_execution_order(self.goals)
        items: list[dict[str, Any]] = []
        for goal, task in planned_candidates:
            if task is None:
                items.append(
                    {
                        "title": goal.title,
                        "meta": f"{priority_display(goal, execution_order)} | {target_date_badge(goal.target_date)} | goal-level focus",
                        "goalId": goal.id,
                        "taskId": None,
                    }
                )
            else:
                items.append(
                    {
                        "title": task.title,
                        "meta": f"{priority_display(goal, execution_order)} | {goal.title} | {task.status.replace('_', ' ')}",
                        "goalId": goal.id,
                        "taskId": task.id,
                    }
                )
        return items

    def _build_goal_items(self) -> list[dict[str, Any]]:
        execution_order = active_execution_order(self.goals)
        items: list[dict[str, Any]] = []
        for goal in sorted_goals(self.goals):
            total_tasks = len(goal.tasks)
            done_tasks = len([task for task in goal.tasks if task.status == "done"])
            open_tasks = len([task for task in goal.tasks if task.status in {"todo", "in_progress"}])
            items.append(
                {
                    "id": goal.id,
                    "title": goal.title,
                    "category": goal.category,
                    "priority": goal.priority,
                    "status": goal.status,
                    "targetDate": goal.target_date or "",
                    "targetLabel": target_date_badge(goal.target_date),
                    "notes": goal.notes,
                    "meta": f"{priority_display(goal, execution_order)} | {goal.category} | {goal.status}",
                    "progressText": f"{done_tasks}/{total_tasks} done",
                    "openTasks": open_tasks,
                    "doneTasks": done_tasks,
                    "totalTasks": total_tasks,
                }
            )
        return items

    def _build_task_items(self, goal: Goal | None) -> list[dict[str, Any]]:
        if goal is None:
            return []
        return [
            {
                "id": task.id,
                "title": task.title,
                "status": task.status,
                "meta": f"{task.status.replace('_', ' ')} | created {task.created_at[:10]}",
            }
            for task in sorted(goal.tasks, key=task_status_sort_key)
        ]

    def _build_session_items(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        goals = {goal.id: goal for goal in self.goals}
        for session in sorted(self.sessions, key=lambda item: item.started_at, reverse=True):
            goal = goals.get(session.goal_id)
            task = find_task(goal, session.task_id) if goal is not None else None
            minutes = session.duration_seconds // 60
            started = self._format_session_time(session.started_at)
            title = goal.title if goal is not None else "Deleted goal"
            if task is not None:
                title = f"{title}: {task.title}"
            items.append(
                {
                    "title": title,
                    "meta": f"{minutes} min | {session.session_type.replace('_', ' ')} | {started}",
                    "status": session.status,
                    "notes": session.notes,
                }
            )
        return items

    def _set_selected_goal_from_index(self) -> None:
        if not self._goal_items:
            self._selected_goal = {}
            self._selected_goal_tasks = []
            return
        selected_item = self._goal_items[self._selected_goal_index]
        self._selected_goal = selected_item
        goal = find_goal(self.goals, selected_item["id"])
        self._selected_goal_tasks = self._build_task_items(goal)

    def _format_session_time(self, value: str) -> str:
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return value
        return parsed.strftime("%d %b, %I:%M %p")

    def _build_available_items(self, active_goals: list[Goal]) -> list[dict[str, Any]]:
        execution_order = active_execution_order(self.goals)
        planned_lookup = {(item.goal_id, item.task_id) for item in self.today_plan.items}
        items: list[dict[str, Any]] = []
        for goal in sorted_goals(active_goals):
            actionable_tasks = [task for task in sorted(goal.tasks, key=task_status_sort_key) if actionable_task(task)]
            if actionable_tasks:
                for task in actionable_tasks:
                    key = (goal.id, task.id)
                    if key in planned_lookup:
                        continue
                    items.append(
                        {
                            "title": task.title,
                            "meta": f"{priority_display(goal, execution_order)} | {goal.title} | {target_date_badge(goal.target_date)}",
                            "goalId": goal.id,
                            "taskId": task.id,
                        }
                    )
            else:
                key = (goal.id, None)
                if key in planned_lookup:
                    continue
                items.append(
                    {
                        "title": goal.title,
                        "meta": f"{priority_display(goal, execution_order)} | {target_date_badge(goal.target_date)} | goal-level focus",
                        "goalId": goal.id,
                        "taskId": None,
                    }
                )
        return items

    def _build_focus_items(self, active_goals: list[Goal]) -> list[dict[str, Any]]:
        execution_order = active_execution_order(self.goals)
        items: list[dict[str, Any]] = []
        for goal in sorted_goals(active_goals):
            actionable_tasks = [task for task in sorted(goal.tasks, key=task_status_sort_key) if actionable_task(task)]
            if actionable_tasks:
                for task in actionable_tasks:
                    items.append(
                        {
                            "title": f"{goal.title}: {task.title}",
                            "meta": f"{priority_display(goal, execution_order)} | {target_date_badge(goal.target_date)} | {task.status.replace('_', ' ')}",
                            "goalId": goal.id,
                            "taskId": task.id,
                        }
                    )
            else:
                items.append(
                    {
                        "title": goal.title,
                        "meta": f"{priority_display(goal, execution_order)} | {target_date_badge(goal.target_date)} | goal-level focus",
                        "goalId": goal.id,
                        "taskId": None,
                    }
                )
        return items
