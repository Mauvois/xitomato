import json
import math
import os
from datetime import datetime, date as date_type, time as time_type, timedelta
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from .db import Base, SessionLocal, engine
from .models import (
    DailyState,
    PauseCard,
    PauseCardUse,
    Session as SessionModel,
    Settings,
    Task,
)
from .schemas import (
    DailyStateResponse,
    PauseCardCreate,
    PauseCardResponse,
    PauseCardUpdate,
    PauseConsume,
    SessionAdjust,
    SessionPlan,
    SessionResponse,
    SessionStart,
    SessionUpdate,
    SettingsResponse,
    SettingsUpdate,
    TaskCreate,
    TaskResponse,
    TaskUpdate,
)
from .utils import build_datetime, resolve_daypart_name

Base.metadata.create_all(bind=engine)


def ensure_schema():
    with engine.connect() as conn:
        result = conn.exec_driver_sql("PRAGMA table_info(sessions);")
        columns = {row[1] for row in result}
        if "title" not in columns:
            conn.exec_driver_sql("ALTER TABLE sessions ADD COLUMN title VARCHAR;")


ensure_schema()

app = FastAPI(title="Tomate API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def default_dayparts():
    return [
        {"name": "Matin", "start": "09:00", "end": "12:00"},
        {"name": "Apres-midi", "start": "13:00", "end": "17:00"},
        {"name": "Soir", "start": "21:30", "end": "00:00"},
    ]


def settings_to_response(settings: Settings, needs_setup: bool) -> SettingsResponse:
    return SettingsResponse(
        dayparts=json.loads(settings.dayparts_json),
        default_focus_minutes=settings.default_focus_minutes,
        default_break_minutes=settings.default_break_minutes,
        notifications_enabled=settings.notifications_enabled,
        sound_enabled=settings.sound_enabled,
        needs_setup=needs_setup,
    )


def get_or_create_settings(db: Session) -> tuple[Settings, bool]:
    settings = db.query(Settings).first()
    if settings:
        return settings, False
    settings = Settings(
        dayparts_json=json.dumps(default_dayparts()),
        default_focus_minutes=45,
        default_break_minutes=5,
        notifications_enabled=True,
        sound_enabled=True,
    )
    db.add(settings)
    db.commit()
    db.refresh(settings)
    seed_pause_cards(db)
    return settings, True


def current_time() -> datetime:
    return datetime.now()


def parse_client_now(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo:
            return parsed.replace(tzinfo=None)
        return parsed
    except ValueError:
        return None


def seed_pause_cards(db: Session) -> None:
    existing = db.query(PauseCard).count()
    if existing > 0:
        return
    cards = [
        PauseCard(name="Cafe", daily_quota=2, is_joker=False),
        PauseCard(name="Toilettes", daily_quota=2, is_joker=False),
        PauseCard(name="Etirements", daily_quota=2, is_joker=False),
        PauseCard(name="Joker", daily_quota=1, is_joker=True),
    ]
    db.add_all(cards)
    db.commit()


def get_daily_state(db: Session, date_value: str) -> DailyState:
    state = db.query(DailyState).filter(DailyState.date == date_value).first()
    if state:
        return state
    state = DailyState(date=date_value, pause_due_minutes=0)
    db.add(state)
    db.commit()
    db.refresh(state)
    return state


def compute_actual_minutes(start_at: datetime, end_at: datetime) -> int:
    delta_seconds = max(0, int((end_at - start_at).total_seconds()))
    minutes = max(1, int(round(delta_seconds / 60)))
    return minutes


def break_for(minutes_value: int) -> int:
    return 10 if minutes_value >= 45 else 5


def resolve_break_minutes(focus_minutes: int, fallback: int) -> int:
    if not focus_minutes:
        return fallback or 5
    if focus_minutes >= 45:
        return 10
    return 5


def ceil_to_step(value: int, step: int = 5) -> int:
    return int(math.ceil(value / step) * step)


def minutes_from_datetime(value: datetime) -> int:
    return value.hour * 60 + value.minute


def minutes_from_time_string(value: str) -> int:
    hour, minute = value.split(":")
    return int(hour) * 60 + int(minute)


def daypart_bounds(dayparts, name: str) -> Optional[tuple[int, int]]:
    for part in dayparts:
        if part["name"] != name:
            continue
        start = minutes_from_time_string(part["start"])
        end = minutes_from_time_string(part["end"])
        if end == 0 or end <= start:
            end = 1440
        return start, end
    return None


def resolve_daypart_name_by_minutes(dayparts, minutes_value: int) -> str:
    for part in dayparts:
        start = minutes_from_time_string(part["start"])
        end = minutes_from_time_string(part["end"])
        if end == 0 or end <= start:
            end = 1440
        if start <= minutes_value < end:
            return part["name"]
    return dayparts[0]["name"] if dayparts else ""


def datetime_from_minutes(date_value: str, minutes_value: int) -> datetime:
    clamped = max(0, min(1439, minutes_value))
    hour = clamped // 60
    minute = clamped % 60
    return datetime.combine(
        datetime.fromisoformat(date_value).date(), time_type(hour, minute)
    )


def adjust_for_gap(start_minutes: int, dayparts) -> Optional[int]:
    ranges = []
    for part in dayparts:
        start = int(part["start"].split(":")[0]) * 60 + int(part["start"].split(":")[1])
        end = int(part["end"].split(":")[0]) * 60 + int(part["end"].split(":")[1])
        if end == 0 or end <= start:
            end = 1440
        ranges.append({"name": part["name"], "start": start, "end": end})
    ranges.sort(key=lambda item: item["start"])

    for daypart in ranges:
        if start_minutes >= daypart["start"] and start_minutes < daypart["end"]:
            return start_minutes

    next_range = next((item for item in ranges if start_minutes < item["start"]), None)
    if not next_range:
        return None
    return next_range["start"]


def shift_planned_after_early_stop(
    db: Session, session: SessionModel, settings: Settings
) -> None:
    if session.kind != "focus":
        return
    if not session.actual_minutes:
        return
    if session.actual_minutes >= session.planned_minutes:
        return
    planned = (
        db.query(SessionModel)
        .filter(
            SessionModel.date == session.date,
            SessionModel.state == "planned",
            SessionModel.kind == "focus",
        )
        .order_by(SessionModel.start_at.asc(), SessionModel.id.asc())
        .all()
    )
    if not planned:
        return
    dayparts = json.loads(settings.dayparts_json)
    break_minutes = resolve_break_minutes(
        session.planned_minutes, settings.default_break_minutes
    )
    base_minutes = minutes_from_datetime(session.end_at) + break_minutes
    base_minutes = ceil_to_step(base_minutes, 5)
    base_minutes = adjust_for_gap(base_minutes, dayparts)
    if base_minutes is None:
        return

    for planned_session in planned:
        planned_start = datetime_from_minutes(session.date, base_minutes)
        planned_session.start_at = planned_start
        planned_session.daypart_name = resolve_daypart_name(dayparts, planned_start)
        base_minutes = (
            base_minutes
            + planned_session.planned_minutes
            + break_for(planned_session.planned_minutes)
        )
        base_minutes = ceil_to_step(base_minutes, 5)
        base_minutes = adjust_for_gap(base_minutes, dayparts)
        if base_minutes is None:
            break


def shift_planned_after_adjust(
    db: Session,
    session: SessionModel,
    settings: Settings,
    client_now: Optional[datetime],
) -> None:
    if session.kind != "focus":
        return
    if session.state != "running":
        return
    dayparts = json.loads(settings.dayparts_json)
    planned_end = session.start_at + timedelta(minutes=session.planned_minutes)
    now = client_now or current_time()
    break_minutes = resolve_break_minutes(
        session.planned_minutes, settings.default_break_minutes
    )
    base_minutes = minutes_from_datetime(max(now, planned_end)) + break_minutes
    base_minutes = ceil_to_step(base_minutes, 5)
    base_minutes = adjust_for_gap(base_minutes, dayparts)
    if base_minutes is None:
        return
    planned = (
        db.query(SessionModel)
        .filter(
            SessionModel.date == session.date,
            SessionModel.state == "planned",
            SessionModel.kind == "focus",
        )
        .order_by(SessionModel.start_at.asc(), SessionModel.id.asc())
        .all()
    )
    if not planned:
        return
    for planned_session in planned:
        planned_start = datetime_from_minutes(session.date, base_minutes)
        planned_session.start_at = planned_start
        planned_session.daypart_name = resolve_daypart_name(dayparts, planned_start)
        base_minutes = (
            base_minutes
            + planned_session.planned_minutes
            + break_for(planned_session.planned_minutes)
        )
        base_minutes = ceil_to_step(base_minutes, 5)
        base_minutes = adjust_for_gap(base_minutes, dayparts)
        if base_minutes is None:
            break


def shift_planned_for_today(
    db: Session,
    date_value: str,
    settings: Settings,
    client_date: Optional[str],
    client_minutes: Optional[int],
) -> None:
    today_value = client_date or date_type.today().isoformat()
    if date_value != today_value:
        return
    planned = (
        db.query(SessionModel)
        .filter(
            SessionModel.date == date_value,
            SessionModel.state == "planned",
            SessionModel.kind == "focus",
        )
        .order_by(SessionModel.start_at.asc(), SessionModel.id.asc())
        .all()
    )
    if not planned:
        return
    dayparts = json.loads(settings.dayparts_json)
    now = current_time()
    minutes_now = (
        client_minutes if client_minutes is not None else minutes_from_datetime(now)
    )
    current_daypart = resolve_daypart_name_by_minutes(dayparts, minutes_now)
    current_bounds = daypart_bounds(dayparts, current_daypart)
    base_minutes = minutes_now
    running = (
        db.query(SessionModel)
        .filter(
            SessionModel.date == date_value,
            SessionModel.state == "running",
        )
        .order_by(SessionModel.start_at.desc(), SessionModel.id.desc())
        .first()
    )
    if running:
        planned_end = running.start_at + timedelta(minutes=running.planned_minutes)
        extra_break = (
            resolve_break_minutes(
                running.planned_minutes, settings.default_break_minutes
            )
            if running.kind == "focus"
            else 0
        )
        base_minutes = max(
            base_minutes, minutes_from_datetime(planned_end) + extra_break
        )
    break_override = False
    planned_in_daypart = [
        session for session in planned if session.daypart_name == current_daypart
    ]
    if planned_in_daypart and current_bounds:
        base_rounded = ceil_to_step(base_minutes, 5)
        base_in_daypart = max(base_rounded, current_bounds[0])
        available = max(0, current_bounds[1] - base_in_daypart)
        if available > 0:

            def break_duration(minutes_value: int, override: bool) -> int:
                if override and minutes_value >= 45:
                    return 5
                return break_for(minutes_value)

            def workload(sessions, override: bool) -> int:
                if not sessions:
                    return 0
                total = sum(session.planned_minutes for session in sessions)
                if len(sessions) > 1:
                    total += sum(
                        break_duration(session.planned_minutes, override)
                        for session in sessions[:-1]
                    )
                return total

            def reduce_sessions(sessions, from_minutes: int, to_minutes: int) -> None:
                for session in sessions:
                    if session.planned_minutes == from_minutes:
                        session.planned_minutes = to_minutes

            if workload(planned_in_daypart, break_override) > available:
                break_override = True
                if workload(planned_in_daypart, break_override) > available:
                    reduce_sessions(planned_in_daypart, 45, 40)
                    if workload(planned_in_daypart, break_override) > available:
                        reduce_sessions(planned_in_daypart, 20, 15)
                        if workload(planned_in_daypart, break_override) > available:
                            reduce_sessions(planned_in_daypart, 40, 35)
    base_minutes = ceil_to_step(base_minutes, 5)
    base_minutes = adjust_for_gap(base_minutes, dayparts)
    if base_minutes is None:
        return
    for planned_session in planned:
        planned_start = datetime_from_minutes(date_value, base_minutes)
        planned_session.start_at = planned_start
        planned_session.daypart_name = resolve_daypart_name(dayparts, planned_start)
        in_current_daypart = (
            current_bounds is not None
            and current_bounds[0] <= base_minutes < current_bounds[1]
        )
        break_minutes = break_for(planned_session.planned_minutes)
        if (
            break_override
            and in_current_daypart
            and planned_session.planned_minutes >= 45
        ):
            break_minutes = 5
        base_minutes = base_minutes + planned_session.planned_minutes + break_minutes
        base_minutes = ceil_to_step(base_minutes, 5)
        base_minutes = adjust_for_gap(base_minutes, dayparts)
        if base_minutes is None:
            break


@app.get("/api/v1/daily-state", response_model=DailyStateResponse)
def read_daily_state(
    date: Optional[str] = Query(default=None), db: Session = Depends(get_db)
):
    date_value = date or date_type.today().isoformat()
    state = get_daily_state(db, date_value)
    return DailyStateResponse(
        date=state.date, pause_due_minutes=state.pause_due_minutes
    )


@app.get("/api/v1/settings", response_model=SettingsResponse)
def get_settings(db: Session = Depends(get_db)):
    settings, needs_setup = get_or_create_settings(db)
    return settings_to_response(settings, needs_setup)


@app.put("/api/v1/settings", response_model=SettingsResponse)
def update_settings(payload: SettingsUpdate, db: Session = Depends(get_db)):
    settings, _ = get_or_create_settings(db)
    settings.dayparts_json = json.dumps([dp.model_dump() for dp in payload.dayparts])
    settings.default_focus_minutes = payload.default_focus_minutes
    settings.default_break_minutes = payload.default_break_minutes
    settings.notifications_enabled = payload.notifications_enabled
    settings.sound_enabled = payload.sound_enabled
    db.commit()
    db.refresh(settings)
    return settings_to_response(settings, False)


@app.get("/api/v1/tasks", response_model=List[TaskResponse])
def list_tasks(
    status: Optional[str] = Query(default=None), db: Session = Depends(get_db)
):
    query = db.query(Task)
    if status:
        query = query.filter(Task.status == status)
    return query.order_by(Task.created_at.desc()).all()


@app.post("/api/v1/tasks", response_model=TaskResponse)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    task = Task(
        title=payload.title,
        estimate_pomodoros=payload.estimate_pomodoros,
        note=payload.note,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@app.put("/api/v1/tasks/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


@app.post("/api/v1/tasks/{task_id}/complete", response_model=TaskResponse)
def complete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.status = "done"
    db.commit()
    db.refresh(task)
    return task


@app.get("/api/v1/sessions", response_model=List[SessionResponse])
def list_sessions(
    from_date: str = Query(..., alias="from"),
    to_date: str = Query(..., alias="to"),
    client_date: Optional[str] = Query(default=None),
    client_minutes: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
):
    return (
        db.query(SessionModel)
        .filter(and_(SessionModel.date >= from_date, SessionModel.date <= to_date))
        .order_by(SessionModel.start_at.asc())
        .all()
    )


@app.post("/api/v1/sessions/start", response_model=SessionResponse)
def start_session(payload: SessionStart, db: Session = Depends(get_db)):
    if payload.kind == "break":
        raise HTTPException(
            status_code=400, detail="Use /pause/consume to start breaks"
        )
    settings, _ = get_or_create_settings(db)
    minutes = payload.minutes or settings.default_focus_minutes
    now = parse_client_now(payload.client_now) or current_time()
    dayparts = json.loads(settings.dayparts_json)
    session = SessionModel(
        kind=payload.kind,
        task_id=payload.task_id,
        title=payload.title,
        start_at=now,
        planned_minutes=minutes,
        state="running",
        note=None,
        date=now.date().isoformat(),
        daypart_name=resolve_daypart_name(dayparts, now),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@app.post("/api/v1/sessions/plan", response_model=SessionResponse)
def plan_session(payload: SessionPlan, db: Session = Depends(get_db)):
    if payload.kind != "focus":
        raise HTTPException(
            status_code=400, detail="Only focus sessions can be planned"
        )
    settings, _ = get_or_create_settings(db)
    minutes = payload.minutes or settings.default_focus_minutes
    start_at = build_datetime(payload.date, payload.planned_time)
    today_value = date_type.today().isoformat()
    if payload.date == today_value:
        now = current_time()
        if start_at < now:
            dayparts = json.loads(settings.dayparts_json)
            base_minutes = minutes_from_datetime(now)
            base_minutes = ceil_to_step(base_minutes, 5)
            base_minutes = adjust_for_gap(base_minutes, dayparts)
            if base_minutes is not None:
                start_at = datetime_from_minutes(payload.date, base_minutes)
    session = SessionModel(
        kind=payload.kind,
        task_id=payload.task_id,
        title=payload.title,
        start_at=start_at,
        planned_minutes=minutes,
        state="planned",
        note=None,
        date=payload.date,
        daypart_name=payload.daypart_name,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@app.post("/api/v1/sessions/{session_id}/start", response_model=SessionResponse)
def start_planned_session(
    session_id: int,
    client_now: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.state != "planned":
        raise HTTPException(status_code=400, detail="Session is not planned")
    settings, _ = get_or_create_settings(db)
    dayparts = json.loads(settings.dayparts_json)
    now = parse_client_now(client_now) or current_time()
    session.start_at = now
    session.state = "running"
    session.date = now.date().isoformat()
    session.daypart_name = resolve_daypart_name(dayparts, now)
    db.commit()
    db.refresh(session)
    return session


@app.post("/api/v1/sessions/{session_id}/stop", response_model=SessionResponse)
def stop_session(
    session_id: int,
    client_now: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.state != "running":
        raise HTTPException(status_code=400, detail="Session is not running")
    settings, _ = get_or_create_settings(db)
    session.end_at = parse_client_now(client_now) or current_time()
    session.actual_minutes = compute_actual_minutes(session.start_at, session.end_at)
    session.state = "completed"
    shift_planned_after_early_stop(db, session, settings)
    db.commit()
    db.refresh(session)
    return session


@app.post("/api/v1/sessions/{session_id}/skip", response_model=SessionResponse)
def skip_session(
    session_id: int,
    client_now: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.state = "skipped"
    session.end_at = parse_client_now(client_now) or current_time()
    session.actual_minutes = 0
    db.commit()
    db.refresh(session)
    return session


@app.post("/api/v1/sessions/{session_id}/adjust", response_model=SessionResponse)
def adjust_session(
    session_id: int, payload: SessionAdjust, db: Session = Depends(get_db)
):
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.planned_minutes = max(1, session.planned_minutes + payload.minutes_delta)
    settings, _ = get_or_create_settings(db)
    shift_planned_after_adjust(
        db, session, settings, parse_client_now(payload.client_now)
    )
    db.commit()
    db.refresh(session)
    return session


@app.post("/api/v1/sessions/{session_id}/reset")
def reset_session(
    session_id: int,
    client_now: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.state == "planned":
        db.delete(session)
        db.commit()
        return {"status": "deleted"}
    session.state = "aborted"
    session.end_at = parse_client_now(client_now) or current_time()
    session.actual_minutes = 0
    db.commit()
    return {"status": "aborted"}


@app.post("/api/v1/sessions/reset-day")
def reset_day(
    date: str = Query(...),
    mode: str = Query(default="planned"),
    db: Session = Depends(get_db),
):
    if mode not in {"planned", "history", "all"}:
        raise HTTPException(status_code=400, detail="Invalid reset mode")
    if mode == "planned":
        db.query(SessionModel).filter(
            SessionModel.date == date, SessionModel.state == "planned"
        ).delete()
    elif mode == "history":
        db.query(SessionModel).filter(
            SessionModel.date == date, SessionModel.state != "planned"
        ).delete()
        db.query(PauseCardUse).filter(PauseCardUse.date == date).delete()
    else:
        db.query(SessionModel).filter(SessionModel.date == date).delete()
        db.query(PauseCardUse).filter(PauseCardUse.date == date).delete()
    state = get_daily_state(db, date)
    state.pause_due_minutes = 0
    db.commit()
    return {"status": "ok"}


@app.post("/api/v1/sessions/{session_id}/merge-next", response_model=SessionResponse)
def merge_next(
    session_id: int,
    client_now: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.kind != "focus":
        raise HTTPException(status_code=400, detail="Only focus sessions can merge")
    next_session = (
        db.query(SessionModel)
        .filter(
            SessionModel.date == session.date,
            SessionModel.state == "planned",
            SessionModel.kind == "focus",
            SessionModel.id != session.id,
        )
        .order_by(SessionModel.start_at.asc(), SessionModel.id.asc())
        .first()
    )
    if not next_session:
        raise HTTPException(status_code=404, detail="No next focus session to merge")
    settings, _ = get_or_create_settings(db)
    state = get_daily_state(db, session.date)
    state.pause_due_minutes += settings.default_break_minutes
    session.planned_minutes += next_session.planned_minutes
    next_session.state = "skipped"
    next_session.end_at = parse_client_now(client_now) or current_time()
    next_session.actual_minutes = 0
    db.commit()
    db.refresh(session)
    return session


@app.put("/api/v1/sessions/{session_id}", response_model=SessionResponse)
def update_session(
    session_id: int, payload: SessionUpdate, db: Session = Depends(get_db)
):
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    updates = payload.model_dump(exclude_unset=True)
    planned_time = updates.pop("planned_time", None)
    for field, value in updates.items():
        setattr(session, field, value)
    if planned_time:
        session.start_at = build_datetime(session.date, planned_time)
    db.commit()
    db.refresh(session)
    return session


@app.get("/api/v1/pause-cards", response_model=List[PauseCardResponse])
def list_pause_cards(db: Session = Depends(get_db)):
    today = date_type.today().isoformat()
    cards = db.query(PauseCard).order_by(PauseCard.created_at.asc()).all()
    results = []
    for card in cards:
        used = (
            db.query(func.count(PauseCardUse.id))
            .filter(
                PauseCardUse.pause_card_id == card.id,
                PauseCardUse.date == today,
            )
            .scalar()
        )
        remaining = max(0, card.daily_quota - int(used or 0))
        results.append(
            PauseCardResponse(
                id=card.id,
                name=card.name,
                daily_quota=card.daily_quota,
                is_joker=card.is_joker,
                created_at=card.created_at,
                remaining_today=remaining,
            )
        )
    return results


@app.post("/api/v1/pause-cards", response_model=PauseCardResponse)
def create_pause_card(payload: PauseCardCreate, db: Session = Depends(get_db)):
    card = PauseCard(
        name=payload.name,
        daily_quota=payload.daily_quota,
        is_joker=payload.is_joker,
    )
    db.add(card)
    db.commit()
    db.refresh(card)
    return PauseCardResponse(
        id=card.id,
        name=card.name,
        daily_quota=card.daily_quota,
        is_joker=card.is_joker,
        created_at=card.created_at,
        remaining_today=card.daily_quota,
    )


@app.put("/api/v1/pause-cards/{card_id}", response_model=PauseCardResponse)
def update_pause_card(
    card_id: int, payload: PauseCardUpdate, db: Session = Depends(get_db)
):
    card = db.query(PauseCard).filter(PauseCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Pause card not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(card, field, value)
    db.commit()
    db.refresh(card)
    used = (
        db.query(func.count(PauseCardUse.id))
        .filter(
            PauseCardUse.pause_card_id == card.id,
            PauseCardUse.date == date_type.today().isoformat(),
        )
        .scalar()
    )
    remaining = max(0, card.daily_quota - int(used or 0))
    return PauseCardResponse(
        id=card.id,
        name=card.name,
        daily_quota=card.daily_quota,
        is_joker=card.is_joker,
        created_at=card.created_at,
        remaining_today=remaining,
    )


@app.post("/api/v1/pause-cards/reset")
def reset_pause_cards(date: str = Query(...), db: Session = Depends(get_db)):
    db.query(PauseCardUse).filter(PauseCardUse.date == date).delete()
    db.commit()
    return {"status": "ok"}


@app.post("/api/v1/pause/consume", response_model=SessionResponse)
def consume_pause_card(payload: PauseConsume, db: Session = Depends(get_db)):
    card = db.query(PauseCard).filter(PauseCard.id == payload.pause_card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Pause card not found")
    client_now = parse_client_now(payload.client_now)
    today = (
        client_now.date().isoformat() if client_now else date_type.today().isoformat()
    )
    used = (
        db.query(func.count(PauseCardUse.id))
        .filter(PauseCardUse.pause_card_id == card.id, PauseCardUse.date == today)
        .scalar()
    )
    remaining = max(0, card.daily_quota - int(used or 0))
    if remaining <= 0:
        raise HTTPException(status_code=400, detail="Pause card quota exhausted")
    settings, _ = get_or_create_settings(db)
    minutes = payload.minutes or settings.default_break_minutes
    now = client_now or current_time()
    dayparts = json.loads(settings.dayparts_json)
    session = SessionModel(
        kind="break",
        task_id=None,
        start_at=now,
        planned_minutes=minutes,
        state="running",
        note=None,
        date=today,
        daypart_name=resolve_daypart_name(dayparts, now),
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    use = PauseCardUse(
        pause_card_id=card.id,
        date=today,
        session_id=session.id,
    )
    db.add(use)

    state = get_daily_state(db, today)
    if state.pause_due_minutes > 0:
        state.pause_due_minutes = max(0, state.pause_due_minutes - minutes)

    db.commit()
    db.refresh(session)
    return session


@app.get("/api/v1/export/sqlite")
def export_sqlite():
    db_path = "/data/app.db"
    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="Database not found")
    return FileResponse(
        db_path, media_type="application/octet-stream", filename="tomate.db"
    )
