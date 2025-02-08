from database import load_race_tmp, load_event_date, calc_average
from datetime import datetime
from pytz import timezone

sydney_tz = timezone('Australia/Sydney')

def time_to_seconds(time_str):
    """Convert a time string (HH:MM:SS) to total seconds. If the format is incorrect, return None."""
    try:
        h, m, s = map(int, time_str.split(':'))
        return h * 3600 + m * 60 + s
    except ValueError:
        return None

def calculate_race_rankings(race_code):
    # load race times from race_tmp table
    race_times = load_race_tmp(race_code)
    print(f"Ready to calculate rankings at: {datetime.now(sydney_tz)}")
    print(type(race_times))
    print(race_times)

    event = load_event_date(race_code)
    ip = event['ip']

    # get eligibility and averages
    for competitor in race_times:
        eligible, average = calc_average(competitor['full_name'], event['date'])
        print(f"name {competitor['full_name']}, eligible {eligible}, average {average} ")
        competitor['eligible'] = eligible
        competitor['average'] = average

    # calculate race statistics
    print(f"ip {ip}")
    # WT + 50% is the time of the lower non-zero competitor['race_time'] plus 50%
    non_zero_times = []
    for competitor in race_times:
        try:
            race_time = time_to_seconds(competitor['race_time'])
            if race_time:
                non_zero_times.append(race_time)
        except ValueError:
            print(f"Invalid race_time value for competitor {competitor['full_name']}: {competitor['race_time']}")

    if non_zero_times:
        wt_plus_50 = min(non_zero_times) * 1.5
        print(f"WT + 50% (seconds): {wt_plus_50}")
    else:
        wt_plus_50 = None
        print("No valid race times found.")

    # RR (ranked runners) = number of competitors with a valid average and race_time <= WT + 50%
    ranked_runners = [
        competitor for competitor in race_times
        if competitor['eligible'] is not None and
        competitor['eligible'] == 'Y' and
        competitor['average'] is not None and
        time_to_seconds(competitor['race_time']) is not None and
        time_to_seconds(competitor['race_time']) <= wt_plus_50
    ]
    rr_count = len(ranked_runners)
    print(f"Ranked Runners (RR): {rr_count}")

    # MP is the mean of competitor['average'] for ranked runners
    mp = sum(competitor['average'] for competitor in ranked_runners) / rr_count
    print(f"MP: {mp}")
    # SP is the standard deviation of competitor['average'] for ranked runners
    sp = (sum((competitor['average'] - mp) ** 2 for competitor in ranked_runners) / rr_count) ** 0.5
    print(f"SP: {sp}")

    # MT is the mean of competitor['race_time'] for ranked runners, noting that race_time is in HH:MM:SS format
    mt = sum(time_to_seconds(competitor['race_time']) for competitor in ranked_runners) / rr_count
    print(f"MT (seconds): {mt}")
    # ST is the standard deviation of competitor['race_time'] for ranked runners
    st = (sum((time_to_seconds(competitor['race_time']) - mt) ** 2 for competitor in ranked_runners) / rr_count) ** 0.5
    print(f"ST (seconds): {st}")

    

    # calculate rankings

    # save rankings to database
    print(f"Finished calculating rankings at: {datetime.now(sydney_tz)}")

    return