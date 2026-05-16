from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
import json
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

try:
    from pymongo import MongoClient
    from pymongo.collection import Collection
    from pymongo.errors import PyMongoError
except ImportError:
    MongoClient = None
    Collection = Any
    PyMongoError = Exception

TASK_STATUSES = {"todo", "in_progress", "done", "blocked"}
DEFAULT_LIFE_AREAS = [
    ("career", "Career", "Become valuable through shipped work and opportunity creation."),
    ("learning", "Learning", "Build durable skills through practice and proof of work."),
    ("health", "Health", "Protect energy, body, and baseline discipline."),
    ("money", "Money", "Improve financial clarity and long-term options."),
    ("relationships", "Relationships", "Invest in people who matter."),
    ("systems", "Personal Systems", "Design routines, environment, and habits that make execution easier."),
]

LIKERT_OPTIONS = ["Strongly disagree", "Disagree", "Neutral", "Agree", "Strongly agree"]
FREQUENCY_OPTIONS = ["Never", "Rarely", "Sometimes", "Often", "Always"]
QUESTION_BANK = [
    {
        "id": "identity_becoming",
        "section": "North Star",
        "construct": "identity",
        "prompt": "The person I am becoming is clear enough to guide my daily choices.",
        "response_type": "likert",
        "options": LIKERT_OPTIONS,
        "source": "Kairos identity reflection",
    },
    {
        "id": "anti_vision",
        "section": "North Star",
        "construct": "anti_vision",
        "prompt": "What future are you trying to avoid if nothing changes?",
        "response_type": "open",
        "options": [],
        "source": "Kairos coaching prompt",
    },
    {
        "id": "values_rank",
        "section": "Values",
        "construct": "values",
        "prompt": "Rank the values that should drive your next season.",
        "response_type": "ranking",
        "options": ["Mastery", "Health", "Freedom", "Relationships", "Security", "Service", "Adventure"],
        "source": "Kairos values reflection",
    },
    {
        "id": "autonomy",
        "section": "Motivation",
        "construct": "autonomy",
        "prompt": "I feel that my current goals are chosen by me, not just inherited from pressure or comparison.",
        "response_type": "likert",
        "options": LIKERT_OPTIONS,
        "source": "Self-Determination Theory inspired",
    },
    {
        "id": "competence",
        "section": "Motivation",
        "construct": "competence",
        "prompt": "I usually know the next concrete step when I sit down to work.",
        "response_type": "likert",
        "options": LIKERT_OPTIONS,
        "source": "Self-Determination Theory inspired",
    },
    {
        "id": "relatedness",
        "section": "Motivation",
        "construct": "relatedness",
        "prompt": "My goals are connected to people, communities, or responsibilities that matter to me.",
        "response_type": "likert",
        "options": LIKERT_OPTIONS,
        "source": "Self-Determination Theory inspired",
    },
    {
        "id": "energy_pattern",
        "section": "Current State",
        "construct": "energy",
        "prompt": "When during the day do you usually have the cleanest energy?",
        "response_type": "choice",
        "options": ["Early morning", "Late morning", "Afternoon", "Evening", "It varies"],
        "source": "Kairos energy mapping",
    },
    {
        "id": "internal_trigger_frequency",
        "section": "Distraction",
        "construct": "internal_trigger",
        "prompt": "I drift because of internal discomfort before I drift because of external notifications.",
        "response_type": "likert",
        "options": LIKERT_OPTIONS,
        "source": "Nir Eyal trigger analysis inspired",
    },
    {
        "id": "wellbeing_recent",
        "section": "Wellbeing",
        "construct": "wellbeing",
        "prompt": "Over the last two weeks I have felt active and vigorous.",
        "response_type": "frequency",
        "options": FREQUENCY_OPTIONS,
        "source": "WHO-5 inspired, non-diagnostic",
    },
    {
        "id": "struggle_top",
        "section": "Current State",
        "construct": "struggle",
        "prompt": "What is the main pattern that keeps breaking your time discipline?",
        "response_type": "open",
        "options": [],
        "source": "Kairos behavioral review",
    },
]


def timestamp() -> str:
    return datetime.now().isoformat(timespec="seconds")


def current_week_key() -> str:
    iso = date.today().isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def week_key_for(value: date) -> str:
    iso = value.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def bounded_optional_int(value: Any, low: int, high: int) -> int | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    if number < low or number > high:
        return None
    return number


def default_life_areas() -> list["LifeArea"]:
    return [
        LifeArea(id=area_id, name=name, desired_state=desired_state)
        for area_id, name, desired_state in DEFAULT_LIFE_AREAS
    ]


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
    internal_trigger: str = ""
    external_trigger: str = ""
    pact: str = ""
    activity_type: str = ""
    quality: int | None = None
    mood: int | None = None
    energy: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FocusSession":
        return cls(
            id=data["id"],
            goal_id=data.get("goal_id", ""),
            task_id=data.get("task_id"),
            started_at=data["started_at"],
            duration_seconds=data["duration_seconds"],
            session_type=data.get("session_type", "pomodoro"),
            status=data.get("status", "completed"),
            notes=data.get("notes", ""),
            internal_trigger=data.get("internal_trigger", ""),
            external_trigger=data.get("external_trigger", ""),
            pact=data.get("pact", ""),
            activity_type=data.get("activity_type", ""),
            quality=bounded_optional_int(data.get("quality"), 1, 5),
            mood=bounded_optional_int(data.get("mood"), 1, 5),
            energy=bounded_optional_int(data.get("energy"), 1, 5),
        )


