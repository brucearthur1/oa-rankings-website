import pandas as pd
from datetime import datetime
import re

# Function to convert time format
def convert_to_time_format(time_str):
    try:
        # Use regular expression to extract the time component (HH:MM:SS) 
        match = re.search(r'(\d{2}:\d{2}:\d{2})', time_str) 
        if match: 
            time_obj = datetime.strptime(match.group(1), '%H:%M:%S') 
            return time_obj.strftime('%H:%M:%S') 
        return time_str 
    except ValueError:
        return time_str  # Return original if not time format



