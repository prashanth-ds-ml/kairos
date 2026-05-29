from __future__ import annotations

import json
from datetime import date, datetime, timedelta
import os
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import Flask, Response, make_response, redirect, request, url_for

from .storage import BrainMemory, BrainProfile, CurrentSeason, DailyLog, FocusSession, Goal, JsonStore, LifeArea, NorthStar, QUESTION_BANK, ResearchSession, ResearchSource, SearchMemoryItem, Task, TodayBlock, TodayPlanItem, WeeklyPlan, WeeklyPlanItem, create_store, default_day_template, current_week_key, question_by_id, week_key_for


LOCAL_ENV_KEYS = {"HF_TOKEN", "HUGGINGFACE_API_TOKEN", "HUGGINGFACE_HUB_TOKEN", "HF_MODEL", "KAIROS_ACCESS_KEY", "KAIROS_MONGODB_URI", "KAIROS_MONGODB_DATABASE", "KAIROS_MONGODB_COLLECTION", "KAIROS_STORAGE", "KAIROS_VAULT_DIR", "KAIROS_SEARXNG_URL"}
LOCAL_ENV_ALIASES = {
    "HF_TOKEN": "HF_TOKEN",
    "HF_TOKEN".lower(): "HF_TOKEN",
    "HF_Token": "HF_TOKEN",
    "HUGGINGFACE_API_TOKEN": "HUGGINGFACE_API_TOKEN",
    "HUGGINGFACE_HUB_TOKEN": "HUGGINGFACE_HUB_TOKEN",
    "HF_MODEL": "HF_MODEL",
}
PRIORITY_LEVELS = ["P1", "P2", "P3", "P4", "P5"]
PRIORITY_ORDER = {priority: index for index, priority in enumerate(PRIORITY_LEVELS)}
TASK_STATUS_LABELS = {
    "todo": "Todo",
    "in_progress": "Doing",
    "done": "Done",
    "on_hold": "On hold",
    "blocked": "Blocked",
}
BLOCK_KINDS = {
    "deep_work": ("Deep Work", "traction"),
    "learning": ("Learning", "traction"),
    "exercise": ("Exercise", "traction"),
    "meditation": ("Meditation", "traction"),
    "relationship": ("Relationship", "traction"),
    "personal": ("Personal", "support"),
    "admin": ("Admin", "maintenance"),
    "recovery": ("Recovery", "support"),
    "break": ("Break", "support"),
    "buffer": ("Buffer", "maintenance"),
    "distraction": ("Distraction", "distraction"),
}
DEFAULT_HF_MODEL = "Qwen/Qwen2.5-7B-Instruct-1M"
HF_MODEL_FALLBACKS = [
    DEFAULT_HF_MODEL,
    "google/gemma-2-2b-it",
    "openai/gpt-oss-120b",
]


def create_app() -> Flask:
    load_local_env()
    app = Flask(__name__)
    app.secret_key = os.environ.get("KAIROS_SECRET_KEY", "kairos-local")
    data_dir = Path(os.environ.get("KAIROS_DATA_DIR", Path(__file__).resolve().parents[2] / "data"))
    app.config["STORE"] = create_store(data_dir)

    @app.before_request
    def require_access_key() -> Response | None:
        access_key = os.environ.get("KAIROS_ACCESS_KEY", "").strip()
        if not access_key or request.endpoint in {"unlock", "health"}:
            return None
        if request.cookies.get("kairos_access") == access_key:
            return None
        return make_response(unlock_page(), 401)

    @app.get("/health")
    def health() -> str:
        return "ok"

    @app.route("/unlock", methods=["GET", "POST"])
    def unlock() -> Response | str:
        access_key = os.environ.get("KAIROS_ACCESS_KEY", "").strip()
        if not access_key:
            return redirect(url_for("home"))
        if request.method == "POST" and form_data().get("key", "") == access_key:
            response = redirect(url_for("home"))
            response.set_cookie("kairos_access", access_key, max_age=60 * 60 * 24 * 365, httponly=True, secure=request.is_secure, samesite="Lax")
            return response
        return unlock_page()

    @app.get("/")
    def home() -> str:
        store = get_store()
        goals = store.load_goals()
        sessions = store.load_sessions()
        today_plan = store.load_today_plan()
        day_template = store.load_day_template()
        settings = store.load_settings()
        season = store.load_current_season()
        planned_items = planned_work_items(goals, today_plan.items)
        focus_items = focus_candidates(goals)
        next_item = planned_items[0] if planned_items else (focus_items[0] if focus_items else None)
        today_sessions = sessions_for_today(sessions)
        today_log = store.load_daily_log()
        today_minutes = sum(session.duration_seconds for session in today_sessions) // 60
        score = discipline_score(today_log, today_minutes, len(planned_items))
        stats = {
            "active_goals": len([goal for goal in goals if goal.status == "active"]),
            "planned": f"{len(planned_items)}/3",
            "today_minutes": today_minutes,
            "today_blocks": len(today_sessions),
            "score": score,
            "streak": discipline_streak(store.load_daily_logs(), today_log, score),
        }
        return page(
            "Today",
            render_today(stats, today_log, today_plan, day_template, season, next_item, planned_items, focus_items, settings.pomodoro_minutes),
        )

    @app.get("/goals")
    def goals_page() -> str:
        store = get_store()
        goals = sorted_goals(store.load_goals())
        areas = store.load_life_areas()
        selected_id = request.args.get("selected") or (goals[0].id if goals else "")
        selected = find_goal(goals, selected_id)
        return page("Goals", render_goals(goals, selected, areas))

    @app.get("/north-star")
    def north_star_page() -> str:
        store = get_store()
        return page("North Star", render_north_star(store.load_north_star(), store.load_life_areas(), store.load_goals()))

    @app.get("/season")
    def season_page() -> str:
        store = get_store()
        return page(
            "Season",
            render_season(
                store.load_current_season(),
                store.load_goals(),
                store.load_sessions(),
                store.load_brain_answers(),
                store.load_brain_memories(),
            ),
        )

    @app.get("/brain")
    def brain_page() -> str:
        store = get_store()
        return page(
            "Brain",
            render_brain(
                store.load_brain_profile(),
                store.load_brain_answers(),
                store.load_brain_memories(),
                store.load_search_memory(),
                store.load_north_star(),
                store.load_current_season(),
                store.load_life_areas(),
                store.load_goals(),
            ),
        )

    @app.get("/areas")
    def areas_page() -> str:
        store = get_store()
        return page("Areas", render_areas(store.load_life_areas(), store.load_goals(), store.load_sessions()))

    @app.get("/focus")
    def focus_page() -> str:
        store = get_store()
        goals = store.load_goals()
        sessions = store.load_sessions()
        settings = store.load_settings()
        candidates = focus_candidates(goals)
        selected_key = request.args.get("target") or item_key(candidates[0]) if candidates else ""
        selected = next((item for item in candidates if item_key(item) == selected_key), candidates[0] if candidates else None)
        return page(
            "Focus",
            render_focus(selected, candidates, settings.pomodoro_minutes, sessions_for_today(sessions)),
        )

    @app.get("/history")
    def history_page() -> str:
        store = get_store()
        goals = {goal.id: goal for goal in store.load_goals()}
        sessions = sorted(store.load_sessions(), key=lambda item: item.started_at, reverse=True)
        areas = store.load_life_areas()
        logs = store.load_daily_logs()
        weekly_plan = store.load_weekly_plan(current_week_key())
        return page("Review", render_history(goals, areas, sessions, logs, weekly_plan, store.load_current_season()))

    @app.get("/weekly")
    def weekly_page() -> str:
        store = get_store()
        goals = sorted_goals(store.load_goals())
        sessions = store.load_sessions()
        week_key = request.args.get("week") or current_week_key()
        plan = store.load_weekly_plan(week_key)
        return page("Weekly", render_weekly(plan, goals, sessions))

    @app.route("/coach", methods=["GET", "POST"])
    def coach_page() -> str:
        store = get_store()
        goals = store.load_goals()
        sessions = store.load_sessions()
        areas = store.load_life_areas()
        today_plan = store.load_today_plan()
        logs = store.load_daily_logs()
        brain_profile = store.load_brain_profile()
        brain_answers = store.load_brain_answers()
        search_memory = store.load_search_memory()
        question = ""
        answer = ""
        if request.method == "POST":
            question = form_data().get("question", "").strip()
            answer = run_hf_coach(question, goals, areas, sessions, today_plan, logs, brain_profile, brain_answers, search_memory)
        return page("Coach", render_coach(question, answer, goals, areas, sessions, today_plan, logs, brain_profile, brain_answers, search_memory))

    @app.route("/research", methods=["GET", "POST"])
    def research_page() -> str:
        store = get_store()
        query = ""
        results: list[dict[str, str]] = []
        error = ""
        active_session = None
        if request.method == "POST":
            query = form_data().get("query", "").strip()
            results, error = searxng_search(query)
            if query and results:
                sources = [ResearchSource(title=item.get("title", ""), url=item.get("url", ""), snippet=item.get("snippet", "")) for item in results[:6]]
                active_session = store.add_research_session(query, synthesize_research_answer(query, sources), sources)
        return page("Research", render_research(query, results, error, store.load_search_memory(), store.load_research_sessions(), active_session))

    @app.get("/research/read")
    def research_read_page() -> str:
        store = get_store()
        query = request.args.get("query", "").strip()
        target_url = request.args.get("url", "").strip()
        fallback_title = request.args.get("title", "").strip()
        fallback_snippet = request.args.get("snippet", "").strip()
        reader, error = fetch_readable_page(target_url)
        if not reader and target_url:
            reader = {
                "query": query,
                "title": fallback_title or "Unreadable page",
                "url": target_url,
                "text": fallback_snippet,
                "snippet": fallback_snippet,
                "read_error": error,
            }
            error = ""
        elif reader:
            reader["query"] = query
            reader["title"] = reader.get("title") or fallback_title
            reader["snippet"] = reader.get("snippet") or fallback_snippet
        return page("Research", render_research(query, [], error, store.load_search_memory(), store.load_research_sessions(), None, reader))

    @app.post("/goals")
    def create_goal() -> Response:
        form = form_data()
        title = form.get("title", "").strip()
        if title:
            get_store().add_goal(
                title=title,
                category=form.get("category", "career").strip() or "career",
                priority=form.get("priority", "P3").strip() or "P3",
                target_date=form.get("target_date", "").strip() or None,
                notes=form.get("notes", "").strip(),
                task_titles=[line.strip() for line in form.get("tasks", "").splitlines() if line.strip()],
            )
        return redirect(url_for("goals_page"))

    @app.post("/north-star")
    def save_north_star() -> Response:
        form = form_data()
        priorities = [
            form.get(f"priority_{index}", "").strip()
            for index in range(1, 4)
            if form.get(f"priority_{index}", "").strip()
        ]
        get_store().save_north_star(
            NorthStar(
                one_year_vision=form.get("one_year_vision", "").strip(),
                ninety_day_outcomes=form.get("ninety_day_outcomes", "").strip(),
                season_focus=form.get("season_focus", "").strip(),
                identity_statement=form.get("identity_statement", "").strip(),
                values=form.get("values", "").strip(),
                anti_vision=form.get("anti_vision", "").strip(),
                alignment_notes=form.get("alignment_notes", "").strip(),
                top_priorities=priorities,
            )
        )
        return redirect(url_for("north_star_page"))

    @app.post("/season")
    def save_season() -> Response:
        form = form_data()
        start_date = valid_date(form.get("start_date", ""), date.today())
        end_date = valid_date(form.get("end_date", ""), start_date + timedelta(days=20))
        if end_date < start_date:
            end_date = start_date + timedelta(days=20)
        get_store().save_current_season(
            CurrentSeason(
                title=form.get("title", "").strip(),
                primary_track=form.get("primary_track", "").strip(),
                support_track=form.get("support_track", "").strip(),
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                daily_minimum_minutes=nonnegative_form_int(form.get("daily_minimum_minutes")),
                weekly_target_minutes=nonnegative_form_int(form.get("weekly_target_minutes")),
                success_criteria=form.get("success_criteria", "").strip(),
                constraints=form.get("constraints", "").strip(),
                paused_goals=form.get("paused_goals", "").strip(),
                review_question=form.get("review_question", "").strip(),
                day_7_review=form.get("day_7_review", "").strip(),
                day_14_review=form.get("day_14_review", "").strip(),
                day_21_review=form.get("day_21_review", "").strip(),
                final_decision=form.get("final_decision", "").strip(),
                status=form.get("status", "active").strip() or "active",
            )
        )
        return redirect(url_for("season_page"))

    @app.post("/season/autofill")
    def autofill_season() -> Response:
        store = get_store()
        current = store.load_current_season()
        suggestion = build_season_suggestion(store.load_goals(), store.load_brain_answers(), store.load_brain_memories())
        start_date = valid_date(current.start_date, date.today())
        end_date = valid_date(current.end_date, start_date + timedelta(days=20))
        store.save_current_season(
            CurrentSeason(
                title=current.title or suggestion["title"],
                primary_track=current.primary_track or suggestion["primary_track"],
                support_track=current.support_track or suggestion["support_track"],
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                daily_minimum_minutes=current.daily_minimum_minutes or int(suggestion["daily_minimum_minutes"]),
                weekly_target_minutes=current.weekly_target_minutes or int(suggestion["weekly_target_minutes"]),
                success_criteria=current.success_criteria or suggestion["success_criteria"],
                constraints=current.constraints or suggestion["constraints"],
                paused_goals=current.paused_goals or suggestion["paused_goals"],
                review_question=current.review_question or suggestion["review_question"],
                day_7_review=current.day_7_review,
                day_14_review=current.day_14_review,
                day_21_review=current.day_21_review,
                final_decision=current.final_decision,
                status=current.status,
            )
        )
        return redirect(url_for("season_page"))

    @app.post("/direction/apply")
    def apply_direction_from_data() -> Response:
        store = get_store()
        goals = store.load_goals()
        suggestion = build_season_suggestion(goals, store.load_brain_answers(), store.load_brain_memories())
        north_star = store.load_north_star()
        primary_title = str(suggestion["title"]).replace(" validation", "").strip()
        support_titles = [item.strip() for item in str(suggestion["support_track"]).split(",") if item.strip()]
        north_star.season_focus = north_star.season_focus or str(suggestion["title"])
        if not north_star.ninety_day_outcomes.strip():
            north_star.ninety_day_outcomes = (
                f"Run a 21-day season for {primary_title}. "
                f"Use focus evidence and checkpoints to decide whether to continue, adjust, or pause."
            )
        if not north_star.top_priorities:
            north_star.top_priorities = [item for item in [primary_title, *support_titles[:2]] if item][:3]
        store.save_north_star(north_star)
        store.save_life_areas(apply_area_targets_from_goals(store.load_life_areas(), goals, primary_title, support_titles))
        return redirect(url_for("season_page"))

    @app.post("/brain/profile")
    def save_brain_profile() -> Response:
        form = form_data()
        get_store().save_brain_profile(
            BrainProfile(
                identity=form.get("identity", "").strip(),
                values=form.get("values", "").strip(),
                anti_vision=form.get("anti_vision", "").strip(),
                current_state=form.get("current_state", "").strip(),
                strengths=form.get("strengths", "").strip(),
                struggles=form.get("struggles", "").strip(),
                energy_patterns=form.get("energy_patterns", "").strip(),
                motivation_notes=form.get("motivation_notes", "").strip(),
            )
        )
        return redirect(url_for("brain_page"))

    @app.post("/brain/answer")
    def save_brain_answer() -> Response:
        form = form_data()
        question_id = form.get("question_id", "").strip()
        answer_text = form.get("answer", "").strip()
        if answer_text:
            get_store().add_brain_answer(question_id, answer_text)
        return redirect(url_for("brain_page"))

    @app.post("/brain/reflection")
    def save_brain_reflection() -> Response:
        form = form_data()
        answer_text = form.get("answer", "").strip()
        if answer_text:
            get_store().add_brain_reflection(
                prompt=form.get("prompt", "").strip(),
                answer_text=answer_text,
                construct=form.get("construct", "reflection").strip(),
                section=form.get("section", "Triggered reflection").strip(),
            )
        target = form.get("next", "").strip()
        return redirect(target or url_for("brain_page"))

    @app.post("/brain/memory")
    def save_brain_memory() -> Response:
        form = form_data()
        statement = form.get("statement", "").strip()
        if statement:
            get_store().add_brain_memory(
                statement=statement,
                memory_type=form.get("memory_type", "pattern").strip(),
                source_type=form.get("source_type", "").strip(),
                source_id=form.get("source_id", "").strip(),
            )
        return redirect(url_for("brain_page"))

    @app.post("/brain/sync")
    def sync_brain() -> Response:
        store = get_store()
        store.sync_brain_to_vault(store.load_north_star(), store.load_life_areas(), store.load_goals())
        return redirect(url_for("brain_page"))

    @app.post("/research/save")
    def save_research_memory() -> Response:
        form = form_data()
        query = form.get("query", "").strip()
        session_id = form.get("session_id", "").strip()
        note = form.get("note", "").strip()
        linked_to = form.get("linked_to", "").strip()
        if query:
            store = get_store()
            store.add_search_memory(
                query=query,
                title=form.get("title", "").strip(),
                url=form.get("url", "").strip(),
                snippet=form.get("snippet", "").strip(),
                note=note,
                linked_to=linked_to,
            )
            if session_id:
                store.confirm_research_insight(session_id, note or form.get("snippet", "").strip(), linked_to)
        return redirect(url_for("research_page"))

    @app.post("/areas/<area_id>")
    def update_area(area_id: str) -> Response:
        form = form_data()
        get_store().update_life_area(
            area_id,
            desired_state=form.get("desired_state", "").strip(),
            current_score=int(form.get("current_score", "5") or "5"),
            weekly_target_minutes=int(form.get("weekly_target_minutes", "0") or "0"),
            notes=form.get("notes", "").strip(),
        )
        return redirect(url_for("areas_page"))

    @app.post("/goals/<goal_id>/tasks")
    def add_task(goal_id: str) -> Response:
        title = form_data().get("title", "").strip()
        if title:
            get_store().add_task(goal_id, title)
        return redirect(url_for("goals_page", selected=goal_id))

    @app.post("/goals/<goal_id>/status")
    def update_goal_status(goal_id: str) -> Response:
        status = form_data().get("status", "active")
        get_store().update_goal_status(goal_id, status)
        return redirect(url_for("goals_page", selected=goal_id))

    @app.post("/goals/<goal_id>/tasks/<task_id>/status")
    def update_task_status(goal_id: str, task_id: str) -> Response:
        status = form_data().get("status", "todo")
        get_store().update_task_status(goal_id, task_id, status)
        return redirect(url_for("goals_page", selected=goal_id))

    @app.post("/today/auto-plan")
    def auto_plan_today() -> Response:
        store = get_store()
        plan = store.load_today_plan()
        planned = {(item.goal_id, item.task_id) for item in plan.items}
        for item in focus_candidates(store.load_goals()):
            if len(plan.items) >= 3:
                break
            key = (item["goal"].id, item["task"].id if item["task"] else None)
            if key in planned:
                continue
            plan.items.append(TodayPlanItem(goal_id=key[0], task_id=key[1]))
            planned.add(key)
        store.save_today_plan(plan)
        return redirect(url_for("home"))

    @app.post("/today/add")
    def add_today_item() -> Response:
        store = get_store()
        form = form_data()
        goal_id = form.get("goal_id", "")
        task_id = form.get("task_id") or None
        plan = store.load_today_plan()
        if goal_id and len(plan.items) < 3:
            key = (goal_id, task_id)
            planned = {(item.goal_id, item.task_id) for item in plan.items}
            if key not in planned:
                plan.items.append(TodayPlanItem(goal_id=goal_id, task_id=task_id))
                store.save_today_plan(plan)
        return redirect(url_for("home"))

    @app.post("/today/remove")
    def remove_today_item() -> Response:
        store = get_store()
        form = form_data()
        goal_id = form.get("goal_id", "")
        task_id = form.get("task_id") or None
        plan = store.load_today_plan()
        plan.items = [
            item
            for item in plan.items
            if not (item.goal_id == goal_id and item.task_id == task_id)
        ]
        store.save_today_plan(plan)
        return redirect(url_for("home"))

    @app.post("/today/task-status")
    def update_today_task_status() -> Response:
        form = form_data()
        goal_id = form.get("goal_id", "")
        task_id = form.get("task_id", "")
        status = form.get("status", "todo")
        if goal_id and task_id:
            get_store().update_task_status(goal_id, task_id, status)
        return redirect(url_for("home"))

    @app.post("/today/clear")
    def clear_today() -> Response:
        store = get_store()
        plan = store.load_today_plan()
        plan.items = []
        store.save_today_plan(plan)
        return redirect(url_for("home"))

    @app.post("/today/bounds")
    def save_today_bounds() -> Response:
        form = form_data()
        day_start = valid_time(form.get("day_start", "09:00"), "09:00")
        day_end = valid_time(form.get("day_end", "18:00"), "18:00")
        if time_to_minutes(day_end) <= time_to_minutes(day_start):
            day_end = "18:00"
        get_store().save_day_bounds(day_start, day_end)
        return redirect(url_for("home"))

    @app.post("/today/blocks")
    def add_today_block() -> Response:
        form = form_data()
        start_time = valid_time(form.get("start_time", "09:00"), "09:00")
        end_time = valid_time(form.get("end_time", "09:30"), "09:30")
        if time_to_minutes(end_time) <= time_to_minutes(start_time):
            end_time = minutes_to_time(time_to_minutes(start_time) + 25)
        target = form.get("target", "")
        goal_id, task_id = parse_block_target(target)
        kind = form.get("kind", "traction")
        if kind not in BLOCK_KINDS:
            kind = "deep_work"
        get_store().add_today_block(
            start_time=start_time,
            end_time=end_time,
            kind=kind,
            goal_id=goal_id,
            task_id=task_id,
            title=form.get("title", "").strip(),
            note=form.get("note", "").strip(),
        )
        return redirect(url_for("home"))

    @app.post("/today/blocks/remove")
    def remove_today_block() -> Response:
        block_id = form_data().get("block_id", "")
        if block_id:
            get_store().remove_today_block(block_id)
        return redirect(url_for("home"))

    @app.post("/today/blocks/clear")
    def clear_today_blocks() -> Response:
        get_store().clear_today_blocks()
        return redirect(url_for("home"))

    @app.post("/today/template/apply")
    def apply_today_template() -> Response:
        get_store().apply_day_template()
        return redirect(url_for("home"))

    @app.post("/today/template/save")
    def save_today_template() -> Response:
        get_store().save_today_as_template()
        return redirect(url_for("home"))

    @app.post("/today/template/reset")
    def reset_today_template() -> Response:
        get_store().save_day_template(default_day_template())
        return redirect(url_for("home"))

    @app.post("/daily-log")
    def save_daily_log() -> Response:
        store = get_store()
        form = form_data()
        today_log = store.load_daily_log()
        intention = form.get("intention", "").strip()
        must_win = form.get("must_win", "").strip()
        shutdown = form.get("shutdown", "").strip()
        pact = form.get("pact", "").strip()
        planned_items = planned_work_items(store.load_goals(), store.load_today_plan().items)
        today_minutes = sum(session.duration_seconds for session in sessions_for_today(store.load_sessions())) // 60
        score = discipline_score(
            DailyLog(
                log_date=today_log.log_date,
                intention=intention,
                must_win=must_win,
                shutdown=shutdown,
                pact=pact,
            ),
            today_minutes,
            len(planned_items),
        )
        store.save_daily_log(today_log.log_date, intention, must_win, shutdown, score, pact)
        return redirect(url_for("home"))

    @app.post("/weekly/save")
    def save_weekly_plan() -> Response:
        form = form_data()
        week_key = form.get("week_key", current_week_key())
        capacity_minutes = max(0, int(form.get("capacity_minutes", "0") or "0"))
        items: list[WeeklyPlanItem] = []
        for goal in get_store().load_goals():
            if goal.status != "active":
                continue
            planned = max(0, int(form.get(f"planned_{goal.id}", "0") or "0"))
            backlog = max(0, int(form.get(f"backlog_{goal.id}", "0") or "0"))
            notes = form.get(f"notes_{goal.id}", "").strip()
            if planned or backlog or notes:
                items.append(WeeklyPlanItem(goal_id=goal.id, planned_minutes=planned, backlog_minutes=backlog, notes=notes))
        get_store().save_weekly_plan(WeeklyPlan(week_key=week_key, capacity_minutes=capacity_minutes, items=items))
        return redirect(url_for("weekly_page", week=week_key))

    @app.post("/weekly/auto-allocate")
    def auto_allocate_weekly_plan() -> Response:
        form = form_data()
        week_key = form.get("week_key", current_week_key())
        capacity_minutes = max(0, int(form.get("capacity_minutes", "0") or "0"))
        goals = [goal for goal in sorted_goals(get_store().load_goals()) if goal.status == "active"]
        items = auto_allocate_weekly_items(goals, capacity_minutes)
        existing = {item.goal_id: item for item in get_store().load_weekly_plan(week_key).items}
        for item in items:
            item.backlog_minutes = existing.get(item.goal_id, WeeklyPlanItem(goal_id=item.goal_id)).backlog_minutes
            item.notes = existing.get(item.goal_id, WeeklyPlanItem(goal_id=item.goal_id)).notes
        get_store().save_weekly_plan(WeeklyPlan(week_key=week_key, capacity_minutes=capacity_minutes, items=items))
        return redirect(url_for("weekly_page", week=week_key))

    @app.post("/weekly/rollover")
    def rollover_weekly_plan() -> Response:
        form = form_data()
        week_key = form.get("week_key", current_week_key())
        store = get_store()
        plan = store.load_weekly_plan(week_key)
        prev_key = previous_week_key(week_key)
        previous = store.load_weekly_plan(prev_key)
        actual = weekly_actual_minutes_by_goal(store.load_sessions(), prev_key)
        carry = {
            item.goal_id: max(0, item.planned_minutes + item.backlog_minutes - actual.get(item.goal_id, 0))
            for item in previous.items
        }
        if not plan.items:
            plan.items = auto_allocate_weekly_items([goal for goal in sorted_goals(store.load_goals()) if goal.status == "active"], plan.capacity_minutes)
        for item in plan.items:
            if item.goal_id in carry:
                item.backlog_minutes = carry[item.goal_id]
        store.save_weekly_plan(plan)
        return redirect(url_for("weekly_page", week=week_key))

    @app.post("/focus/complete")
    def complete_focus() -> Response:
        form = form_data()
        goal_id = form.get("goal_id", "")
        task_id = form.get("task_id") or None
        minutes = max(1, int(form.get("minutes", "25") or "25"))
        outcome = form.get("outcome", "completed")
        if outcome not in {"completed", "partial", "blocked"}:
            outcome = "completed"
        commitment = form.get("commitment", "").strip()
        friction = form.get("friction", "").strip()
        internal_trigger = form.get("internal_trigger", "").strip()
        external_trigger = form.get("external_trigger", "").strip()
        pact = form.get("pact", "").strip()
        result_note = form.get("result_note", "").strip()
        notes = " | ".join(
            item
            for item in [
                f"Commitment: {commitment}" if commitment else "",
                f"Friction: {friction}" if friction else "",
                f"Result: {result_note}" if result_note else "",
            ]
            if item
        )
        store = get_store()
        store.add_session(
            goal_id,
            task_id,
            minutes * 60,
            outcome,
            session_type="pomodoro",
            notes=notes,
            internal_trigger=internal_trigger,
            external_trigger=external_trigger,
            pact=pact,
            quality=bounded_form_int(form.get("quality"), 1, 5),
            mood=bounded_form_int(form.get("mood"), 1, 5),
            energy=bounded_form_int(form.get("energy"), 1, 5),
        )
        if task_id:
            if outcome == "completed":
                store.update_task_status(goal_id, task_id, "done")
            elif outcome == "partial":
                store.update_task_status(goal_id, task_id, "in_progress")
            elif outcome == "blocked":
                store.update_task_status(goal_id, task_id, "blocked")
        return redirect(url_for("home"))

    @app.post("/activity/complete")
    def complete_activity() -> Response:
        form = form_data()
        minutes = max(1, int(form.get("minutes", "10") or "10"))
        activity_type = form.get("activity_type", "exercise")
        if activity_type not in {"exercise", "meditation", "breathing", "recovery", "other"}:
            activity_type = "other"
        get_store().add_session(
            "",
            None,
            minutes * 60,
            "completed",
            session_type="activity",
            notes=form.get("note", "").strip(),
            activity_type=activity_type,
            quality=bounded_form_int(form.get("quality"), 1, 5),
            mood=bounded_form_int(form.get("mood"), 1, 5),
            energy=bounded_form_int(form.get("energy"), 1, 5),
        )
        return redirect(url_for("history_page"))

    return app