@dataclass
class WeeklyPlanItem:
    goal_id: str
    planned_minutes: int = 0
    backlog_minutes: int = 0
    notes: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WeeklyPlanItem":
        return cls(
            goal_id=data.get("goal_id", ""),
            planned_minutes=max(0, int(data.get("planned_minutes", 0) or 0)),
            backlog_minutes=max(0, int(data.get("backlog_minutes", 0) or 0)),
            notes=data.get("notes", ""),
        )


@dataclass
class WeeklyPlan:
    week_key: str
    capacity_minutes: int = 0
    items: list[WeeklyPlanItem] = field(default_factory=list)
    created_at: str = field(default_factory=timestamp)
    updated_at: str = field(default_factory=timestamp)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WeeklyPlan":
        return cls(
            week_key=data.get("week_key", current_week_key()),
            capacity_minutes=max(0, int(data.get("capacity_minutes", 0) or 0)),
            items=[WeeklyPlanItem.from_dict(item) for item in data.get("items", [])],
            created_at=data.get("created_at", timestamp()),
            updated_at=data.get("updated_at", timestamp()),
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
class TodayBlock:
    id: str
    start_time: str
    end_time: str
    kind: str = "deep_work"
    goal_id: str = ""
    task_id: str | None = None
    title: str = ""
    note: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TodayBlock":
        return cls(
            id=data.get("id", f"block-{uuid4().hex[:8]}"),
            start_time=data.get("start_time", "09:00"),
            end_time=data.get("end_time", "09:30"),
            kind=data.get("kind", "deep_work"),
            goal_id=data.get("goal_id", ""),
            task_id=data.get("task_id"),
            title=data.get("title", ""),
            note=data.get("note", ""),
        )


@dataclass
class TodayPlan:
    plan_date: str
    day_start: str = "09:00"
    day_end: str = "18:00"
    items: list[TodayPlanItem] = field(default_factory=list)
    blocks: list[TodayBlock] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TodayPlan":
        return cls(
            plan_date=data.get("plan_date", datetime.now().date().isoformat()),
            day_start=data.get("day_start", "09:00"),
            day_end=data.get("day_end", "18:00"),
            items=[TodayPlanItem.from_dict(item) for item in data.get("items", [])],
            blocks=[TodayBlock.from_dict(item) for item in data.get("blocks", [])],
        )


@dataclass
class DayTemplate:
    day_start: str = "09:00"
    day_end: str = "18:00"
    blocks: list[TodayBlock] = field(default_factory=list)
    updated_at: str = field(default_factory=timestamp)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DayTemplate":
        return cls(
            day_start=data.get("day_start", "09:00"),
            day_end=data.get("day_end", "18:00"),
            blocks=[TodayBlock.from_dict(item) for item in data.get("blocks", [])],
            updated_at=data.get("updated_at", timestamp()),
        )


@dataclass
class DailyLog:
    log_date: str
    intention: str = ""
    must_win: str = ""
    shutdown: str = ""
    pact: str = ""
    score: int = 0
    created_at: str = field(default_factory=timestamp)
    updated_at: str = field(default_factory=timestamp)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DailyLog":
        return cls(
            log_date=data.get("log_date", datetime.now().date().isoformat()),
            intention=data.get("intention", ""),
            must_win=data.get("must_win", ""),
            shutdown=data.get("shutdown", ""),
            pact=data.get("pact", ""),
            score=int(data.get("score", 0) or 0),
            created_at=data.get("created_at", timestamp()),
            updated_at=data.get("updated_at", timestamp()),
        )


@dataclass
class NorthStar:
    one_year_vision: str = ""
    ninety_day_outcomes: str = ""
    season_focus: str = ""
    identity_statement: str = ""
    values: str = ""
    anti_vision: str = ""
    alignment_notes: str = ""
    top_priorities: list[str] = field(default_factory=list)
    updated_at: str = field(default_factory=timestamp)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NorthStar":
        return cls(
            one_year_vision=data.get("one_year_vision", ""),
            ninety_day_outcomes=data.get("ninety_day_outcomes", ""),
            season_focus=data.get("season_focus", ""),
            identity_statement=data.get("identity_statement", ""),
            values=data.get("values", ""),
            anti_vision=data.get("anti_vision", ""),
            alignment_notes=data.get("alignment_notes", ""),
            top_priorities=list(data.get("top_priorities", [])),
            updated_at=data.get("updated_at", timestamp()),
        )


@dataclass
class LifeArea:
    id: str
    name: str
    desired_state: str = ""
    current_score: int = 5
    weekly_target_minutes: int = 0
    notes: str = ""
    updated_at: str = field(default_factory=timestamp)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LifeArea":
        return cls(
            id=data["id"],
            name=data["name"],
            desired_state=data.get("desired_state", ""),
            current_score=max(1, min(10, int(data.get("current_score", 5) or 5))),
            weekly_target_minutes=max(0, int(data.get("weekly_target_minutes", 0) or 0)),
            notes=data.get("notes", ""),
            updated_at=data.get("updated_at", timestamp()),
        )


@dataclass
class BrainProfile:
    identity: str = ""
    values: str = ""
    anti_vision: str = ""
    current_state: str = ""
    strengths: str = ""
    struggles: str = ""
    energy_patterns: str = ""
    motivation_notes: str = ""
    updated_at: str = field(default_factory=timestamp)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BrainProfile":
        return cls(
            identity=data.get("identity", ""),
            values=data.get("values", ""),
            anti_vision=data.get("anti_vision", ""),
            current_state=data.get("current_state", ""),
            strengths=data.get("strengths", ""),
            struggles=data.get("struggles", ""),
            energy_patterns=data.get("energy_patterns", ""),
            motivation_notes=data.get("motivation_notes", ""),
            updated_at=data.get("updated_at", timestamp()),
        )


@dataclass
class BrainAnswer:
    id: str
    question_id: str
    prompt: str
    response_type: str
    answer: str
    construct: str = ""
    section: str = ""
    source: str = ""
    created_at: str = field(default_factory=timestamp)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BrainAnswer":
        return cls(
            id=data.get("id", f"answer-{uuid4().hex[:8]}"),
            question_id=data.get("question_id", ""),
            prompt=data.get("prompt", ""),
            response_type=data.get("response_type", "open"),
            answer=data.get("answer", ""),
            construct=data.get("construct", ""),
            section=data.get("section", ""),
            source=data.get("source", ""),
            created_at=data.get("created_at", timestamp()),
        )


@dataclass
class SearchMemoryItem:
    id: str
    query: str
    title: str = ""
    url: str = ""
    snippet: str = ""
    note: str = ""
    linked_to: str = ""
    created_at: str = field(default_factory=timestamp)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SearchMemoryItem":
        return cls(
            id=data.get("id", f"search-{uuid4().hex[:8]}"),
            query=data.get("query", ""),
            title=data.get("title", ""),
            url=data.get("url", ""),
            snippet=data.get("snippet", ""),
            note=data.get("note", ""),
            linked_to=data.get("linked_to", ""),
            created_at=data.get("created_at", timestamp()),
        )


class JsonStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.goals_path = data_dir / "goals.json"
        self.sessions_path = data_dir / "sessions.json"
        self.settings_path = data_dir / "settings.json"
        self.today_plan_path = data_dir / "today_plan.json"
        self.day_template_path = data_dir / "day_template.json"
        self.daily_logs_path = data_dir / "daily_logs.json"
        self.weekly_plans_path = data_dir / "weekly_plans.json"
        self.north_star_path = data_dir / "north_star.json"
        self.life_areas_path = data_dir / "life_areas.json"
        self.brain_profile_path = data_dir / "brain_profile.json"
        self.brain_answers_path = data_dir / "brain_answers.json"
        self.search_memory_path = data_dir / "search_memory.json"
        self.vault_dir = Path(os.environ.get("KAIROS_VAULT_DIR", Path(__file__).resolve().parents[2] / "vault"))
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
        if not self.day_template_path.exists():
            self.save_day_template(default_day_template())
        if not self.daily_logs_path.exists():
            self._write_json(self.daily_logs_path, [])
        if not self.weekly_plans_path.exists():
            self._write_json(self.weekly_plans_path, [])
        if not self.north_star_path.exists():
            self.save_north_star(NorthStar())
        if not self.life_areas_path.exists():
            self.save_life_areas(default_life_areas())
        if not self.brain_profile_path.exists():
            self.save_brain_profile(BrainProfile())
        if not self.brain_answers_path.exists():
            self._write_json(self.brain_answers_path, [])
        if not self.search_memory_path.exists():
            self._write_json(self.search_memory_path, [])

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

    def load_day_template(self) -> DayTemplate:
        payload = self._read_json(self.day_template_path, {})
        template = DayTemplate.from_dict(payload)
        if not template.blocks:
            template = default_day_template()
            self.save_day_template(template)
        return template

    def save_day_template(self, template: DayTemplate) -> None:
        template.updated_at = timestamp()
        self._write_json(self.day_template_path, asdict(template))

    def load_daily_logs(self) -> list[DailyLog]:
        payload = self._read_json(self.daily_logs_path, [])
        return [DailyLog.from_dict(item) for item in payload]

    def save_daily_logs(self, logs: list[DailyLog]) -> None:
        self._write_json(self.daily_logs_path, [asdict(log) for log in logs])

    def load_weekly_plans(self) -> list[WeeklyPlan]:
        payload = self._read_json(self.weekly_plans_path, [])
        return [WeeklyPlan.from_dict(item) for item in payload]

    def save_weekly_plans(self, plans: list[WeeklyPlan]) -> None:
        self._write_json(self.weekly_plans_path, [asdict(plan) for plan in plans])

    def load_weekly_plan(self, week_key: str | None = None) -> WeeklyPlan:
        target_week = week_key or current_week_key()
        plan = next((item for item in self.load_weekly_plans() if item.week_key == target_week), None)
        if plan is not None:
            return plan
        return WeeklyPlan(week_key=target_week)

    def save_weekly_plan(self, plan: WeeklyPlan) -> WeeklyPlan:
        plans = self.load_weekly_plans()
        existing = next((item for item in plans if item.week_key == plan.week_key), None)
        plan.updated_at = timestamp()
        if existing is None:
            plans.append(plan)
        else:
            existing.capacity_minutes = max(0, int(plan.capacity_minutes))
            existing.items = plan.items
            existing.updated_at = plan.updated_at
        self.save_weekly_plans(plans)
        return plan

    def load_daily_log(self, log_date: str | None = None) -> DailyLog:
        target_date = log_date or datetime.now().date().isoformat()
        log = next((item for item in self.load_daily_logs() if item.log_date == target_date), None)
        if log is not None:
            return log
        return DailyLog(log_date=target_date)

    def save_daily_log(
        self,
        log_date: str,
        intention: str,
        must_win: str,
        shutdown: str,
        score: int,
        pact: str = "",
    ) -> DailyLog:
        logs = self.load_daily_logs()
        existing = next((item for item in logs if item.log_date == log_date), None)
        if existing is None:
            existing = DailyLog(log_date=log_date)
            logs.append(existing)
        existing.intention = intention
        existing.must_win = must_win
        existing.shutdown = shutdown
        existing.pact = pact
        existing.score = max(0, min(100, score))
        existing.updated_at = timestamp()
        self.save_daily_logs(logs)
        return existing

    def load_north_star(self) -> NorthStar:
        payload = self._read_json(self.north_star_path, {})
        return NorthStar.from_dict(payload)

    def save_north_star(self, north_star: NorthStar) -> None:
        north_star.updated_at = timestamp()
        self._write_json(self.north_star_path, asdict(north_star))

    def load_life_areas(self) -> list[LifeArea]:
        payload = self._read_json(self.life_areas_path, [])
        areas = [LifeArea.from_dict(item) for item in payload]
        if not areas:
            areas = default_life_areas()
            self.save_life_areas(areas)
        return areas

    def save_life_areas(self, areas: list[LifeArea]) -> None:
        self._write_json(self.life_areas_path, [asdict(area) for area in areas])

    def load_brain_profile(self) -> BrainProfile:
        payload = self._read_json(self.brain_profile_path, {})
        return BrainProfile.from_dict(payload)

    def save_brain_profile(self, profile: BrainProfile) -> BrainProfile:
        profile.updated_at = timestamp()
        self._write_json(self.brain_profile_path, asdict(profile))
        return profile

    def load_brain_answers(self) -> list[BrainAnswer]:
        payload = self._read_json(self.brain_answers_path, [])
        return [BrainAnswer.from_dict(item) for item in payload]

    def save_brain_answers(self, answers: list[BrainAnswer]) -> None:
        self._write_json(self.brain_answers_path, [asdict(answer) for answer in answers])

    def add_brain_answer(self, question_id: str, answer_text: str) -> BrainAnswer:
        question = question_by_id(question_id)
        answer = BrainAnswer(
            id=f"answer-{uuid4().hex[:8]}",
            question_id=question["id"],
            prompt=question["prompt"],
            response_type=question["response_type"],
            answer=answer_text.strip(),
            construct=question["construct"],
            section=question["section"],
            source=question["source"],
        )
        answers = self.load_brain_answers()
        answers.append(answer)
        self.save_brain_answers(answers)
        self.synthesize_brain_profile_from_answer(answer)
        return answer

    def synthesize_brain_profile_from_answer(self, answer: BrainAnswer) -> None:
        target_by_construct = {
            "identity": "identity",
            "anti_vision": "anti_vision",
            "values": "values",
            "energy": "energy_patterns",
            "struggle": "struggles",
            "internal_trigger": "struggles",
            "wellbeing": "current_state",
            "autonomy": "motivation_notes",
            "competence": "motivation_notes",
            "relatedness": "motivation_notes",
        }
        target = target_by_construct.get(answer.construct)
        if not target:
            return
        profile = self.load_brain_profile()
        entry = f"- {answer.section}: {answer.answer}"
        current = getattr(profile, target, "").strip()
        if entry in current:
            return
        setattr(profile, target, f"{current}\n{entry}".strip() if current else entry)
        self.save_brain_profile(profile)

    def load_search_memory(self) -> list[SearchMemoryItem]:
        payload = self._read_json(self.search_memory_path, [])
        return [SearchMemoryItem.from_dict(item) for item in payload]

    def save_search_memory(self, items: list[SearchMemoryItem]) -> None:
        self._write_json(self.search_memory_path, [asdict(item) for item in items])

    def add_search_memory(
        self,
        query: str,
        title: str = "",
        url: str = "",
        snippet: str = "",
        note: str = "",
        linked_to: str = "",
    ) -> SearchMemoryItem:
        item = SearchMemoryItem(
            id=f"search-{uuid4().hex[:8]}",
            query=query.strip(),
            title=title.strip(),
            url=url.strip(),
            snippet=snippet.strip(),
            note=note.strip(),
            linked_to=linked_to.strip(),
        )
        items = self.load_search_memory()
        items.append(item)
        self.save_search_memory(items)
        return item

    def sync_brain_to_vault(
        self,
        north_star: NorthStar,
        areas: list[LifeArea],
        goals: list[Goal],
    ) -> None:
        profile = self.load_brain_profile()
        answers = self.load_brain_answers()
        searches = self.load_search_memory()
        brain_dir = self.vault_dir / "10 Brain"
        research_dir = self.vault_dir / "20 Research"
        brain_dir.mkdir(parents=True, exist_ok=True)
        research_dir.mkdir(parents=True, exist_ok=True)
        (brain_dir / "Profile.md").write_text(render_brain_profile_markdown(profile, north_star), encoding="utf-8")
        (brain_dir / "North Star.md").write_text(render_north_star_markdown(north_star, goals), encoding="utf-8")
        (brain_dir / "Current State.md").write_text(render_current_state_markdown(profile, areas), encoding="utf-8")
        (brain_dir / "Questionnaire History.md").write_text(render_answers_markdown(answers), encoding="utf-8")
        (research_dir / "Search Memory.md").write_text(render_search_memory_markdown(searches), encoding="utf-8")

    def update_life_area(
        self,
        area_id: str,
        desired_state: str,
        current_score: int,
        weekly_target_minutes: int,
        notes: str,
    ) -> LifeArea:
        areas = self.load_life_areas()
        for area in areas:
            if area.id != area_id:
                continue
            area.desired_state = desired_state
            area.current_score = max(1, min(10, current_score))
            area.weekly_target_minutes = max(0, weekly_target_minutes)
            area.notes = notes
            area.updated_at = timestamp()
            self.save_life_areas(areas)
            return area
        raise ValueError(f"Life area not found: {area_id}")

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

    def save_day_bounds(self, day_start: str, day_end: str) -> TodayPlan:
        plan = self.load_today_plan()
        plan.day_start = day_start
        plan.day_end = day_end
        self.save_today_plan(plan)
        return plan

    def add_today_block(
        self,
        start_time: str,
        end_time: str,
        kind: str,
        goal_id: str,
        task_id: str | None,
        title: str,
        note: str,
    ) -> TodayBlock:
        plan = self.load_today_plan()
        block = TodayBlock(
            id=f"block-{uuid4().hex[:8]}",
            start_time=start_time,
            end_time=end_time,
            kind=kind,
            goal_id=goal_id,
            task_id=task_id,
            title=title,
            note=note,
        )
        plan.blocks.append(block)
        plan.blocks.sort(key=lambda item: item.start_time)
        self.save_today_plan(plan)
        return block

    def remove_today_block(self, block_id: str) -> TodayPlan:
        plan = self.load_today_plan()
        plan.blocks = [block for block in plan.blocks if block.id != block_id]
        self.save_today_plan(plan)
        return plan

    def clear_today_blocks(self) -> TodayPlan:
        plan = self.load_today_plan()
        plan.blocks = []
        self.save_today_plan(plan)
        return plan

    def save_today_as_template(self) -> DayTemplate:
        plan = self.load_today_plan()
        template = DayTemplate(
            day_start=plan.day_start,
            day_end=plan.day_end,
            blocks=[
                TodayBlock(
                    id=f"template-{uuid4().hex[:8]}",
                    start_time=block.start_time,
                    end_time=block.end_time,
                    kind=block.kind,
                    title=block.title,
                    note=block.note,
                )
                for block in plan.blocks
            ],
        )
        if not template.blocks:
            template = default_day_template()
        self.save_day_template(template)
        return template

    def apply_day_template(self) -> TodayPlan:
        template = self.load_day_template()
        plan = self.load_today_plan()
        plan.day_start = template.day_start
        plan.day_end = template.day_end
        plan.blocks = [
            TodayBlock(
                id=f"block-{uuid4().hex[:8]}",
                start_time=block.start_time,
                end_time=block.end_time,
                kind=block.kind,
                title=block.title,
                note=block.note,
            )
            for block in template.blocks
        ]
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
        internal_trigger: str = "",
        external_trigger: str = "",
        pact: str = "",
        activity_type: str = "",
        quality: int | None = None,
        mood: int | None = None,
        energy: int | None = None,
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
            internal_trigger=internal_trigger,
            external_trigger=external_trigger,
            pact=pact,
            activity_type=activity_type,
            quality=bounded_optional_int(quality, 1, 5),
            mood=bounded_optional_int(mood, 1, 5),
            energy=bounded_optional_int(energy, 1, 5),
        )
        sessions.append(session)
        self.save_sessions(sessions)
        return session


