from datetime import datetime
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .db import Base


class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    dayparts_json = Column(Text, nullable=False)
    default_focus_minutes = Column(Integer, nullable=False, default=45)
    default_break_minutes = Column(Integer, nullable=False, default=5)
    notifications_enabled = Column(Boolean, nullable=False, default=True)
    sound_enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DailyState(Base):
    __tablename__ = "daily_state"

    date = Column(String, primary_key=True)
    pause_due_minutes = Column(Integer, nullable=False, default=0)


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    estimate_pomodoros = Column(Integer, nullable=False, default=1)
    note = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    sessions = relationship("Session", back_populates="task")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    kind = Column(String, nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    start_at = Column(DateTime, nullable=False)
    end_at = Column(DateTime, nullable=True)
    planned_minutes = Column(Integer, nullable=False)
    actual_minutes = Column(Integer, nullable=True)
    state = Column(String, nullable=False, default="planned")
    title = Column(String, nullable=True)
    note = Column(Text, nullable=True)
    date = Column(String, nullable=False)
    daypart_name = Column(String, nullable=False)

    task = relationship("Task", back_populates="sessions")


class PauseCard(Base):
    __tablename__ = "pause_cards"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    daily_quota = Column(Integer, nullable=False, default=1)
    is_joker = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    uses = relationship("PauseCardUse", back_populates="card")


class PauseCardUse(Base):
    __tablename__ = "pause_card_uses"

    id = Column(Integer, primary_key=True, index=True)
    pause_card_id = Column(Integer, ForeignKey("pause_cards.id"), nullable=False)
    date = Column(String, nullable=False)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    used_at = Column(DateTime, default=datetime.utcnow)

    card = relationship("PauseCard", back_populates="uses")
