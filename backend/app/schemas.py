from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class Daypart(BaseModel):
    name: str
    start: str
    end: str


class SettingsBase(BaseModel):
    dayparts: List[Daypart]
    default_focus_minutes: int = Field(ge=1)
    default_break_minutes: int = Field(ge=1)
    notifications_enabled: bool
    sound_enabled: bool


class SettingsResponse(SettingsBase):
    needs_setup: bool = False


class SettingsUpdate(SettingsBase):
    pass


class TaskBase(BaseModel):
    title: str
    estimate_pomodoros: int = Field(ge=1)
    note: Optional[str] = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    estimate_pomodoros: Optional[int] = Field(default=None, ge=1)
    note: Optional[str] = None
    status: Optional[str] = None


class TaskResponse(TaskBase):
    id: int
    status: str
    created_at: datetime
    updated_at: datetime


class SessionBase(BaseModel):
    kind: str
    task_id: Optional[int] = None
    planned_minutes: int = Field(ge=1)
    title: Optional[str] = None
    note: Optional[str] = None
    date: str
    daypart_name: str


class SessionResponse(SessionBase):
    id: int
    start_at: datetime
    end_at: Optional[datetime] = None
    actual_minutes: Optional[int] = None
    state: str


class SessionStart(BaseModel):
    kind: str
    task_id: Optional[int] = None
    minutes: Optional[int] = Field(default=None, ge=1)
    title: Optional[str] = None


class SessionPlan(BaseModel):
    kind: str
    task_id: Optional[int] = None
    minutes: Optional[int] = Field(default=None, ge=1)
    title: Optional[str] = None
    date: str
    daypart_name: str
    planned_time: str


class SessionStop(BaseModel):
    pass


class SessionAdjust(BaseModel):
    minutes_delta: int


class SessionMerge(BaseModel):
    pass


class SessionUpdate(BaseModel):
    note: Optional[str] = None
    daypart_name: Optional[str] = None
    date: Optional[str] = None
    task_id: Optional[int] = None
    title: Optional[str] = None
    planned_time: Optional[str] = None
    planned_minutes: Optional[int] = Field(default=None, ge=1)


class PauseCardBase(BaseModel):
    name: str
    daily_quota: int = Field(ge=0)
    is_joker: bool = False


class PauseCardCreate(PauseCardBase):
    pass


class PauseCardUpdate(BaseModel):
    name: Optional[str] = None
    daily_quota: Optional[int] = Field(default=None, ge=0)
    is_joker: Optional[bool] = None


class PauseCardResponse(PauseCardBase):
    id: int
    created_at: datetime
    remaining_today: int


class PauseConsume(BaseModel):
    pause_card_id: int
    minutes: Optional[int] = Field(default=None, ge=1)


class DailyStateResponse(BaseModel):
    date: str
    pause_due_minutes: int