class MongoStore(JsonStore):
    def __init__(
        self,
        uri: str = "mongodb://localhost:27017",
        database: str = "kairos",
        collection: str = "state",
    ) -> None:
        if MongoClient is None:
            raise RuntimeError("pymongo is not installed. Install project dependencies to use MongoDB storage.")
        self.client = MongoClient(uri, serverSelectionTimeoutMS=2000)
        self.client.admin.command("ping")
        self.collection: Collection = self.client[database][collection]
        self.vault_dir = Path(os.environ.get("KAIROS_VAULT_DIR", Path(__file__).resolve().parents[2] / "vault"))
        self.collection.create_index("_id", unique=True)
        self._ensure_documents()

    def _ensure_documents(self) -> None:
        self.collection.update_one({"_id": "goals"}, {"$setOnInsert": {"data": []}}, upsert=True)
        self.collection.update_one({"_id": "sessions"}, {"$setOnInsert": {"data": []}}, upsert=True)
        self.collection.update_one(
            {"_id": "settings"},
            {"$setOnInsert": {"data": asdict(AppSettings())}},
            upsert=True,
        )
        self.collection.update_one(
            {"_id": "today_plan"},
            {"$setOnInsert": {"data": asdict(TodayPlan(plan_date=datetime.now().date().isoformat()))}},
            upsert=True,
        )
        self.collection.update_one(
            {"_id": "day_template"},
            {"$setOnInsert": {"data": asdict(default_day_template())}},
            upsert=True,
        )
        self.collection.update_one({"_id": "daily_logs"}, {"$setOnInsert": {"data": []}}, upsert=True)
        self.collection.update_one({"_id": "weekly_plans"}, {"$setOnInsert": {"data": []}}, upsert=True)
        self.collection.update_one(
            {"_id": "north_star"},
            {"$setOnInsert": {"data": asdict(NorthStar())}},
            upsert=True,
        )
        self.collection.update_one(
            {"_id": "life_areas"},
            {"$setOnInsert": {"data": [asdict(area) for area in default_life_areas()]}},
            upsert=True,
        )
        self.collection.update_one(
            {"_id": "brain_profile"},
            {"$setOnInsert": {"data": asdict(BrainProfile())}},
            upsert=True,
        )
        self.collection.update_one({"_id": "brain_answers"}, {"$setOnInsert": {"data": []}}, upsert=True)
        self.collection.update_one({"_id": "search_memory"}, {"$setOnInsert": {"data": []}}, upsert=True)

    def _read_document(self, key: str, default: Any) -> Any:
        document = self.collection.find_one({"_id": key}, {"data": 1})
        if document is None:
            return default
        return document.get("data", default)

    def _write_document(self, key: str, data: Any) -> None:
        self.collection.update_one(
            {"_id": key},
            {"$set": {"data": data, "updated_at": timestamp()}},
            upsert=True,
        )

    def load_goals(self) -> list[Goal]:
        payload = self._read_document("goals", [])
        return [Goal.from_dict(item) for item in payload]

    def save_goals(self, goals: list[Goal]) -> None:
        self._write_document("goals", [asdict(goal) for goal in goals])

    def load_sessions(self) -> list[FocusSession]:
        payload = self._read_document("sessions", [])
        return [FocusSession.from_dict(item) for item in payload]

    def save_sessions(self, sessions: list[FocusSession]) -> None:
        self._write_document("sessions", [asdict(session) for session in sessions])

    def load_settings(self) -> AppSettings:
        payload = self._read_document("settings", {})
        return AppSettings.from_dict(payload)

    def save_settings(self, settings: AppSettings) -> None:
        self._write_document("settings", asdict(settings))

    def load_today_plan(self) -> TodayPlan:
        payload = self._read_document("today_plan", {})
        plan = TodayPlan.from_dict(payload)
        today = datetime.now().date().isoformat()
        if plan.plan_date != today:
            plan = TodayPlan(plan_date=today)
            self.save_today_plan(plan)
        return plan

    def save_today_plan(self, plan: TodayPlan) -> None:
        self._write_document("today_plan", asdict(plan))

    def load_day_template(self) -> DayTemplate:
        payload = self._read_document("day_template", {})
        template = DayTemplate.from_dict(payload)
        if not template.blocks:
            template = default_day_template()
            self.save_day_template(template)
        return template

    def save_day_template(self, template: DayTemplate) -> None:
        template.updated_at = timestamp()
        self._write_document("day_template", asdict(template))

    def load_daily_logs(self) -> list[DailyLog]:
        payload = self._read_document("daily_logs", [])
        return [DailyLog.from_dict(item) for item in payload]

    def save_daily_logs(self, logs: list[DailyLog]) -> None:
        self._write_document("daily_logs", [asdict(log) for log in logs])

    def load_weekly_plans(self) -> list[WeeklyPlan]:
        payload = self._read_document("weekly_plans", [])
        return [WeeklyPlan.from_dict(item) for item in payload]

    def save_weekly_plans(self, plans: list[WeeklyPlan]) -> None:
        self._write_document("weekly_plans", [asdict(plan) for plan in plans])

    def load_north_star(self) -> NorthStar:
        payload = self._read_document("north_star", {})
        return NorthStar.from_dict(payload)

    def save_north_star(self, north_star: NorthStar) -> None:
        north_star.updated_at = timestamp()
        self._write_document("north_star", asdict(north_star))

    def load_life_areas(self) -> list[LifeArea]:
        payload = self._read_document("life_areas", [])
        areas = [LifeArea.from_dict(item) for item in payload]
        if not areas:
            areas = default_life_areas()
            self.save_life_areas(areas)
        return areas

    def save_life_areas(self, areas: list[LifeArea]) -> None:
        self._write_document("life_areas", [asdict(area) for area in areas])

    def load_brain_profile(self) -> BrainProfile:
        payload = self._read_document("brain_profile", {})
        return BrainProfile.from_dict(payload)

    def save_brain_profile(self, profile: BrainProfile) -> BrainProfile:
        profile.updated_at = timestamp()
        self._write_document("brain_profile", asdict(profile))
        return profile

    def load_brain_answers(self) -> list[BrainAnswer]:
        payload = self._read_document("brain_answers", [])
        return [BrainAnswer.from_dict(item) for item in payload]

    def save_brain_answers(self, answers: list[BrainAnswer]) -> None:
        self._write_document("brain_answers", [asdict(answer) for answer in answers])

    def load_search_memory(self) -> list[SearchMemoryItem]:
        payload = self._read_document("search_memory", [])
        return [SearchMemoryItem.from_dict(item) for item in payload]

    def save_search_memory(self, items: list[SearchMemoryItem]) -> None:
        self._write_document("search_memory", [asdict(item) for item in items])