def load_local_env() -> None:
    """Load safe local configuration from .env without overriding real environment variables."""
    env_path = Path(os.environ.get("KAIROS_ENV_FILE", Path(__file__).resolve().parents[2] / ".env"))
    if not env_path.exists() or not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key.startswith("export "):
            key = key.removeprefix("export ").strip()
        key = LOCAL_ENV_ALIASES.get(key, key)
        if key not in LOCAL_ENV_KEYS or key in os.environ:
            continue
        os.environ[key] = value.strip().strip('"').strip("'")


app = create_app()


def get_store() -> JsonStore:
    return app.config["STORE"]


def form_data() -> dict[str, str]:
    parsed = parse_qs(request.get_data(as_text=True), keep_blank_values=True)
    return {key: values[-1] for key, values in parsed.items()}


def valid_time(value: str, fallback: str) -> str:
    try:
        datetime.strptime(value, "%H:%M")
    except ValueError:
        return fallback
    return value


def valid_date(value: str, fallback: date) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return fallback


def time_to_minutes(value: str) -> int:
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def minutes_to_time(value: int) -> str:
    value = max(0, min(23 * 60 + 59, value))
    return f"{value // 60:02d}:{value % 60:02d}"


def parse_block_target(value: str) -> tuple[str, str | None]:
    if not value:
        return "", None
    goal_id, _, task_id = value.partition(":")
    return goal_id, task_id or None


def block_label(kind: str) -> str:
    return BLOCK_KINDS.get(kind, (kind.replace("_", " ").title(), "maintenance"))[0]


def block_signal(kind: str) -> str:
    return BLOCK_KINDS.get(kind, ("", "maintenance"))[1]


def parse_target_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def target_badge(value: str | None) -> str:
    parsed = parse_target_date(value)
    if parsed is None:
        return "No target date"
    today = date.today()
    if parsed < today:
        return f"Overdue: {parsed.strftime('%d %b')}"
    if parsed == today:
        return "Due today"
    delta = (parsed - today).days
    if delta <= 3:
        return f"Due in {delta} day{'s' if delta != 1 else ''}"
    return f"Due {parsed.strftime('%d %b')}"


def area_label(area_id: str, areas: list[LifeArea] | None = None) -> str:
    if areas is None:
        areas = get_store().load_life_areas()
    match = next((area for area in areas if area.id == area_id), None)
    return match.name if match else area_id.replace("_", " ").title()


def sorted_goals(goals: list[Goal]) -> list[Goal]:
    return sorted(
        goals,
        key=lambda goal: (
            1 if goal.status != "active" else 0,
            PRIORITY_ORDER.get(goal.priority, 99),
            goal.target_date or "9999-12-31",
            goal.created_at,
        ),
    )


def sorted_tasks(tasks: list[Task]) -> list[Task]:
    order = {"in_progress": 0, "todo": 1, "on_hold": 2, "blocked": 3, "done": 4}
    return sorted(tasks, key=lambda task: (order.get(task.status, 99), task.created_at))


def focus_candidates(goals: list[Goal]) -> list[dict[str, Goal | Task | None | str]]:
    items: list[dict[str, Goal | Task | None | str]] = []
    active_goals = [goal for goal in sorted_goals(goals) if goal.status == "active"]
    for goal in active_goals:
        tasks = [task for task in sorted_tasks(goal.tasks) if task.status in {"todo", "in_progress"}]
        if not tasks:
            items.append({"goal": goal, "task": None, "title": goal.title, "meta": target_badge(goal.target_date)})
            continue
        for task in tasks:
            items.append(
                {
                    "goal": goal,
                    "task": task,
                    "title": f"{goal.title}: {task.title}",
                    "meta": f"{goal.priority} | {target_badge(goal.target_date)} | {TASK_STATUS_LABELS.get(task.status, task.status)}",
                }
            )
    return items


def planned_work_items(goals: list[Goal], plan_items: list[TodayPlanItem]) -> list[dict[str, Goal | Task | None | str]]:
    by_goal = {goal.id: goal for goal in goals}
    items: list[dict[str, Goal | Task | None | str]] = []
    for plan_item in plan_items:
        goal = by_goal.get(plan_item.goal_id)
        if goal is None or goal.status != "active":
            continue
        task = next((item for item in goal.tasks if item.id == plan_item.task_id), None)
        if plan_item.task_id and (task is None or task.status not in {"todo", "in_progress"}):
            continue
        title = goal.title if task is None else f"{goal.title}: {task.title}"
        items.append({"goal": goal, "task": task, "title": title, "meta": f"{goal.priority} | {target_badge(goal.target_date)}"})
    return items


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


def discipline_score(log: DailyLog, today_minutes: int, planned_count: int) -> int:
    score = 0
    if log.intention.strip():
        score += 20
    if log.must_win.strip():
        score += 20
    if planned_count > 0:
        score += 20
    if today_minutes >= 25:
        score += 25
    elif today_minutes > 0:
        score += 15
    if log.shutdown.strip():
        score += 15
    return score


def discipline_streak(logs: list[DailyLog], today_log: DailyLog, today_score: int) -> int:
    by_date = {log.log_date: log.score for log in logs}
    current = date.today()
    streak = 0
    while True:
        key = current.isoformat()
        score = today_score if key == today_log.log_date else by_date.get(key, 0)
        if score < 70:
            return streak
        streak += 1
        current -= timedelta(days=1)


def find_goal(goals: list[Goal], goal_id: str) -> Goal | None:
    return next((goal for goal in goals if goal.id == goal_id), None)


def item_key(item: dict[str, Goal | Task | None | str]) -> str:
    goal = item["goal"]
    task = item["task"]
    assert isinstance(goal, Goal)
    return f"{goal.id}:{task.id if isinstance(task, Task) else ''}"


def item_ids(item: dict[str, Goal | Task | None | str]) -> tuple[str, str]:
    goal = item["goal"]
    task = item["task"]
    assert isinstance(goal, Goal)
    return goal.id, task.id if isinstance(task, Task) else ""


def bounded_form_int(value: str | None, low: int, high: int) -> int | None:
    try:
        number = int(value or "")
    except ValueError:
        return None
    if number < low or number > high:
        return None
    return number


def nonnegative_form_int(value: str | None) -> int:
    try:
        return max(0, int(value or "0"))
    except ValueError:
        return 0


def week_start_for_key(week_key: str) -> date:
    normalized = week_key.replace("W", "")
    year_text, week_text = normalized.split("-", 1)
    return date.fromisocalendar(int(year_text), int(week_text), 1)


def previous_week_key(week_key: str) -> str:
    return week_key_for(week_start_for_key(week_key) - timedelta(days=7))


def sessions_for_week(sessions: list[FocusSession], week_key: str, include_activity: bool = True) -> list[FocusSession]:
    start = week_start_for_key(week_key)
    end = start + timedelta(days=7)
    items: list[FocusSession] = []
    for session in sessions:
        if session.status not in {"completed", "partial", "blocked"}:
            continue
        if not include_activity and session.session_type != "pomodoro":
            continue
        session_day = session_date(session)
        if session_day is not None and start <= session_day < end:
            items.append(session)
    return items


def weekly_actual_minutes_by_goal(sessions: list[FocusSession], week_key: str) -> dict[str, int]:
    totals: dict[str, int] = {}
    for session in sessions_for_week(sessions, week_key, include_activity=False):
        if not session.goal_id:
            continue
        totals[session.goal_id] = totals.get(session.goal_id, 0) + session.duration_seconds // 60
    return totals


def priority_weight(goal: Goal) -> int:
    return {"P1": 5, "P2": 3, "P3": 2, "P4": 1, "P5": 1}.get(goal.priority, 1)


