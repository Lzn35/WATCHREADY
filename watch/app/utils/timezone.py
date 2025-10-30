"""
Timezone utilities for WATCH System
Ensures all dates use Philippine timezone (Asia/Manila) regardless of server location
"""

from datetime import datetime, date, time, timedelta
import sys

# Try to use zoneinfo (Python 3.9+), fallback to pytz if needed
try:
    from zoneinfo import ZoneInfo
    PH_TIMEZONE = ZoneInfo('Asia/Manila')
except ImportError:
    # Fallback for Python < 3.9
    try:
        import pytz
        PH_TIMEZONE = pytz.timezone('Asia/Manila')
    except ImportError:
        # Last resort: calculate UTC+8 manually (8 hours ahead)
        PH_TIMEZONE = None

def get_ph_now():
    """Get current datetime in Philippine timezone"""
    if PH_TIMEZONE is not None:
        try:
            return datetime.now(PH_TIMEZONE)
        except:
            pass
    
    # Fallback: add 8 hours to UTC (Philippines is UTC+8)
    try:
        from datetime import timezone as tz
        utc_now = datetime.now(tz.utc)
        ph_offset = timedelta(hours=8)
        ph_time = utc_now + ph_offset
        # Return naive datetime (timezone-aware conversions handled elsewhere)
        return datetime(ph_time.year, ph_time.month, ph_time.day, 
                       ph_time.hour, ph_time.minute, ph_time.second, 
                       ph_time.microsecond)
    except:
        # Last resort: assume server time is already correct or use local time
        # This shouldn't happen, but provides a fallback
        return datetime.now()

def get_ph_today():
    """Get today's date in Philippine timezone"""
    return get_ph_now().date()

def get_ph_weekday():
    """Get today's weekday name in Philippine timezone (e.g., 'Monday', 'Friday')"""
    weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    today = get_ph_today()
    return weekday_names[today.weekday()]

def convert_to_ph_time(dt):
    """Convert a datetime to Philippine timezone"""
    if dt.tzinfo is None:
        # If no timezone info, assume it's already in PH time
        return dt.replace(tzinfo=PH_TIMEZONE)
    return dt.astimezone(PH_TIMEZONE)

def get_ph_datetime(year, month, day, hour=0, minute=0, second=0):
    """Create a datetime in Philippine timezone"""
    return datetime(year, month, day, hour, minute, second, tzinfo=PH_TIMEZONE)