def create_store(data_dir: Path) -> JsonStore:
    storage_mode = os.environ.get("KAIROS_STORAGE", "mongodb").strip().lower()
    if storage_mode in {"json", "local"}:
        return JsonStore(data_dir)

    mongo_uri = os.environ.get("KAIROS_MONGODB_URI", "mongodb://localhost:27017")
    mongo_database = os.environ.get("KAIROS_MONGODB_DATABASE", "kairos")
    mongo_collection = os.environ.get("KAIROS_MONGODB_COLLECTION", "state")
    try:
        mongo_store = MongoStore(mongo_uri, mongo_database, mongo_collection)
        seed_mongo_from_json(mongo_store, JsonStore(data_dir))
        return mongo_store
    except (RuntimeError, PyMongoError, OSError):
        return JsonStore(data_dir)


def default_day_template() -> DayTemplate:
    return DayTemplate(
        day_start="09:00",
        day_end="18:00",
        blocks=[
            TodayBlock(id="template-plan", start_time="09:00", end_time="09:20", kind="personal", title="Plan the day", note="Choose the must-win and protect traction."),
            TodayBlock(id="template-deep-1", start_time="09:20", end_time="11:00", kind="deep_work", title="Deep work", note="Highest leverage goal before messages take over."),
            TodayBlock(id="template-break-1", start_time="11:00", end_time="11:15", kind="break", title="Reset", note="Step away from screens."),
            TodayBlock(id="template-deep-2", start_time="11:15", end_time="12:45", kind="learning", title="Learning block", note="Build career capital deliberately."),
            TodayBlock(id="template-lunch", start_time="12:45", end_time="13:30", kind="recovery", title="Lunch", note="Real break, no drift."),
            TodayBlock(id="template-admin", start_time="13:30", end_time="14:15", kind="admin", title="Admin", note="Messages, chores, and small obligations."),
            TodayBlock(id="template-deep-3", start_time="14:15", end_time="16:00", kind="deep_work", title="Deep work", note="Second serious push."),
            TodayBlock(id="template-health", start_time="16:00", end_time="16:45", kind="exercise", title="Exercise", note="Health is scheduled, not optional."),
            TodayBlock(id="template-relationships", start_time="16:45", end_time="17:20", kind="relationship", title="Relationships", note="Parents, friends, or one meaningful connection."),
            TodayBlock(id="template-shutdown", start_time="17:20", end_time="18:00", kind="personal", title="Shutdown", note="Review, record, and choose tomorrow's first block."),
        ],
    )


