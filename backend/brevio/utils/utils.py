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