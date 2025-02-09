from database import load_race_tmp, load_event_date, calc_average, insert_new_results, insert_event_statistics, update_event_ip
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
    # enhancement factor is the importance of the race
    # enhancement factor is usually 1.0 for Australian events, except Australian Championships (1.05)
    enhancement_factor = float(event['ip'])  # Convert to float

    # get eligibility and averages
    for competitor in race_times:
        eligible, average = calc_average(competitor['full_name'], event['date'])
        print(f"name {competitor['full_name']}, eligible {eligible}, average {average} ")
        competitor['eligible'] = eligible
        competitor['average'] = average

    # calculate race statistics
    print(f"enhancement_factor {enhancement_factor}")
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

    # Determine the unweighted calculated score for the winner using the appropriate formula

    # 7.4
    # If there is at least one ranked athlete, perform a preliminary calculation of ranking points prelim_rp for each competitor at the event as follows:
    if ranked_runners:
        mp_ranked = sum(competitor['average'] for competitor in ranked_runners) / rr_count
        sp_ranked = (sum((competitor['average'] - mp_ranked) ** 2 for competitor in ranked_runners) / rr_count) ** 0.5
        mt_ranked = sum(time_to_seconds(competitor['race_time']) for competitor in ranked_runners) / rr_count
        st_ranked = (sum((time_to_seconds(competitor['race_time']) - mt_ranked) ** 2 for competitor in ranked_runners) / rr_count) ** 0.5

        for competitor in race_times:
            rt = time_to_seconds(competitor['race_time'])
            if rt is not None:
                if rr_count >= 8:
                    prelim_rp = (mp_ranked + sp_ranked * (mt_ranked - rt) / st_ranked) * float(enhancement_factor)
                else:
                    prelim_rp = (2000 - rt * (2000 - mp_ranked) / mt_ranked) * float(enhancement_factor)
                competitor['prelim_rp'] = max(prelim_rp, 10)  # Ensure prelim_rp is at least 10
                print(f"Competitor {competitor['full_name']} prelim_rp: {competitor['prelim_rp']}")
            else:
                competitor['prelim_rp'] = 0
                print(f"Competitor {competitor['full_name']} has invalid race time, prelim_rp set to 0.")
    else:
        winner_time = min(time_to_seconds(competitor['race_time']) for competitor in race_times if time_to_seconds(competitor['race_time']) is not None)
        for competitor in race_times:
            rt = time_to_seconds(competitor['race_time'])
            if rt is not None:
                prelim_rp = (2000 - rt * 1200 / winner_time) * float(enhancement_factor)
                competitor['prelim_rp'] = max(prelim_rp, 10)  # Ensure prelim_rp is at least 10
                print(f"Competitor {competitor['full_name']} prelim_rp: {competitor['prelim_rp']}")
            else:
                competitor['prelim_rp'] = 0
                print(f"Competitor {competitor['full_name']} has invalid race time, prelim_rp set to 0.")


    # 7.1
    # An outlier athlete is one whose preliminary calculated unweighted ranking points RP are more than 100 different from their average prior unweighted ranking points.
    for competitor in race_times:
        if competitor['prelim_rp'] is not None and competitor['average'] is not None:
            if abs(competitor['prelim_rp'] - competitor['average']) > 100:
                competitor['outlier'] = True
            else:
                competitor['outlier'] = False
        else:
            competitor['outlier'] = False
    

    # calculate the winner's unweighted calculated score
    winners_unweighted_calculated_score = max(
    (competitor['prelim_rp'] for competitor in race_times if competitor['prelim_rp'] is not None),
    default=None 
    )

    # 7.3
    # The Winner scores a minimum of 800 and a maximum of 1375 
    # o If the Winner’s unweighted calculated score is between 800 and 1375, IP = 1 x enhancement factor 
    # o If the Winner’s unweighted calculated score is less than 800, IP = 800/Winner’s unweighted calculated score x Enhancement Factor o If the Winner’s unweighted calculated score is greater than 1375, IP = 1375/Winner’s unweighted calculated score x Enhancement Factor    
    # ip = total weighting factor appied to the event (including enhancement factor x any adjustments for the winner's points to be in the correct range)
    ip_change = False
    if winners_unweighted_calculated_score is not None:
        if 800 <= winners_unweighted_calculated_score <= 1375:
            ip = 1 * enhancement_factor
        elif winners_unweighted_calculated_score < 800:
            ip = 800 / winners_unweighted_calculated_score * enhancement_factor
            ip_change = True
        else:
            ip = 1375 / winners_unweighted_calculated_score * enhancement_factor
            ip_change = True
        print(f"Winner's unweighted calculated score: {winners_unweighted_calculated_score}, IP: {ip}")
    else:
        print("No valid prelim_rp found for any competitor.")

    # print the number of non-outlier ranked athletes
    non_outlier_ranked_count = len([competitor for competitor in ranked_runners if not competitor['outlier']])  
    print(f"Non-outlier ranked athletes: {non_outlier_ranked_count}")

    # 7.5
    # Finally, recalculate the ranking points RP for each competitor at the event as follows:
    # • Calculate the mean MP and the standard deviation SP of the average prior unweighted ranking points of all ranked non-outlier athletes.
    # • Calculate the mean MT and the standard deviation ST of the race times RT of all non-outlier ranked athletes.
    # • The formula RP = (MP + SP x (MT- RT)/ST) x IP is used if there are 8 or more non-outlier ranked athletes.
    # • The formula RP = (2000 - RT x (2000 - MP) / MT) x IP is used if there is at least one but fewer than 8 non-outlier ranked athletes.
    # • If there are no non-outlier ranked athletes then MT is set to the winner’s time and the formula RP = (2000 – RT x 1200/MT) x IP is used.
    # • Any competitor who successfully finishes a WR event according to the rules of the event, but for whom RP is less than 10 as calculated above, shall be given 10 ranking points.
    non_outlier_ranked_runners = [
        competitor for competitor in ranked_runners if not competitor.get('outlier', False)
    ]
    if non_outlier_ranked_runners:
        mp_non_outliers = sum(competitor['average'] for competitor in non_outlier_ranked_runners) / len(non_outlier_ranked_runners)
        sp_non_outliers = (sum((competitor['average'] - mp_non_outliers) ** 2 for competitor in non_outlier_ranked_runners) / len(non_outlier_ranked_runners)) ** 0.5
        mt_non_outliers = sum(time_to_seconds(competitor['race_time']) for competitor in non_outlier_ranked_runners) / len(non_outlier_ranked_runners)
        st_non_outliers = (sum((time_to_seconds(competitor['race_time']) - mt_non_outliers) ** 2 for competitor in non_outlier_ranked_runners) / len(non_outlier_ranked_runners)) ** 0.5

        for competitor in race_times:
            rt = time_to_seconds(competitor['race_time'])
            if rt is not None:
                if len(non_outlier_ranked_runners) >= 8:
                    rp = (mp_non_outliers + sp_non_outliers * (mt_non_outliers - rt) / st_non_outliers) * float(ip)
                else:
                    rp = (2000 - rt * (2000 - mp_non_outliers) / mt_non_outliers) * float(ip)
                competitor['rp'] = max(rp, 10)  # Ensure RP is at least 10
                print(f"Competitor {competitor['full_name']} RP: {competitor['rp']}")
            else:
                competitor['rp'] = 0
                print(f"Competitor {competitor['full_name']} has invalid race time, RP set to 0.")
    else:
        winner_time = min(time_to_seconds(competitor['race_time']) for competitor in race_times if time_to_seconds(competitor['race_time']) is not None)
        for competitor in race_times:
            rt = time_to_seconds(competitor['race_time'])
            if rt is not None:
                rp = (2000 - rt * 1200 / winner_time) * float(ip)
                competitor['rp'] = max(rp, 10)  # Ensure RP is at least 10
                print(f"Competitor {competitor['full_name']} RP: {competitor['rp']}")
            else:
                competitor['rp'] = 0
                print(f"Competitor {competitor['full_name']} has invalid race time, RP set to 0.")

    # save rankings to database
    insert_new_results(race_times)

    calculated = datetime.now(sydney_tz)
    rule = "Australian Rankings"
    my_min = 800
    my_max = 1375
    event_stats = [ calculated, mt, st, mp, sp, rule, my_min, my_max, rr_count, enhancement_factor]
    # save event_stats to database
    insert_event_statistics(event['id'], event_stats)
    if ip_change:
        print(f"IP was adjusted for the winner's points to be in the correct range. IP: {ip}")
        update_event_ip(race_code, ip)


    print(f"Finished calculating rankings at: {datetime.now(sydney_tz)}")

    return