def seed_mongo_from_json(mongo_store: MongoStore, json_store: JsonStore) -> None:
    local_goals = json_store.load_goals()
    if local_goals and not mongo_store.load_goals():
        mongo_store.save_goals(local_goals)

    local_sessions = json_store.load_sessions()
    if local_sessions and not mongo_store.load_sessions():
        mongo_store.save_sessions(local_sessions)

    local_settings = json_store.load_settings()
    if mongo_store.load_settings() == AppSettings() and local_settings != AppSettings():
        mongo_store.save_settings(local_settings)

    local_template = json_store.load_day_template()
    if local_template.blocks and not mongo_store.load_day_template().blocks:
        mongo_store.save_day_template(local_template)

    local_plan = json_store.load_today_plan()
    remote_plan = mongo_store.load_today_plan()
    if local_plan.items and not remote_plan.items:
        mongo_store.save_today_plan(local_plan)

    local_logs = json_store.load_daily_logs()
    if local_logs and not mongo_store.load_daily_logs():
        mongo_store.save_daily_logs(local_logs)

    local_weekly_plans = json_store.load_weekly_plans()
    if local_weekly_plans and not mongo_store.load_weekly_plans():
        mongo_store.save_weekly_plans(local_weekly_plans)

    local_north_star = json_store.load_north_star()
    remote_north_star = mongo_store.load_north_star()
    if not north_star_is_empty(local_north_star) and north_star_is_empty(remote_north_star):
        mongo_store.save_north_star(local_north_star)

    local_areas = json_store.load_life_areas()
    remote_areas = mongo_store.load_life_areas()
    if local_areas and life_areas_are_default(remote_areas):
        mongo_store.save_life_areas(local_areas)

    local_profile = json_store.load_brain_profile()
    remote_profile = mongo_store.load_brain_profile()
    if not brain_profile_is_empty(local_profile) and brain_profile_is_empty(remote_profile):
        mongo_store.save_brain_profile(local_profile)

    local_answers = json_store.load_brain_answers()
    if local_answers and not mongo_store.load_brain_answers():
        mongo_store.save_brain_answers(local_answers)

    local_searches = json_store.load_search_memory()
    if local_searches and not mongo_store.load_search_memory():
        mongo_store.save_search_memory(local_searches)