def auto_allocate_weekly_items(goals: list[Goal], capacity_minutes: int) -> list[WeeklyPlanItem]:
    active = [goal for goal in goals if goal.status == "active"]
    if not active or capacity_minutes <= 0:
        return [WeeklyPlanItem(goal_id=goal.id) for goal in active]
    weights = [priority_weight(goal) for goal in active]
    total_weight = sum(weights) or 1
    raw = [(weight / total_weight) * capacity_minutes for weight in weights]
    base = [int(value // 5) * 5 for value in raw]
    remaining = capacity_minutes - sum(base)
    order = sorted(range(len(active)), key=lambda index: raw[index] - base[index], reverse=True)
    step = 5
    for index in order:
        if remaining < step:
            break
        base[index] += step
        remaining -= step
    if remaining and base:
        base[order[0]] += remaining
    return [WeeklyPlanItem(goal_id=goal.id, planned_minutes=minutes) for goal, minutes in zip(active, base)]


def weekly_plan_item_map(plan: WeeklyPlan) -> dict[str, WeeklyPlanItem]:
    return {item.goal_id: item for item in plan.items}


def season_dates(season: CurrentSeason) -> tuple[date, date]:
    start = valid_date(season.start_date, date.today())
    end = valid_date(season.end_date, start + timedelta(days=20))
    if end < start:
        end = start + timedelta(days=20)
    return start, end


def season_day_label(season: CurrentSeason) -> str:
    start, end = season_dates(season)
    today = date.today()
    total_days = max(1, (end - start).days + 1)
    if today < start:
        return f"Starts in {(start - today).days} days"
    if today > end:
        return "Review due"
    return f"Day {(today - start).days + 1} of {total_days}"


def season_progress(season: CurrentSeason) -> int:
    start, end = season_dates(season)
    total_days = max(1, (end - start).days + 1)
    elapsed = min(total_days, max(0, (date.today() - start).days + 1))
    return min(100, round((elapsed / total_days) * 100))


def season_current_day(season: CurrentSeason) -> int:
    start, end = season_dates(season)
    total_days = max(1, (end - start).days + 1)
    return min(total_days, max(1, (date.today() - start).days + 1))


def season_checkpoint_label(season: CurrentSeason) -> str:
    day = season_current_day(season)
    if day <= 7:
        return "Day 7 check"
    if day <= 14:
        return "Day 14 check"
    return "Day 21 decision"


def page(title: str, content: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Kairos - {escape(title)}</title>
  <link rel="stylesheet" href="{url_for('static', filename='app.css')}">
</head>
<body>
  <aside>
    <div class="brand">
      <div class="brand-mark">K</div>
      <div>
        <h1>Kairos</h1>
        <p>Plan clearly. Focus steadily.</p>
      </div>
    </div>
    <nav>
      {nav_link("/", "Today", title)}
      {nav_link("/north-star", "North Star", title)}
      {nav_link("/season", "Season", title)}
      {nav_link("/brain", "Brain", title)}
      {nav_link("/areas", "Areas", title)}
      {nav_link("/focus", "Focus", title)}
      {nav_link("/goals", "Goals", title)}
      {nav_link("/weekly", "Weekly", title)}
      {nav_link("/history", "Review", title)}
      {nav_link("/research", "Research", title)}
      {nav_link("/coach", "Coach", title)}
    </nav>
  </aside>
  <main><div class="workspace">{content}</div></main>
  <script src="{url_for('static', filename='app.js')}"></script>
</body>
</html>"""


def unlock_page() -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Kairos - Unlock</title>
  <link rel="stylesheet" href="{url_for('static', filename='app.css')}">
</head>
<body class="unlock-body">
  <main class="unlock-card">
    <h1>Kairos</h1>
    <p>Enter your personal access key.</p>
    <form method="post" action="/unlock" class="stack">
      <input name="key" type="password" autofocus required>
      <button class="primary">Unlock</button>
    </form>
  </main>
</body>
</html>"""


def nav_link(href: str, label: str, current_title: str) -> str:
    klass = "active" if label == current_title else ""
    return f"<a class='{klass}' href='{href}'><span class='nav-dot'></span>{label}</a>"


def today_state(
    today_log: DailyLog,
    planned_items: list[dict[str, Goal | Task | None | str]],
    today_minutes: int,
) -> dict[str, str]:
    if not today_log.intention.strip() or not today_log.must_win.strip():
        return {
            "label": "Morning setup",
            "title": "Write the day before it starts",
            "body": "Set your intention, choose the must-win, and name the pact that protects your traction.",
            "action": "Save setup",
            "href": "#daily-loop",
            "tone": "attention",
        }
    if not planned_items:
        return {
            "label": "Planning",
            "title": "Choose 1-3 commitments for today",
            "body": "Keep the day small enough to win. Auto-plan can pick from your highest priority active work.",
            "action": "Auto-plan today",
            "href": "#available-work",
            "tone": "attention",
        }
    if today_minutes <= 0:
        return {
            "label": "Now",
            "title": "Start the first focus block",
            "body": "You have a plan. The next discipline move is to start one single-task block.",
            "action": "Start focus",
            "href": "",
            "tone": "primary",
        }
    if not today_log.shutdown.strip():
        return {
            "label": "Continue",
            "title": "Keep momentum or close the loop",
            "body": "Record another block if energy is good. If the workday is done, write a short shutdown.",
            "action": "Continue focus",
            "href": "",
            "tone": "strong",
        }
    return {
        "label": "Closed",
        "title": "Today has a clean record",
        "body": "You planned, focused, and closed the day. Review the pattern when you are ready.",
        "action": "Review week",
        "href": "/history",
        "tone": "strong",
    }


def now_panel(
    state: dict[str, str],
    next_item: dict[str, Goal | Task | None | str] | None,
) -> str:
    href = state["href"]
    if state["action"] in {"Start focus", "Continue focus"} and next_item is not None:
        action = focus_link(next_item, state["action"])
    elif state["action"] == "Auto-plan today":
        action = "<form method='post' action='/today/auto-plan'><button class='primary'>Auto-plan today</button></form>"
    else:
        action = f"<a class='button primary' href='{escape(href)}'>{escape(state['action'])}</a>"
    return f"""
<section class="now-panel {escape(state['tone'])}">
  <div>
    <span>{escape(state['label'])}</span>
    <h3>{escape(state['title'])}</h3>
    <p>{escape(state['body'])}</p>
  </div>
  <div class="now-action">{action}</div>
</section>"""


def render_today(
    stats: dict[str, int | str],
    today_log: DailyLog,
    today_plan: object,
    day_template: object,
    season: CurrentSeason,
    next_item: dict[str, Goal | Task | None | str] | None,
    planned_items: list[dict[str, Goal | Task | None | str]],
    focus_items: list[dict[str, Goal | Task | None | str]],
    default_minutes: int,
) -> str:
    state = today_state(today_log, planned_items, int(stats["today_minutes"]))
    cards = "".join(metric(label, value, tone) for label, value, tone in [
        ("Discipline", stats["score"], "primary"),
        ("Focus", f"{stats['today_minutes']} min", "strong"),
        ("Plan", stats["planned"], ""),
    ])
    return f"""
<header class="page-head"><div><p>{date.today().strftime('%A, %d %b %Y')}</p><h2>Today</h2></div><a class="button" href="/history">Review week</a></header>
{now_panel(state, next_item)}
{season_today_panel(season)}
{triggered_question_panel(triggered_today_question(season, today_log, planned_items, int(stats["today_minutes"])), "/")}
<section class="metrics today-strip">{cards}</section>
{daily_loop_panel(today_log, planned_items, int(stats["today_minutes"]))}
<div class="today-sections">
  <div class="daily-loop">
    <section class="panel" id="today-commitments">
      <div class="panel-head"><div><h3>Today's commitments</h3><p>Commit to one to three outcomes before opening the backlog.</p></div><form method="post" action="/today/clear"><button data-confirm="Clear today's plan?">Clear</button></form></div>
      {today_queue(planned_items, default_minutes)}
    </section>
    {day_planner(today_plan, day_template, focus_items)}
  </div>
  <div class="daily-loop">
    <details class="panel secondary-panel" id="available-work">
      <summary><span>Backlog</span><strong>Add or replan work</strong></summary>
      <div class="panel-head"><div><h3>Backlog</h3><p>Use this only when today's committed list needs another useful block.</p></div><form method="post" action="/today/auto-plan"><button class="primary">Auto-plan</button></form></div>
      {available_work_list(focus_items[:5], planned_items)}
    </details>
  </div>
</div>"""


def season_today_panel(season: CurrentSeason) -> str:
    if not season.title.strip() and not season.primary_track.strip():
        return """
<section class="panel">
  <div class="panel-head"><div><h3>Set your 21-day season</h3><p>Choose one primary track before the day fills with scattered work.</p></div><a class="button primary" href="/season">Start setup</a></div>
</section>"""
    progress = season_progress(season)
    return f"""
<section class="panel season-strip">
  <div class="panel-head">
    <div>
      <span class="pill">{escape(season_day_label(season))}</span>
      <h3>{escape(season.title or "Current 21-day season")}</h3>
      <p><strong>Primary:</strong> {escape(season.primary_track or "Not set")} | <strong>Support:</strong> {escape(season.support_track or "Not set")}</p>
    </div>
    <a class="button" href="/season">Edit season</a>
  </div>
  <div class="progress"><span style="width:{progress}%"></span></div>
</section>"""


def triggered_today_question(
    season: CurrentSeason,
    today_log: DailyLog,
    planned_items: list[dict[str, Goal | Task | None | str]],
    today_minutes: int,
) -> dict[str, str] | None:
    if not season.title.strip() and not season.primary_track.strip():
        return {
            "label": "Clarity",
            "prompt": "What should be your primary 21-day track right now, and what must be paused?",
            "construct": "season_clarity",
        }
    if not planned_items:
        return {
            "label": "Planning friction",
            "prompt": "What is making it hard to choose one to three commitments for today?",
            "construct": "planning_friction",
        }
    if today_minutes <= 0 and today_log.must_win.strip():
        return {
            "label": "Execution friction",
            "prompt": "What is the first friction between your must-win and starting the first focus block?",
            "construct": "execution_friction",
        }
    if today_minutes > 0 and not today_log.shutdown.strip():
        return {
            "label": "Learning",
            "prompt": "What did today's focus evidence teach you about the 21-day season?",
            "construct": "season_learning",
        }
    return None


def triggered_question_panel(question: dict[str, str] | None, next_url: str) -> str:
    if question is None:
        return ""
    return f"""
<section class="panel reflection-panel">
  <div class="panel-head"><div><span>{escape(question["label"])}</span><h3>Suggested reflection</h3></div></div>
  <form method="post" action="/brain/reflection" class="stack">
    <input type="hidden" name="prompt" value="{escape(question["prompt"])}">
    <input type="hidden" name="construct" value="{escape(question["construct"])}">
    <input type="hidden" name="section" value="Question engine">
    <input type="hidden" name="next" value="{escape(next_url)}">
    <p>{escape(question["prompt"])}</p>
    <textarea name="answer" rows="2" placeholder="Answer only if it would help future you."></textarea>
    <button>Save reflection</button>
  </form>
</section>"""


def render_weekly(plan: WeeklyPlan, goals: list[Goal], sessions: list[FocusSession]) -> str:
    active_goals = [goal for goal in goals if goal.status == "active"]
    if plan.capacity_minutes <= 0:
        plan.capacity_minutes = 25 * max(1, min(12, len(active_goals) * 2))
    item_map = weekly_plan_item_map(plan)
    actual = weekly_actual_minutes_by_goal(sessions, plan.week_key)
    rows = []
    for goal in active_goals:
        item = item_map.get(goal.id, WeeklyPlanItem(goal_id=goal.id))
        target = item.planned_minutes + item.backlog_minutes
        done = actual.get(goal.id, 0)
        progress = min(100, round((done / target) * 100)) if target else 0
        planned_blocks = item.planned_minutes / 25
        backlog_blocks = item.backlog_minutes / 25
        status = "Unallocated"
        status_class = "muted"
        if target > 0:
            status = "Committed"
            status_class = "planned"
        if item.backlog_minutes > item.planned_minutes and item.backlog_minutes > 0:
            status = "Backlog-heavy"
            status_class = "attention"
        rows.append(
            f"""
<article class="weekly-row">
  <div>
    <div class="weekly-goal-head"><h4>{escape(goal.title)}</h4><span class="weekly-status {status_class}">{status}</span></div>
    <p>{escape(goal.priority)} | {escape(area_label(goal.category))} | {format_minutes(done)} actual / {format_minutes(target)} target</p>
    <div class="progress"><span style="width:{progress}%"></span></div>
    <small>{planned_blocks:.1f} planned blocks | {backlog_blocks:.1f} backlog blocks</small>
  </div>
  <label>Planned minutes<input type="number" min="0" step="5" name="planned_{goal.id}" value="{item.planned_minutes}"></label>
  <label>Backlog<input type="number" min="0" step="5" name="backlog_{goal.id}" value="{item.backlog_minutes}"></label>
  <label>Notes<input name="notes_{goal.id}" value="{escape(item.notes)}" placeholder="Constraint or emphasis"></label>
</article>"""
        )
    total_planned = sum(item.planned_minutes for item in item_map.values())
    total_backlog = sum(item.backlog_minutes for item in item_map.values())
    total_actual = sum(actual.values())
    adherence = round((min(total_actual, total_planned + total_backlog) / (total_planned + total_backlog)) * 100) if total_planned + total_backlog else 0
    cards = "".join(
        metric(label, value, tone)
        for label, value, tone in [
            ("Capacity", format_minutes(plan.capacity_minutes), "primary"),
            ("Target", format_minutes(total_planned + total_backlog), "strong"),
            ("Actual", format_minutes(total_actual), ""),
            ("Adherence", f"{adherence}%", ""),
        ]
    )
    body = "".join(rows) or "<p class='muted'>No active goals yet. Create goals before planning the week.</p>"
    prev_key = previous_week_key(plan.week_key)
    realism = weekly_realism_panel(plan.week_key, plan.capacity_minutes, total_planned, total_backlog, total_actual, len(active_goals), prev_key)
    return f"""
<header class="page-head"><div><p>Guided planning</p><h2>Weekly</h2></div><a class="button" href="/history">Review week</a></header>
<section class="metrics weekly-metrics">{cards}</section>
{realism}
<section class="panel">
  <div class="panel-head"><div><h3>Plan {escape(plan.week_key)}</h3><p>Start with real capacity. Allocate only the work you can realistically protect.</p></div></div>
  <form method="post" action="/weekly/save" class="weekly-plan-form">
    <input type="hidden" name="week_key" value="{escape(plan.week_key)}">
    <div class="weekly-capacity">
      <label>Real focus capacity this week<input type="number" min="0" step="25" name="capacity_minutes" value="{plan.capacity_minutes}"></label>
      <div>
        <strong>{plan.capacity_minutes // 25} focus blocks available</strong>
        <p class="muted">Use protected focus time, not total free time. A realistic plan should leave buffer for life, admin, and low-energy days.</p>
      </div>
      <div class="weekly-nav">
        <a class="button" href="/weekly?week={escape(prev_key)}">Previous week</a>
        <a class="button" href="/weekly?week={escape(current_week_key())}">Current week</a>
      </div>
    </div>
    <div class="weekly-list">{body}</div>
    <div class="weekly-actions">
      <button class="primary">Save weekly plan</button>
      <button formaction="/weekly/auto-allocate">Auto-allocate by priority</button>
      <button formaction="/weekly/rollover" data-confirm="Replace this week's backlog with missed work from {escape(prev_key)}?">Apply rollover from {escape(prev_key)}</button>
    </div>
  </form>
</section>
<section class="panel">
  <div class="panel-head"><div><h3>Backlog policy</h3><p>Rollover uses previous target minus previous actual per goal. It only carries goals that still exist in the current plan.</p></div></div>
  <p class="muted">Current planned: {format_minutes(total_planned)} | Backlog: {format_minutes(total_backlog)} | Surplus: {format_minutes(max(0, total_actual - total_planned - total_backlog))}</p>
</section>"""


def weekly_realism_panel(
    week_key: str,
    capacity_minutes: int,
    planned_minutes: int,
    backlog_minutes: int,
    actual_minutes: int,
    active_goal_count: int,
    prev_key: str,
) -> str:
    target = planned_minutes + backlog_minutes
    remaining = capacity_minutes - target
    if capacity_minutes <= 0:
        verdict = "Set capacity before allocating goals"
        body = "Choose the real number of protected focus minutes available this week."
        tone = "attention"
    elif target > capacity_minutes:
        verdict = "Plan exceeds capacity"
        body = f"Target is {format_minutes(target - capacity_minutes)} over capacity. Reduce planned work or choose what backlog will wait."
        tone = "attention"
    elif target == 0 and active_goal_count:
        verdict = "Capacity is open"
        body = "Allocate the week before execution starts. Auto-allocate can create a first draft by priority."
        tone = "attention"
    elif remaining >= 50:
        verdict = "Plan has buffer"
        body = f"{format_minutes(remaining)} remains unallocated. Keep it as buffer or assign it deliberately."
        tone = "strong"
    else:
        verdict = "Plan is realistic"
        body = "Target is within capacity. Save the plan, then use Today to protect the first block."
        tone = "strong"

    guide_items = [
        ("1", "Capacity", f"{format_minutes(capacity_minutes)} real focus time"),
        ("2", "Current work", f"{format_minutes(planned_minutes)} planned"),
        ("3", "Rollover", f"{format_minutes(backlog_minutes)} from earlier commitments"),
        ("4", "Reality check", f"{format_minutes(actual_minutes)} already logged"),
    ]
    guide = "".join(
        f"<article><span>{num}</span><strong>{escape(title)}</strong><small>{escape(text)}</small></article>"
        for num, title, text in guide_items
    )
    return f"""
<section class="weekly-guide {tone}">
  <div>
    <span>Plan realism</span>
    <h3>{escape(verdict)}</h3>
    <p>{escape(body)}</p>
  </div>
  <div class="weekly-guide-grid">{guide}</div>
  <div class="weekly-guide-actions">
    <form method="post" action="/weekly/auto-allocate">
      <input type="hidden" name="week_key" value="{escape(week_key)}">
      <input type="hidden" name="capacity_minutes" value="{capacity_minutes}">
      <button class="primary">Auto-allocate this week</button>
    </form>
    <form method="post" action="/weekly/rollover">
      <input type="hidden" name="week_key" value="{escape(week_key)}">
      <button data-confirm="Replace this week's backlog with missed work from {escape(prev_key)}?">Apply rollover</button>
    </form>
  </div>
</section>"""


def tutorial_panel() -> str:
    return """
<details class="tutorial">
  <summary>How to use Kairos</summary>
  <div class="tutorial-grid">
    <article><span>1</span><h4>Set direction</h4><p>Use North Star for your one-year direction, 90-day outcomes, and identity.</p></article>
    <article><span>2</span><h4>Balance life areas</h4><p>Use Areas to decide where time should go across career, learning, health, money, relationships, and systems.</p></article>
    <article><span>3</span><h4>Create goals</h4><p>Use Goals for real outcomes. Each goal should have a next task that can be finished in a focus block.</p></article>
    <article><span>4</span><h4>Plan today</h4><p>On Today, pick only 1-3 commitments. If you feel stuck, use Auto-plan.</p></article>
    <article><span>5</span><h4>Focus</h4><p>Start one timer, work on one target, then record triggers, outcome, and friction.</p></article>
    <article><span>6</span><h4>Review weekly</h4><p>Use Review to see traction, distractions, triggers, and what needs to change next week.</p></article>
  </div>
</details>"""


def day_planner(today_plan: object, day_template: object, focus_items: list[dict[str, Goal | Task | None | str]]) -> str:
    day_start = getattr(today_plan, "day_start", "09:00")
    day_end = getattr(today_plan, "day_end", "18:00")
    blocks = sorted(getattr(today_plan, "blocks", []), key=lambda item: item.start_time)
    template_blocks = sorted(getattr(day_template, "blocks", []), key=lambda item: item.start_time)
    options = block_target_options(focus_items)
    return f"""
<details class="panel planner secondary-panel">
  <summary><span>Timebox</span><strong>Edit the shape of today</strong></summary>
  <div class="panel-head">
    <div><h3>Timeboxed day</h3><p>Start from a reusable morning template, then attach today's goals.</p></div>
    <div class="template-actions">
      <form method="post" action="/today/template/apply"><button class="primary" data-confirm="Replace today's blocks with your saved template?">Use template</button></form>
      <form method="post" action="/today/template/save"><button data-confirm="Save today's block shape as your reusable template?">Save template</button></form>
      <form method="post" action="/today/blocks/clear"><button data-confirm="Clear all time blocks?">Clear</button></form>
    </div>
  </div>
  <div class="template-strip">
    <div><strong>Saved template</strong><span>{len(template_blocks)} blocks | {escape(getattr(day_template, "day_start", "09:00"))} - {escape(getattr(day_template, "day_end", "18:00"))}</span></div>
    <form method="post" action="/today/template/reset"><button data-confirm="Reset your saved template to the Kairos starter day?">Reset starter</button></form>
  </div>
  <form method="post" action="/today/bounds" class="planner-bounds">
    <label>Start<input type="time" name="day_start" value="{escape(day_start)}"></label>
    <label>End<input type="time" name="day_end" value="{escape(day_end)}"></label>
    <button>Set day</button>
  </form>
  <div class="signal-legend">
    <span><i class="signal-dot traction"></i>Traction</span>
    <span><i class="signal-dot distraction"></i>Distraction</span>
    <span><i class="signal-dot maintenance"></i>Maintenance</span>
    <span><i class="signal-dot support"></i>Support</span>
  </div>
    <div class="planner-grid">
      <div class="timeline">{timeline_rows(day_start, day_end, blocks)}</div>
      <details class="block-form">
        <summary><h4>Add time block</h4></summary>
        <form method="post" action="/today/blocks" class="block-form-body">
          <div class="row">
            <label>Start<input type="time" name="start_time" value="{escape(day_start)}"></label>
            <label>End<input type="time" name="end_time" value="{minutes_to_time(min(time_to_minutes(day_end), time_to_minutes(day_start) + 50))}"></label>
          </div>
          <label>Type<select name="kind">
            {block_kind_options()}
          </select></label>
          <label>Goal or task<select name="target">{options}</select></label>
          <label>Label<input name="title" placeholder="Optional label, e.g. lunch, walk, email"></label>
          <label>Intent<input name="note" placeholder="What is this block meant to protect?"></label>
          <button class="primary">Add block</button>
        </form>
      </details>
    </div>
  </details>"""


def block_target_options(items: list[dict[str, Goal | Task | None | str]]) -> str:
    options = ["<option value=''>No goal/task</option>"]
    for item in items:
        options.append(f"<option value='{escape(item_key(item))}'>{escape(str(item['title']))}</option>")
    return "".join(options)


def block_kind_options() -> str:
    return "".join(
        f"<option value='{escape(key)}'>{escape(label)}</option>"
        for key, (label, _signal) in BLOCK_KINDS.items()
    )


def timeline_rows(day_start: str, day_end: str, blocks: list[TodayBlock]) -> str:
    if not blocks:
        return f"""
<div class="timeline-empty">
  <strong>{escape(day_start)} - {escape(day_end)}</strong>
  <p>No time blocks yet. Add traction, breaks, admin, and shutdown so the day has a shape before distractions arrive.</p>
</div>"""
    return "".join(timeline_block(block) for block in blocks)


def timeline_block(block: TodayBlock) -> str:
    title = block.title.strip() or block_label(block.kind)
    if block.goal_id:
        goal = find_goal(get_store().load_goals(), block.goal_id)
        if goal:
            title = goal.title
            if block.task_id:
                task = next((item for item in goal.tasks if item.id == block.task_id), None)
                if task:
                    title = f"{goal.title}: {task.title}"
    duration = max(0, time_to_minutes(block.end_time) - time_to_minutes(block.start_time))
    label = block_label(block.kind)
    signal = block_signal(block.kind)
    return f"""
<article class="time-block {escape(signal)} {escape(block.kind)}">
  <div class="time-range"><strong>{escape(block.start_time)}</strong><span>{escape(block.end_time)}</span></div>
  <div>
    <h4>{escape(title)}</h4>
    <p><span class="signal-dot {escape(signal)}"></span>{escape(label)} | {duration} min{f' | {escape(block.note)}' if block.note else ''}</p>
  </div>
  <form method="post" action="/today/blocks/remove">
    <input type="hidden" name="block_id" value="{escape(block.id)}">
    <button>Remove</button>
  </form>
</article>"""


def render_focus(
    selected: dict[str, Goal | Task | None | str] | None,
    candidates: list[dict[str, Goal | Task | None | str]],
    default_minutes: int,
    today_sessions: list[FocusSession],
) -> str:
    minutes = sum(session.duration_seconds for session in today_sessions) // 60
    selected_title = str(selected["title"]) if selected else "No target selected"
    selected_meta = str(selected["meta"]) if selected else "Add an active task first."
    selected_goal = selected["goal"] if selected else None
    selected_task = selected["task"] if selected else None
    goal_name = selected_goal.title if isinstance(selected_goal, Goal) else "No goal"
    area_name = area_label(selected_goal.category) if isinstance(selected_goal, Goal) else "No area"
    task_state = TASK_STATUS_LABELS.get(selected_task.status, selected_task.status) if isinstance(selected_task, Task) else "Goal-level block"
    return f"""
<header class="page-head"><div><p>Deep work</p><h2>Focus</h2></div><a class="button" href="/">Back to today</a></header>
<div class="focus-layout">
  <section class="timer">
    <span>Selected</span>
    <h3>{escape(selected_title)}</h3>
    <p>{escape(selected_meta)}</p>
    <div class="focus-context">
      <div><span>Goal</span><strong>{escape(goal_name)}</strong></div>
      <div><span>Area</span><strong>{escape(area_name)}</strong></div>
      <div><span>Status</span><strong>{escape(task_state)}</strong></div>
    </div>
    <div class="clock-wrap"><div class="clock" data-minutes="{default_minutes}">{default_minutes}:00</div><small>single-task block</small></div>
    <div class="row">
      <button type="button" class="primary" id="timer-start">Start</button>
      <button type="button" id="timer-pause">Pause</button>
      <button type="button" id="timer-reset">Reset</button>
    </div>
    {focus_form(selected, default_minutes, "Record block") if selected else ""}
    <p class="muted">{minutes} minutes recorded today.</p>
  </section>
  <section class="panel target-panel">
    <div class="panel-head"><div><h3>Change target</h3><p>Switch only when the current block is the wrong work.</p></div></div>
    {target_links(candidates, selected)}
  </section>
  <section class="panel activity-panel">
    <div class="panel-head"><div><h3>Log activity</h3><p>Record wellbeing work without attaching it to a career goal.</p></div></div>
    {activity_form()}
  </section>
</div>"""


def activity_form() -> str:
    return f"""
<form method="post" action="/activity/complete" class="focus-complete">
  <div class="row">
    <label>Type<select name="activity_type">
      <option value="exercise">Exercise</option>
      <option value="meditation">Meditation</option>
      <option value="breathing">Breathing</option>
      <option value="recovery">Recovery</option>
      <option value="other">Other</option>
    </select></label>
    <label class="minutes-field">Minutes<input type="number" min="1" max="240" name="minutes" value="10"></label>
  </div>
  <div class="row">
    <label>Quality<select name="quality">{rating_options()}</select></label>
    <label>Mood<select name="mood">{rating_options()}</select></label>
    <label>Energy<select name="energy">{rating_options()}</select></label>
  </div>
  <label>Note<input name="note" placeholder="Optional context"></label>
  <button>Record activity</button>
</form>"""


def render_goals(goals: list[Goal], selected: Goal | None, areas: list[LifeArea]) -> str:
    goal_rows = "".join(goal_row(goal, selected and goal.id == selected.id) for goal in goals) or "<p class='muted'>No goals yet.</p>"
    details = render_goal_details(selected)
    return f"""
<header class="page-head"><div><p>Career and learning outcomes</p><h2>Goals</h2></div><a class="button" href="/">Plan today</a></header>
<div class="goals-layout">
  <section class="panel goal-list-panel">
    <div class="panel-head"><div><h3>Active goals</h3><p>Choose the outcome that needs the next visible action.</p></div></div>
    <div class="list">{goal_rows}</div>
    <details class="create-goal">
      <summary><h3>Create goal</h3></summary>
    <form method="post" action="/goals" class="stack">
      <input name="title" placeholder="Goal title" required>
      <select name="category">{area_options(areas, "career")}</select>
      <div class="row"><select name="priority">{priority_options("P3")}</select><input type="date" name="target_date"></div>
      <textarea name="tasks" rows="3" placeholder="One task per line"></textarea>
      <textarea name="notes" rows="2" placeholder="Notes"></textarea>
      <button class="primary">Create goal</button>
    </form>
    </details>
  </section>
  <section class="panel goal-detail-panel">{details}</section>
</div>"""


def render_goal_details(goal: Goal | None) -> str:
    if goal is None:
        return "<h3>Goal details</h3><p class='muted'>Select or create a goal.</p>"
    done = len([task for task in goal.tasks if task.status == "done"])
    total = len(goal.tasks)
    blocked = len([task for task in goal.tasks if task.status == "blocked"])
    next_task = next((task for task in sorted_tasks(goal.tasks) if task.status in {"in_progress", "todo", "blocked"}), None)
    progress = int((done / total) * 100) if total else 0
    health = goal_health(goal)
    tasks = "".join(task_row(goal, task) for task in sorted_tasks(goal.tasks)) or "<p class='muted'>No tasks yet.</p>"
    next_task_warning = "" if next_task else f"""
<section class="goal-warning">
  <strong>This goal needs one visible task.</strong>
  <p>Without a task, Kairos cannot plan it into Today, Weekly allocation, or Focus cleanly.</p>
</section>"""
    return f"""
<div class="panel-head">
  <div><h3>{escape(goal.title)}</h3><p>{escape(goal.priority)} | {escape(area_label(goal.category))} | {escape(goal.status)} | {escape(target_badge(goal.target_date))}</p></div>
  <form method="post" action="/goals/{goal.id}/status">
    <input type="hidden" name="status" value="{'completed' if goal.status == 'active' else 'active'}">
    <button>{'Complete' if goal.status == 'active' else 'Reactivate'}</button>
  </form>
</div>
<div class="goal-progress">
  <div><span>Progress</span><strong>{done}/{total}</strong></div>
  <div><span>Blocked</span><strong>{blocked}</strong></div>
  <div><span>Health</span><strong>{escape(health)}</strong></div>
</div>
<div class="progress goal-progress-bar"><span style="width:{progress}%"></span></div>
<section class="goal-next">
  <span>Open task</span>
  <h4>{escape(next_task.title if next_task else 'Add a concrete task')}</h4>
  <p>{escape(goal.notes or 'No notes yet. Add the reason, deliverable, or proof of work expected from this goal.')}</p>
</section>
{next_task_warning}
<form method="post" action="/goals/{goal.id}/tasks" class="row">
  <input name="title" placeholder="Add next task" required>
  <button class="primary">Add</button>
</form>
<div class="list">{tasks}</div>"""


def goal_health(goal: Goal) -> str:
    if goal.status != "active":
        return "Closed"
    if not goal.tasks:
        return "Needs next task"
    if any(task.status == "blocked" for task in goal.tasks):
        return "Blocked"
    if all(task.status == "done" for task in goal.tasks):
        return "Ready to close"
    if not any(task.status == "in_progress" for task in goal.tasks):
        return "Needs current task"
    return "Active"


def render_north_star(north_star: NorthStar, areas: list[LifeArea], goals: list[Goal]) -> str:
    active_goals = [goal for goal in goals if goal.status == "active"]
    priorities = north_star.top_priorities + ["", "", ""]
    area_rows = "".join(north_star_area_row(area, active_goals) for area in areas)
    return f"""
<header class="page-head"><div><p>Direction</p><h2>North Star</h2></div><a class="button primary" href="/areas">Review areas</a></header>
<section class="north-grid">
  <form method="post" action="/north-star" class="panel north-form">
    <h3>Life direction</h3>
    <label>1-year vision<textarea name="one_year_vision" rows="4" placeholder="What should life and career look like one year from now?">{escape(north_star.one_year_vision)}</textarea></label>
    <label>90-day outcomes<textarea name="ninety_day_outcomes" rows="3" placeholder="Concrete outcomes to create in the next 90 days">{escape(north_star.ninety_day_outcomes)}</textarea></label>
    <label>Current season focus<input name="season_focus" value="{escape(north_star.season_focus)}" placeholder="The theme for this season"></label>
    <label>Identity statement<input name="identity_statement" value="{escape(north_star.identity_statement)}" placeholder="I am becoming..."></label>
    <label>Values<textarea name="values" rows="3" placeholder="What should guide choices when life is noisy?">{escape(north_star.values)}</textarea></label>
    <label>Anti-vision<textarea name="anti_vision" rows="3" placeholder="What future are you avoiding if nothing changes?">{escape(north_star.anti_vision)}</textarea></label>
    <label>Brain alignment notes<textarea name="alignment_notes" rows="3" placeholder="What has the Brain interview revealed about this direction?">{escape(north_star.alignment_notes)}</textarea></label>
    <div class="priority-grid">
      <label>Priority 1<input name="priority_1" value="{escape(priorities[0])}"></label>
      <label>Priority 2<input name="priority_2" value="{escape(priorities[1])}"></label>
      <label>Priority 3<input name="priority_3" value="{escape(priorities[2])}"></label>
    </div>
    <button class="primary">Save North Star</button>
  </form>
  <section class="panel">
    <h3>Life area alignment</h3>
    <p class="muted">Use Brain questions to make this less performative and more honest, then translate the direction into area targets and goals.</p>
    <a class="button" href="/brain">Continue Brain interview</a>
    <div class="list">{area_rows}</div>
  </section>
</section>"""


def render_season(
    season: CurrentSeason,
    goals: list[Goal],
    sessions: list[FocusSession],
    answers: list[object],
    memories: list[BrainMemory],
) -> str:
    start, end = season_dates(season)
    season_sessions = [
        session
        for session in sessions
        if session.session_type == "pomodoro"
        and (session_day := session_date(session)) is not None
        and start <= session_day <= end
    ]
    total_minutes = sum(session.duration_seconds for session in season_sessions) // 60
    target = max(1, season.weekly_target_minutes * max(1, ((end - start).days + 1 + 6) // 7))
    target_progress = min(100, round((total_minutes / target) * 100)) if season.weekly_target_minutes else 0
    suggestion = build_season_suggestion(goals, answers, memories)
    active_goal_titles = ", ".join(goal.title for goal in goals if goal.status == "active") or "No active goals yet"
    checkpoint_cards = season_checkpoint_cards(season)
    status_options = "".join(
        f"<option value='{value}' {'selected' if season.status == value else ''}>{label}</option>"
        for value, label in [("active", "Active"), ("closed", "Closed"), ("paused", "Paused")]
    )
    return f"""
<header class="page-head"><div><p>21-day operating agreement</p><h2>Season</h2></div><a class="button" href="/north-star">North Star</a></header>
<section class="metrics">
  {metric("Season day", season_day_label(season), "primary")}
  {metric("Tracked focus", f"{total_minutes} min", "strong")}
  {metric("Daily minimum", f"{season.daily_minimum_minutes} min", "")}
</section>
<section class="panel season-decision">
  <div class="panel-head">
    <div>
      <h3>{escape(season.title or str(suggestion["title"]))}</h3>
      <p><strong>Primary:</strong> {escape(season.primary_track or str(suggestion["primary_track"]))}</p>
      <p><strong>Support:</strong> {escape(season.support_track or str(suggestion["support_track"]))}</p>
    </div>
    <div class="actions">
      <form method="post" action="/season/autofill"><button class="primary">Apply empty fields</button></form>
      <form method="post" action="/direction/apply"><button>Update Direction</button></form>
    </div>
  </div>
</section>
<section class="north-grid">
  <form method="post" action="/season" class="panel north-form">
    <h3>Edit season</h3>
    <label>Season title<input name="title" value="{escape(season.title)}" placeholder="ESE validation while building Kairos"></label>
    <label>Primary track<textarea name="primary_track" rows="3" placeholder="The one track that gets protected first">{escape(season.primary_track)}</textarea></label>
    <label>Support track<textarea name="support_track" rows="3" placeholder="Important work that supports the season without taking over">{escape(season.support_track)}</textarea></label>
    <div class="priority-grid">
      <label>Start date<input type="date" name="start_date" value="{escape(start.isoformat())}"></label>
      <label>End date<input type="date" name="end_date" value="{escape(end.isoformat())}"></label>
      <label>Status<select name="status">{status_options}</select></label>
    </div>
    <div class="priority-grid">
      <label>Daily minimum minutes<input type="number" min="0" step="5" name="daily_minimum_minutes" value="{season.daily_minimum_minutes}"></label>
      <label>Weekly target minutes<input type="number" min="0" step="15" name="weekly_target_minutes" value="{season.weekly_target_minutes}"></label>
      <label>Progress target<div class="progress"><span style="width:{target_progress}%"></span></div></label>
    </div>
    <label>Success criteria<textarea name="success_criteria" rows="3" placeholder="What evidence proves this season is real?">{escape(season.success_criteria)}</textarea></label>
    <label>Constraints<textarea name="constraints" rows="3" placeholder="Rules like office hours for AI/Kairos, home hours for ESE, one certification max">{escape(season.constraints)}</textarea></label>
    <label>Paused goals<textarea name="paused_goals" rows="3" placeholder="What is explicitly not allowed to compete this season?">{escape(season.paused_goals)}</textarea></label>
    <label>Day-21 review question<textarea name="review_question" rows="2" placeholder="Continue, adjust, or pause the primary track?">{escape(season.review_question)}</textarea></label>
    <details class="edit-details">
      <summary>Checkpoint notes</summary>
      <label>Day 7 review<textarea name="day_7_review" rows="3" placeholder="Is the plan realistic? What has evidence shown?">{escape(season.day_7_review)}</textarea></label>
      <label>Day 14 review<textarea name="day_14_review" rows="3" placeholder="What needs to change for the final week?">{escape(season.day_14_review)}</textarea></label>
      <label>Day 21 review<textarea name="day_21_review" rows="3" placeholder="What did the season prove?">{escape(season.day_21_review)}</textarea></label>
      <label>Final decision<textarea name="final_decision" rows="2" placeholder="Continue, adjust, or pause?">{escape(season.final_decision)}</textarea></label>
    </details>
    <button class="primary">Save season</button>
  </form>
  <section class="panel">
    <h3>Season clarity</h3>
    <p class="muted">A season is a 21-day test. It should turn hope into evidence without forcing a permanent life decision.</p>
    <div class="list">
      <article class="item"><h4>Active goals</h4><p>{escape(active_goal_titles)}</p></article>
      <article class="item"><h4>Suggested default</h4><p>Primary: ESE home-hours validation. Support: Kairos and AI career growth during office/available work hours.</p></article>
      <article class="item"><h4>Decision rule</h4><p>At the end, decide from tracked evidence: continue, adjust, or pause.</p></article>
    </div>
    <h3>Checkpoint rhythm</h3>
    <div class="list">{checkpoint_cards}</div>
  </section>
</section>"""


def season_suggestion_panel(suggestion: dict[str, str | int]) -> str:
    return f"""
<section class="item">
  <div class="area-meta"><span>Suggested from Goals + Brain</span><span>Confirm before use</span></div>
  <h4>{escape(str(suggestion["title"]))}</h4>
  <p><strong>Primary:</strong> {escape(str(suggestion["primary_track"]))}</p>
  <p><strong>Support:</strong> {escape(str(suggestion["support_track"]))}</p>
  <p><strong>Constraint:</strong> {escape(str(suggestion["constraints"]))}</p>
  <form method="post" action="/season/autofill">
    <button>Apply empty fields</button>
  </form>
  <form method="post" action="/direction/apply">
    <button>Update North Star + Areas</button>
  </form>
</section>"""


def build_season_suggestion(
    goals: list[Goal],
    answers: list[object],
    memories: list[BrainMemory],
) -> dict[str, str | int]:
    active = sorted_goals([goal for goal in goals if goal.status == "active"])
    primary = choose_primary_goal(active)
    support = choose_support_goals(active, primary)
    paused = [goal for goal in active if goal != primary and goal not in support and goal.priority in {"P3", "P4", "P5"}]
    primary_text = goal_track_text(primary, "Choose one primary track")
    support_text = ", ".join(goal.title for goal in support[:2]) or "Keep job/career maintenance visible without letting it take over"
    friction = recent_friction_text(answers, memories)
    daily_minimum = 90 if primary and "ese" in primary.title.lower() else 45
    weekly_target = daily_minimum * 5
    title = f"{primary.title} validation" if primary else "21-day clarity season"
    return {
        "title": title,
        "primary_track": primary_text,
        "support_track": support_text,
        "daily_minimum_minutes": daily_minimum,
        "weekly_target_minutes": weekly_target,
        "success_criteria": f"{15 if daily_minimum >= 90 else 10}+ focused sessions and one honest review of progress evidence.",
        "constraints": friction or "One primary track, one support track, and one active certification at most.",
        "paused_goals": ", ".join(goal.title for goal in paused[:5]) or "Any goal that does not support the current season.",
        "review_question": "Based on 21 days of evidence, should this track continue, adjust, or pause?",
    }


def choose_primary_goal(goals: list[Goal]) -> Goal | None:
    if not goals:
        return None
    dated = [goal for goal in goals if parse_target_date(goal.target_date) is not None]
    if dated:
        return sorted(dated, key=lambda goal: (parse_target_date(goal.target_date) or date.max, PRIORITY_ORDER.get(goal.priority, 9)))[0]
    return goals[0]


def choose_support_goals(goals: list[Goal], primary: Goal | None) -> list[Goal]:
    return [
        goal
        for goal in goals
        if goal != primary and goal.category in {"career", "learning", "systems"}
    ][:3]


def goal_track_text(goal: Goal | None, fallback: str) -> str:
    if goal is None:
        return fallback
    next_task = next((task for task in sorted_tasks(goal.tasks) if task.status in {"in_progress", "todo", "blocked"}), None)
    task_text = f" Open task: {next_task.title}." if next_task else " Add one concrete task."
    return f"{goal.title}.{task_text}"


def recent_friction_text(answers: list[object], memories: list[BrainMemory]) -> str:
    memory = next((item for item in sorted(memories, key=lambda entry: entry.created_at, reverse=True) if item.memory_type in {"pattern", "rule"}), None)
    if memory is not None:
        return memory.statement
    answer = next(
        (
            item
            for item in sorted(answers, key=lambda entry: getattr(entry, "created_at", ""), reverse=True)
            if getattr(item, "construct", "") in {"planning_friction", "execution_friction", "season_clarity", "season_learning"}
        ),
        None,
    )
    if answer is None:
        return ""
    return str(getattr(answer, "answer", "")).strip()


def apply_area_targets_from_goals(
    areas: list[LifeArea],
    goals: list[Goal],
    primary_title: str,
    support_titles: list[str],
) -> list[LifeArea]:
    active = [goal for goal in goals if goal.status == "active"]
    primary_goal = next((goal for goal in active if goal.title == primary_title), None)
    support_set = set(support_titles)
    for area in areas:
        area_goals = [goal for goal in active if goal.category == area.id]
        if not area_goals:
            continue
        if primary_goal and primary_goal.category == area.id:
            area.weekly_target_minutes = max(area.weekly_target_minutes, 450)
            area.notes = area.notes or f"Primary 21-day season area: {primary_goal.title}."
        elif any(goal.title in support_set for goal in area_goals):
            area.weekly_target_minutes = max(area.weekly_target_minutes, 150)
            area.notes = area.notes or "Support track area for the current season."
        else:
            area.weekly_target_minutes = max(area.weekly_target_minutes, 25)
    return areas


def season_checkpoint_cards(season: CurrentSeason) -> str:
    current = season_checkpoint_label(season)
    checkpoints = [
        ("Day 7 check", "Reality", "Is the daily minimum realistic?", season.day_7_review),
        ("Day 14 check", "Adjustment", "What must change for the final week?", season.day_14_review),
        ("Day 21 decision", "Decision", "Continue, adjust, or pause?", season.day_21_review or season.final_decision),
    ]
    rows = []
    for label, title, prompt, answer in checkpoints:
        status = "Current" if label == current else ("Done" if answer.strip() else "Open")
        rows.append(
            f"<article class='item'><div class='area-meta'><span>{escape(status)}</span><span>{escape(label)}</span></div><h4>{escape(title)}</h4><p>{escape(answer.strip() or prompt)}</p></article>"
        )
    return "".join(rows)


def north_star_area_row(area: LifeArea, goals: list[Goal]) -> str:
    goal_count = len([goal for goal in goals if goal.category == area.id])
    return f"""
<article class="area-row">
  <div class="score-dot">{area.current_score}</div>
  <div>
    <h4>{escape(area.name)}</h4>
    <p>{goal_count} active goals | {area.weekly_target_minutes // 60}h weekly target</p>
  </div>
</article>"""


def render_brain(
    profile: BrainProfile,
    answers: list[object],
    memories: list[BrainMemory],
    searches: list[SearchMemoryItem],
    north_star: NorthStar,
    season: CurrentSeason,
    areas: list[LifeArea],
    goals: list[Goal],
) -> str:
    progress_items = [
        ("Identity", bool(profile.identity or north_star.identity_statement)),
        ("Values", bool(profile.values)),
        ("Anti-vision", bool(profile.anti_vision)),
        ("Current state", bool(profile.current_state)),
        ("Energy", bool(profile.energy_patterns)),
        ("Struggles", bool(profile.struggles)),
    ]
    progress = sum(1 for _, done in progress_items if done)
    cards = "".join(metric(label, "Done" if done else "Open", "good" if done else "") for label, done in progress_items)
    question_cards = grouped_question_cards(QUESTION_BANK)
    type_counts = count_values(question["response_type"] for question in QUESTION_BANK)
    question_summary = ", ".join(f"{key}: {value}" for key, value in sorted(type_counts.items()))
    recommended_cards = "".join(brain_question_card(question) for question in recommended_questions(QUESTION_BANK, season, goals, answers))
    recent_answers = "".join(
        f"<article class='item'><h4>{escape(getattr(answer, 'section', 'Reflection'))}</h4><p>{escape(getattr(answer, 'prompt', ''))}</p><p class='session-note'>{escape(getattr(answer, 'answer', ''))}</p></article>"
        for answer in sorted(answers, key=lambda item: getattr(item, "created_at", ""), reverse=True)[:8]
    ) or "<p class='muted'>No answers yet. Start with one question that feels relevant today.</p>"
    search_rows = "".join(
        f"<article class='item'><h4>{escape(item.query)}</h4><p>{escape(item.title or item.url or item.note or 'Saved search')}</p></article>"
        for item in sorted(searches, key=lambda entry: entry.created_at, reverse=True)[:5]
    ) or "<p class='muted'>Saved research will appear here.</p>"
    memory_rows = "".join(
        f"<article class='item'><div class='area-meta'><span>{escape(memory.memory_type)}</span></div><h4>{escape(memory.statement)}</h4><small>{escape(memory.created_at[:16].replace('T', ' '))}</small></article>"
        for memory in sorted(memories, key=lambda item: item.created_at, reverse=True)[:8]
    ) or "<p class='muted'>Confirmed memories will appear here after you save candidates.</p>"
    candidate_rows = brain_memory_candidates(answers, searches, memories)
    return f"""
<header class="page-head"><div><p>Local cognitive mirror</p><h2>Brain</h2></div><a class="button primary" href="/research">Open research</a></header>
<section class="coach-hero panel">
  <div>
    <span class="coach-status connected">Obsidian first</span>
    <h3>Build a visible, editable model of you</h3>
    <p>Kairos stores raw answers separately from generated summaries. Use this for self-understanding, not diagnosis.</p>
  </div>
  <form method="post" action="/brain/sync">
    <button class="primary">Sync brain to vault</button>
  </form>
</section>
<section class="coach-context"><div class="coach-context-grid">{cards}</div></section>
<section class="panel">
  <div class="panel-head"><div><h3>Recommended now</h3><p>Answer only what helps today's direction, season, or next block.</p></div></div>
  <div class="question-grid">{recommended_cards}</div>
</section>
<div class="grid two coach-grid">
  <form method="post" action="/brain/profile" class="panel stack">
    <div class="panel-head"><div><h3>Brain profile</h3><p>{progress}/6 core fields defined. Keep it honest and editable.</p></div></div>
    <label>Identity<textarea name="identity" rows="2" placeholder="I am becoming...">{escape(profile.identity)}</textarea></label>
    <label>Values<textarea name="values" rows="2" placeholder="What should guide choices when life is noisy?">{escape(profile.values)}</textarea></label>
    <label>Anti-vision<textarea name="anti_vision" rows="2" placeholder="What future are you avoiding?">{escape(profile.anti_vision)}</textarea></label>
    <label>Current state<textarea name="current_state" rows="3" placeholder="What is true about your life right now?">{escape(profile.current_state)}</textarea></label>
    <label>Strengths<textarea name="strengths" rows="2" placeholder="What already works for you?">{escape(profile.strengths)}</textarea></label>
    <label>Struggles<textarea name="struggles" rows="2" placeholder="What keeps breaking your discipline?">{escape(profile.struggles)}</textarea></label>
    <label>Energy patterns<textarea name="energy_patterns" rows="2" placeholder="When do you have clean energy, low energy, and drift risk?">{escape(profile.energy_patterns)}</textarea></label>
    <label>Motivation notes<textarea name="motivation_notes" rows="2" placeholder="Autonomy, competence, relatedness, pressure, comparison, meaning...">{escape(profile.motivation_notes)}</textarea></label>
    <button class="primary">Save profile</button>
  </form>
  <section class="panel">
    <div class="panel-head"><div><h3>Recent memory</h3><p>Raw answers and saved research that Coach can use.</p></div></div>
    <div class="list">{recent_answers}</div>
    <h3>Confirmed memories</h3>
    <div class="list">{memory_rows}</div>
    <h3>Memory candidates</h3>
    <div class="list">{candidate_rows}</div>
    <h3>Saved research</h3>
    <div class="list">{search_rows}</div>
  </section>
</div>
<section class="panel">
  <div class="panel-head"><div><h3>Question engine</h3><p>{len(QUESTION_BANK)} questions. {escape(question_summary)}.</p></div></div>
  <h3>Full library</h3>
  <div class="list">{question_cards}</div>
</section>"""


def recommended_questions(
    questions: list[dict[str, object]],
    season: CurrentSeason,
    goals: list[Goal],
    answers: list[object],
) -> list[dict[str, object]]:
    answered_ids = {getattr(answer, "question_id", "") for answer in answers}
    triggers: set[str] = {"today_setup", "weekly_planning"}
    if not season.title.strip() and not season.primary_track.strip():
        triggers.add("season_setup")
    if any(goal.status == "active" and not goal.tasks for goal in goals):
        triggers.add("new_goal")
    if season_current_day(season) >= 7:
        triggers.add("day_7_review")
    if season_current_day(season) >= 14:
        triggers.add("day_14_review")
    if season_current_day(season) >= 21:
        triggers.add("day_21_review")
    candidates = [
        question
        for question in questions
        if question.get("priority") == "high"
        and question.get("trigger") in triggers
        and question.get("id") not in answered_ids
    ]
    return candidates[:6] or [
        question
        for question in questions
        if question.get("priority") in {"high", "medium"} and question.get("id") not in answered_ids
    ][:6]


def brain_memory_candidates(
    answers: list[object],
    searches: list[SearchMemoryItem],
    memories: list[BrainMemory],
) -> str:
    existing_sources = {(memory.source_type, memory.source_id) for memory in memories if memory.source_id}
    cards: list[str] = []
    for answer in sorted(answers, key=lambda item: getattr(item, "created_at", ""), reverse=True)[:6]:
        answer_id = getattr(answer, "id", "")
        if ("answer", answer_id) in existing_sources:
            continue
        statement = candidate_from_answer(answer)
        cards.append(memory_candidate_card(statement, "pattern", "answer", answer_id))
    for item in sorted(searches, key=lambda entry: entry.created_at, reverse=True)[:4]:
        if ("research", item.id) in existing_sources:
            continue
        statement = item.note.strip() or item.snippet.strip() or item.title.strip()
        if statement:
            cards.append(memory_candidate_card(statement, "research", "research", item.id))
    return "".join(cards[:6]) or "<p class='muted'>No new candidates. Answer a reflection or save a research insight.</p>"


def candidate_from_answer(answer: object) -> str:
    construct = getattr(answer, "construct", "reflection")
    text = getattr(answer, "answer", "").strip()
    prompt = getattr(answer, "prompt", "").strip()
    if construct in {"planning_friction", "execution_friction"}:
        return f"Friction pattern: {text}"
    if construct in {"season_clarity", "season_learning"}:
        return f"Season insight: {text}"
    if prompt:
        return f"{prompt} Answer: {text}"
    return text


def memory_candidate_card(statement: str, memory_type: str, source_type: str, source_id: str) -> str:
    return f"""
<article class="item">
  <form method="post" action="/brain/memory" class="stack compact">
    <input type="hidden" name="source_type" value="{escape(source_type)}">
    <input type="hidden" name="source_id" value="{escape(source_id)}">
    <label>Candidate memory<textarea name="statement" rows="2">{escape(statement)}</textarea></label>
    <label>Type<input name="memory_type" value="{escape(memory_type)}"></label>
    <button>Confirm memory</button>
  </form>
</article>"""


def grouped_question_cards(questions: list[dict[str, object]]) -> str:
    sections: dict[str, list[dict[str, object]]] = {}
    for question in questions:
        sections.setdefault(str(question["section"]), []).append(question)
    groups = []
    for section, items in sections.items():
        cards = "".join(brain_question_card(question) for question in items)
        open_attr = ""
        section_label = f"{section} (optional)" if section.startswith("IPIP ") else section
        groups.append(
            f"""
<details class="panel secondary-panel"{open_attr}>
  <summary><span>{len(items)} questions</span><strong>{escape(section_label)}</strong></summary>
  <div class="question-grid">{cards}</div>
</details>"""
        )
    return "".join(groups)


def brain_question_card(question: dict[str, object]) -> str:
    qid = str(question["id"])
    response_type = str(question["response_type"])
    options = [str(item) for item in question.get("options", [])]
    if response_type in {"likert", "frequency", "choice"}:
        control = f"<select name='answer'>{''.join(f'<option value={quote_attr(item)}>{escape(item)}</option>' for item in options)}</select>"
    elif response_type == "ranking":
        control = f"<textarea name='answer' rows='2' placeholder='Rank: {escape(', '.join(options))}'></textarea>"
    else:
        control = "<textarea name='answer' rows='2' placeholder='Write the honest answer, not the impressive one.'></textarea>"
    return f"""
<article class="question-card">
  <span>{escape(str(question["section"]))} | {escape(str(question["source"]))}</span>
  <h4>{escape(str(question["prompt"]))}</h4>
  <form method="post" action="/brain/answer">
    <input type="hidden" name="question_id" value="{escape(qid)}">
    {control}
    <button>Save answer</button>
  </form>
</article>"""


def render_areas(areas: list[LifeArea], goals: list[Goal], sessions: list[FocusSession]) -> str:
    active_goals = [goal for goal in goals if goal.status == "active"]
    rows = "".join(area_card(area, active_goals, sessions) for area in areas)
    overview = areas_overview(areas, active_goals, sessions)
    return f"""
<header class="page-head"><div><p>Life scorecard</p><h2>Areas</h2></div><a class="button primary" href="/north-star">Edit North Star</a></header>
{overview}
<section class="area-grid">{rows}</section>"""


def areas_overview(areas: list[LifeArea], goals: list[Goal], sessions: list[FocusSession]) -> str:
    scored = sorted(areas, key=lambda area: (area.current_score, area.name))
    weakest = scored[0] if scored else None
    target_count = len([area for area in areas if area.weekly_target_minutes > 0])
    focus_minutes = sum(focus_minutes_for_area(area.id, goals, sessions) for area in areas)
    goal_area_count = len({goal.category for goal in goals})
    weakest_label = weakest.name if weakest else "No areas"
    return f"""
<section class="area-overview">
  <article class="panel">
    <span>Lowest score</span>
    <strong>{escape(weakest_label)}</strong>
    <p>Start here if life feels uneven.</p>
  </article>
  <article class="panel">
    <span>Weekly targets</span>
    <strong>{target_count}/{len(areas)}</strong>
    <p>Targets make balance measurable.</p>
  </article>
  <article class="panel">
    <span>Focus this week</span>
    <strong>{format_minutes(focus_minutes)}</strong>
    <p>Actual investment across all areas.</p>
  </article>
  <article class="panel">
    <span>Areas with goals</span>
    <strong>{goal_area_count}/{len(areas)}</strong>
    <p>Active outcomes should match priorities.</p>
  </article>
</section>"""


def area_card(area: LifeArea, goals: list[Goal], sessions: list[FocusSession]) -> str:
    area_goals = [goal for goal in goals if goal.category == area.id]
    minutes = focus_minutes_for_area(area.id, goals, sessions)
    target = area.weekly_target_minutes
    target_text = "No target" if target <= 0 else f"{format_minutes(minutes)} / {format_minutes(target)}"
    status, status_label, recommendation = area_status(area, minutes, len(area_goals))
    warning = f" {status}"
    return f"""
<article class="panel area-card{warning}">
  <div class="area-head">
    <div><span>Score</span><strong>{area.current_score}/10</strong></div>
    <h3>{escape(area.name)}</h3>
  </div>
  <p>{escape(area.desired_state or 'Define what strong looks like for this area.')}</p>
  <div class="area-meta">
    <span>{len(area_goals)} active goals</span>
    <span>{target_text}</span>
    <span>{escape(status_label)}</span>
  </div>
  <div class="progress"><span style="width:{area_progress_width(minutes, target)}%"></span></div>
  <p class="recommendation">{escape(recommendation)}</p>
  <form method="post" action="/areas/{area.id}" class="quick-targets" aria-label="Quick target for {escape(area.name)}">
    <input type="hidden" name="desired_state" value="{escape(area.desired_state)}">
    <input type="hidden" name="current_score" value="{area.current_score}">
    <input type="hidden" name="notes" value="{escape(area.notes)}">
    <button name="weekly_target_minutes" value="25">25m</button>
    <button name="weekly_target_minutes" value="50">50m</button>
    <button name="weekly_target_minutes" value="100">100m</button>
  </form>
  <details class="edit-details">
    <summary>Edit area</summary>
    <form method="post" action="/areas/{area.id}" class="stack compact">
      <label>Desired state<textarea name="desired_state" rows="2">{escape(area.desired_state)}</textarea></label>
      <div class="row">
        <label>Score<input type="number" min="1" max="10" name="current_score" value="{area.current_score}"></label>
        <label>Weekly minutes<input type="number" min="0" step="15" name="weekly_target_minutes" value="{area.weekly_target_minutes}"></label>
      </div>
      <label>Notes<textarea name="notes" rows="2">{escape(area.notes)}</textarea></label>
      <button>Update area</button>
    </form>
  </details>
</article>"""


def area_progress_width(minutes: int, target: int) -> int:
    if target <= 0:
        return 0
    return min(100, max(4, round((minutes / target) * 100)))


def area_status(area: LifeArea, minutes: int, goal_count: int) -> tuple[str, str, str]:
    if area.weekly_target_minutes <= 0:
        return "attention", "Needs target", "Set a weekly time target so this area can be managed intentionally."
    ratio = minutes / area.weekly_target_minutes
    if ratio >= 0.8:
        return "healthy", "Healthy", "This area is getting attention. Keep the rhythm steady."
    if ratio >= 0.35:
        return "attention", "Needs attention", "Schedule one more focus block before the week ends."
    if goal_count == 0:
        return "neglected", "Neglected", "Create one active goal or lower the target if this area is not a priority now."
    return "neglected", "Neglected", "Add this area to today's plan or protect time for it this week."


def focus_minutes_for_area(area_id: str, goals: list[Goal], sessions: list[FocusSession]) -> int:
    area_goal_ids = {goal.id for goal in goals if goal.category == area_id}
    week_start = date.today() - timedelta(days=date.today().weekday())
    total = 0
    for session in sessions:
        if session.status != "completed":
            continue
        try:
            if datetime.fromisoformat(session.started_at).date() < week_start:
                continue
        except ValueError:
            continue
        if session.session_type == "activity" and area_id == "health":
            total += session.duration_seconds // 60
        elif session.session_type == "pomodoro" and session.goal_id in area_goal_ids:
            total += session.duration_seconds // 60
    return total


def format_minutes(minutes: int) -> str:
    hours = minutes // 60
    remainder = minutes % 60
    if hours and remainder:
        return f"{hours}h {remainder}m"
    if hours:
        return f"{hours}h"
    return f"{remainder}m"


def render_history(
    goals: dict[str, Goal],
    areas: list[LifeArea],
    sessions: list[FocusSession],
    logs: list[DailyLog],
    weekly_plan: WeeklyPlan,
    season: CurrentSeason,
) -> str:
    week_sessions = sessions_for_current_week(sessions)
    week_key = current_week_key()
    week_logs = daily_logs_for_current_week(logs)
    completed = [session for session in week_sessions if session.status == "completed" and session.session_type == "pomodoro"]
    traction_minutes = sum(session.duration_seconds for session in completed) // 60
    partial_or_blocked = [session for session in week_sessions if session.status in {"partial", "blocked"} and session.session_type == "pomodoro"]
    planned_days = len([log for log in week_logs if log.intention.strip() or log.must_win.strip()])
    shutdown_days = len([log for log in week_logs if log.shutdown.strip()])
    pact_days = len([log for log in week_logs if log.pact.strip()])
    total_minutes = sum(session.duration_seconds for session in week_sessions if session.session_type == "pomodoro") // 60
    activity_minutes = sum(session.duration_seconds for session in week_sessions if session.session_type == "activity") // 60
    planned_minutes = sum(item.planned_minutes for item in weekly_plan.items)
    backlog_minutes = sum(item.backlog_minutes for item in weekly_plan.items)
    target_minutes = planned_minutes + backlog_minutes
    adherence = round((min(total_minutes, target_minutes) / target_minutes) * 100) if target_minutes else 0
    surplus = max(0, total_minutes - target_minutes)
    area_rows = review_area_rows(areas, goals, week_sessions)
    trigger_rows = trigger_review_rows(week_sessions)
    insight_title, insight_body, insight_action = review_insight(total_minutes, planned_days, shutdown_days, partial_or_blocked, areas, goals, week_sessions)
    decisions = review_decisions(
        goals,
        areas,
        week_sessions,
        logs,
        weekly_plan,
        target_minutes,
        planned_days,
        shutdown_days,
        partial_or_blocked,
    )
    recent_rows = []
    for session in sessions[:80]:
        recent_rows.append(
            f"<article class='item'><h4>{escape(session_title(goals, session))}</h4><p>{session.duration_seconds // 60} min | {escape(session.status)} | {escape(session.started_at[:16].replace('T', ' '))}</p>{session_note(session)}</article>"
        )
    body = "".join(recent_rows) or "<p class='muted'>No sessions yet.</p>"
    cards = "".join(
        metric(label, value, tone)
        for label, value, tone in [
            ("Focus this week", format_minutes(total_minutes), "primary"),
            ("Weekly target", format_minutes(target_minutes), "strong"),
            ("Adherence", f"{adherence}%", ""),
            ("Surplus", format_minutes(surplus), ""),
        ]
    )
    planning_cards = "".join(
        metric(label, value, tone)
        for label, value, tone in [
            ("Capacity", format_minutes(weekly_plan.capacity_minutes), "primary"),
            ("Planned", format_minutes(planned_minutes), ""),
            ("Backlog", format_minutes(backlog_minutes), ""),
            ("Activity", format_minutes(activity_minutes), ""),
        ]
    )
    charts = review_charts(goals, areas, week_sessions, sessions)
    season_panel = review_season_panel(season, sessions)
    return f"""
<header class='page-head'><div><p>Weekly learning</p><h2>Review</h2></div><div class="row"><a class='button' href='/weekly'>Plan week</a><a class='button primary' href='/focus'>Start focus</a></div></header>
<section class='review-hero panel'>
  <div>
    <span>Weekly readout</span>
    <h3>{escape(insight_title)}</h3>
    <p>{escape(insight_body)}</p>
  </div>
  <a class='button primary' href='{escape(insight_action[1])}'>{escape(insight_action[0])}</a>
</section>
{season_panel}
{decisions}
<section class='metrics review-metrics'>{cards}</section>
<section class='metrics review-metrics'>{planning_cards}</section>
{charts}
<div class='grid two'>
  <section class='panel'>
    <div class='panel-head'><div><h3>Area balance</h3><p>Compare where your time went against the life areas you said matter.</p></div></div>
    <div class='list'>{area_rows}</div>
  </section>
  <section class='panel'>
    <div class='panel-head'><div><h3>Trigger review</h3><p>Time management improves when discomfort patterns become visible.</p></div></div>
    <div class='list'>{trigger_rows}</div>
  </section>
</div>
<div class='grid two review-lower'>
  <section class='panel'>
    <div class='panel-head'><div><h3>Weekly reflection</h3><p>Use these prompts during shutdown or your weekly reset.</p></div></div>
    <div class='review-prompts'>
      <div><span>Win</span><p>What moved forward this week?</p></div>
      <div><span>Pain</span><p>What discomfort repeatedly pulled you away?</p></div>
      <div><span>Pact</span><p>What rule should protect next week's traction?</p></div>
    </div>
  </section>
  <section class='panel'>
    <div class='panel-head'><div><h3>Traction summary</h3><p>Completed blocks count as traction. Partial and blocked blocks show where to improve the system.</p></div></div>
    <div class='traction-summary'>
      <strong>{len(completed)}</strong><span>completed blocks</span>
      <strong>{len(partial_or_blocked)}</strong><span>partial or blocked blocks</span>
      <strong>{shutdown_days}/7</strong><span>shutdowns</span>
    </div>
  </section>
</div>
<section class='panel review-list'>
  <div class='panel-head'><div><h3>Recent sessions</h3><p>Evidence of work, including partial and blocked blocks.</p></div></div>
  <div class='list'>{body}</div>
</section>"""


def review_season_panel(season: CurrentSeason, sessions: list[FocusSession]) -> str:
    if not season.title.strip() and not season.primary_track.strip():
        return ""
    start, end = season_dates(season)
    season_sessions = [
        session
        for session in sessions
        if session.session_type == "pomodoro"
        and (session_day := session_date(session)) is not None
        and start <= session_day <= end
    ]
    minutes = sum(session.duration_seconds for session in season_sessions) // 60
    target = season.weekly_target_minutes * max(1, ((end - start).days + 1 + 6) // 7)
    target_text = f"{format_minutes(minutes)} / {format_minutes(target)}" if target else format_minutes(minutes)
    return f"""
<section class="panel">
  <div class="panel-head">
    <div>
      <span class="pill">{escape(season_day_label(season))}</span>
      <h3>{escape(season.title or "21-day season")}</h3>
      <p><strong>Primary:</strong> {escape(season.primary_track or "Not set")}</p>
    </div>
    <a class="button" href="/season">Review season</a>
  </div>
  <div class="metrics">
    {metric("Season focus", target_text, "primary")}
    {metric("Daily minimum", f"{season.daily_minimum_minutes} min", "")}
    {metric("Checkpoint", season_checkpoint_label(season), "")}
    {metric("Decision", season.final_decision or season.review_question or "Continue, adjust, or pause?", "strong")}
  </div>
</section>"""


def review_decisions(
    goals: dict[str, Goal],
    areas: list[LifeArea],
    week_sessions: list[FocusSession],
    logs: list[DailyLog],
    weekly_plan: WeeklyPlan,
    target_minutes: int,
    planned_days: int,
    shutdown_days: int,
    partial_or_blocked: list[FocusSession],
) -> str:
    items: list[tuple[str, str, str, str]] = []
    if weekly_plan.capacity_minutes > 0 and target_minutes == 0:
        items.append(("Allocate this week", "Capacity exists but no goals have target minutes yet.", "/weekly", "Allocate"))
    if planned_days == 0:
        items.append(("Plan the next day", "No daily intention or must-win is recorded this week.", "/", "Plan"))
    no_task_goal = next((goal for goal in sorted_goals(goals.values()) if goal.status == "active" and not goal.tasks), None)
    if no_task_goal:
        items.append((f"Give {no_task_goal.title} a task", "A goal without a concrete task cannot become a focus block.", f"/goals?selected={no_task_goal.id}", "Fix goal"))
    untargeted = next((area for area in areas if area.weekly_target_minutes <= 0), None)
    if untargeted:
        items.append((f"Set a target for {untargeted.name}", "Review cannot judge balance until this area has a weekly time budget.", "/areas", "Set target"))
    trigger_counts = count_values(
        value
        for session in week_sessions
        for value in [session.internal_trigger, session.external_trigger, session.pact]
    )
    if trigger_counts:
        top_trigger = sorted(trigger_counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
        items.append((f"Design around {top_trigger}", "Repeated trigger data is a cue to change the environment, pact, or task size.", "#trigger-review", "Review"))
    if partial_or_blocked:
        items.append(("Simplify blocked work", "Partial or blocked sessions mean the task was too large, unclear, or under-supported.", "/goals", "Simplify"))
    if shutdown_days == 0:
        items.append(("Add shutdown review", "End-of-day closure is where Kairos learns what to carry forward.", "/#daily-shutdown", "Shutdown"))
    if not items:
        items.append(("Keep the loop steady", "Planning, focus, and review signals are present. Protect consistency over novelty.", "/focus", "Focus"))
    cards = "".join(
        f"""
<article class="decision-card">
  <span>{index}</span>
  <div><h4>{escape(title)}</h4><p>{escape(body)}</p></div>
  <a class="button" href="{escape(href)}">{escape(action)}</a>
</article>"""
        for index, (title, body, href, action) in enumerate(items[:3], start=1)
    )
    return f"""
<section class="panel decision-panel">
  <div class="panel-head"><div><h3>3 decisions for next week</h3><p>Use Review to make choices, not to stare at more data.</p></div></div>
  <div class="decision-grid">{cards}</div>
</section>"""


def review_charts(
    goals: dict[str, Goal],
    areas: list[LifeArea],
    week_sessions: list[FocusSession],
    all_sessions: list[FocusSession],
) -> str:
    return f"""
<section class="review-chart-grid">
  {weekly_focus_chart(week_sessions)}
  {area_budget_chart(areas, goals, week_sessions)}
  {focus_heatmap(all_sessions)}
  {goal_progress_chart(list(goals.values()))}
  {outcome_mix_chart(week_sessions)}
  {trigger_rank_chart(week_sessions)}
</section>"""


def weekly_focus_chart(week_sessions: list[FocusSession]) -> str:
    start = date.today() - timedelta(days=date.today().weekday())
    rows: list[tuple[str, int, int]] = []
    for offset in range(7):
        day = start + timedelta(days=offset)
        day_sessions = [
            session
            for session in week_sessions
            if session_date(session) == day and session.status == "completed" and session.session_type == "pomodoro"
        ]
        minutes = sum(session.duration_seconds for session in day_sessions) // 60
        rows.append((day.strftime("%a"), minutes, len(day_sessions)))
    max_minutes = max([minutes for _, minutes, _ in rows] + [1])
    bars = "".join(
        f"""
<div class="day-bar">
  <div class="bar-track vertical"><span style="height:{max(4 if minutes else 0, round((minutes / max_minutes) * 100))}%"></span></div>
  <strong>{minutes}</strong>
  <small>{escape(label)}</small>
</div>"""
        for label, minutes, _ in rows
    )
    total_blocks = sum(blocks for _, _, blocks in rows)
    return f"""
<article class="panel chart-card focus-trend">
  <div class="panel-head"><div><h3>Weekly focus trend</h3><p>Minutes completed each day.</p></div><span>{total_blocks} blocks</span></div>
  <div class="day-bars">{bars}</div>
</article>"""


def focus_heatmap(sessions: list[FocusSession], weeks: int = 13) -> str:
    end = date.today()
    start = end - timedelta(days=weeks * 7 - 1)
    start = start - timedelta(days=start.weekday())
    totals: dict[date, int] = {}
    for session in sessions:
        if session.session_type != "pomodoro" or session.status not in {"completed", "partial", "blocked"}:
            continue
        day = session_date(session)
        if day is None or day < start or day > end:
            continue
        totals[day] = totals.get(day, 0) + session.duration_seconds // 60
    max_minutes = max(totals.values(), default=1)
    cells = []
    total_days = (end - start).days + 1
    for offset in range(total_days):
        day = start + timedelta(days=offset)
        minutes = totals.get(day, 0)
        level = 0 if minutes == 0 else min(4, max(1, round((minutes / max_minutes) * 4)))
        cells.append(
            f"<span class='heat-cell level-{level}' title='{day.isoformat()}: {minutes} min'></span>"
        )
    return f"""
<article class="panel chart-card heatmap-card">
  <div class="panel-head"><div><h3>Focus consistency</h3><p>Daily focus minutes over the last {weeks} weeks.</p></div></div>
  <div class="heatmap-grid">{''.join(cells)}</div>
</article>"""


def area_budget_chart(
    areas: list[LifeArea],
    goals: dict[str, Goal],
    week_sessions: list[FocusSession],
) -> str:
    goal_list = list(goals.values())
    rows = []
    max_value = max(
        [
            max(area.weekly_target_minutes, focus_minutes_for_area(area.id, goal_list, week_sessions))
            for area in areas
        ]
        + [1]
    )
    for area in areas:
        actual = focus_minutes_for_area(area.id, goal_list, week_sessions)
        target = area.weekly_target_minutes
        actual_width = round((actual / max_value) * 100) if max_value else 0
        target_width = round((target / max_value) * 100) if max_value else 0
        rows.append(
            f"""
<div class="comparison-row">
  <div><strong>{escape(area.name)}</strong><span>{format_minutes(actual)} actual | {format_minutes(target) if target else 'no target'}</span></div>
  <div class="comparison-bars">
    <span class="actual" style="width:{actual_width}%"></span>
    <span class="target" style="width:{target_width}%"></span>
  </div>
</div>"""
        )
    return f"""
<article class="panel chart-card">
  <div class="panel-head"><div><h3>Area actual vs target</h3><p>Whether time matches stated priorities.</p></div></div>
  <div class="comparison-list">{''.join(rows)}</div>
</article>"""


def goal_progress_chart(goals: list[Goal]) -> str:
    active = [goal for goal in sorted_goals(goals) if goal.status == "active"][:6]
    if not active:
        body = "<p class='muted'>No active goals yet.</p>"
    else:
        rows = []
        for goal in active:
            counts = task_status_counts(goal)
            total = sum(counts.values())
            segments = "".join(
                f"<span class='{status}' style='width:{status_width(count, total)}%'></span>"
                for status, count in counts.items()
                if count
            )
            rows.append(
                f"""
<div class="goal-chart-row">
  <div><strong>{escape(goal.title)}</strong><span>{escape(goal.priority)} | {escape(area_label(goal.category))}</span></div>
  <div class="stacked-bar">{segments}</div>
  <small>{counts['done']} done | {counts['in_progress']} doing | {counts['on_hold']} on hold | {counts['blocked']} blocked | {counts['todo']} todo</small>
</div>"""
            )
        body = "".join(rows)
    return f"""
<article class="panel chart-card">
  <div class="panel-head"><div><h3>Goal progress</h3><p>Task state across active outcomes.</p></div></div>
  <div class="goal-chart-list">{body}</div>
</article>"""


def outcome_mix_chart(week_sessions: list[FocusSession]) -> str:
    focus_sessions = [session for session in week_sessions if session.session_type == "pomodoro"]
    counts = {
        "completed": len([session for session in focus_sessions if session.status == "completed"]),
        "partial": len([session for session in focus_sessions if session.status == "partial"]),
        "blocked": len([session for session in focus_sessions if session.status == "blocked"]),
    }
    total = sum(counts.values())
    segments = "".join(
        f"<span class='{status}' style='width:{status_width(count, total)}%'></span>"
        for status, count in counts.items()
        if count
    )
    if not segments:
        segments = "<span class='empty' style='width:100%'></span>"
    legend = "".join(
        f"<div><span class='legend-dot {status}'></span><strong>{count}</strong><small>{escape(status.title())}</small></div>"
        for status, count in counts.items()
    )
    return f"""
<article class="panel chart-card compact-chart">
  <div class="panel-head"><div><h3>Outcome mix</h3><p>Quality of execution.</p></div></div>
  <div class="stacked-bar large">{segments}</div>
  <div class="chart-legend">{legend}</div>
</article>"""


def trigger_rank_chart(week_sessions: list[FocusSession]) -> str:
    focus_sessions = [session for session in week_sessions if session.session_type == "pomodoro"]
    counts = count_values(
        value
        for session in focus_sessions
        for value in [session.internal_trigger, session.external_trigger, session.pact]
    )
    if not counts:
        body = "<p class='muted'>No trigger, friction, or pact patterns logged yet.</p>"
    else:
        max_count = max(counts.values())
        body = "".join(
            f"""
<div class="rank-row">
  <div><strong>{escape(name)}</strong><span>{count} logged</span></div>
  <div class="bar-track"><span style="width:{round((count / max_count) * 100)}%"></span></div>
</div>"""
            for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:6]
        )
    return f"""
<article class="panel chart-card compact-chart" id="trigger-review">
  <div class="panel-head"><div><h3>Trigger and pact ranking</h3><p>Repeated patterns worth designing around.</p></div></div>
  <div class="rank-list">{body}</div>
</article>"""


def task_status_counts(goal: Goal) -> dict[str, int]:
    counts = {"done": 0, "in_progress": 0, "on_hold": 0, "blocked": 0, "todo": 0}
    for task in goal.tasks:
        if task.status in counts:
            counts[task.status] += 1
        else:
            counts["todo"] += 1
    return counts


def status_width(count: int, total: int) -> int:
    if total <= 0 or count <= 0:
        return 0
    return max(6, round((count / total) * 100))


def session_date(session: FocusSession) -> date | None:
    try:
        return datetime.fromisoformat(session.started_at).date()
    except ValueError:
        return None


def review_insight(
    total_minutes: int,
    planned_days: int,
    shutdown_days: int,
    partial_or_blocked: list[FocusSession],
    areas: list[LifeArea],
    goals: dict[str, Goal],
    sessions: list[FocusSession],
) -> tuple[str, str, tuple[str, str]]:
    if planned_days == 0:
        return (
            "This week needs a plan",
            "No planning days are recorded yet. Start with one intention, one must-win, and one protected focus block.",
            ("Plan today", "/"),
        )
    if total_minutes == 0:
        return (
            "Planning has not turned into focus yet",
            "The week has planning signals but no recorded focus minutes. Pick the next concrete task and run a short block.",
            ("Start focus", "/focus"),
        )
    if partial_or_blocked:
        return (
            "Friction is visible",
            "Partial or blocked blocks were recorded. Review triggers and simplify the next task before adding more work.",
            ("Review triggers", "#trigger-review"),
        )
    neglected = [
        area
        for area in areas
        if area.weekly_target_minutes > 0
        and focus_minutes_for_area(area.id, list(goals.values()), sessions) < area.weekly_target_minutes * 0.35
    ]
    if neglected:
        return (
            f"{neglected[0].name} needs attention",
            "One of your stated life areas is underfunded this week. Put one block for it on today's plan.",
            ("Review areas", "/areas"),
        )
    if shutdown_days == 0:
        return (
            "Close the loop",
            "Focus is happening, but shutdowns are missing. End-of-day review is where the system learns.",
            ("Shutdown today", "/#daily-discipline"),
        )
    return (
        "The loop is working",
        "Planning, focus, and review signals are present. Keep the rhythm and look for the next bottleneck.",
        ("Continue focus", "/focus"),
    )


def sessions_for_current_week(sessions: list[FocusSession]) -> list[FocusSession]:
    start = date.today() - timedelta(days=date.today().weekday())
    items = []
    for session in sessions:
        if session.status not in {"completed", "partial", "blocked"}:
            continue
        try:
            if datetime.fromisoformat(session.started_at).date() >= start:
                items.append(session)
        except ValueError:
            continue
    return items


def daily_logs_for_current_week(logs: list[DailyLog]) -> list[DailyLog]:
    start = date.today() - timedelta(days=date.today().weekday())
    items = []
    for log in logs:
        try:
            if date.fromisoformat(log.log_date) >= start:
                items.append(log)
        except ValueError:
            continue
    return items


def session_title(goals: dict[str, Goal], session: FocusSession) -> str:
    if session.session_type == "activity":
        return f"Activity: {(session.activity_type or 'other').replace('_', ' ').title()}"
    goal = goals.get(session.goal_id)
    title = goal.title if goal else "Deleted goal"
    if goal and session.task_id:
        task = next((item for item in goal.tasks if item.id == session.task_id), None)
        if task:
            title = f"{title}: {task.title}"
    return title


def session_note(session: FocusSession) -> str:
    tags = [
        f"Internal: {session.internal_trigger}" if session.internal_trigger else "",
        f"External: {session.external_trigger}" if session.external_trigger else "",
        f"Pact: {session.pact}" if session.pact else "",
        f"Quality: {session.quality}/5" if session.quality else "",
        f"Mood: {session.mood}/5" if session.mood else "",
        f"Energy: {session.energy}/5" if session.energy else "",
        session.notes.strip(),
    ]
    text = " | ".join(item for item in tags if item)
    if not text:
        return ""
    return f"<p class='session-note'>{escape(text)}</p>"


def review_area_rows(areas: list[LifeArea], goals: dict[str, Goal], sessions: list[FocusSession]) -> str:
    rows = []
    goal_list = list(goals.values())
    for area in areas:
        area_goal_ids = {goal.id for goal in goal_list if goal.category == area.id}
        minutes = sum(
            session.duration_seconds
            for session in sessions
            if (session.session_type == "pomodoro" and session.goal_id in area_goal_ids)
            or (session.session_type == "activity" and area.id == "health")
        ) // 60
        target = area.weekly_target_minutes
        status, status_label, recommendation = area_status(area, minutes, len(area_goal_ids))
        target_label = format_minutes(target) if target else "no target"
        rows.append(
            f"<article class='item area-review {status}'><div><h4>{escape(area.name)}</h4><p>{format_minutes(minutes)} focused | {target_label}</p><p>{escape(recommendation)}</p></div><span>{escape(status_label)}</span></article>"
        )
    return "".join(rows)


def trigger_review_rows(sessions: list[FocusSession]) -> str:
    focus_sessions = [session for session in sessions if session.session_type == "pomodoro"]
    internal = count_values(session.internal_trigger for session in focus_sessions)
    external = count_values(session.external_trigger for session in focus_sessions)
    pacts = count_values(session.pact for session in focus_sessions)
    rows = [
        trigger_row("Internal trigger", internal, "No internal triggers logged yet."),
        trigger_row("External trigger", external, "No external triggers logged yet."),
        trigger_row("Pact used", pacts, "No focus pacts logged yet."),
    ]
    return "".join(rows)


def count_values(values: object) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        text = str(value).strip()
        if not text:
            continue
        counts[text] = counts.get(text, 0) + 1
    return counts


def trigger_row(label: str, counts: dict[str, int], empty: str) -> str:
    if not counts:
        return f"<article class='item'><h4>{escape(label)}</h4><p>{escape(empty)}</p></article>"
    name, count = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0]
    return f"<article class='item trigger-row'><div><h4>{escape(label)}</h4><p>{escape(name)}</p></div><strong>{count}</strong></article>"


def render_research(
    query: str,
    results: list[dict[str, str]],
    error: str,
    saved: list[SearchMemoryItem],
    sessions: list[ResearchSession],
    active_session: ResearchSession | None = None,
    reader: dict[str, str] | None = None,
) -> str:
    result_rows = "".join(research_result_card(query, item) for item in results[:8])
    if not result_rows:
        message = error or "Search locally, open a result to read it here, then save only what matters."
        result_rows = f"<p class='muted'>{escape(message)}</p>"
    reader_panel = render_reader_panel(reader) if reader else ""
    answer_panel = render_research_answer(active_session) if active_session else ""
    saved_rows = "".join(
        f"<article class='item'><h4>{escape(item.query)}</h4><p>{escape(item.title or item.url or item.note or 'Saved research')}</p><p class='session-note'>{escape(item.note)}</p></article>"
        for item in sorted(saved, key=lambda entry: entry.created_at, reverse=True)[:12]
    ) or "<p class='muted'>No saved research yet.</p>"
    session_rows = "".join(
        research_session_row(item)
        for item in sorted(sessions, key=lambda entry: entry.created_at, reverse=True)[:8]
    ) or "<p class='muted'>No research sessions yet.</p>"
    count_label = f"{len(results[:8])} results" if results else "Search memory"
    session_steps = research_session_steps(bool(query), bool(reader), len(saved))
    return f"""
<header class="page-head"><div><p>Search memory</p><h2>Research</h2></div><a class="button primary" href="/brain">Open brain</a></header>
{session_steps}
{answer_panel}
{reader_panel}
<div class="research-layout">
  <section class="panel research-main">
    <div class="panel-head"><div><h3>Research question</h3><p>Ask a question, get source-backed synthesis, then save the insight that should affect your plan.</p></div><span class="pill">{escape(count_label)}</span></div>
    <form method="post" action="/research" class="research-search">
      <input name="query" value="{escape(query)}" placeholder="Ask a research question">
      <button class="primary">Research</button>
    </form>
    <div class="research-results">{result_rows}</div>
  </section>
  <section class="research-side">
    <details class="panel manual-save">
      <summary><h3>Manual save</h3><span>Capture article, idea, or query</span></summary>
      <form method="post" action="/research/save" class="stack">
        <input name="query" value="{escape(query)}" placeholder="Search intent or question" required>
        <input name="title" placeholder="Result title">
        <input name="url" placeholder="URL">
        <textarea name="snippet" rows="2" placeholder="Snippet or summary"></textarea>
        <input name="linked_to" placeholder="Linked goal, area, or theme">
        <textarea name="note" rows="2" placeholder="Why this matters"></textarea>
        <button class="primary">Save to memory</button>
      </form>
    </details>
    <section class="panel saved-memory">
      <div class="panel-head"><div><h3>Saved memory</h3><p>Pages you chose to keep.</p></div></div>
    <div class="list">{saved_rows}</div>
    </section>
    <section class="panel saved-memory">
      <div class="panel-head"><div><h3>Research sessions</h3><p>Question, answer, and sources kept together.</p></div></div>
      <div class="list">{session_rows}</div>
    </section>
  </section>
</div>"""


def render_research_answer(session: ResearchSession | None) -> str:
    if session is None:
        return ""
    source_rows = "".join(
        f"<li><a href='{escape(source.url)}' target='_blank' rel='noreferrer'>{escape(source.title or source.url)}</a></li>"
        for source in session.sources[:6]
    )
    return f"""
<section class="panel reader-panel">
  <div class="panel-head">
    <div><span class="pill">{len(session.sources)} sources</span><h3>{escape(session.question)}</h3></div>
    <form method="post" action="/research/save">
      <input type="hidden" name="session_id" value="{escape(session.id)}">
      <input type="hidden" name="query" value="{escape(session.question)}">
      <input type="hidden" name="title" value="Research answer">
      <input type="hidden" name="snippet" value="{escape(session.answer)}">
      <input name="linked_to" placeholder="Link to season, goal, or area">
      <textarea name="note" rows="2" placeholder="Confirmed insight to remember"></textarea>
      <button>Save to Brain memory</button>
    </form>
  </div>
  <div class="reader-grid">
    <div class="coach-answer">{readable_paragraphs(session.answer)}</div>
    <div class="reader-save"><h4>Sources</h4><ol>{source_rows}</ol></div>
  </div>
</section>"""


def research_session_row(session: ResearchSession) -> str:
    status = "Saved insight" if session.saved_insight.strip() else "Unsaved"
    note = session.saved_insight.strip() or session.answer[:220]
    linked = f" | {session.linked_to}" if session.linked_to.strip() else ""
    return f"""
<article class='item'>
  <div class="area-meta"><span>{escape(status)}</span><span>{len(session.sources)} sources</span></div>
  <h4>{escape(session.question)}</h4>
  <p>{escape(note)}</p>
  <small>{escape(session.created_at[:16].replace('T', ' '))}{escape(linked)}</small>
</article>"""


def research_session_steps(has_query: bool, has_reader: bool, saved_count: int) -> str:
    steps = [
        ("Search", "Ask a real question", has_query),
        ("Read", "Open one result inside Kairos", has_reader),
        ("Save", "Keep the excerpt and why it matters", saved_count > 0),
    ]
    body = "".join(
        f"<article class='{'done' if done else ''}'><span>{index}</span><div><strong>{escape(title)}</strong><small>{escape(text)}</small></div></article>"
        for index, (title, text, done) in enumerate(steps, start=1)
    )
    return f"""
<section class="research-session panel">
  <div><h3>Research session</h3><p>Search is only useful when it becomes a decision, memory, or concrete task.</p></div>
  <div class="research-steps">{body}</div>
</section>"""


def render_reader_panel(reader: dict[str, str] | None) -> str:
    if not reader:
        return ""
    title = reader.get("title", "") or "Readable page"
    url = reader.get("url", "")
    query = reader.get("query", "")
    text = reader.get("text", "")
    snippet = reader.get("snippet", "") or text[:1400]
    read_error = reader.get("read_error", "")
    notice = f"<p class='muted reader-notice'>{escape(read_error)} Open the original in another tab, then save your note here.</p>" if read_error else ""
    return f"""
<section class="panel reader-panel">
  <div class="panel-head">
    <div>
      <h3>{escape(title)}</h3>
      <p>{escape(url)}</p>
    </div>
    <a class="button" href="{escape(url)}" target="_blank" rel="noreferrer">Open original</a>
  </div>
  {notice}
  <div class="reader-grid">
    <div class="reader-content">{readable_paragraphs(text)}</div>
    <form method="post" action="/research/save" class="reader-save">
      <h4>Save to memory</h4>
      <input type="hidden" name="query" value="{escape(query)}">
      <input type="hidden" name="title" value="{escape(title)}">
      <input type="hidden" name="url" value="{escape(url)}">
      <label>Useful excerpt<textarea name="snippet" rows="7">{escape(snippet[:1800])}</textarea></label>
      <label>Link to<input name="linked_to" placeholder="Goal, area, North Star theme, or open question"></label>
      <label>Why remember this?<textarea name="note" rows="4" placeholder="What did you learn? What should it change?"></textarea></label>
      <button class="primary">Save after reading</button>
    </form>
  </div>
</section>"""


def readable_paragraphs(text: str) -> str:
    paragraphs = [item.strip() for item in text.split("\n") if len(item.strip()) >= 40]
    if not paragraphs:
        return "<p class='muted'>Could not extract much readable text from this page. Open the original, then save a manual note if useful.</p>"
    return "".join(f"<p>{escape(paragraph)}</p>" for paragraph in paragraphs[:12])


def research_result_card(query: str, item: dict[str, str]) -> str:
    read_url = "/research/read?" + urlencode(
        {
            "query": query,
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "snippet": item.get("snippet", ""),
        }
    )
    return f"""
<article class="research-result">
  <div class="research-result-body">
    <h4>{escape(item.get("title", "Untitled"))}</h4>
    <a class="result-url" href="{escape(item.get("url", ""))}" target="_blank" rel="noreferrer">{escape(item.get("url", ""))}</a>
    <p class="session-note">{escape(item.get("snippet", ""))}</p>
    <div class="actions"><a class="button primary" href="{escape(read_url)}">Read in Kairos</a><a class="button" href="{escape(item.get("url", ""))}" target="_blank" rel="noreferrer">Open original</a></div>
  </div>
  <details class="quick-save">
    <summary>Quick save</summary>
    <form method="post" action="/research/save" class="stack">
      <input type="hidden" name="query" value="{escape(query)}">
      <input type="hidden" name="title" value="{escape(item.get("title", ""))}">
      <input type="hidden" name="url" value="{escape(item.get("url", ""))}">
      <input type="hidden" name="snippet" value="{escape(item.get("snippet", ""))}">
      <input name="linked_to" placeholder="Link to goal/area/theme">
      <input name="note" placeholder="Why save this?">
      <button>Save</button>
    </form>
  </details>
</article>"""


def synthesize_research_answer(question: str, sources: list[ResearchSource]) -> str:
    if not sources:
        return "No useful sources were found. Try a narrower question or configure SearXNG."
    lines = [
        f"Research question: {question}",
        "",
        "Working answer:",
    ]
    for index, source in enumerate(sources[:5], start=1):
        snippet = source.snippet.strip() or "No snippet was available from this source."
        title = source.title.strip() or source.url.strip() or f"Source {index}"
        lines.append(f"{index}. {snippet} [{index}]")
        lines.append(f"   Source: {title}")
    lines.extend(
        [
            "",
            "How to use this:",
            "Treat this as a source-backed first pass, then open the strongest sources and save only the insight that changes a goal, season, or decision.",
        ]
    )
    return "\n".join(lines)


def searxng_search(query: str) -> tuple[list[dict[str, str]], str]:
    if not query:
        return [], ""
    base_url = os.environ.get("KAIROS_SEARXNG_URL", "").strip().rstrip("/")
    if not base_url:
        return [], "KAIROS_SEARXNG_URL is not configured."
    url = f"{base_url}/search?{urlencode({'q': query, 'format': 'json'})}"
    request = Request(url, headers={"User-Agent": "Kairos local brain"})
    try:
        with urlopen(request, timeout=12) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        return [], f"SearXNG search failed: {error}"
    results = []
    for item in data.get("results", []):
        results.append(
            {
                "title": str(item.get("title", "")),
                "url": str(item.get("url", "")),
                "snippet": str(item.get("content", "") or item.get("snippet", "")),
            }
        )
    return results, ""


def fetch_readable_page(url: str) -> tuple[dict[str, str] | None, str]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None, "Choose a valid http or https result to read."
    request = Request(
        url,
        headers={
            "User-Agent": "Kairos local reader",
            "Accept": "text/html,application/xhtml+xml,text/plain;q=0.8,*/*;q=0.2",
        },
    )
    try:
        with urlopen(request, timeout=15) as response:
            content_type = response.headers.get("content-type", "")
            charset = response.headers.get_content_charset() or "utf-8"
            raw = response.read(900_000)
    except (HTTPError, URLError, TimeoutError) as error:
        return None, f"Could not read that page inside Kairos: {error}"
    text = raw.decode(charset, errors="ignore")
    if "html" in content_type or "<html" in text[:500].lower():
        extractor = ReadableHTMLExtractor()
        extractor.feed(text)
        body = extractor.text()
        title = extractor.title.strip()
    else:
        body = normalize_readable_text(text)
        title = parsed.netloc
    if not body:
        return None, "Kairos opened the page but could not extract readable text."
    return {
        "url": url,
        "title": title or parsed.netloc,
        "text": body[:12000],
        "snippet": body[:1800],
    }, ""


class ReadableHTMLExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.title_parts: list[str] = []
        self.skip_stack: list[str] = []
        self.in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg", "canvas", "form", "nav", "footer", "header"}:
            self.skip_stack.append(tag)
        if tag == "title":
            self.in_title = True
        if tag in {"p", "br", "li", "h1", "h2", "h3", "article", "section"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self.skip_stack and self.skip_stack[-1] == tag:
            self.skip_stack.pop()
        if tag == "title":
            self.in_title = False
        if tag in {"p", "li", "h1", "h2", "h3", "article", "section"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        cleaned = " ".join(data.split())
        if not cleaned:
            return
        if self.in_title:
            self.title_parts.append(cleaned)
            return
        if self.skip_stack:
            return
        self.parts.append(cleaned)

    @property
    def title(self) -> str:
        return " ".join(self.title_parts)

    def text(self) -> str:
        return normalize_readable_text(" ".join(self.parts))


def normalize_readable_text(value: str) -> str:
    lines = []
    current = ""
    for token in value.replace("\r", "\n").split("\n"):
        token = " ".join(token.split())
        if not token:
            if current:
                lines.append(current.strip())
                current = ""
            continue
        current = f"{current} {token}".strip()
        if len(current) >= 260:
            lines.append(current.strip())
            current = ""
    if current:
        lines.append(current.strip())
    seen = set()
    kept = []
    for line in lines:
        lowered = line.lower()
        if len(line) < 25 or lowered in seen:
            continue
        seen.add(lowered)
        kept.append(line)
    return "\n".join(kept)


def render_coach(
    question: str,
    answer: str,
    goals: list[Goal],
    areas: list[LifeArea],
    sessions: list[FocusSession],
    today_plan: object,
    logs: list[DailyLog],
    brain_profile: BrainProfile,
    brain_answers: list[object],
    search_memory: list[SearchMemoryItem],
) -> str:
    hf_config = hugging_face_config()
    ready = hf_config["ready"] == "true"
    status = "Connected" if ready else "Needs HF_TOKEN"
    status_class = "connected" if ready else "missing"
    suggestions = [
        "Plan my day using my active goals, life areas, and available time.",
        "What area of life am I neglecting based on my Kairos data?",
        "What trigger pattern should I watch this week?",
        "What does my Brain profile suggest I should simplify next?",
        "Turn my top goal into time blocks for tomorrow.",
    ]
    suggestion_buttons = "".join(
        f"<button name='question' value='{escape(item)}'>{escape(item)}</button>"
        for item in suggestions
    )
    return f"""
<header class="page-head"><div><p>Private guidance</p><h2>Coach</h2></div><a class="button" href="/">Plan today</a></header>
<section class="coach-hero panel">
  <div>
    <span class="coach-status {status_class}">{escape(status)}</span>
    <h3>Kairos data coach</h3>
    <p>This coach receives a compact summary of your Kairos data: goals, areas, today blocks, recent focus sessions, trigger patterns, and confirmed Brain memory.</p>
  </div>
  <div class="coach-model">
    <span>Model</span>
    <strong>{escape(hf_config["model"])}</strong>
    <small>{escape(hf_config["source"])}</small>
  </div>
</section>
<div class="grid two coach-grid">
  <section class="panel">
    <h3>Ask for guidance</h3>
    <form method="post" action="/coach" class="coach-form">
      <textarea name="question" rows="4" placeholder="Ask the coach to plan, review, or diagnose using only Kairos data.">{escape(question)}</textarea>
      <button class="primary">Ask coach</button>
    </form>
    <form method="post" action="/coach" class="coach-suggestions">{suggestion_buttons}</form>
  </section>
  <section class="panel">
    <h3>Coach response</h3>
    {coach_answer(answer, ready)}
  </section>
</div>
<section class="panel coach-context">
  <div class="panel-head"><div><h3>Data the coach can see</h3><p>No outside memory. No private data beyond this app summary.</p></div></div>
  {coach_context_cards(goals, areas, sessions, today_plan, logs, brain_answers, search_memory)}
</section>"""


def coach_answer(answer: str, ready: bool) -> str:
    if answer:
        return f"<div class='coach-answer'>{escape(answer).replace(chr(10), '<br>')}</div>"
    if not ready:
        return "<p class='muted'>Set HF_TOKEN in your shell, hosting environment, or local .env file. Restart Kairos after changing it.</p>"
    return "<p class='muted'>Ask a question or use one of the prompts. The answer will be generated from Kairos data only.</p>"


def hugging_face_config() -> dict[str, str]:
    token_name = next(
        (name for name in ["HF_TOKEN", "HUGGINGFACE_API_TOKEN", "HUGGINGFACE_HUB_TOKEN"] if os.environ.get(name)),
        "",
    )
    source = "Inference Providers enabled" if token_name else "Token not configured"
    return {
        "ready": "true" if token_name else "false",
        "token": os.environ.get(token_name, "") if token_name else "",
        "model": os.environ.get("HF_MODEL", DEFAULT_HF_MODEL),
        "source": source,
    }


def coach_context_cards(
    goals: list[Goal],
    areas: list[LifeArea],
    sessions: list[FocusSession],
    today_plan: object,
    logs: list[DailyLog],
    brain_answers: list[object],
    search_memory: list[SearchMemoryItem],
) -> str:
    blocks = getattr(today_plan, "blocks", [])
    active_goals = len([goal for goal in goals if goal.status == "active"])
    week_sessions = sessions_for_current_week(sessions)
    triggers = len([session for session in week_sessions if session.internal_trigger or session.external_trigger])
    planned_days = len(daily_logs_for_current_week(logs))
    items = [
        ("Active goals", active_goals),
        ("Today blocks", len(blocks)),
        ("Week sessions", len(week_sessions)),
        ("Trigger logs", triggers),
        ("Areas", len(areas)),
        ("Daily logs", planned_days),
        ("Brain answers", len(brain_answers)),
        ("Saved research", len(search_memory)),
    ]
    return "<div class='coach-context-grid'>" + "".join(metric(label, value, "") for label, value in items) + "</div>"


def run_hf_coach(
    question: str,
    goals: list[Goal],
    areas: list[LifeArea],
    sessions: list[FocusSession],
    today_plan: object,
    logs: list[DailyLog],
    brain_profile: BrainProfile,
    brain_answers: list[object],
    search_memory: list[SearchMemoryItem],
) -> str:
    if not question:
        return "Ask a specific question so I can help with planning, review, or distraction patterns."
    hf_config = hugging_face_config()
    if hf_config["ready"] != "true":
        return local_coach_answer(question, goals, areas, sessions, today_plan, logs, brain_profile, search_memory, "Hugging Face is not configured yet.")
    token = hf_config["token"]
    requested_model = hf_config["model"]
    models = [requested_model]
    for fallback in HF_MODEL_FALLBACKS:
        if fallback not in models:
            models.append(fallback)
    last_error = ""
    for model in models:
        answer, retryable_error = request_hf_chat_completion(token, model, question, goals, areas, sessions, today_plan, logs, brain_profile, brain_answers, search_memory)
        if answer:
            prefix = "" if model == requested_model else f"Used fallback model `{model}` because `{requested_model}` was unavailable.\n\n"
            return prefix + answer
        last_error = retryable_error
    reason = last_error or "Hugging Face could not return a response with any configured model."
    return local_coach_answer(question, goals, areas, sessions, today_plan, logs, brain_profile, search_memory, reason)


def local_coach_answer(
    question: str,
    goals: list[Goal],
    areas: list[LifeArea],
    sessions: list[FocusSession],
    today_plan: object,
    logs: list[DailyLog],
    brain_profile: BrainProfile,
    search_memory: list[SearchMemoryItem],
    provider_note: str,
) -> str:
    active_goals = [goal for goal in sorted_goals(goals) if goal.status == "active"]
    week_sessions = sessions_for_current_week(sessions)
    planned_today = len(getattr(today_plan, "items", []))
    focus_minutes = sum(session.duration_seconds for session in week_sessions if session.session_type == "pomodoro") // 60
    weakest_area = min(areas, key=lambda area: (area.current_score, area.name), default=None)
    no_task_goal = next((goal for goal in active_goals if not goal.tasks), None)
    next_goal = next((goal for goal in active_goals if goal.tasks), active_goals[0] if active_goals else None)
    trigger_counts = count_values(
        value
        for session in week_sessions
        for value in [session.internal_trigger, session.external_trigger, session.pact]
    )
    top_trigger = sorted(trigger_counts.items(), key=lambda item: (-item[1], item[0]))[0][0] if trigger_counts else ""
    lines = [
        "Local coach fallback:",
        f"1. Start with today's plan. You currently have {planned_today} commitment(s). Keep it to 1-3 and protect the first block.",
    ]
    if no_task_goal:
        lines.append(f"2. Fix goal clarity first: add one concrete next task to '{no_task_goal.title}'.")
    elif next_goal:
        lines.append(f"2. Use '{next_goal.title}' as the next execution target unless it conflicts with your North Star.")
    if weakest_area:
        lines.append(f"3. Watch life balance: '{weakest_area.name}' has the lowest score. Give it a small weekly target or consciously defer it.")
    if top_trigger:
        lines.append(f"4. Design around the repeated trigger '{top_trigger}'. Shrink the next task, change the environment, or create a pact before starting.")
    elif brain_profile.struggles:
        lines.append(f"4. Brain profile struggle to account for: {brain_profile.struggles.splitlines()[0].lstrip('- ')}")
    lines.append(f"5. This week has {format_minutes(focus_minutes)} recorded. Judge the task list by whether it increases real traction, not planning complexity.")
    if search_memory:
        lines.append(f"Recent research memory available: {search_memory[-1].query}. Link it to a goal only if it changes a decision.")
    lines.append(f"Provider note: {provider_note}")
    return "\n".join(lines)


def request_hf_chat_completion(
    token: str,
    model: str,
    question: str,
    goals: list[Goal],
    areas: list[LifeArea],
    sessions: list[FocusSession],
    today_plan: object,
    logs: list[DailyLog],
    brain_profile: BrainProfile,
    brain_answers: list[object],
    search_memory: list[SearchMemoryItem],
) -> tuple[str, str]:
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {
                "role": "system",
                "content": "You are Kairos Coach. Use only the provided Kairos data. Return final guidance only. Be concise, practical, and behavior-focused. Do not show analysis, hidden reasoning, or a data inventory. Do not invent facts.",
            },
            {
                "role": "user",
                "content": f"Kairos data:\n{kairos_summary(goals, areas, sessions, today_plan, logs, brain_profile, brain_answers, search_memory)}\n\nQuestion: {question}",
            },
        ],
        "max_tokens": 650,
        "temperature": 0.35,
        "reasoning_effort": "minimal",
    }
    request = Request(
        "https://router.huggingface.co/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=45) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="ignore")
        return "", hf_error_message(error.code, detail, model)
    except URLError as error:
        return "", f"Hugging Face request failed: {error.reason}"
    except TimeoutError:
        return "", "Hugging Face request timed out. Try again with a smaller question."
    try:
        return data["choices"][0]["message"]["content"].strip(), ""
    except (KeyError, IndexError, TypeError):
        return "", f"Unexpected Hugging Face response: {json.dumps(data)[:600]}"


def hf_error_message(status_code: int, detail: str, model: str) -> str:
    lower = detail.lower()
    if status_code in {401, 403}:
        return "Hugging Face rejected the request. Open models still require a token with Inference Providers permission. Create or update the token in Hugging Face Settings > Access Tokens, then restart Kairos."
    if status_code == 404 or "model" in lower and "not found" in lower:
        return f"Hugging Face could not use the configured model ({model}). Set HF_MODEL to a chat model available through Inference Providers."
    if status_code == 429:
        return "Hugging Face rate limited the request. Wait a bit or choose another provider/model policy."
    if status_code >= 500:
        return "Hugging Face is temporarily unavailable. Try again in a minute."
    return f"Hugging Face request failed ({status_code}). {detail[:240]}"


def kairos_summary(
    goals: list[Goal],
    areas: list[LifeArea],
    sessions: list[FocusSession],
    today_plan: object,
    logs: list[DailyLog],
    brain_profile: BrainProfile | None = None,
    brain_answers: list[object] | None = None,
    search_memory: list[SearchMemoryItem] | None = None,
) -> str:
    active_goals = [
        {
            "title": goal.title,
            "area": area_label(goal.category, areas),
            "priority": goal.priority,
            "target": goal.target_date,
            "open_tasks": [task.title for task in goal.tasks if task.status in {"todo", "in_progress", "blocked"}][:5],
        }
        for goal in sorted_goals(goals)
        if goal.status == "active"
    ][:8]
    blocks = [
        {
            "time": f"{block.start_time}-{block.end_time}",
            "type": block_label(block.kind),
            "signal": block_signal(block.kind),
            "title": block.title,
            "note": block.note,
        }
        for block in sorted(getattr(today_plan, "blocks", []), key=lambda item: item.start_time)
    ]
    week_sessions = sessions_for_current_week(sessions)
    trigger_counts = {
        "internal": count_values(session.internal_trigger for session in week_sessions),
        "external": count_values(session.external_trigger for session in week_sessions),
        "pacts": count_values(session.pact for session in week_sessions),
    }
    area_data = [
        {
            "name": area.name,
            "score": area.current_score,
            "weekly_target_minutes": area.weekly_target_minutes,
            "desired_state": area.desired_state,
        }
        for area in areas
    ]
    recent_logs = [
        {
            "date": log.log_date,
            "intention": log.intention,
            "must_win": log.must_win,
            "pact": log.pact,
            "shutdown": log.shutdown,
            "score": log.score,
        }
        for log in sorted(logs, key=lambda item: item.log_date, reverse=True)[:7]
    ]
    profile = brain_profile or BrainProfile()
    recent_answers = [
        {
            "section": getattr(answer, "section", ""),
            "construct": getattr(answer, "construct", ""),
            "prompt": getattr(answer, "prompt", ""),
            "answer": getattr(answer, "answer", ""),
            "created_at": getattr(answer, "created_at", ""),
        }
        for answer in sorted(brain_answers or [], key=lambda item: getattr(item, "created_at", ""), reverse=True)[:10]
    ]
    saved_research = [
        {
            "query": item.query,
            "title": item.title,
            "linked_to": item.linked_to,
            "note": item.note,
        }
        for item in sorted(search_memory or [], key=lambda entry: entry.created_at, reverse=True)[:8]
    ]
    return json.dumps(
        {
            "date": date.today().isoformat(),
            "active_goals": active_goals,
            "life_areas": area_data,
            "today_time_blocks": blocks,
            "week_focus_minutes": sum(session.duration_seconds for session in week_sessions) // 60,
            "week_trigger_counts": trigger_counts,
            "recent_daily_logs": recent_logs,
            "brain_profile": {
                "identity": profile.identity,
                "values": profile.values,
                "anti_vision": profile.anti_vision,
                "current_state": profile.current_state,
                "strengths": profile.strengths,
                "struggles": profile.struggles,
                "energy_patterns": profile.energy_patterns,
                "motivation_notes": profile.motivation_notes,
            },
            "recent_brain_answers": recent_answers,
            "saved_research": saved_research,
        },
        indent=2,
    )


def metric(label: str, value: int | str, tone: str = "") -> str:
    klass = f"metric {tone}".strip()
    return f"<article class='{klass}'><strong>{escape(str(value))}</strong><span>{escape(label)}</span></article>"


def daily_loop_panel(today_log: DailyLog, planned_items: list[dict[str, Goal | Task | None | str]], today_minutes: int) -> str:
    focus_href = f"/focus?target={escape(item_key(planned_items[0]))}" if planned_items else "#available-work"
    checks = [
        ("Intention", bool(today_log.intention.strip()), "#daily-intention", "Set"),
        ("Must-win", bool(today_log.must_win.strip()), "#daily-must-win", "Choose"),
        ("Daily pact", bool(today_log.pact.strip()), "#daily-pact", "Protect"),
        ("1-3 planned tasks", 0 < len(planned_items) <= 3, "#today-commitments", "Plan"),
        ("Focus block", today_minutes > 0, focus_href, "Start"),
        ("Shutdown", bool(today_log.shutdown.strip()), "#daily-shutdown", "Close"),
    ]
    rows = "".join(
        daily_loop_step(index + 1, label, done, href, action)
        for index, (label, done, href, action) in enumerate(checks)
    )
    return f"""
<section class="panel daily-loop-panel" id="daily-loop">
  <div class="panel-head">
    <div><h3>Daily loop</h3><p>Set the day, commit to the next block, then close the loop without making this a second task list.</p></div>
    <span class="loop-count">{sum(1 for _label, done, _href, _action in checks if done)}/{len(checks)}</span>
  </div>
  <div class="daily-loop-grid">
    <ol class="loop-steps">{rows}</ol>
    <form method="post" action="/daily-log" class="daily-loop-form">
      <div class="discipline-split">
        <section>
          <h4>Morning setup</h4>
          <label>Intention<input id="daily-intention" name="intention" value="{escape(today_log.intention)}" placeholder="How I will show up"></label>
          <label>Must win<input id="daily-must-win" name="must_win" value="{escape(today_log.must_win)}" placeholder="One result that matters"></label>
          <label>Daily pact<input id="daily-pact" name="pact" value="{escape(today_log.pact)}" placeholder="One rule that protects traction"></label>
        </section>
        <section>
          <h4>Shutdown</h4>
          <label>End-of-day review<textarea id="daily-shutdown" name="shutdown" rows="6" placeholder="What happened, what carries forward, and what changes tomorrow?">{escape(today_log.shutdown)}</textarea></label>
        </section>
      </div>
      <div class="discipline-actions"><button class="primary">Save daily loop</button></div>
    </form>
  </div>
</section>"""


def daily_loop_step(index: int, label: str, done: bool, href: str, action: str) -> str:
    return f"""
<li class="{'done' if done else ''}">
  <a href="{escape(href)}">
    <span>{index}</span>
    <div><strong>{escape(label)}</strong><small>{'Done' if done else action}</small></div>
  </a>
</li>"""


def plan_checklist(today_log: DailyLog, planned_items: list[dict[str, Goal | Task | None | str]], today_minutes: int) -> str:
    return daily_loop_panel(today_log, planned_items, today_minutes)


def today_queue(items: list[dict[str, Goal | Task | None | str]], default_minutes: int) -> str:
    if not items:
        return """
<div class="empty-action">
  <p class="muted">No plan yet. Auto-plan can choose up to three useful commitments from active work.</p>
  <form method="post" action="/today/auto-plan"><button class="primary">Auto-plan today</button></form>
  <a class="button" href="#available-work">Choose manually</a>
</div>"""
    return "<div class='list'>" + "".join(today_queue_item(item, default_minutes) for item in items) + "</div>"


def today_queue_item(item: dict[str, Goal | Task | None | str], default_minutes: int) -> str:
    goal_id, task_id = item_ids(item)
    task = item["task"]
    status_forms = ""
    if isinstance(task, Task):
        status_forms = "".join(
            f"""
<form method="post" action="/today/task-status">
  <input type="hidden" name="goal_id" value="{goal_id}">
  <input type="hidden" name="task_id" value="{task_id}">
  <button name="status" value="{status}" class="{'primary' if task.status == status else ''}">{label}</button>
</form>"""
            for status, label in [("in_progress", "Start"), ("done", "Done"), ("on_hold", "On hold"), ("blocked", "Blocked")]
        )
    return f"""
<article class="item actionable">
  <div>
    <h4>{escape(str(item['title']))}</h4>
    <p>{escape(str(item['meta']))}</p>
  </div>
  <div class="actions">
    {focus_link(item, "Focus")}
    {status_forms}
    <form method="post" action="/today/remove">
      <input type="hidden" name="goal_id" value="{goal_id}">
      <input type="hidden" name="task_id" value="{task_id}">
      <button>Remove</button>
    </form>
  </div>
</article>"""


def available_work_list(
    items: list[dict[str, Goal | Task | None | str]],
    planned_items: list[dict[str, Goal | Task | None | str]],
) -> str:
    if not items:
        return "<p class='muted'>No active work available.</p>"
    planned_keys = {item_key(item) for item in planned_items}
    return "<div class='list'>" + "".join(available_work_item(item, item_key(item) in planned_keys) for item in items) + "</div>"


def available_work_item(item: dict[str, Goal | Task | None | str], already_planned: bool) -> str:
    goal_id, task_id = item_ids(item)
    add_form = "<span class='pill'>Planned</span>" if already_planned else f"""
<form method="post" action="/today/add">
  <input type="hidden" name="goal_id" value="{goal_id}">
  <input type="hidden" name="task_id" value="{task_id}">
  <button>Add</button>
</form>"""
    return f"""
<article class="item actionable">
  <div>
    <h4>{escape(str(item['title']))}</h4>
    <p>{escape(str(item['meta']))}</p>
  </div>
  <div class="actions">{add_form}</div>
</article>"""


def work_list(items: list[dict[str, Goal | Task | None | str]], empty: str) -> str:
    if not items:
        return f"<p class='muted'>{escape(empty)}</p>"
    return "<div class='list'>" + "".join(work_item(item) for item in items) + "</div>"


def work_item(item: dict[str, Goal | Task | None | str]) -> str:
    return f"<article class='item'><h4>{escape(str(item['title']))}</h4><p>{escape(str(item['meta']))}</p></article>"


def target_links(
    items: list[dict[str, Goal | Task | None | str]],
    selected: dict[str, Goal | Task | None | str] | None = None,
) -> str:
    if not items:
        return "<p class='muted'>No active work available.</p>"
    selected_key = item_key(selected) if selected else ""
    rows = []
    for item in items:
        klass = "item link selected" if item_key(item) == selected_key else "item link"
        rows.append(f"<a class='{klass}' href='/focus?target={escape(item_key(item))}'><h4>{escape(str(item['title']))}</h4><p>{escape(str(item['meta']))}</p></a>")
    return "<div class='list'>" + "".join(rows) + "</div>"


def goal_row(goal: Goal, selected: bool) -> str:
    done = len([task for task in goal.tasks if task.status == "done"])
    total = len(goal.tasks)
    progress = int((done / total) * 100) if total else 0
    klass = "item link selected" if selected else "item link"
    return f"""
<a class="{klass} goal-row" href="/goals?selected={goal.id}">
  <div><h4>{escape(goal.title)}</h4><p>{escape(goal.priority)} | {escape(area_label(goal.category))} | {escape(target_badge(goal.target_date))}</p></div>
  <span>{done}/{total}</span>
  <div class="progress"><span style="width:{progress}%"></span></div>
</a>"""


def task_row(goal: Goal, task: Task) -> str:
    buttons = "".join(
        f"<button name='status' value='{status}' class='{'primary' if task.status == status else ''}'>{label}</button>"
        for status, label in TASK_STATUS_LABELS.items()
    )
    return f"""
<article class="item task-row {escape(task.status)}">
  <div>
    <h4>{escape(task.title)}</h4>
    <p>{escape(TASK_STATUS_LABELS.get(task.status, task.status))}</p>
  </div>
  <form method="post" action="/goals/{goal.id}/tasks/{task.id}/status" class="row">{buttons}</form>
</article>"""


def focus_form(item: dict[str, Goal | Task | None | str] | None, default_minutes: int, label: str) -> str:
    if item is None:
        return ""
    goal = item["goal"]
    task = item["task"]
    assert isinstance(goal, Goal)
    return f"""
<form method="post" action="/focus/complete" class="focus-complete">
  <input type="hidden" name="goal_id" value="{goal.id}">
  <input type="hidden" name="task_id" value="{task.id if isinstance(task, Task) else ''}">
  <label>Block commitment<input name="commitment" placeholder="What will be true when this block is done?"></label>
  <div class="indistractable-grid">
    <label>Internal trigger<select name="internal_trigger">
      <option value="">No internal trigger</option>
      <option value="Uncertainty">Uncertainty</option>
      <option value="Boredom">Boredom</option>
      <option value="Anxiety">Anxiety</option>
      <option value="Fatigue">Fatigue</option>
      <option value="Overwhelm">Overwhelm</option>
      <option value="Avoidance">Avoidance</option>
    </select></label>
    <label>External trigger<select name="external_trigger">
      <option value="">No external trigger</option>
      <option value="Phone">Phone</option>
      <option value="Notifications">Notifications</option>
      <option value="Messages">Messages</option>
      <option value="Open tabs">Open tabs</option>
      <option value="Noise">Noise</option>
      <option value="People">People</option>
    </select></label>
    <label>Focus pact<select name="pact">
      <option value="">No pact</option>
      <option value="Phone away">Phone away</option>
      <option value="No tab switching">No tab switching</option>
      <option value="Start for 5 minutes">Start for 5 minutes</option>
      <option value="Write the next question if blocked">Write the next question if blocked</option>
      <option value="One screen only">One screen only</option>
    </select></label>
  </div>
  <div class="row">
    <label class="minutes-field">Minutes<input id="focus-minutes" type="number" min="1" max="240" name="minutes" value="{default_minutes}"></label>
    <label>Outcome<select name="outcome">
      <option value="completed">Complete</option>
      <option value="partial">Partial</option>
      <option value="blocked">Blocked</option>
    </select></label>
  </div>
  <div class="row">
    <label>Friction<select name="friction">
      <option value="">No friction</option>
      <option value="Low energy">Low energy</option>
      <option value="Unclear task">Unclear task</option>
      <option value="Too big">Too big</option>
      <option value="Distraction">Distraction</option>
      <option value="Avoidance">Avoidance</option>
      <option value="Blocked dependency">Blocked dependency</option>
    </select></label>
    <label>Result note<input name="result_note" placeholder="What changed?"></label>
  </div>
  <div class="row">
    <label>Quality<select name="quality">{rating_options()}</select></label>
    <label>Mood<select name="mood">{rating_options()}</select></label>
    <label>Energy<select name="energy">{rating_options()}</select></label>
  </div>
  <button class="primary">{escape(label)}</button>
</form>"""


def focus_link(item: dict[str, Goal | Task | None | str] | None, label: str) -> str:
    if item is None:
        return ""
    return f"<a class='button primary' href='/focus?target={escape(item_key(item))}'>{escape(label)}</a>"


def priority_options(selected: str) -> str:
    return "".join(
        f"<option value='{priority}' {'selected' if priority == selected else ''}>{priority}</option>"
        for priority in PRIORITY_LEVELS
    )


def rating_options() -> str:
    return "<option value=''>-</option>" + "".join(
        f"<option value='{value}'>{value}</option>"
        for value in range(1, 6)
    )


def area_options(areas: list[LifeArea], selected: str) -> str:
    return "".join(
        f"<option value='{area.id}' {'selected' if area.id == selected else ''}>{escape(area.name)}</option>"
        for area in areas
    )


def escape(value: str) -> str:
    return (
        str(value).replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def quote_attr(value: str) -> str:
    return f"'{escape(value)}'"


CSS = """
:root {
  color-scheme: light;
  font-family: Inter, Arial, sans-serif;
  color: #111827;
  background: #f3f5f8;
  --ink: #111827;
  --muted: #64748b;
  --line: #dce3ee;
  --panel: #ffffff;
  --blue: #155eef;
  --blue-soft: #eef4ff;
  --green-soft: #edfdf5;
  --green: #047857;
}
* { box-sizing: border-box; }
body { margin: 0; display: grid; grid-template-columns: 248px 1fr; min-height: 100vh; background: #f3f5f8; }
aside { background: #0f172a; color: white; padding: 22px 18px; }
.brand { display: flex; gap: 12px; align-items: center; margin-bottom: 28px; }
.brand-mark { width: 38px; height: 38px; border-radius: 8px; display: grid; place-items: center; background: #2563eb; font-weight: 800; }
aside h1 { margin: 0; font-size: 21px; line-height: 1.1; }
aside p { margin: 4px 0 0; color: #aeb8c7; font-size: 12px; }
nav { display: grid; gap: 7px; }
nav a { color: #d1d5db; text-decoration: none; padding: 11px 12px; border-radius: 7px; font-weight: 650; }
nav a:hover, nav a.active { background: #1e293b; color: white; }
main { padding: 24px 30px 42px; max-width: 1320px; width: 100%; }
.page-head { display: flex; justify-content: space-between; align-items: start; gap: 18px; margin-bottom: 18px; }
header p { margin: 0 0 5px; color: var(--muted); font-size: 12px; font-weight: 800; text-transform: uppercase; }
header h2 { margin: 0; font-size: 34px; line-height: 1.1; letter-spacing: 0; }
.metrics { display: grid; grid-template-columns: repeat(4, minmax(130px, 1fr)); gap: 12px; margin-bottom: 16px; }
.metric, .panel, .hero, .timer { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04); }
.metric { padding: 15px; min-height: 82px; }
.metric strong { display: block; font-size: 26px; line-height: 1.05; color: #0f172a; }
.metric span, .muted, .item p, .panel-head p, .hero p, .timer p { color: var(--muted); font-size: 13px; }
.metric.primary { background: var(--blue); border-color: var(--blue); }
.metric.primary strong, .metric.primary span { color: white; }
.metric.strong { background: var(--green-soft); border-color: #bbf7d0; }
.metric.strong strong { color: var(--green); }
.checklist { margin-bottom: 16px; padding: 16px 18px; }
.checklist h3 { margin: 0 0 12px; }
.checklist ul { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 8px; list-style: none; margin: 0; padding: 0; }
.checklist li { border: 1px solid #e7edf5; border-radius: 8px; padding: 10px 11px; color: #334155; font-size: 13px; font-weight: 750; }
.checklist li span { display: block; color: #b45309; font-size: 11px; text-transform: uppercase; margin-bottom: 4px; }
.checklist li.done { background: var(--green-soft); border-color: #bbf7d0; }
.checklist li.done span { color: var(--green); }
.discipline { display: grid; grid-template-columns: minmax(210px, 0.8fr) minmax(0, 3fr); gap: 18px; margin-bottom: 16px; padding: 18px; }
.discipline h3 { margin: 0 0 8px; }
.discipline p { max-width: 31ch; }
.discipline-form { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)) auto; gap: 10px; align-items: end; }
.discipline-form label, .minutes-field { display: grid; gap: 6px; color: #334155; font-size: 12px; font-weight: 750; }
.now-panel { border: 1px solid #adc8ff; border-radius: 8px; padding: 22px 24px; display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: 18px; margin-bottom: 16px; background: #fff; box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04); }
.now-panel.primary { background: linear-gradient(180deg, #ffffff 0%, #f7fbff 100%); }
.now-panel.strong { border-color: #bbf7d0; background: #f5fdf8; }
.now-panel.attention { border-color: #fed7aa; background: #fffaf4; }
.now-panel span, .hero span, .timer span { color: #52637a; font-size: 11px; font-weight: 850; text-transform: uppercase; }
.now-panel h3 { margin: 8px 0; font-size: 28px; line-height: 1.1; }
.now-panel p { margin: 6px 0 0; color: var(--muted); }
.now-action form { margin: 0; }
.tutorial { background: #ffffff; border: 1px solid var(--line); border-radius: 8px; padding: 14px 18px; margin-bottom: 16px; box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04); }
.tutorial summary { cursor: pointer; font-weight: 850; color: #0f172a; }
.tutorial-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; margin-top: 14px; }
.tutorial article { border: 1px solid #e7edf5; border-radius: 8px; padding: 12px; background: #fbfdff; }
.tutorial span { width: 26px; height: 26px; border-radius: 999px; display: grid; place-items: center; background: var(--blue); color: white; font-weight: 850; font-size: 12px; }
.tutorial h4 { margin: 10px 0 5px; font-size: 14px; }
.tutorial p { margin: 0; color: var(--muted); font-size: 13px; line-height: 1.35; }
.hero { border-color: #adc8ff; padding: 22px 24px; display: flex; align-items: center; justify-content: space-between; gap: 18px; margin-bottom: 16px; background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%); }
.hero h3, .timer h3 { margin: 8px 0; font-size: 24px; line-height: 1.15; }
.grid.two { display: grid; grid-template-columns: minmax(0, 3fr) minmax(340px, 2fr); gap: 16px; align-items: start; }
.panel, .timer { padding: 18px; }
.panel h3, .timer h3 { margin-top: 0; }
.panel-head { display: flex; align-items: start; justify-content: space-between; gap: 12px; margin-bottom: 14px; }
.list { display: grid; gap: 9px; }
.item { display: block; background: #fff; border: 1px solid #e7edf5; border-radius: 8px; padding: 13px; text-decoration: none; color: inherit; }
.item.selected, .item:hover { border-color: #93b8ff; background: var(--blue-soft); }
.item h4 { margin: 0 0 6px; font-size: 14px; line-height: 1.25; }
.item p { margin: 0; line-height: 1.35; }
.item.actionable { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 12px; align-items: center; }
.actions { display: flex; flex-wrap: wrap; gap: 7px; justify-content: flex-end; }
.actions form { margin: 0; }
.actions button, .actions .button { min-height: 32px; padding: 7px 10px; font-size: 12px; }
.pill { display: inline-flex; align-items: center; min-height: 32px; padding: 6px 10px; border-radius: 999px; background: var(--green-soft); color: var(--green); font-weight: 800; font-size: 12px; }
.stack { display: grid; gap: 9px; margin-bottom: 20px; }
.row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
input, select, textarea { width: 100%; border: 1px solid #cbd5e1; border-radius: 6px; padding: 10px 11px; font: inherit; background: white; }
textarea { resize: vertical; }
input:focus, select:focus, textarea:focus { outline: 2px solid #bfdbfe; border-color: #60a5fa; }
.row input, .row select { width: auto; flex: 1 1 160px; }
button, .button { border: 1px solid #cbd5e1; background: white; color: #182230; border-radius: 7px; padding: 9px 14px; font-weight: 750; cursor: pointer; text-decoration: none; display: inline-flex; align-items: center; justify-content: center; min-height: 38px; }
button.primary, .button.primary { background: var(--blue); color: white; border-color: var(--blue); }
button:hover, .button:hover { filter: brightness(0.98); }
.focus-layout { display: grid; grid-template-columns: minmax(0, 1.3fr) minmax(320px, 0.9fr); gap: 16px; align-items: start; }
.timer { min-height: 560px; display: flex; flex-direction: column; justify-content: center; align-items: stretch; border-color: #c8d7f7; }
.clock-wrap { margin: 14px 0 16px; }
.clock { font-size: 76px; font-weight: 850; line-height: 1; color: #0f172a; }
.clock-wrap small { color: var(--muted); font-weight: 700; text-transform: uppercase; font-size: 11px; }
.focus-complete { display: grid; gap: 10px; margin-top: 14px; }
.focus-complete label { display: grid; gap: 6px; color: #334155; font-size: 12px; font-weight: 750; }
.indistractable-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
.target-panel { max-height: calc(100vh - 64px); overflow: auto; }
.north-grid { display: grid; grid-template-columns: minmax(0, 1.4fr) minmax(340px, 0.8fr); gap: 16px; align-items: start; }
.north-form { display: grid; gap: 12px; }
.north-form label, .area-card label { display: grid; gap: 6px; color: #334155; font-size: 12px; font-weight: 750; }
.priority-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
.area-row { display: flex; gap: 12px; align-items: center; border: 1px solid #e7edf5; border-radius: 8px; padding: 12px; }
.area-row h4 { margin: 0 0 4px; }
.area-row p { margin: 0; color: var(--muted); font-size: 13px; }
.score-dot { width: 42px; height: 42px; border-radius: 8px; display: grid; place-items: center; background: var(--blue-soft); color: var(--blue); font-weight: 850; }
.area-grid { display: grid; grid-template-columns: repeat(3, minmax(260px, 1fr)); gap: 16px; }
.area-card { display: grid; gap: 12px; }
.area-card.neglected { border-color: #fdba74; background: #fffaf4; }
.area-card.attention { border-color: #bfdbfe; }
.area-card.healthy { border-color: #bbf7d0; }
.area-head { display: flex; align-items: start; justify-content: space-between; gap: 12px; }
.area-head h3 { margin: 0; }
.area-head span { display: block; color: var(--muted); font-size: 11px; font-weight: 800; text-transform: uppercase; }
.area-head strong { font-size: 24px; color: var(--blue); }
.area-meta { display: flex; flex-wrap: wrap; gap: 8px; }
.area-meta span { border: 1px solid #e7edf5; border-radius: 999px; padding: 6px 9px; color: var(--muted); font-size: 12px; font-weight: 750; }
.progress { height: 8px; overflow: hidden; border-radius: 999px; background: #e7edf5; }
.progress span { display: block; height: 100%; background: var(--blue); border-radius: inherit; }
.recommendation { color: #334155; font-size: 13px; line-height: 1.35; }
.edit-details summary { cursor: pointer; color: var(--blue); font-weight: 800; }
.edit-details form { margin-top: 10px; }
.review-metrics { margin-top: 0; }
.review-list { margin-top: 16px; }
.review-lower { margin-top: 16px; }
.review-prompts { display: grid; gap: 10px; }
.review-prompts div { border: 1px solid #e7edf5; border-radius: 8px; padding: 12px; }
.review-prompts span { display: block; color: var(--blue); font-size: 11px; font-weight: 850; text-transform: uppercase; margin-bottom: 4px; }
.review-prompts p, .session-note { margin: 0; color: var(--muted); font-size: 13px; }
.area-review { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 12px; align-items: start; }
.area-review span { border-radius: 999px; padding: 5px 8px; background: var(--blue-soft); color: var(--blue); font-size: 11px; font-weight: 850; }
.area-review.healthy span { background: var(--green-soft); color: var(--green); }
.area-review.neglected span { background: #fff7ed; color: #c2410c; }
.trigger-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: 12px; }
.trigger-row strong { color: var(--blue); font-size: 22px; }
.traction-summary { display: grid; grid-template-columns: auto 1fr; gap: 8px 12px; align-items: baseline; }
.traction-summary strong { color: #0f172a; font-size: 24px; }
.traction-summary span { color: var(--muted); font-size: 13px; }
.planner { margin-bottom: 16px; }
.planner-bounds { display: flex; flex-wrap: wrap; gap: 10px; align-items: end; margin-bottom: 14px; }
.planner-bounds label, .block-form label { display: grid; gap: 6px; color: #334155; font-size: 12px; font-weight: 750; }
.planner-bounds input { width: 150px; }
.planner-grid { display: grid; grid-template-columns: minmax(0, 1.6fr) minmax(300px, 0.9fr); gap: 16px; align-items: start; }
.timeline { display: grid; gap: 8px; }
.timeline-empty { border: 1px dashed #cbd5e1; border-radius: 8px; padding: 18px; background: #fbfdff; }
.timeline-empty p { margin: 6px 0 0; color: var(--muted); }
.time-block { display: grid; grid-template-columns: 88px minmax(0, 1fr) auto; gap: 12px; align-items: center; border: 1px solid #e7edf5; border-left: 5px solid var(--blue); border-radius: 8px; padding: 12px; background: #fff; }
.time-block.break { border-left-color: #16a34a; }
.time-block.admin { border-left-color: #7c3aed; }
.time-block.personal { border-left-color: #f59e0b; }
.time-block.buffer { border-left-color: #64748b; }
.time-range strong, .time-range span { display: block; }
.time-range strong { font-size: 16px; }
.time-range span { color: var(--muted); font-size: 12px; margin-top: 2px; }
.time-block h4 { margin: 0 0 5px; font-size: 14px; }
.time-block p { margin: 0; color: var(--muted); font-size: 13px; }
.block-form { display: grid; gap: 10px; border: 1px solid #e7edf5; border-radius: 8px; padding: 14px; background: #fbfdff; }
.block-form h4 { margin: 0; }
.compact { margin-bottom: 0; }
.unlock-body { display: grid; grid-template-columns: 1fr; place-items: center; padding: 24px; }
.unlock-card { width: min(420px, 100%); background: white; border: 1px solid var(--line); border-radius: 8px; padding: 24px; }
@media (max-width: 1020px) {
  .metrics { grid-template-columns: repeat(2, minmax(120px, 1fr)); }
  .area-grid { grid-template-columns: repeat(2, minmax(260px, 1fr)); }
  .discipline, .discipline-form, .indistractable-grid { grid-template-columns: 1fr; }
}
@media (max-width: 860px) {
  body { grid-template-columns: 1fr; }
  aside { position: static; padding: 18px; }
  .brand { margin-bottom: 16px; }
  nav { grid-template-columns: repeat(4, minmax(0, 1fr)); }
  nav a { text-align: center; padding: 10px 6px; }
  main { padding: 22px 18px 34px; }
  .page-head { align-items: stretch; flex-direction: column; }
  .metrics, .grid.two, .north-grid, .area-grid, .priority-grid, .focus-layout, .now-panel, .tutorial-grid, .planner-grid { grid-template-columns: 1fr; }
  .checklist ul { grid-template-columns: 1fr; }
  .item.actionable { grid-template-columns: 1fr; }
  .actions { justify-content: flex-start; }
  .hero { align-items: stretch; flex-direction: column; }
  .clock { font-size: 62px; }
  .timer { min-height: 0; }
  .target-panel { max-height: none; }
  .time-block { grid-template-columns: 1fr; }
  .planner-bounds input { width: 100%; }
}

/* Professional redesign pass */
:root {
  --ink: #101828;
  --muted: #667085;
  --subtle: #98a2b3;
  --line: #d8dee8;
  --line-soft: #e8edf4;
  --panel: #ffffff;
  --canvas: #f6f8fb;
  --blue: #175cd3;
  --blue-strong: #1849a9;
  --blue-soft: #eff6ff;
  --green: #067647;
  --green-soft: #ecfdf3;
  --amber: #b54708;
  --amber-soft: #fffaeb;
  --red: #b42318;
  --shadow: 0 1px 2px rgba(16, 24, 40, 0.06), 0 10px 24px rgba(16, 24, 40, 0.04);
}

body {
  grid-template-columns: 236px 1fr;
  background: var(--canvas);
  color: var(--ink);
}

aside {
  position: sticky;
  top: 0;
  height: 100vh;
  background: #111827;
  border-right: 1px solid rgba(255, 255, 255, 0.06);
  padding: 24px 18px;
}

.brand {
  padding: 0 4px 18px;
  margin-bottom: 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.brand-mark {
  background: #2563eb;
  box-shadow: inset 0 -10px 18px rgba(0, 0, 0, 0.16);
}

nav {
  gap: 4px;
}

nav a {
  border-radius: 6px;
  color: #cbd5e1;
  font-size: 14px;
  padding: 11px 12px;
}

nav a:hover,
nav a.active {
  background: rgba(255, 255, 255, 0.09);
}

main {
  max-width: 1260px;
  padding: 28px 32px 52px;
}

.page-head {
  margin-bottom: 20px;
}

header p {
  color: #667085;
  font-size: 11px;
  letter-spacing: 0.05em;
}

header h2 {
  font-size: 32px;
  font-weight: 850;
}

.panel,
.metric,
.timer,
.hero,
.now-panel,
.tutorial {
  border-color: var(--line);
  border-radius: 10px;
  box-shadow: var(--shadow);
}

.panel,
.timer {
  padding: 20px;
}

.panel h3,
.timer h3 {
  font-size: 18px;
  line-height: 1.2;
}

.panel-head {
  margin-bottom: 16px;
}

.panel-head p,
.muted,
.item p,
.timer p {
  color: var(--muted);
}

.metrics {
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.metric {
  min-height: 76px;
  padding: 14px 16px;
}

.metric strong {
  font-size: 24px;
  font-weight: 850;
}

.metric span {
  color: #475467;
}

.metric.primary {
  background: #155eef;
  border-color: #155eef;
}

.metric.strong {
  background: var(--green-soft);
  border-color: #abefc6;
}

.now-panel {
  background: #ffffff;
  border-left: 5px solid #f79009;
  padding: 22px 24px;
}

.now-panel.primary {
  border-left-color: var(--blue);
}

.now-panel.strong {
  border-left-color: var(--green);
}

.now-panel h3 {
  font-size: 26px;
  max-width: 760px;
}

.now-panel span,
.timer span {
  color: #344054;
  letter-spacing: 0.05em;
}

.tutorial {
  padding: 12px 16px;
}

.tutorial[open] {
  padding-bottom: 16px;
}

.tutorial summary {
  list-style-position: outside;
}

.tutorial article,
.item,
.area-row,
.review-prompts div,
.timeline-empty,
.block-form {
  border-color: var(--line-soft);
  background: #ffffff;
}

.tutorial article {
  background: #f9fafb;
}

.checklist {
  padding: 18px;
}

.checklist ul {
  gap: 10px;
}

.checklist li {
  background: #f9fafb;
  border-color: var(--line-soft);
  border-radius: 8px;
  min-height: 60px;
}

.checklist li span {
  color: var(--amber);
}

.checklist li.done {
  background: var(--green-soft);
}

.planner {
  padding: 20px;
}

.planner-grid {
  grid-template-columns: minmax(0, 1.4fr) minmax(320px, 0.75fr);
}

.planner-bounds {
  padding: 10px 0 16px;
  border-bottom: 1px solid var(--line-soft);
}

.timeline-empty {
  min-height: 116px;
  display: grid;
  align-content: center;
  border-style: dashed;
  background: #f8fafc;
}

.time-block {
  border-radius: 10px;
  border-color: var(--line-soft);
  border-left-width: 6px;
}

.time-block.traction {
  border-left-color: #12b76a;
  background: linear-gradient(90deg, rgba(236, 253, 243, 0.72), #ffffff 32%);
}

.time-block.distraction {
  border-left-color: #f04438;
  background: linear-gradient(90deg, rgba(254, 243, 242, 0.78), #ffffff 32%);
}

.time-block.maintenance {
  border-left-color: #f79009;
  background: linear-gradient(90deg, rgba(255, 250, 235, 0.82), #ffffff 32%);
}

.time-block.support {
  border-left-color: #2e90fa;
  background: linear-gradient(90deg, rgba(239, 248, 255, 0.86), #ffffff 32%);
}

.signal-dot {
  width: 9px;
  height: 9px;
  display: inline-block;
  border-radius: 999px;
  margin-right: 7px;
}

.signal-dot.traction { background: #12b76a; }
.signal-dot.distraction { background: #f04438; }
.signal-dot.maintenance { background: #f79009; }
.signal-dot.support { background: #2e90fa; }

.coach-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(240px, auto);
  gap: 18px;
  align-items: center;
  margin-bottom: 16px;
}

.coach-hero h3 {
  margin: 8px 0;
  font-size: 26px;
}

.coach-status {
  display: inline-flex;
  border-radius: 999px;
  padding: 5px 9px;
  font-size: 11px;
  font-weight: 850;
  text-transform: uppercase;
}

.coach-status.connected {
  background: var(--green-soft);
  color: var(--green);
}

.coach-status.missing {
  background: var(--amber-soft);
  color: var(--amber);
}

.coach-model {
  border: 1px solid var(--line-soft);
  border-radius: 10px;
  padding: 14px;
  background: #f8fafc;
}

.coach-model span {
  display: block;
  color: var(--muted);
  font-size: 11px;
  font-weight: 850;
  text-transform: uppercase;
  margin-bottom: 5px;
}

.coach-model strong {
  display: block;
  max-width: 320px;
  overflow-wrap: anywhere;
}

.coach-model small {
  display: block;
  margin-top: 6px;
  color: var(--muted);
  font-size: 12px;
  font-weight: 750;
}

.coach-form {
  display: grid;
  gap: 10px;
}

.coach-suggestions {
  display: grid;
  gap: 8px;
  margin-top: 14px;
}

.coach-suggestions button {
  justify-content: flex-start;
  min-height: 38px;
  text-align: left;
}

.coach-answer {
  border: 1px solid var(--line-soft);
  border-radius: 10px;
  padding: 14px;
  background: #f8fafc;
  color: #1d2939;
  line-height: 1.55;
}

.coach-context {
  margin-top: 16px;
}

.coach-context-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 10px;
}

.block-form {
  background: #f8fafc;
  padding: 16px;
}

.discipline {
  grid-template-columns: minmax(180px, 0.7fr) minmax(0, 3fr);
  align-items: center;
}

.discipline-form {
  grid-template-columns: repeat(4, minmax(130px, 1fr)) auto;
}

.grid.two {
  grid-template-columns: minmax(0, 1.35fr) minmax(360px, 0.9fr);
}

.item {
  border-radius: 10px;
  padding: 14px;
}

.item:hover,
.item.selected {
  background: #f0f6ff;
  border-color: #84adff;
}

.item h4 {
  font-size: 14px;
  font-weight: 800;
}

.actions {
  gap: 6px;
}

input,
select,
textarea {
  border-color: #cfd8e3;
  border-radius: 8px;
  min-height: 40px;
}

input:focus,
select:focus,
textarea:focus {
  outline: 3px solid #d1e9ff;
  border-color: #2e90fa;
}

button,
.button {
  border-radius: 8px;
  min-height: 40px;
  font-weight: 800;
}

button.primary,
.button.primary {
  background: var(--blue);
  border-color: var(--blue);
}

button.primary:hover,
.button.primary:hover {
  background: var(--blue-strong);
}

.focus-layout {
  grid-template-columns: minmax(0, 1.35fr) minmax(360px, 0.85fr);
}

.timer {
  min-height: 0;
  padding: 24px;
}

.clock {
  font-size: 84px;
  letter-spacing: 0;
}

.focus-complete {
  padding-top: 12px;
  border-top: 1px solid var(--line-soft);
}

.target-panel {
  max-height: calc(100vh - 92px);
}

.area-grid {
  grid-template-columns: repeat(3, minmax(280px, 1fr));
}

.area-card {
  min-height: 270px;
}

.area-card.attention,
.area-card.healthy,
.area-card.neglected {
  background: #ffffff;
}

.area-card.neglected {
  border-left: 5px solid #f79009;
}

.area-head strong {
  color: var(--blue);
}

.area-meta span,
.pill,
.area-review span {
  border-radius: 999px;
}

.progress {
  background: #eef2f6;
}

.review-lower {
  margin-top: 16px;
}

.review-prompts div {
  background: #f9fafb;
}

.traction-summary {
  align-content: start;
}

@media (max-width: 1020px) {
  body {
    grid-template-columns: 1fr;
  }

  aside {
    position: static;
    height: auto;
  }
}

@media (max-width: 860px) {
  main {
    padding: 20px 18px 36px;
  }

  aside {
    padding: 18px;
  }

  .brand {
    border-bottom: 0;
    padding-bottom: 0;
  }

  nav {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
  }

  nav a {
    background: rgba(255, 255, 255, 0.04);
    min-height: 44px;
    display: grid;
    place-items: center;
  }

  header h2 {
    font-size: 30px;
  }

  .now-panel,
  .panel,
  .timer,
  .tutorial,
  .metric {
    border-radius: 10px;
  }

  .metrics {
    grid-template-columns: 1fr 1fr;
  }

  .checklist ul,
  .discipline,
  .discipline-form,
  .planner-grid,
  .grid.two,
  .focus-layout,
  .coach-hero,
  .coach-context-grid,
  .north-grid,
  .area-grid,
  .priority-grid,
  .indistractable-grid,
  .tutorial-grid {
    grid-template-columns: 1fr;
  }

  .discipline {
    align-items: stretch;
  }

  .clock {
    font-size: 64px;
  }

  .target-panel {
    max-height: none;
  }
}

/* Rich product redesign */
:root {
  --canvas: #eef3f8;
  --surface: rgba(255, 255, 255, 0.92);
  --surface-strong: #ffffff;
  --ink: #0b1220;
  --muted: #5b6b82;
  --faint: #eef2f7;
  --nav: #09111f;
  --nav-2: #121d2f;
  --blue: #2563eb;
  --blue-strong: #1d4ed8;
  --cyan: #0891b2;
  --green: #059669;
  --green-soft: #e8fff3;
  --red: #dc2626;
  --red-soft: #fff1f2;
  --amber: #d97706;
  --amber-soft: #fff7e6;
  --violet: #7c3aed;
  --shadow: 0 20px 55px rgba(15, 23, 42, 0.08), 0 2px 8px rgba(15, 23, 42, 0.05);
  --shadow-soft: 0 10px 30px rgba(15, 23, 42, 0.06);
}

html {
  background: var(--canvas);
}

body {
  font-family: Inter, "Segoe UI", ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
  background:
    linear-gradient(180deg, #f8fafc 0, #eef3f8 340px, #eef3f8 100%);
  color: var(--ink);
}

aside {
  background:
    linear-gradient(180deg, rgba(37, 99, 235, 0.16), rgba(37, 99, 235, 0) 180px),
    linear-gradient(180deg, var(--nav), var(--nav-2));
  box-shadow: 12px 0 40px rgba(15, 23, 42, 0.13);
  z-index: 2;
}

.brand {
  gap: 14px;
  margin-bottom: 20px;
}

.brand-mark {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  background: linear-gradient(145deg, #3b82f6, #1d4ed8);
}

aside h1 {
  font-size: 22px;
}

aside p {
  max-width: 130px;
  line-height: 1.25;
}

nav a {
  display: grid;
  grid-template-columns: 12px 1fr;
  align-items: center;
  gap: 10px;
  color: #d7e3f4;
  border: 1px solid transparent;
}

.nav-dot {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.54);
}

nav a.active {
  background: rgba(255, 255, 255, 0.12);
  border-color: rgba(255, 255, 255, 0.08);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

nav a.active .nav-dot {
  background: #60a5fa;
  box-shadow: 0 0 0 4px rgba(96, 165, 250, 0.16);
}

main {
  max-width: none;
  padding: 0;
}

.workspace {
  width: min(1180px, calc(100vw - 236px));
  margin: 0 auto;
  padding: 28px 32px 60px;
}

.page-head {
  align-items: center;
  margin-bottom: 18px;
}

header h2 {
  font-size: 36px;
  letter-spacing: -0.01em;
}

header p {
  color: #64748b;
  font-weight: 900;
}

.button,
button {
  transition: transform 140ms ease, box-shadow 140ms ease, background 140ms ease;
}

.button:hover,
button:hover {
  transform: translateY(-1px);
}

button.primary,
.button.primary {
  background: linear-gradient(180deg, #2563eb, #1d4ed8);
  box-shadow: 0 10px 18px rgba(37, 99, 235, 0.22);
}

.panel,
.timer,
.metric,
.tutorial,
.now-panel {
  background: var(--surface);
  border: 1px solid rgba(203, 213, 225, 0.82);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
  backdrop-filter: blur(10px);
}

.now-panel {
  position: relative;
  overflow: hidden;
  min-height: 132px;
  color: white;
  background:
    linear-gradient(135deg, rgba(15, 23, 42, 0.98), rgba(30, 64, 175, 0.9)),
    #0f172a;
  border: 0;
  box-shadow: var(--shadow);
}

.now-panel.attention,
.now-panel.primary,
.now-panel.strong {
  background:
    linear-gradient(135deg, rgba(15, 23, 42, 0.97), rgba(30, 64, 175, 0.92)),
    #0f172a;
  border: 0;
}

.now-panel.attention {
  box-shadow: var(--shadow), inset 5px 0 0 #f59e0b;
}

.now-panel.primary {
  box-shadow: var(--shadow), inset 5px 0 0 #3b82f6;
}

.now-panel.strong {
  box-shadow: var(--shadow), inset 5px 0 0 #10b981;
}

.now-panel::before {
  content: none;
}

.now-panel > * {
  position: relative;
}

.now-panel span,
.now-panel p,
.now-panel strong {
  color: rgba(255, 255, 255, 0.74);
}

.now-panel h3 {
  color: white;
  font-size: 28px;
}

.now-panel .button,
.now-panel button {
  border: 0;
  background: #ffffff;
  color: #0f172a;
  box-shadow: 0 16px 26px rgba(0, 0, 0, 0.2);
}

.metrics {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin-bottom: 18px;
}

.metric {
  position: relative;
  overflow: hidden;
  min-height: 82px;
}

.metric::after {
  content: "";
  position: absolute;
  right: 14px;
  top: 14px;
  width: 34px;
  height: 34px;
  border-radius: 12px;
  background: var(--faint);
}

.metric.primary {
  color: white;
  background: linear-gradient(145deg, #2563eb, #0f3fbd);
  border: 0;
}

.metric.primary::after {
  background: rgba(255, 255, 255, 0.18);
}

.metric.strong {
  background: linear-gradient(145deg, #ecfdf3, #ffffff);
}

.checklist {
  background: #ffffff;
}

.checklist ul {
  grid-template-columns: repeat(6, minmax(0, 1fr));
}

.checklist li {
  position: relative;
  overflow: hidden;
}

.checklist li::before {
  content: "";
  position: absolute;
  inset: 0 auto 0 0;
  width: 4px;
  background: var(--amber);
}

.checklist li.done::before {
  background: var(--green);
}

.planner {
  background:
    linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
  box-shadow: 0 12px 36px rgba(15, 23, 42, 0.07);
}

.planner .panel-head {
  padding-bottom: 12px;
  border-bottom: 1px solid var(--faint);
}

.template-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.template-strip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin: 0 0 16px;
  padding: 12px 14px;
  border: 1px solid #dbeafe;
  border-radius: 8px;
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.06), rgba(5, 150, 105, 0.04));
}

.template-strip div {
  display: grid;
  gap: 3px;
}

.template-strip span {
  color: var(--muted);
  font-size: 12px;
  font-weight: 750;
}

.signal-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 0 0 14px;
}

.signal-legend span {
  display: inline-flex;
  align-items: center;
  border: 1px solid var(--faint);
  border-radius: 999px;
  padding: 7px 10px;
  background: #fff;
  color: var(--muted);
  font-size: 12px;
  font-weight: 800;
}

.planner-grid {
  grid-template-columns: minmax(0, 1.55fr) minmax(340px, 0.8fr);
}

.timeline-empty {
  min-height: 180px;
  border: 1px dashed #b8c4d6;
  background:
    linear-gradient(135deg, rgba(37, 99, 235, 0.04), rgba(8, 145, 178, 0.04)),
    #fbfdff;
}

.block-form {
  background: #f8fafc;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.74);
}

.discipline {
  background:
    linear-gradient(135deg, rgba(37, 99, 235, 0.05), transparent 38%),
    #ffffff;
}

.grid.two {
  align-items: start;
}

.item {
  background: #ffffff;
  box-shadow: 0 1px 0 rgba(15, 23, 42, 0.02);
}

.item.actionable {
  border-left: 4px solid #dbeafe;
}

.available-work .item,
#available-work .item {
  background: #fcfdff;
}

.focus-layout {
  align-items: stretch;
}

.timer {
  position: relative;
  overflow: hidden;
  background:
    linear-gradient(145deg, #ffffff 0%, #f8fbff 100%);
  box-shadow: var(--shadow);
}

.timer::before {
  content: "";
  position: absolute;
  inset: 0 0 auto;
  height: 6px;
  background: linear-gradient(90deg, var(--green), var(--blue), var(--amber));
}

.clock {
  font-size: 88px;
  letter-spacing: -0.02em;
}

.target-panel {
  background: #ffffff;
}

.area-card {
  position: relative;
  overflow: hidden;
  box-shadow: var(--shadow-soft);
}

.area-card::before {
  content: "";
  position: absolute;
  inset: 0 0 auto;
  height: 5px;
  background: linear-gradient(90deg, var(--blue), var(--cyan));
}

.area-card.neglected::before {
  background: var(--amber);
}

.area-card.healthy::before {
  background: var(--green);
}

.review-metrics .metric:nth-child(2) {
  background: linear-gradient(145deg, var(--green-soft), #ffffff);
}

.coach-hero {
  background:
    linear-gradient(135deg, rgba(37, 99, 235, 0.07), rgba(5, 150, 105, 0.05)),
    #ffffff;
  box-shadow: var(--shadow);
}

.coach-status.connected,
.coach-status.missing {
  letter-spacing: 0.04em;
}

.coach-grid .panel:first-child {
  background:
    linear-gradient(180deg, #ffffff, #fbfdff);
}

.coach-suggestions button {
  background: #f8fafc;
}

.coach-suggestions button:hover {
  background: #eef6ff;
}

.coach-answer {
  min-height: 160px;
  background:
    linear-gradient(180deg, #f8fafc, #ffffff);
}

@media (max-width: 1020px) {
  .workspace {
    width: 100%;
  }
}

@media (max-width: 860px) {
  body {
    background: #eef3f8;
  }

  .workspace {
    padding: 20px 18px 40px;
  }

  nav {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  nav a {
    grid-template-columns: 1fr;
    gap: 0;
  }

  .nav-dot {
    display: none;
  }

  .now-panel {
    min-height: 0;
    padding: 24px;
  }

  .now-panel h3 {
    font-size: 27px;
  }

  .timeline-empty {
    min-height: 120px;
  }

  .planner-grid {
    grid-template-columns: 1fr;
  }

  .template-actions,
  .template-strip {
    align-items: stretch;
    flex-direction: column;
  }

  .block-form {
    margin-top: 10px;
  }

  .metrics {
    grid-template-columns: 1fr;
  }

  .checklist ul {
    grid-template-columns: 1fr;
  }

  .clock {
    font-size: 66px;
  }
}

.question-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 16px;
}

.question-card {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 16px;
  background: #fff;
  display: grid;
  gap: 10px;
  align-content: start;
}

.question-card span {
  color: var(--muted);
  font-size: 0.78rem;
  font-weight: 700;
  text-transform: uppercase;
}

.question-card h4 {
  margin: 0;
  line-height: 1.35;
}

.question-card form {
  display: grid;
  gap: 8px;
}

.question-card button {
  justify-self: start;
}

.research-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(340px, 0.9fr);
  gap: 18px;
  align-items: start;
}

.research-main,
.research-side {
  min-width: 0;
}

.research-side {
  display: grid;
  gap: 18px;
  position: sticky;
  top: 24px;
}

.research-search {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
  margin-bottom: 18px;
}

.research-results {
  display: grid;
  gap: 14px;
}

.research-result {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
  padding: 16px;
  display: grid;
  gap: 12px;
}

.research-result h4 {
  margin: 0 0 6px;
  line-height: 1.35;
}

.result-url {
  color: #475569;
  display: block;
  font-size: 0.9rem;
  margin-bottom: 8px;
  overflow-wrap: anywhere;
  text-decoration: none;
}

.research-result .actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.quick-save {
  border-top: 1px solid var(--line);
  padding-top: 10px;
}

.quick-save summary,
.manual-save summary {
  cursor: pointer;
  font-weight: 800;
}

.manual-save summary {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
}

.manual-save summary h3 {
  margin: 0;
}

.manual-save summary span {
  color: var(--muted);
  font-size: 0.85rem;
  font-weight: 500;
}

.manual-save form {
  margin-top: 14px;
}

.saved-memory .item h4 {
  overflow-wrap: anywhere;
}

.reader-panel {
  margin-bottom: 18px;
}

.reader-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(320px, 0.75fr);
  gap: 16px;
  align-items: start;
}

.reader-content {
  max-height: 520px;
  overflow: auto;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 18px;
  background: #f8fafc;
}

.reader-content p {
  margin: 0 0 12px;
  line-height: 1.6;
  color: #243044;
}

.reader-save {
  display: grid;
  gap: 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 14px;
  background: #fff;
}

.reader-save h4 {
  margin: 0;
}

.reader-notice {
  border: 1px solid #fde68a;
  background: #fffbeb;
  border-radius: 8px;
  padding: 10px 12px;
}

@media (max-width: 780px) {
  .research-layout,
  .reader-grid {
    grid-template-columns: 1fr;
  }

  .research-side {
    position: static;
  }

  .research-search {
    grid-template-columns: 1fr;
  }

  .reader-save {
    grid-template-columns: 1fr;
  }
}
"""


JS = """
const clock = document.querySelector('.clock');
if (clock) {
  const total = Number(clock.dataset.minutes || '25') * 60;
  let remaining = total;
  let elapsed = 0;
  let timer = null;
  const minutesInput = document.querySelector('#focus-minutes');
  const render = () => {
    const minutes = Math.floor(remaining / 60).toString().padStart(2, '0');
    const seconds = (remaining % 60).toString().padStart(2, '0');
    clock.textContent = `${minutes}:${seconds}`;
    if (minutesInput) minutesInput.value = elapsed > 0 ? Math.max(1, Math.ceil(elapsed / 60)) : Math.floor(total / 60);
  };
  const tick = () => {
    if (remaining > 0) {
      remaining -= 1;
      elapsed += 1;
      render();
      return;
    }
    clearInterval(timer);
    timer = null;
  };
  document.querySelector('#timer-start')?.addEventListener('click', () => {
    if (!timer) timer = setInterval(tick, 1000);
  });
  document.querySelector('#timer-pause')?.addEventListener('click', () => {
    clearInterval(timer);
    timer = null;
  });
  document.querySelector('#timer-reset')?.addEventListener('click', () => {
    clearInterval(timer);
    timer = null;
    remaining = total;
    elapsed = 0;
    render();
  });
  render();
}
document.querySelectorAll('[data-confirm]').forEach((button) => {
  button.addEventListener('click', (event) => {
    if (!confirm(button.dataset.confirm || 'Continue?')) event.preventDefault();
  });
});
"""
