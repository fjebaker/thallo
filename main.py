from thallo.calendar import Calendar
from datetime import datetime, timedelta

today = datetime.today()
week_before = today - timedelta(days=7 * 2)
week_after = today + timedelta(days=7 * 2)

cal = Calendar()
events = cal.fetch_dict(week_before, week_after)
print(events)