def question_by_id(question_id: str) -> dict[str, Any]:
    match = next((question for question in QUESTION_BANK if question["id"] == question_id), None)
    if match is not None:
        return match
    return {
        "id": "custom",
        "section": "Custom",
        "construct": "reflection",
        "prompt": "Custom reflection",
        "response_type": "open",
        "options": [],
        "source": "Kairos",
    }


def brain_profile_is_empty(profile: BrainProfile) -> bool:
    return not any(
        [
            profile.identity.strip(),
            profile.values.strip(),
            profile.anti_vision.strip(),
            profile.current_state.strip(),
            profile.strengths.strip(),
            profile.struggles.strip(),
            profile.energy_patterns.strip(),
            profile.motivation_notes.strip(),
        ]
    )


def markdown_list(items: list[str]) -> str:
    kept = [item.strip() for item in items if item.strip()]
    if not kept:
        return "- Not defined yet\n"
    return "".join(f"- {item}\n" for item in kept)


def render_brain_profile_markdown(profile: BrainProfile, north_star: NorthStar) -> str:
    return f"""---
type: kairos-brain-profile
updated: {profile.updated_at}
---

# Profile

## Identity
{profile.identity or north_star.identity_statement or "Not defined yet."}

## Values
{profile.values or "Not defined yet."}

## Anti-Vision
{profile.anti_vision or "Not defined yet."}

## Current State
{profile.current_state or "Not defined yet."}

## Strengths
{profile.strengths or "Not defined yet."}

## Struggles
{profile.struggles or "Not defined yet."}

## Energy Patterns
{profile.energy_patterns or "Not defined yet."}

## Motivation Notes
{profile.motivation_notes or "Not defined yet."}
"""


