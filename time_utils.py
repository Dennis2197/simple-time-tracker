import datetime


def format_datetime(iso_str):
    """Format ISO datetime as HH:MM:SS DD.MM.YYYY."""
    if not iso_str:
        return "-"
    dt = datetime.datetime.fromisoformat(iso_str)
    return dt.strftime("%H:%M:%S  %d.%m.%Y")


def format_duration(seconds):
    """Format seconds as HH:MM:SS."""
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"
