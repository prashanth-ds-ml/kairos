from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QStyle,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from .storage import FocusSession, Goal, JsonStore, Task, TodayPlan, TodayPlanItem


APP_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #f5f6f8;
    color: #1f2937;
    font-size: 14px;
}
QWidget#appShell {
    background-color: #f5f6f8;
}
QWidget#sidebarPanel {
    background-color: #ffffff;
    border: 1px solid #d9dee7;
    border-radius: 12px;
}
QLabel#brandTitle {
    color: #111827;
    font-size: 20px;
    font-weight: 700;
}
QLabel#brandSubtitle {
    color: #6b7280;
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
    border-radius: 8px;
    margin: 4px 0;
    color: #374151;
}
QListWidget#sidebarNav::item:selected {
    background: #e8f0fe;
    color: #1d4ed8;
    border: 1px solid #c9dafd;
    font-weight: 600;
}
QListWidget#sidebarNav::item:hover:!selected {
    background: #f3f4f6;
}
QLabel#pageTitle {
    color: #111827;
    font-size: 28px;
    font-weight: 700;
}
QLabel#pageSubtitle {
    color: #6b7280;
    font-size: 12px;
}
QLabel#sectionTitle {
    color: #111827;
    font-size: 16px;
    font-weight: 700;
}
QWidget#card, QGroupBox {
    background-color: #ffffff;
    border: 1px solid #d9dee7;
    border-radius: 12px;
    margin-top: 10px;
    padding-top: 10px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
    color: #4b5563;
    font-weight: 600;
}
QPushButton {
    background-color: #ffffff;
    color: #1f2937;
    border: 1px solid #cfd6e2;
    border-radius: 8px;
    padding: 8px 14px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #f9fafb;
}
QPushButton#primaryButton {
    background-color: #2563eb;
    color: #ffffff;
    border: 1px solid #2563eb;
}
QPushButton#primaryButton:hover {
    background-color: #1d4ed8;
}
QPushButton#secondaryButton {
    background-color: #eef4ff;
    color: #1d4ed8;
    border: 1px solid #cfe0ff;
}
QPushButton#ghostButton {
    color: #6b7280;
}
QPushButton:disabled {
    background-color: #f3f4f6;
    color: #9ca3af;
    border: 1px solid #e5e7eb;
}
QListWidget {
    background-color: #ffffff;
    border: 1px solid #d2d9e3;
    border-radius: 8px;
    padding: 8px;
}
QListWidget::item {
    background-color: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 10px 12px;
    margin: 4px 0;
}
QListWidget::item:selected {
    background-color: #eef4ff;
    border: 1px solid #cfe0ff;
    color: #111827;
}
"""


PRIORITY_LEVELS = ["P1", "P2", "P3", "P4", "P5"]
PRIORITY_ORDER = {priority: index for index, priority in enumerate(PRIORITY_LEVELS)}


def make_label(text: str, object_name: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName(object_name)
    return label


def create_page(widget: QWidget) -> QVBoxLayout:
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(24, 24, 24, 24)
    layout.setSpacing(16)
    return layout


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
    return f"#{active_rank} • {goal.priority}"


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


class TodayPage(QWidget):
    focus_requested = Signal(str, object)
    data_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.goals: list[Goal] = []
        self.today_plan = TodayPlan(plan_date=date.today().isoformat())
        self.available_targets: list[tuple[str, str | None]] = []
        self.planned_targets: list[tuple[str, str | None]] = []
        self.suggested_goal_id: str | None = None
        self.suggested_task_id: str | None = None

        layout = create_page(self)

        self.title_label = make_label("Today", "pageTitle")
        self.subtitle_label = make_label(
            "Plan the day, pick the next block, and start working.",
            "pageSubtitle",
        )
        self.subtitle_label.setWordWrap(True)
        self.summary_label = make_label("", "pageSubtitle")
        self.summary_label.setWordWrap(True)

        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)
        layout.addWidget(self.summary_label)

        self.next_focus_card = QGroupBox("Next focus")
        next_focus_layout = QVBoxLayout(self.next_focus_card)
        next_focus_layout.setContentsMargins(18, 20, 18, 18)
        next_focus_layout.setSpacing(10)

        self.suggestion_label = make_label("", "sectionTitle")
        self.suggestion_label.setWordWrap(True)
        self.reason_label = make_label("", "pageSubtitle")
        self.reason_label.setWordWrap(True)
        self.start_button = QPushButton("Start focus")
        self.start_button.setObjectName("primaryButton")
        self.start_button.clicked.connect(self.emit_focus_request)

        next_focus_layout.addWidget(self.suggestion_label)
        next_focus_layout.addWidget(self.reason_label)
        next_focus_layout.addWidget(self.start_button, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.next_focus_card)

        content_row = QHBoxLayout()
        content_row.setSpacing(16)

        queue_card = QGroupBox("Today's queue")
        queue_layout = QVBoxLayout(queue_card)
        queue_layout.setContentsMargins(18, 20, 18, 18)
        queue_layout.setSpacing(10)
        queue_hint = make_label("Keep the queue small. Limit it to 3 items.", "pageSubtitle")
        queue_hint.setWordWrap(True)
        self.today_plan_list = QListWidget()
        self.today_plan_list.setMinimumHeight(320)
        self.remove_from_today_button = QPushButton("Remove selected")
        self.remove_from_today_button.setObjectName("secondaryButton")
        self.remove_from_today_button.clicked.connect(self.remove_selected_from_today)
        self.clear_today_button = QPushButton("Clear all")
        self.clear_today_button.setObjectName("ghostButton")
        self.clear_today_button.clicked.connect(self.clear_today_plan)
        queue_actions = QHBoxLayout()
        queue_actions.setSpacing(10)
        queue_actions.addWidget(self.remove_from_today_button)
        queue_actions.addWidget(self.clear_today_button)
        queue_actions.addStretch(1)
        queue_layout.addWidget(queue_hint)
        queue_layout.addWidget(self.today_plan_list, 1)
        queue_layout.addLayout(queue_actions)

        available_card = QGroupBox("Available work")
        available_layout = QVBoxLayout(available_card)
        available_layout.setContentsMargins(18, 20, 18, 18)
        available_layout.setSpacing(10)
        available_hint = make_label("Pick the next item worth pulling into today.", "pageSubtitle")
        available_hint.setWordWrap(True)
        self.available_work_list = QListWidget()
        self.available_work_list.setMinimumHeight(320)
        self.add_to_today_button = QPushButton("Add to today")
        self.add_to_today_button.setObjectName("primaryButton")
        self.add_to_today_button.clicked.connect(self.add_selected_to_today)
        available_actions = QHBoxLayout()
        available_actions.setSpacing(10)
        available_actions.addWidget(self.add_to_today_button)
        available_actions.addStretch(1)
        available_layout.addWidget(available_hint)
        available_layout.addWidget(self.available_work_list, 1)
        available_layout.addLayout(available_actions)

        content_row.addWidget(queue_card, 1)
        content_row.addWidget(available_card, 1)
        layout.addLayout(content_row)

        self.empty_label = make_label(
            "Create your first goal in Goals. Once you have an active goal and a few tasks, Today will show the next recommended block.",
            "pageSubtitle",
        )
        self.empty_label.setWordWrap(True)
        layout.addWidget(self.empty_label)
        layout.addStretch()

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
        total_minutes = sum(session.duration_seconds for session in completed_focus_sessions(sessions)) // 60
        planned_candidates = planned_focus_candidates(goals, today_plan)

        self.summary_label.setText(
            f"{len(active_goals)} active goals • {len(planned_candidates)} planned today • {total_minutes} focus minutes completed"
        )

        self.today_plan_list.clear()
        self.available_work_list.clear()
        self.available_targets = []
        self.planned_targets = []

        suggested_goal, suggested_task = choose_next_focus(goals, today_plan)
        self.suggested_goal_id = suggested_goal.id if suggested_goal else None
        self.suggested_task_id = suggested_task.id if suggested_task else None

        if not active_goals:
            self.suggestion_label.setText("Nothing is ready yet.")
            self.reason_label.setText(
                "Add your first active goal and a few actionable tasks to unlock recommendations."
            )
            self.start_button.setEnabled(False)
            self.next_focus_card.setEnabled(False)
            self.empty_label.show()
        else:
            self.next_focus_card.setEnabled(True)
            self.empty_label.hide()
            if suggested_goal is None:
                self.suggestion_label.setText("No active goal is ready for focus.")
                self.reason_label.setText("Create an active goal with at least one task that can move today.")
                self.start_button.setEnabled(False)
            elif suggested_task is None:
                self.suggestion_label.setText(suggested_goal.title)
                self.reason_label.setText(f"{target_date_badge(suggested_goal.target_date)} • Focus at the goal level.")
                self.start_button.setEnabled(True)
            else:
                self.suggestion_label.setText(f"{suggested_goal.title} -> {suggested_task.title}")
                self.reason_label.setText(
                    f"{target_date_badge(suggested_goal.target_date)} • Picked from {suggested_goal.category}."
                )
                self.start_button.setEnabled(True)

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
                        f"{priority_display(goal, execution_order)} • {goal.title} -> {task.title}"
                    )
                    self.available_targets.append(key)
            else:
                key = (goal.id, None)
                if key in planned_lookup:
                    continue
                self.available_work_list.addItem(
                    f"{priority_display(goal, execution_order)} • {goal.title} • goal-level focus"
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


class PlaceholderPage(QWidget):
    def __init__(self, title: str, message: str) -> None:
        super().__init__()
        layout = create_page(self)
        title_label = make_label(title, "pageTitle")
        body_label = make_label(message, "pageSubtitle")
        body_label.setWordWrap(True)
        card = QWidget()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        card_layout.addWidget(make_label("Coming next", "sectionTitle"))
        card_layout.addWidget(body_label)
        card_layout.addStretch()
        layout.addWidget(title_label)
        layout.addWidget(card)
        layout.addStretch()


class FocusPlaceholderPage(PlaceholderPage):
    def __init__(self) -> None:
        super().__init__(
            "Focus",
            "The Focus tab will be rebuilt after Today is approved. For now this page just receives the selected target.",
        )
        self.target_label = make_label("", "pageSubtitle")
        self.layout().insertWidget(1, self.target_label)

    def set_target(self, goal_text: str, task_text: str | None) -> None:
        if task_text:
            self.target_label.setText(f"Selected target: {goal_text} -> {task_text}")
        else:
            self.target_label.setText(f"Selected target: {goal_text}")


class MainWindow(QMainWindow):
    def __init__(self, store: JsonStore) -> None:
        super().__init__()
        self.store = store
        self.tray_icon: QSystemTrayIcon | None = None

        self.setWindowTitle("Kairos")
        self.resize(1180, 780)
        self.setStyleSheet(APP_STYLESHEET)

        container = QWidget()
        container.setObjectName("appShell")
        shell_layout = QHBoxLayout(container)
        shell_layout.setContentsMargins(12, 12, 12, 12)
        shell_layout.setSpacing(12)

        sidebar_panel = QWidget()
        sidebar_panel.setObjectName("sidebarPanel")
        sidebar_panel.setFixedWidth(220)
        sidebar_layout = QVBoxLayout(sidebar_panel)
        sidebar_layout.setContentsMargins(16, 18, 16, 18)
        sidebar_layout.setSpacing(12)
        sidebar_layout.addWidget(make_label("Kairos", "brandTitle"))
        sidebar_layout.addWidget(make_label("Plan clearly. Focus steadily.", "brandSubtitle"))

        self.navigation = QListWidget()
        self.navigation.setObjectName("sidebarNav")
        for item in ["Today", "Dashboard", "Goals", "Focus", "History"]:
            QListWidgetItem(item, self.navigation)
        self.navigation.currentRowChanged.connect(self.switch_page)
        sidebar_layout.addWidget(self.navigation, 1)

        self.stack = QStackedWidget()
        self.today_page = TodayPage()
        self.dashboard_page = PlaceholderPage("Dashboard", "Dashboard will be rebuilt after Today is approved.")
        self.goals_page = PlaceholderPage("Goals", "Goals will be rebuilt after Today is approved.")
        self.focus_page = FocusPlaceholderPage()
        self.history_page = PlaceholderPage("History", "History will be rebuilt after Today is approved.")

        self.today_page.focus_requested.connect(self.open_focus_for_target)
        self.today_page.data_changed.connect(self.save_today_plan)

        self.stack.addWidget(self.today_page)
        self.stack.addWidget(self.dashboard_page)
        self.stack.addWidget(self.goals_page)
        self.stack.addWidget(self.focus_page)
        self.stack.addWidget(self.history_page)

        shell_layout.addWidget(sidebar_panel)
        shell_layout.addWidget(self.stack, 1)
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
        goals = self.store.load_goals()
        goal = find_goal(goals, goal_id)
        task = find_task(goal, task_id) if goal is not None else None
        if goal is not None:
            self.focus_page.set_target(goal.title, task.title if task is not None else None)
        self.navigation.setCurrentRow(3)

    def save_today_plan(self) -> None:
        self.store.save_today_plan(self.today_page.today_plan)
        self.refresh_all()

    def refresh_all(self) -> None:
        goals = self.store.load_goals()
        sessions = self.store.load_sessions()
        today_plan = self.store.load_today_plan()
        self.today_page.refresh(goals, sessions, today_plan)