def render_north_star_markdown(north_star: NorthStar, goals: list[Goal]) -> str:
    active_goals = [goal.title for goal in goals if goal.status == "active"]
    return f"""---
type: kairos-north-star
updated: {north_star.updated_at}
---

# North Star

## Identity Statement
{north_star.identity_statement or "Not defined yet."}

## Values
{north_star.values or "Not defined yet."}

## Anti-Vision
{north_star.anti_vision or "Not defined yet."}

## One-Year Vision
{north_star.one_year_vision or "Not defined yet."}

## 90-Day Outcomes
{north_star.ninety_day_outcomes or "Not defined yet."}

## Current Season Focus
{north_star.season_focus or "Not defined yet."}

## Brain Alignment Notes
{north_star.alignment_notes or "Not defined yet."}

## Top Priorities
{markdown_list(north_star.top_priorities)}
## Active Goals
{markdown_list(active_goals)}
"""


def render_current_state_markdown(profile: BrainProfile, areas: list[LifeArea]) -> str:
    area_rows = "\n".join(
        f"- {area.name}: score {area.current_score}/10, target {area.weekly_target_minutes} min/week. {area.notes or area.desired_state}"
        for area in areas
    )
    return f"""---
type: kairos-current-state
updated: {profile.updated_at}
---

# Current State

## Summary
{profile.current_state or "Not defined yet."}

## Energy
{profile.energy_patterns or "Not defined yet."}

## Struggles
{profile.struggles or "Not defined yet."}

## Life Areas
{area_rows or "- No life areas yet."}
"""


