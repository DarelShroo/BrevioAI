from datetime import timedelta

def parse_duration(duration):
    time_parts = duration.split(":")
        
    if len(time_parts) == 2:
        minutes, seconds = map(int, time_parts)
        hours = 0
    elif len(time_parts) == 3:
        hours, minutes, seconds = map(int, time_parts)
    else:
        print("Formato de duración no válido:", duration)
        return timedelta()
        
    return timedelta(hours=hours, minutes=minutes, seconds=seconds)

def format_time(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    return f"[{hours:02d}:{minutes:02d}:{seconds:02d}]"