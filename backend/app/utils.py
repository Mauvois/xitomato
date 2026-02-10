from datetime import datetime, time


def parse_time(value: str) -> time:
    parts = value.split(":")
    hour = int(parts[0])
    minute = int(parts[1])
    return time(hour=hour, minute=minute)


def resolve_daypart_name(dayparts, at_dt: datetime) -> str:
    current = at_dt.time()
    for daypart in dayparts:
        start = parse_time(daypart["start"])
        end = parse_time(daypart["end"])
        if start <= end:
            if start <= current < end:
                return daypart["name"]
        else:
            if current >= start or current < end:
                return daypart["name"]
    return dayparts[0]["name"]


def get_daypart_start(dayparts, daypart_name: str) -> time:
    for daypart in dayparts:
        if daypart["name"] == daypart_name:
            return parse_time(daypart["start"])
    return parse_time(dayparts[0]["start"])


def build_datetime(date_value: str, time_value: str) -> datetime:
    planned_date = datetime.fromisoformat(f"{date_value}T00:00:00").date()
    planned_time = parse_time(time_value)
    return datetime.combine(planned_date, planned_time)