def render_answers_markdown(answers: list[BrainAnswer]) -> str:
    rows = []
    for answer in sorted(answers, key=lambda item: item.created_at, reverse=True):
        rows.append(
            f"## {answer.created_at} - {answer.section}\n"
            f"- Construct: {answer.construct}\n"
            f"- Source: {answer.source}\n"
            f"- Question: {answer.prompt}\n"
            f"- Answer: {answer.answer}\n"
        )
    body = "\n".join(rows) if rows else "No questionnaire answers yet.\n"
    return f"""---
type: kairos-questionnaire-history
---

# Questionnaire History

{body}
"""


def render_search_memory_markdown(items: list[SearchMemoryItem]) -> str:
    rows = []
    for item in sorted(items, key=lambda entry: entry.created_at, reverse=True):
        title = item.title or item.query
        link = f"[{title}]({item.url})" if item.url else title
        rows.append(
            f"## {item.created_at} - {item.query}\n"
            f"- Saved result: {link}\n"
            f"- Linked to: {item.linked_to or 'Unlinked'}\n"
            f"- Snippet: {item.snippet or 'None'}\n"
            f"- Note: {item.note or 'None'}\n"
        )
    body = "\n".join(rows) if rows else "No saved search memory yet.\n"
    return f"""---
type: kairos-search-memory
---

# Search Memory

{body}
"""


def north_star_is_empty(north_star: NorthStar) -> bool:
    return not any(
        [
            north_star.one_year_vision.strip(),
            north_star.ninety_day_outcomes.strip(),
            north_star.season_focus.strip(),
            north_star.identity_statement.strip(),
            north_star.values.strip(),
            north_star.anti_vision.strip(),
            north_star.alignment_notes.strip(),
            [item for item in north_star.top_priorities if item.strip()],
        ]
    )


def life_areas_are_default(areas: list[LifeArea]) -> bool:
    defaults = {area.id: area for area in default_life_areas()}
    if {area.id for area in areas} != set(defaults):
        return False
    for area in areas:
        default = defaults[area.id]
        if (
            area.name != default.name
            or area.desired_state != default.desired_state
            or area.current_score != default.current_score
            or area.weekly_target_minutes != default.weekly_target_minutes
            or area.notes
        ):
            return False
    return True
