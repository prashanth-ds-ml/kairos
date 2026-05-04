from __future__ import annotations

from datetime import date, datetime, timedelta

from PySide6.QtCore import QDate, QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QScrollArea,
    QStackedWidget,
    QStyle,
    QSystemTrayIcon,
    QTableWidget,
    QTableWidgetItem,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
    QLineEdit,
)

from .storage import AppSettings, FocusSession, Goal, JsonStore, Task, TodayPlan, TodayPlanItem


APP_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #eef1f5;
    color: #1f2937;
    font-size: 14px;
}
QLabel {
    background: transparent;
}
QWidget#appShell {
    background-color: #eef1f5;
}
QWidget#sidebarPanel {
    background-color: #f8fafc;
    border: 1px solid #d4dbe6;
    border-radius: 10px;
}
QLabel#brandTitle {
    font-size: 20px;
    font-weight: 700;
    color: #162238;
}
QLabel#brandSubtitle {
    color: #5f6b7a;
    font-size: 12px;
}
QListWidget#sidebarNav {
    background: transparent;
    border: none;
    outline: none;
    padding: 2px;
}
QListWidget#sidebarNav::item {
    padding: 10px 12px;
    border-radius: 6px;
    margin: 4px 0;
}
QListWidget#sidebarNav::item:selected {
    background: #e7ecf3;
    color: #1f2937;
    font-weight: 600;
    border-left: 3px solid #506784;
}
QWidget#contentPanel {
    background: transparent;
}
QWidget#statCard, QGroupBox {
    background-color: #ffffff;
    border: 1px solid #d4dbe6;
    border-radius: 8px;
    margin-top: 10px;
    padding-top: 10px;
}
QWidget#heroCard {
    background-color: #ffffff;
    border: 1px solid #d4dbe6;
    border-radius: 8px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
    color: #425268;
    font-weight: 600;
}
QLabel#pageTitle {
    font-size: 24px;
    font-weight: 700;
    color: #162238;
}
QLabel#pageSubtitle {
    color: #5f6b7a;
    font-size: 12px;
}
QLabel#sectionTitle {
    font-size: 16px;
    font-weight: 700;
    color: #162238;
}
QLabel#focusHeadline {
    font-size: 16px;
    font-weight: 700;
    color: #162238;
}
QLabel#focusSupport {
    color: #5f6b7a;
    font-size: 12px;
}
QLabel#heatmapLabel {
    color: #6b7280;
    font-size: 11px;
}
QLabel#statCaption {
    color: #6b7280;
    font-size: 11px;
}
QLabel#statValue {
    color: #162238;
    font-size: 22px;
    font-weight: 700;
}
QLabel#metricPill {
    background-color: #f8fafc;
    color: #374151;
    border: 1px solid #d8dee8;
    border-radius: 6px;
    padding: 8px 10px;
    font-weight: 600;
}
QPushButton {
    background-color: #f8fafc;
    color: #1f2937;
    border: 1px solid #c9d2df;
    border-radius: 6px;
    padding: 8px 12px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #eef2f7;
}
QPushButton:disabled {
    background-color: #f1f4f8;
    color: #a0acb9;
    border: 1px solid #d9e0e8;
}
QLineEdit, QPlainTextEdit, QComboBox, QDateEdit, QListWidget, QTableWidget {
    background-color: #ffffff;
    border: 1px solid #cfd6e0;
    border-radius: 6px;
    padding: 8px;
}
QListWidget, QTableWidget {
    padding: 8px;
}
QListWidget::item {
    padding: 8px 6px;
    border-radius: 4px;
    margin: 2px 0;
}
QListWidget::item:selected {
    background-color: #eceff4;
    color: #1f2937;
}
QListWidget#contentList {
    padding: 8px;
}
QListWidget#contentList::item {
    background-color: #ffffff;
    border: 1px solid #dde3eb;
    padding: 10px 12px;
    border-radius: 6px;
    margin: 4px 0;
}
QListWidget#contentList::item:selected {
    background-color: #eceff4;
    border: 1px solid #c7d0db;
}
QHeaderView::section {
    background-color: #f4f6f8;
    color: #4b5563;
    border: none;
    border-bottom: 1px solid #d6dde6;
    padding: 8px;
    font-weight: 600;
}
"""


PRIORITY_LEVELS = ["P1", "P2", "P3", "P4", "P5"]
PRIORITY_ORDER = {priority: index for index, priority in enumerate(PRIORITY_LEVELS)}
TASK_STATUSES = ["todo", "in_progress", "done", "blocked"]
TASK_STATUS_LABELS = {
    "todo": "To do",
    "in_progress": "In progress",
    "done": "Done",
    "blocked": "Blocked",
}


def format_minutes(duration_seconds: int) -> str:
    return f"{duration_seconds // 60} min"


def format_timer(total_seconds: int) -> str:
    minutes, seconds = divmod(max(total_seconds, 0), 60)
    return f"{minutes:02d}:{seconds:02d}"


def page_empty_state(message: str) -> QLabel:
    label = QLabel(message)
    label.setWordWrap(True)
    label.setAlignment(Qt.AlignmentFlag.AlignTop)
    label.setObjectName("pageSubtitle")
    return label


def make_label(text: str, object_name: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName(object_name)
    return label


def create_stat_card(title: str) -> tuple[QWidget, QLabel]:
    card = QWidget()
    card.setObjectName("statCard")
    card.setMinimumHeight(96)
    card.setMaximumHeight(110)
    layout = QVBoxLayout(card)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(4)
    caption = make_label(title, "statCaption")
    value = make_label("-", "statValue")
    layout.addWidget(caption)
    layout.addWidget(value)
    layout.addStretch()
    return card, value


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
        return f"Overdue • {format_target_date(value)}"
    if parsed == today:
        return "Due today"
    delta_days = (parsed - today).days
    if delta_days <= 3:
        return f"Due in {delta_days} day{'s' if delta_days != 1 else ''}"
    return f"Due {format_target_date(value)}"


def open_task_count(goal: Goal) -> int:
    return sum(1 for task in goal.tasks if task.status != "done")


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
    return f"Active #{active_rank} • {goal.priority}"


def find_goal(goals: list[Goal], goal_id: str) -> Goal | None:
    return next((goal for goal in goals if goal.id == goal_id), None)


def find_task(goal: Goal, task_id: str | None) -> Task | None:
    if task_id is None:
        return None
    return next((task for task in goal.tasks if task.id == task_id), None)


def planned_focus_candidates(
    goals: list[Goal],
    today_plan: TodayPlan | None,
) -> list[tuple[Goal, Task | None]]:
    if today_plan is None:
        return []

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


def choose_next_focus(
    goals: list[Goal],
    today_plan: TodayPlan | None = None,
) -> tuple[Goal | None, Task | None]:
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
    if not active_goals:
        return None, None

    for goal in active_goals:
        tasks = sorted(goal.tasks, key=task_status_sort_key)
        next_task = next((task for task in tasks if actionable_task(task)), None)
        if next_task is not None:
            return goal, next_task

    return active_goals[0], None


def phase_label_text(phase: str) -> str:
    return {
        "pomodoro": "Focus session",
        "short_break": "Short break",
        "long_break": "Long break",
    }.get(phase, phase)


def completed_focus_sessions(sessions: list[FocusSession]) -> list[FocusSession]:
    return [
        session
        for session in sessions
        if session.status == "completed" and session.session_type == "pomodoro"
    ]


def session_day(session: FocusSession) -> date | None:
    try:
        return datetime.fromisoformat(session.started_at).date()
    except ValueError:
        return None


def focus_minutes_by_day(sessions: list[FocusSession]) -> dict[date, int]:
    minutes_by_day: dict[date, int] = {}
    for session in completed_focus_sessions(sessions):
        day = session_day(session)
        if day is None:
            continue
        minutes_by_day[day] = minutes_by_day.get(day, 0) + (session.duration_seconds // 60)
    return minutes_by_day


def heatmap_color(minutes: int | None) -> str:
    if minutes is None:
        return "#f7f7f7"
    if minutes <= 0:
        return "#ebedf0"
    if minutes < 25:
        return "#d9f2d9"
    if minutes < 50:
        return "#9be9a8"
    if minutes < 125:
        return "#40c463"
    return "#216e39"


def streaks_from_minutes(minutes_by_day: dict[date, int], threshold: int = 25) -> tuple[int, int]:
    if not minutes_by_day:
        return 0, 0

    current_day = min(minutes_by_day)
    today = date.today()
    current_streak = 0
    longest_streak = 0
    active_streak = 0

    while current_day <= today:
        if minutes_by_day.get(current_day, 0) >= threshold:
            active_streak += 1
            longest_streak = max(longest_streak, active_streak)
        else:
            active_streak = 0
        current_day += timedelta(days=1)

    current_day = today
    while minutes_by_day.get(current_day, 0) >= threshold:
        current_streak += 1
        current_day -= timedelta(days=1)

    return current_streak, longest_streak


class TodayPage(QWidget):
    focus_requested = Signal(str, object)
    data_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.goals: list[Goal] = []
        self.today_plan = TodayPlan(plan_date=date.today().isoformat())
        self.available_targets: list[tuple[str, str | None]] = []
        self.planned_targets: list[tuple[str, str | None]] = []

        layout = QVBoxLayout(self)

        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        self.suggestion_label = QLabel()
        self.suggestion_label.setWordWrap(True)
        self.reason_label = QLabel()
        self.reason_label.setWordWrap(True)
        self.start_button = QPushButton("Start suggested focus")
        self.start_button.clicked.connect(self.emit_focus_request)
        self.today_plan_list = QListWidget()
        self.available_work_list = QListWidget()
        self.add_to_today_button = QPushButton("Add selected item to today")
        self.add_to_today_button.clicked.connect(self.add_selected_to_today)
        self.remove_from_today_button = QPushButton("Remove selected planned item")
        self.remove_from_today_button.clicked.connect(self.remove_selected_from_today)
        self.clear_today_button = QPushButton("Clear today plan")
        self.clear_today_button.clicked.connect(self.clear_today_plan)
        self.empty_label = page_empty_state(
            "Create your first goal in Goals. Once you have an active goal, target date, "
            "and a few tasks, Kairos will suggest what to work on next."
        )

        layout.addWidget(QLabel("Today"))
        layout.addWidget(self.summary_label)
        layout.addWidget(self.suggestion_label)
        layout.addWidget(self.reason_label)
        layout.addWidget(self.start_button)
        layout.addWidget(QLabel("Today's queue"))
        layout.addWidget(self.today_plan_list)
        layout.addWidget(self.remove_from_today_button)
        layout.addWidget(self.clear_today_button)
        layout.addWidget(QLabel("Available work"))
        layout.addWidget(self.available_work_list)
        layout.addWidget(self.add_to_today_button)
        layout.addWidget(self.empty_label)

        self.suggested_goal_id: str | None = None
        self.suggested_task_id: str | None = None

    def emit_focus_request(self) -> None:
        if self.suggested_goal_id is None:
            return
        self.focus_requested.emit(self.suggested_goal_id, self.suggested_task_id)

    def refresh(
        self,
        goals: list[Goal],
        sessions: list[FocusSession],
        today_plan: TodayPlan,
    ) -> None:
        self.goals = goals
        self.today_plan = today_plan
        active_goals = [goal for goal in goals if goal.status == "active"]
        execution_order = active_execution_order(goals)
        completed_sessions = completed_focus_sessions(sessions)
        total_minutes = sum(session.duration_seconds for session in completed_sessions) // 60
        planned_candidates = planned_focus_candidates(goals, today_plan)

        self.summary_label.setText(
            f"{len(active_goals)} active goals • {len(planned_candidates)} planned items today • "
            f"{total_minutes} completed focus minutes logged"
        )

        self.today_plan_list.clear()
        self.available_work_list.clear()
        self.available_targets = []
        self.planned_targets = []

        suggested_goal, suggested_task = choose_next_focus(goals, today_plan)
        self.suggested_goal_id = suggested_goal.id if suggested_goal else None
        self.suggested_task_id = suggested_task.id if suggested_task else None

        if not active_goals:
            self.suggestion_label.setText("Nothing queued yet.")
            self.reason_label.setText("")
            self.start_button.setEnabled(False)
            self.empty_label.show()
            return

        self.empty_label.hide()
        self.start_button.setEnabled(True)
        if suggested_goal is None:
            self.suggestion_label.setText("No active goal is ready for focus.")
            self.reason_label.setText("")
            self.start_button.setEnabled(False)
        elif suggested_task is None:
            self.suggestion_label.setText(f"Suggested next focus: {suggested_goal.title}")
            self.reason_label.setText(
                f"{target_date_badge(suggested_goal.target_date)}. "
                "This goal has no actionable task right now, so focus can happen at the goal level."
            )
        else:
            self.suggestion_label.setText(
                f"Suggested next focus: {suggested_goal.title} -> {suggested_task.title}"
            )
            self.reason_label.setText(
                f"{target_date_badge(suggested_goal.target_date)} • "
                f"Picked from your current priorities in {suggested_goal.category}."
            )

        planned_lookup = {(item.goal_id, item.task_id) for item in today_plan.items}
        for goal, task in planned_candidates:
            if task is None:
                label = f"{priority_display(goal, execution_order)} • {goal.title} • goal-level focus"
                key = (goal.id, None)
            else:
                label = f"{priority_display(goal, execution_order)} • {goal.title} -> {task.title}"
                key = (goal.id, task.id)
            self.today_plan_list.addItem(label)
            self.planned_targets.append(key)

        for goal in sorted_goals(active_goals):
            actionable_tasks = [task for task in sorted(goal.tasks, key=task_status_sort_key) if actionable_task(task)]
            if actionable_tasks:
                for task in actionable_tasks:
                    key = (goal.id, task.id)
                    if key in planned_lookup:
                        continue
                    self.available_work_list.addItem(
                        f"{priority_display(goal, execution_order)} • {goal.title} -> "
                        f"{task.title} [{TASK_STATUS_LABELS[task.status]}]"
                    )
                    self.available_targets.append(key)
            else:
                key = (goal.id, None)
                if key in planned_lookup:
                    continue
                self.available_work_list.addItem(
                    f"{priority_display(goal, execution_order)} • {goal.title} • "
                    f"goal-level focus • {target_date_badge(goal.target_date)}"
                )
                self.available_targets.append(key)

        if not planned_candidates:
            self.today_plan_list.addItem("No plan yet. Add 1-3 items for today.")
        if not self.available_targets:
            self.available_work_list.addItem("No more actionable items outside today's plan.")

    def add_selected_to_today(self) -> None:
        index = self.available_work_list.currentRow()
        if index < 0 or index >= len(self.available_targets):
            return
        if len(self.today_plan.items) >= 3:
            QMessageBox.information(
                self,
                "Today plan full",
                "Keep today's plan focused. Limit it to 3 items.",
            )
            return
        goal_id, task_id = self.available_targets[index]
        self.today_plan.items.append(TodayPlanItem(goal_id=goal_id, task_id=task_id))
        self.data_changed.emit()

    def remove_selected_from_today(self) -> None:
        index = self.today_plan_list.currentRow()
        if index < 0 or index >= len(self.planned_targets):
            return
        goal_id, task_id = self.planned_targets[index]
        self.today_plan.items = [
            item
            for item in self.today_plan.items
            if not (item.goal_id == goal_id and item.task_id == task_id)
        ]
        self.data_changed.emit()

    def clear_today_plan(self) -> None:
        if not self.today_plan.items:
            return
        self.today_plan.items = []
        self.data_changed.emit()


class DashboardPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        outer_layout.addWidget(scroll_area)

        scroll_content = QWidget()
        scroll_content.setObjectName("contentPanel")
        scroll_area.setWidget(scroll_content)

        center_layout = QHBoxLayout(scroll_content)
        center_layout.setContentsMargins(24, 24, 24, 24)
        center_layout.setSpacing(0)
        center_layout.addStretch(1)

        content_column = QWidget()
        content_column.setMaximumWidth(1380)
        center_layout.addWidget(content_column)
        center_layout.addStretch(1)

        layout = QVBoxLayout(content_column)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        self.page_title_label = make_label("Dashboard", "pageTitle")
        self.page_subtitle_label = make_label(
            "Track momentum, review consistency, and see what deserves your next block.",
            "pageSubtitle",
        )
        self.page_subtitle_label.setMaximumWidth(700)
        self.summary_card = QWidget()
        self.summary_card.setObjectName("heroCard")
        self.summary_card.setMinimumHeight(140)
        self.summary_card.setMaximumHeight(170)
        summary_layout = QVBoxLayout(self.summary_card)
        summary_layout.setContentsMargins(24, 22, 24, 22)
        summary_layout.setSpacing(8)
        self.suggestion_label = make_label("", "focusHeadline")
        self.suggestion_label.setWordWrap(True)
        self.reason_label = make_label("", "focusSupport")
        self.reason_label.setWordWrap(True)
        summary_layout.addWidget(make_label("Next focus", "sectionTitle"))
        summary_layout.addWidget(self.suggestion_label)
        summary_layout.addWidget(self.reason_label)

        self.guidance_label = page_empty_state(
            "Start by adding a goal, giving it a target date, and defining a few concrete tasks. "
            "Then use Today or Focus to begin a Pomodoro."
        )
        self.metrics_row = QHBoxLayout()
        self.metrics_row.setSpacing(14)
        active_card, self.active_goals_value = create_stat_card("Active goals")
        sessions_card, self.completed_sessions_value = create_stat_card("Completed sessions")
        minutes_card, self.focused_minutes_value = create_stat_card("Focused minutes")
        plan_card, self.planned_items_value = create_stat_card("Planned today")
        self.metrics_row.addWidget(active_card)
        self.metrics_row.addWidget(sessions_card)
        self.metrics_row.addWidget(minutes_card)
        self.metrics_row.addWidget(plan_card)

        self.heatmap_card = QGroupBox("Consistency heatmap")
        self.heatmap_card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        heatmap_layout = QVBoxLayout(self.heatmap_card)
        heatmap_layout.setContentsMargins(18, 22, 18, 18)
        heatmap_layout.setSpacing(10)
        self.heatmap_title_label = make_label("", "sectionTitle")
        self.heatmap_title_label.setWordWrap(True)
        self.heatmap_summary_label = make_label("", "pageSubtitle")
        self.heatmap_summary_label.setWordWrap(True)
        self.heatmap_grid = QGridLayout()
        self.heatmap_grid.setContentsMargins(0, 4, 0, 4)
        self.heatmap_grid.setHorizontalSpacing(3)
        self.heatmap_grid.setVerticalSpacing(3)
        self.heatmap_month_labels: list[QLabel] = []
        for column in range(53):
            label = make_label("", "heatmapLabel")
            label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
            self.heatmap_grid.addWidget(label, 0, column + 1)
            self.heatmap_month_labels.append(label)
        for row, text in ((0, "Mon"), (2, "Wed"), (4, "Fri")):
            label = make_label(text, "heatmapLabel")
            label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.heatmap_grid.addWidget(label, row + 1, 0)
        self.heatmap_cells: list[QLabel] = []
        for row in range(7):
            for column in range(53):
                cell = QLabel()
                cell.setFixedSize(12, 12)
                cell.setStyleSheet(
                    "background-color: #ebedf0; border: 1px solid #d0d7de; border-radius: 3px;"
                )
                self.heatmap_grid.addWidget(cell, row + 1, column + 1)
                self.heatmap_cells.append(cell)
        self.heatmap_legend = make_label(
            "0 min • 1-24 min • 25-49 min • 50-124 min • 125+ min"
            ,
            "pageSubtitle",
        )
        self.current_streak_label = QLabel()
        self.longest_streak_label = QLabel()
        self.success_days_label = QLabel()
        self.focused_days_month_label = QLabel()
        self.total_minutes_year_label = QLabel()
        stats_layout = QGridLayout()
        stats_layout.setSpacing(10)
        stats_layout.addWidget(self.current_streak_label, 0, 0)
        stats_layout.addWidget(self.longest_streak_label, 0, 1)
        stats_layout.addWidget(self.success_days_label, 0, 2)
        stats_layout.addWidget(self.focused_days_month_label, 1, 0)
        stats_layout.addWidget(self.total_minutes_year_label, 1, 1)
        heatmap_layout.addWidget(self.heatmap_title_label)
        heatmap_layout.addWidget(self.heatmap_summary_label)
        heatmap_layout.addLayout(self.heatmap_grid)
        heatmap_layout.addWidget(self.heatmap_legend)
        heatmap_layout.addLayout(stats_layout)

        self.active_goals_card = QGroupBox("Active goals")
        self.active_goals_card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        active_layout = QVBoxLayout(self.active_goals_card)
        active_layout.setContentsMargins(18, 22, 18, 18)
        self.active_goals = QListWidget()
        self.active_goals.setObjectName("contentList")
        self.active_goals.setSpacing(6)
        self.active_goals.setMinimumHeight(180)
        self.active_goals.setMaximumHeight(260)
        active_layout.addWidget(self.active_goals)

        self.recent_sessions_card = QGroupBox("Recent focus sessions")
        self.recent_sessions_card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        recent_layout = QVBoxLayout(self.recent_sessions_card)
        recent_layout.setContentsMargins(18, 22, 18, 18)
        self.recent_sessions = QListWidget()
        self.recent_sessions.setObjectName("contentList")
        self.recent_sessions.setSpacing(6)
        self.recent_sessions.setMinimumHeight(180)
        self.recent_sessions.setMaximumHeight(260)
        recent_layout.addWidget(self.recent_sessions)

        layout.addWidget(self.page_title_label)
        layout.addWidget(self.page_subtitle_label)
        layout.addLayout(self.metrics_row)
        layout.addWidget(self.summary_card)
        layout.addWidget(self.guidance_label)
        layout.addWidget(self.heatmap_card)

        lower_layout = QHBoxLayout()
        lower_layout.setSpacing(16)
        lower_layout.addWidget(self.active_goals_card, 3)
        lower_layout.addWidget(self.recent_sessions_card, 2)
        layout.addLayout(lower_layout)
        layout.addStretch(1)

    def refresh(
        self,
        goals: list[Goal],
        sessions: list[FocusSession],
        today_plan: TodayPlan,
    ) -> None:
        active_goals = [goal for goal in goals if goal.status == "active"]
        execution_order = active_execution_order(goals)
        focus_sessions = completed_focus_sessions(sessions)
        total_minutes = sum(session.duration_seconds for session in focus_sessions) // 60
        suggested_goal, suggested_task = choose_next_focus(goals, today_plan)
        minutes_by_day = focus_minutes_by_day(sessions)
        current_streak, longest_streak = streaks_from_minutes(minutes_by_day)
        today = date.today()
        success_days = sum(
            1
            for day, minutes in minutes_by_day.items()
            if day.year == today.year and minutes >= 25
        )
        focused_days_month = sum(
            1
            for day, minutes in minutes_by_day.items()
            if day.year == today.year and day.month == today.month and minutes > 0
        )
        total_minutes_year = sum(
            minutes
            for day, minutes in minutes_by_day.items()
            if day.year == today.year
        )

        self.active_goals_value.setText(str(len(active_goals)))
        self.completed_sessions_value.setText(str(len(focus_sessions)))
        self.focused_minutes_value.setText(str(total_minutes))
        self.planned_items_value.setText(str(len(today_plan.items)))
        if suggested_goal is None:
            self.suggestion_label.setText("Suggested next focus: nothing queued yet.")
            self.reason_label.setText("Create an active goal with at least one actionable task.")
        elif suggested_task is None:
            self.suggestion_label.setText(f"Suggested next focus: {suggested_goal.title}")
            self.reason_label.setText(
                f"{target_date_badge(suggested_goal.target_date)} • "
                "This goal has no actionable task, so focus can happen at the goal level."
            )
        else:
            self.suggestion_label.setText(
                f"Suggested next focus: {suggested_goal.title} -> {suggested_task.title}"
            )
            self.reason_label.setText(
                f"{target_date_badge(suggested_goal.target_date)} • "
                f"Next actionable task in {suggested_goal.category}."
            )

        self.heatmap_title_label.setText(f"Contribution-style focus map for {today.year}")
        self.heatmap_summary_label.setText(
            "Each square is one day. A successful day means at least 25 completed focus minutes."
        )
        self.render_heatmap(minutes_by_day, today.year)
        self.current_streak_label.setText(f"Current streak: {current_streak} day(s)")
        self.current_streak_label.setObjectName("metricPill")
        self.longest_streak_label.setText(f"Longest streak: {longest_streak} day(s)")
        self.longest_streak_label.setObjectName("metricPill")
        self.success_days_label.setText(f"25+ min days this year: {success_days}")
        self.success_days_label.setObjectName("metricPill")
        self.focused_days_month_label.setText(f"Focused days this month: {focused_days_month}")
        self.focused_days_month_label.setObjectName("metricPill")
        self.total_minutes_year_label.setText(f"Focus minutes this year: {total_minutes_year}")
        self.total_minutes_year_label.setObjectName("metricPill")
        for label in (
            self.current_streak_label,
            self.longest_streak_label,
            self.success_days_label,
            self.focused_days_month_label,
            self.total_minutes_year_label,
        ):
            label.style().unpolish(label)
            label.style().polish(label)

        self.active_goals.clear()
        self.recent_sessions.clear()

        if not goals:
            self.guidance_label.show()
            return

        self.guidance_label.hide()
        if not active_goals:
            self.active_goals.addItem("No active goals yet.")
        else:
            for goal in sorted_goals(active_goals):
                self.active_goals.addItem(
                    f"{priority_display(goal, execution_order)} • {goal.category} • {goal.title} "
                    f"({open_task_count(goal)} open tasks) • {target_date_badge(goal.target_date)}"
                )

        if not sessions:
            self.recent_sessions.addItem("No focus sessions logged yet.")
            return

        for session in sessions[-5:][::-1]:
            self.recent_sessions.addItem(
                f"{session.started_at} • {phase_label_text(session.session_type)} • "
                f"{session.status} • {format_minutes(session.duration_seconds)}"
            )

    def render_heatmap(self, minutes_by_day: dict[date, int], year: int) -> None:
        jan_1 = date(year, 1, 1)
        dec_31 = date(year, 12, 31)
        start_day = jan_1 - timedelta(days=jan_1.weekday())
        total_weeks = ((dec_31 - start_day).days // 7) + 1

        last_month = None
        for column, label in enumerate(self.heatmap_month_labels):
            if column >= total_weeks:
                label.setText("")
                continue
            week_start = start_day + timedelta(weeks=column)
            month_text = ""
            for day_offset in range(7):
                current_day = week_start + timedelta(days=day_offset)
                if current_day.year != year:
                    continue
                if current_day.day == 1 and current_day.month != last_month:
                    month_text = current_day.strftime("%b")
                    last_month = current_day.month
                    break
            label.setText(month_text)

        for week in range(53):
            for weekday in range(7):
                index = (weekday * 53) + week
                cell = self.heatmap_cells[index]
                current_day = start_day + timedelta(weeks=week, days=weekday)
                if week >= total_weeks or current_day.year != year:
                    minutes = None
                elif current_day > date.today():
                    minutes = None
                else:
                    minutes = minutes_by_day.get(current_day, 0)
                cell.setStyleSheet(
                    "background-color: "
                    f"{heatmap_color(minutes)}; border: 1px solid #d0d7de; border-radius: 3px;"
                )
                if minutes is None:
                    if current_day.year != year or week >= total_weeks:
                        cell.setToolTip(f"{current_day.isoformat()} • outside current contribution year")
                    else:
                        cell.setToolTip(f"{current_day.isoformat()} • future day")
                else:
                    cell.setToolTip(f"{current_day.isoformat()} • {minutes} focus min")


class GoalsPage(QWidget):
    data_changed = Signal()

    def __init__(self, store: JsonStore) -> None:
        super().__init__()
        self.store = store
        self.goals: list[Goal] = []
        self.editing_goal_id: str | None = None

        root = QHBoxLayout(self)

        editor_box = QGroupBox("Goal editor")
        editor_layout = QVBoxLayout(editor_box)
        form = QFormLayout()
        self.goal_title = QLineEdit()
        self.category = QLineEdit()
        self.category.setPlaceholderText("Learning, Career, Health...")
        self.priority = QComboBox()
        self.priority.addItems(PRIORITY_LEVELS)
        self.has_target_date = QCheckBox("Set target date")
        self.has_target_date.toggled.connect(self.toggle_target_date)
        self.target_date = QDateEdit()
        self.target_date.setCalendarPopup(True)
        self.target_date.setDisplayFormat("yyyy-MM-dd")
        self.target_date.setDate(QDate.currentDate())
        self.target_date.setEnabled(False)
        self.notes = QPlainTextEdit()
        self.notes.setPlaceholderText("Why this goal matters...")
        self.notes.setFixedHeight(90)
        self.initial_tasks = QPlainTextEdit()
        self.initial_tasks.setPlaceholderText("Optional: one task per line")
        self.initial_tasks.setFixedHeight(110)
        form.addRow("Goal", self.goal_title)
        form.addRow("Category", self.category)
        form.addRow("Priority", self.priority)
        form.addRow(self.has_target_date, self.target_date)
        form.addRow("Notes", self.notes)
        form.addRow("Initial tasks", self.initial_tasks)

        self.editor_hint = QLabel(
            "Create a goal here. When editing an existing goal, use the task controls on the right."
        )
        self.editor_hint.setWordWrap(True)
        self.save_goal_button = QPushButton("Add goal")
        self.save_goal_button.clicked.connect(self.save_goal)
        self.cancel_edit_button = QPushButton("Cancel edit")
        self.cancel_edit_button.clicked.connect(self.reset_form)
        self.cancel_edit_button.setEnabled(False)

        editor_layout.addLayout(form)
        editor_layout.addWidget(self.editor_hint)
        editor_layout.addWidget(self.save_goal_button)
        editor_layout.addWidget(self.cancel_edit_button)
        editor_layout.addStretch()

        browser_layout = QVBoxLayout()
        goals_box = QGroupBox("Goals")
        goals_layout = QVBoxLayout(goals_box)
        self.empty_goals_label = page_empty_state(
            "No goals yet. Add your first goal on the left with a target date and a few tasks."
        )
        self.goal_list = QListWidget()
        self.goal_list.currentItemChanged.connect(self.load_goal_details)
        self.new_goal_button = QPushButton("New goal")
        self.new_goal_button.clicked.connect(self.reset_form)
        self.edit_goal_button = QPushButton("Edit selected goal")
        self.edit_goal_button.clicked.connect(self.start_editing_selected_goal)
        self.toggle_goal_button = QPushButton("Mark completed")
        self.toggle_goal_button.clicked.connect(self.toggle_goal_status)
        self.archive_goal_button = QPushButton("Archive goal")
        self.archive_goal_button.clicked.connect(self.toggle_goal_archive)
        self.delete_goal_button = QPushButton("Delete goal")
        self.delete_goal_button.clicked.connect(self.delete_selected_goal)

        goals_layout.addWidget(self.empty_goals_label)
        goals_layout.addWidget(self.goal_list)
        goals_layout.addWidget(self.new_goal_button)
        goals_layout.addWidget(self.edit_goal_button)
        goals_layout.addWidget(self.toggle_goal_button)
        goals_layout.addWidget(self.archive_goal_button)
        goals_layout.addWidget(self.delete_goal_button)

        tasks_box = QGroupBox("Selected goal details")
        tasks_layout = QVBoxLayout(tasks_box)
        self.goal_summary = page_empty_state("Select a goal to review its details and tasks.")
        self.task_list = QListWidget()
        self.task_list.currentItemChanged.connect(self.on_task_selection_changed)
        self.add_task_button = QPushButton("Add task")
        self.add_task_button.clicked.connect(self.add_task)
        self.rename_task_button = QPushButton("Rename task")
        self.rename_task_button.clicked.connect(self.rename_task)
        self.task_status = QComboBox()
        for status in TASK_STATUSES:
            self.task_status.addItem(TASK_STATUS_LABELS[status], userData=status)
        self.set_task_status_button = QPushButton("Set task status")
        self.set_task_status_button.clicked.connect(self.set_task_status)
        self.delete_task_button = QPushButton("Delete task")
        self.delete_task_button.clicked.connect(self.delete_task)

        tasks_layout.addWidget(self.goal_summary)
        tasks_layout.addWidget(self.task_list)
        tasks_layout.addWidget(self.add_task_button)
        tasks_layout.addWidget(self.rename_task_button)
        tasks_layout.addWidget(self.task_status)
        tasks_layout.addWidget(self.set_task_status_button)
        tasks_layout.addWidget(self.delete_task_button)

        browser_layout.addWidget(goals_box)
        browser_layout.addWidget(tasks_box)

        root.addWidget(editor_box, 2)
        root.addLayout(browser_layout, 3)

        self.update_form_mode()
        self.update_action_state()

    def current_goal_id(self) -> str | None:
        item = self.goal_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def current_goal(self) -> Goal | None:
        goal_id = self.current_goal_id()
        if goal_id is None:
            return None
        return next((goal for goal in self.goals if goal.id == goal_id), None)

    def current_task_id(self) -> str | None:
        item = self.task_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def current_task(self) -> Task | None:
        goal = self.current_goal()
        task_id = self.current_task_id()
        if goal is None or task_id is None:
            return None
        return next((task for task in goal.tasks if task.id == task_id), None)

    def refresh(self, goals: list[Goal]) -> None:
        self.goals = sorted_goals(goals)
        execution_order = active_execution_order(goals)
        selected_goal_id = self.current_goal_id()

        self.goal_list.clear()
        for goal in self.goals:
            item = QListWidgetItem(
                f"{priority_display(goal, execution_order)} • {goal.category} • "
                f"{goal.title} [{goal.status}] • "
                f"{open_task_count(goal)} open tasks • {target_date_badge(goal.target_date)}"
            )
            item.setData(Qt.ItemDataRole.UserRole, goal.id)
            self.goal_list.addItem(item)

        if goals:
            self.empty_goals_label.hide()
        else:
            self.empty_goals_label.show()

        if selected_goal_id:
            for index in range(self.goal_list.count()):
                item = self.goal_list.item(index)
                if item.data(Qt.ItemDataRole.UserRole) == selected_goal_id:
                    self.goal_list.setCurrentRow(index)
                    break

        if self.goal_list.count() and self.goal_list.currentRow() == -1:
            self.goal_list.setCurrentRow(0)
        else:
            self.load_goal_details()

        if self.editing_goal_id and not any(goal.id == self.editing_goal_id for goal in goals):
            self.reset_form()

        self.update_action_state()

    def save_goal(self) -> None:
        title = self.goal_title.text().strip()
        category = self.category.text().strip() or "General"
        notes = self.notes.toPlainText().strip()
        if not title:
            QMessageBox.warning(self, "Missing goal", "Enter a goal title first.")
            return

        target_date = (
            self.target_date.date().toString("yyyy-MM-dd")
            if self.has_target_date.isChecked()
            else None
        )

        if self.editing_goal_id is None:
            task_titles = [
                line.strip()
                for line in self.initial_tasks.toPlainText().splitlines()
                if line.strip()
            ]
            self.store.add_goal(
                title,
                category,
                self.priority.currentText(),
                target_date,
                notes,
                task_titles=task_titles,
            )
        else:
            self.store.update_goal(
                self.editing_goal_id,
                title,
                category,
                self.priority.currentText(),
                target_date,
                notes,
            )

        self.reset_form()
        self.data_changed.emit()

    def start_editing_selected_goal(self) -> None:
        goal = self.current_goal()
        if goal is None:
            QMessageBox.warning(self, "No goal selected", "Select a goal to edit.")
            return

        self.editing_goal_id = goal.id
        self.goal_title.setText(goal.title)
        self.category.setText(goal.category)
        self.priority.setCurrentText(goal.priority)
        if goal.target_date:
            self.has_target_date.setChecked(True)
            parsed = parse_target_date(goal.target_date)
            if parsed is not None:
                self.target_date.setDate(QDate(parsed.year, parsed.month, parsed.day))
        else:
            self.has_target_date.setChecked(False)
            self.target_date.setDate(QDate.currentDate())
        self.notes.setPlainText(goal.notes)
        self.initial_tasks.clear()
        self.update_form_mode()

    def reset_form(self) -> None:
        self.editing_goal_id = None
        self.goal_title.clear()
        self.category.clear()
        self.priority.setCurrentIndex(0)
        self.has_target_date.setChecked(False)
        self.target_date.setDate(QDate.currentDate())
        self.notes.clear()
        self.initial_tasks.clear()
        self.update_form_mode()

    def toggle_target_date(self, checked: bool) -> None:
        self.target_date.setEnabled(checked)

    def update_form_mode(self) -> None:
        editing = self.editing_goal_id is not None
        self.save_goal_button.setText("Save goal changes" if editing else "Add goal")
        self.cancel_edit_button.setEnabled(editing)
        self.initial_tasks.setEnabled(not editing)
        if editing:
            self.initial_tasks.setPlaceholderText("Use the task controls on the right while editing.")
            self.editor_hint.setText(
                "You are editing goal details. Tasks are managed explicitly in the selected goal panel."
            )
        else:
            self.initial_tasks.setPlaceholderText("Optional: one task per line")
            self.editor_hint.setText(
                "Create a goal here. When editing an existing goal, use the task controls on the right."
            )

    def load_goal_details(self, *_args: object) -> None:
        self.task_list.clear()
        goal = self.current_goal()
        if goal is None:
            self.goal_summary.setText("Select a goal to review its details and tasks.")
            self.update_action_state()
            return

        todo_count = sum(1 for task in goal.tasks if task.status == "todo")
        in_progress_count = sum(1 for task in goal.tasks if task.status == "in_progress")
        blocked_count = sum(1 for task in goal.tasks if task.status == "blocked")
        done_count = sum(1 for task in goal.tasks if task.status == "done")
        execution_order = active_execution_order(self.goals)
        self.goal_summary.setText(
            f"{goal.title}\n"
            f"{goal.category} • {priority_display(goal, execution_order)} • "
            f"{goal.status} • {target_date_badge(goal.target_date)}\n"
            f"Todo: {todo_count} • In progress: {in_progress_count} • "
            f"Blocked: {blocked_count} • Done: {done_count}\n\n"
            f"{goal.notes or 'No notes yet.'}"
        )

        if not goal.tasks:
            self.task_list.addItem("No tasks yet. Add one below.")
        else:
            for task in sorted(goal.tasks, key=task_status_sort_key):
                item = QListWidgetItem(f"{task.title} [{TASK_STATUS_LABELS.get(task.status, task.status)}]")
                item.setData(Qt.ItemDataRole.UserRole, task.id)
                self.task_list.addItem(item)

        self.on_task_selection_changed()
        self.update_action_state()

    def update_action_state(self) -> None:
        goal = self.current_goal()
        has_goal = goal is not None
        task = self.current_task()
        has_task = task is not None

        self.edit_goal_button.setEnabled(has_goal)
        self.toggle_goal_button.setEnabled(has_goal and goal.status != "archived")
        self.archive_goal_button.setEnabled(has_goal)
        self.delete_goal_button.setEnabled(has_goal)
        self.add_task_button.setEnabled(has_goal)
        self.rename_task_button.setEnabled(has_task)
        self.task_status.setEnabled(has_task)
        self.set_task_status_button.setEnabled(has_task)
        self.delete_task_button.setEnabled(has_task)

        if not has_goal:
            self.toggle_goal_button.setText("Mark completed")
            self.archive_goal_button.setText("Archive goal")
            return

        self.toggle_goal_button.setText(
            "Mark active" if goal.status == "completed" else "Mark completed"
        )
        self.archive_goal_button.setText(
            "Restore goal" if goal.status == "archived" else "Archive goal"
        )

    def on_task_selection_changed(self, *_args: object) -> None:
        task = self.current_task()
        if task is None:
            self.task_status.setCurrentIndex(0)
            self.update_action_state()
            return
        index = self.task_status.findData(task.status)
        if index >= 0:
            self.task_status.setCurrentIndex(index)
        self.update_action_state()

    def toggle_goal_status(self) -> None:
        goal = self.current_goal()
        if goal is None:
            return
        next_status = "completed" if goal.status == "active" else "active"
        self.store.update_goal_status(goal.id, next_status)
        self.data_changed.emit()

    def toggle_goal_archive(self) -> None:
        goal = self.current_goal()
        if goal is None:
            return
        next_status = "active" if goal.status == "archived" else "archived"
        self.store.update_goal_status(goal.id, next_status)
        self.data_changed.emit()

    def delete_selected_goal(self) -> None:
        goal = self.current_goal()
        if goal is None:
            return
        answer = QMessageBox.question(
            self,
            "Delete goal",
            f"Delete '{goal.title}' and all of its tasks?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        if self.editing_goal_id == goal.id:
            self.reset_form()
        self.store.delete_goal(goal.id)
        self.data_changed.emit()

    def add_task(self) -> None:
        goal = self.current_goal()
        if goal is None:
            return
        task_title, accepted = QInputDialog.getText(self, "Add task", "Task title")
        if accepted and task_title.strip():
            self.store.add_task(goal.id, task_title.strip())
            self.data_changed.emit()

    def rename_task(self) -> None:
        task = self.current_task()
        goal = self.current_goal()
        if goal is None or task is None:
            return
        updated_title, accepted = QInputDialog.getText(
            self,
            "Rename task",
            "Task title",
            text=task.title,
        )
        if accepted and updated_title.strip():
            self.store.rename_task(goal.id, task.id, updated_title.strip())
            self.data_changed.emit()

    def set_task_status(self) -> None:
        task = self.current_task()
        goal = self.current_goal()
        if goal is None or task is None:
            return
        next_status = self.task_status.currentData()
        if next_status == task.status:
            return
        self.store.update_task_status(goal.id, task.id, next_status)
        self.data_changed.emit()

    def delete_task(self) -> None:
        task = self.current_task()
        goal = self.current_goal()
        if goal is None or task is None:
            return
        answer = QMessageBox.question(
            self,
            "Delete task",
            f"Delete task '{task.title}' from '{goal.title}'?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.store.delete_task(goal.id, task.id)
        self.data_changed.emit()


class FocusPage(QWidget):
    data_changed = Signal()
    notification_requested = Signal(str, str)

    def __init__(self, store: JsonStore) -> None:
        super().__init__()
        self.store = store
        self.goals: list[Goal] = []
        self.settings = AppSettings()
        self.completed_pomodoros = 0
        self.current_phase = "pomodoro"
        self.active_goal_id: str | None = None
        self.active_task_id: str | None = None
        self.last_focus_goal_id: str | None = None
        self.last_focus_task_id: str | None = None
        self.total_seconds = 0
        self.remaining_seconds = 0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)

        layout = QVBoxLayout(self)

        self.empty_label = page_empty_state(
            "No active goals yet. Create a goal first, then return here to start a Pomodoro."
        )
        self.phase_label = QLabel()
        self.phase_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.phase_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.cycle_label = QLabel()
        self.cycle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.goal_combo = QComboBox()
        self.goal_combo.currentIndexChanged.connect(self.populate_tasks)
        self.task_combo = QComboBox()
        self.timer_label = QLabel("25:00")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_label.setStyleSheet("font-size: 40px; font-weight: bold;")
        self.state_label = QLabel("Ready to focus.")
        self.state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.session_notes = QPlainTextEdit()
        self.session_notes.setPlaceholderText("Optional note: what will you finish in this focus block?")
        self.session_notes.setFixedHeight(90)

        self.start_button = QPushButton("Start focus session")
        self.start_button.clicked.connect(self.start_session)
        self.complete_button = QPushButton("Complete now")
        self.complete_button.clicked.connect(self.complete_session)
        self.complete_button.setEnabled(False)
        self.stop_button = QPushButton("Interrupt")
        self.stop_button.clicked.connect(self.interrupt_session)
        self.stop_button.setEnabled(False)
        self.skip_button = QPushButton("Skip break")
        self.skip_button.clicked.connect(self.skip_break)
        self.skip_button.setEnabled(False)

        layout.addWidget(self.empty_label)
        layout.addWidget(self.phase_label)
        layout.addWidget(self.cycle_label)
        layout.addWidget(QLabel("Goal"))
        layout.addWidget(self.goal_combo)
        layout.addWidget(QLabel("Task"))
        layout.addWidget(self.task_combo)
        layout.addWidget(self.timer_label)
        layout.addWidget(self.state_label)
        layout.addWidget(QLabel("Session note"))
        layout.addWidget(self.session_notes)
        layout.addWidget(self.start_button)
        layout.addWidget(self.complete_button)
        layout.addWidget(self.stop_button)
        layout.addWidget(self.skip_button)
        layout.addStretch()

        self.prepare_phase("pomodoro", "Ready to focus.")

    def refresh(
        self,
        goals: list[Goal],
        settings: AppSettings,
        sessions: list[FocusSession],
    ) -> None:
        self.goals = sorted_goals([goal for goal in goals if goal.status == "active"])
        execution_order = active_execution_order(goals)
        self.settings = settings
        self.completed_pomodoros = len(
            [
                session
                for session in sessions
                if session.status == "completed" and session.session_type == "pomodoro"
            ]
        )

        current_goal_id = self.goal_combo.currentData()
        self.goal_combo.blockSignals(True)
        self.goal_combo.clear()
        for goal in self.goals:
            self.goal_combo.addItem(
                f"{priority_display(goal, execution_order)} • {goal.category} • "
                f"{goal.title} • {target_date_badge(goal.target_date)}",
                userData=goal.id,
            )
        self.goal_combo.blockSignals(False)

        if current_goal_id is not None:
            index = self.goal_combo.findData(current_goal_id)
            if index >= 0:
                self.goal_combo.setCurrentIndex(index)

        if self.goal_combo.count() and self.goal_combo.currentIndex() == -1:
            self.goal_combo.setCurrentIndex(0)

        self.populate_tasks()
        self.empty_label.setVisible(not self.goals and self.current_phase == "pomodoro")
        self.update_phase_ui()

    def select_target(self, goal_id: str, task_id: object) -> None:
        goal_index = self.goal_combo.findData(goal_id)
        if goal_index >= 0:
            self.goal_combo.setCurrentIndex(goal_index)
            self.populate_tasks()
        if task_id is not None:
            task_index = self.task_combo.findData(task_id)
            if task_index >= 0:
                self.task_combo.setCurrentIndex(task_index)
        self.state_label.setText("Loaded suggested focus from Today.")

    def populate_tasks(self) -> None:
        goal_id = self.goal_combo.currentData()
        self.task_combo.clear()
        self.task_combo.addItem("No task selected", userData=None)
        if goal_id is None:
            return
        goal = next((item for item in self.goals if item.id == goal_id), None)
        if goal is None:
            return
        for task in sorted(goal.tasks, key=task_status_sort_key):
            if actionable_task(task):
                self.task_combo.addItem(
                    f"{task.title} [{TASK_STATUS_LABELS[task.status]}]",
                    userData=task.id,
                )

    def phase_seconds(self, phase: str) -> int:
        if phase == "long_break":
            return self.settings.long_break_minutes * 60
        if phase == "short_break":
            return self.settings.short_break_minutes * 60
        return self.settings.pomodoro_minutes * 60

    def prepare_phase(self, phase: str, message: str) -> None:
        self.current_phase = phase
        self.total_seconds = self.phase_seconds(phase)
        self.remaining_seconds = self.total_seconds
        self.timer_label.setText(format_timer(self.remaining_seconds))
        self.state_label.setText(message)
        if phase == "pomodoro":
            self.session_notes.setEnabled(True)
            self.session_notes.setPlaceholderText(
                "Optional note: what will you finish in this focus block?"
            )
            self.skip_button.setEnabled(False)
        else:
            self.session_notes.setEnabled(False)
            self.session_notes.setPlaceholderText("Notes are only recorded for focus sessions.")
            self.skip_button.setEnabled(True)
        self.update_phase_ui()

    def update_phase_ui(self) -> None:
        self.phase_label.setText(phase_label_text(self.current_phase))
        cycle_position = (self.completed_pomodoros % self.settings.sessions_before_long_break) + 1
        self.cycle_label.setText(
            f"Next long break after focus block {self.settings.sessions_before_long_break}. "
            f"You are on block {cycle_position}."
        )
        if self.current_phase == "pomodoro":
            self.start_button.setText("Start focus session")
        else:
            self.start_button.setText(f"Start {phase_label_text(self.current_phase).lower()}")
        if self.timer.isActive():
            self.start_button.setEnabled(False)
            self.complete_button.setEnabled(True)
            self.stop_button.setEnabled(True)
            self.skip_button.setEnabled(self.current_phase != "pomodoro")
        else:
            no_focus_target = not self.goals and self.current_phase == "pomodoro"
            self.start_button.setEnabled(not no_focus_target)
            self.complete_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            self.skip_button.setEnabled(self.current_phase != "pomodoro")

    def start_session(self) -> None:
        if self.current_phase == "pomodoro":
            goal_id = self.goal_combo.currentData()
            if goal_id is None:
                QMessageBox.warning(
                    self,
                    "No goal selected",
                    "Create or select an active goal first.",
                )
                return
            self.active_goal_id = goal_id
            self.active_task_id = self.task_combo.currentData()
            selected_task = next(
                (
                    task
                    for goal in self.goals
                    if goal.id == goal_id
                    for task in goal.tasks
                    if task.id == self.active_task_id
                ),
                None,
            )
            if selected_task is not None and selected_task.status == "todo":
                self.store.update_task_status(goal_id, selected_task.id, "in_progress")
                selected_task.status = "in_progress"
        else:
            if self.last_focus_goal_id is None:
                self.prepare_phase("pomodoro", "No previous focus session found. Ready to focus.")
                return
            self.active_goal_id = self.last_focus_goal_id
            self.active_task_id = self.last_focus_task_id

        self.total_seconds = self.phase_seconds(self.current_phase)
        self.remaining_seconds = self.total_seconds
        self.timer_label.setText(format_timer(self.remaining_seconds))
        self.state_label.setText(f"{phase_label_text(self.current_phase)} running.")
        self.timer.start(1000)
        self.update_phase_ui()

    def tick(self) -> None:
        self.remaining_seconds -= 1
        self.timer_label.setText(format_timer(self.remaining_seconds))
        if self.remaining_seconds <= 0:
            self.complete_session()

    def complete_session(self) -> None:
        if self.active_goal_id is None:
            return

        elapsed = self.total_seconds if self.remaining_seconds <= 0 else self.total_seconds - self.remaining_seconds
        notes = self.session_notes.toPlainText().strip() if self.current_phase == "pomodoro" else ""
        completed_phase = self.current_phase
        self.store.add_session(
            goal_id=self.active_goal_id,
            task_id=self.active_task_id,
            duration_seconds=max(elapsed, 60),
            status="completed",
            session_type=completed_phase,
            notes=notes,
        )
        self.timer.stop()

        if completed_phase == "pomodoro":
            self.completed_pomodoros += 1
            self.last_focus_goal_id = self.active_goal_id
            self.last_focus_task_id = self.active_task_id
            next_break = (
                "long_break"
                if self.completed_pomodoros % self.settings.sessions_before_long_break == 0
                else "short_break"
            )
            self.prepare_phase(next_break, "Focus session logged. Ready for a break.")
            self.session_notes.clear()
            self.notification_requested.emit(
                "Focus session complete",
                f"Time for a {phase_label_text(next_break).lower()}.",
            )
        else:
            self.prepare_phase("pomodoro", "Break complete. Ready for the next focus block.")
            self.notification_requested.emit(
                "Break complete",
                "Ready for your next focus session.",
            )

        self.active_goal_id = None
        self.active_task_id = None
        self.data_changed.emit()

    def interrupt_session(self) -> None:
        if self.active_goal_id is None:
            return

        elapsed = self.total_seconds - self.remaining_seconds
        if elapsed > 0:
            notes = self.session_notes.toPlainText().strip() if self.current_phase == "pomodoro" else ""
            self.store.add_session(
                goal_id=self.active_goal_id,
                task_id=self.active_task_id,
                duration_seconds=elapsed,
                status="interrupted",
                session_type=self.current_phase,
                notes=notes,
            )

        self.timer.stop()
        self.active_goal_id = None
        self.active_task_id = None
        if self.current_phase == "pomodoro":
            self.prepare_phase("pomodoro", "Focus session interrupted.")
        else:
            self.prepare_phase("pomodoro", "Break interrupted. Ready for focus again.")
        self.data_changed.emit()

    def skip_break(self) -> None:
        if self.current_phase == "pomodoro":
            return
        if self.timer.isActive():
            self.timer.stop()
        self.active_goal_id = None
        self.active_task_id = None
        self.prepare_phase("pomodoro", "Break skipped. Ready for the next focus block.")


class HistoryPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        self.empty_label = page_empty_state(
            "No sessions yet. Start a focus block from Today or Focus to build your history."
        )
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Started", "Type", "Goal", "Task", "Status", "Duration", "Notes"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.empty_label)
        layout.addWidget(self.table)

    def refresh(self, goals: list[Goal], sessions: list[FocusSession]) -> None:
        goal_lookup = {goal.id: goal for goal in goals}
        task_lookup = {
            task.id: task.title
            for goal in goals
            for task in goal.tasks
        }

        if not sessions:
            self.empty_label.show()
            self.table.setRowCount(0)
            return

        self.empty_label.hide()
        ordered_sessions = sessions[::-1]
        self.table.setRowCount(len(ordered_sessions))
        for row, session in enumerate(ordered_sessions):
            goal = goal_lookup.get(session.goal_id)
            values = [
                session.started_at,
                phase_label_text(session.session_type),
                goal.title if goal else "Unknown goal",
                task_lookup.get(session.task_id, "-"),
                session.status,
                format_minutes(session.duration_seconds),
                session.notes or "-",
            ]
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))


class MainWindow(QMainWindow):
    def __init__(self, store: JsonStore) -> None:
        super().__init__()
        self.store = store
        self.setWindowTitle("Kairos")
        self.resize(1200, 760)
        self.tray_icon: QSystemTrayIcon | None = None
        self.setStyleSheet(APP_STYLESHEET)

        container = QWidget()
        container.setObjectName("appShell")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        sidebar_panel = QWidget()
        sidebar_panel.setObjectName("sidebarPanel")
        sidebar_layout = QVBoxLayout(sidebar_panel)
        sidebar_layout.setContentsMargins(16, 18, 16, 18)
        sidebar_layout.setSpacing(12)
        brand_title = make_label("Kairos", "brandTitle")
        brand_subtitle = make_label("Goal OS for focused execution", "brandSubtitle")

        self.navigation = QListWidget()
        self.navigation.setObjectName("sidebarNav")
        self.navigation.setFixedWidth(200)
        self.navigation.addItems(["Today", "Dashboard", "Goals", "Focus", "History"])
        self.navigation.currentRowChanged.connect(self.switch_page)
        sidebar_layout.addWidget(brand_title)
        sidebar_layout.addWidget(brand_subtitle)
        sidebar_layout.addSpacing(8)
        sidebar_layout.addWidget(self.navigation, 1)

        self.stack = QStackedWidget()
        self.stack.setObjectName("contentPanel")
        self.today_page = TodayPage()
        self.dashboard_page = DashboardPage()
        self.goals_page = GoalsPage(store)
        self.focus_page = FocusPage(store)
        self.history_page = HistoryPage()

        self.today_page.focus_requested.connect(self.open_focus_for_target)
        self.today_page.data_changed.connect(self.save_today_plan)
        self.goals_page.data_changed.connect(self.refresh_all)
        self.focus_page.data_changed.connect(self.refresh_all)
        self.focus_page.notification_requested.connect(self.show_notification)

        self.stack.addWidget(self.today_page)
        self.stack.addWidget(self.dashboard_page)
        self.stack.addWidget(self.goals_page)
        self.stack.addWidget(self.focus_page)
        self.stack.addWidget(self.history_page)

        layout.addWidget(sidebar_panel)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(container)
        self.setup_tray_icon()

        self.navigation.setCurrentRow(0)
        self.refresh_all()

    def setup_tray_icon(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray_icon = QSystemTrayIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon),
            self,
        )
        self.tray_icon.setToolTip("Kairos")
        self.tray_icon.show()

    def switch_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)

    def open_focus_for_target(self, goal_id: str, task_id: object) -> None:
        self.focus_page.select_target(goal_id, task_id)
        self.navigation.setCurrentRow(3)

    def save_today_plan(self) -> None:
        self.store.save_today_plan(self.today_page.today_plan)
        self.refresh_all()

    def show_notification(self, title: str, message: str) -> None:
        if self.tray_icon is None:
            return
        self.tray_icon.showMessage(
            title,
            message,
            QSystemTrayIcon.MessageIcon.Information,
            5000,
        )

    def refresh_all(self) -> None:
        goals = self.store.load_goals()
        sessions = self.store.load_sessions()
        settings = self.store.load_settings()
        today_plan = self.store.load_today_plan()

        self.today_page.refresh(goals, sessions, today_plan)
        self.dashboard_page.refresh(goals, sessions, today_plan)
        self.goals_page.refresh(goals)
        self.focus_page.refresh(goals, settings, sessions)
        self.history_page.refresh(goals, sessions)
