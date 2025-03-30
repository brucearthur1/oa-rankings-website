from database import load_race_tmp, load_event_date, calc_average, insert_new_results, insert_event_statistics, update_event_ip, delete_from_race_tmp, load_wre_scores, load_aus_scores, recalibrate_aus_scores, load_aus_scores_aus
from datetime import datetime, timedelta
from pytz import timezone

sydney_tz = timezone('Australia/Sydney')

def time_to_seconds(time_str):
    if '.' in time_str:
        time_str = time_str.split('.')[0]
    """Convert a time string (HH:MM:SS) to total seconds. If the format is incorrect, return None."""
    try:
        if time_str is None:
            return None
        else:
            h, m, s = map(int, time_str.split(':'))
            return h * 3600 + m * 60 + s
    except ValueError:
        return None

def calculate_race_rankings(race_code):
    print(f"Starting to calculate rankings: {race_code}")

    rule = "Australian Rankings"
    my_min = 800
    my_max = 1375

    # load race times from race_tmp table
    race_times = load_race_tmp(race_code)
    if race_times:
        print(f"Ready to calculate rankings at: {datetime.now(sydney_tz)}")
        #print(race_times)


        mt, st, mp, sp = None, None, None, None

        event = load_event_date(race_code)
        #print(event)
        
        #  recalibrate rankings for this list in the 12 months prior to the event date
        recalibrate(event['date'], event['list'], 1)
        
        # enhancement factor is the importance of the race
        # enhancement factor is usually 1.0 for Australian events, except Australian Championships (1.05)
        enhancement_factor = float(event['ip'])  # Convert to float

        # get eligibility and averages
        for competitor in race_times:
            eligible, average = calc_average(competitor['full_name'], event['date'])
            #print(f"name {competitor['full_name']}, eligible {eligible}, average {average} ")
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

        if ranked_runners:
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
                    #print(f"Competitor {competitor['full_name']} prelim_rp: {competitor['prelim_rp']}")
                else:
                    competitor['prelim_rp'] = 0
                    #print(f"Competitor {competitor['full_name']} has invalid race time, prelim_rp set to 0.")
        else:
        # no ranked runners
            #winner_time = min(time_to_seconds(competitor['race_time']) for competitor in race_times if time_to_seconds(competitor['race_time']) is not None)
            for competitor in race_times:
                competitor['prelim_rp'] = None
                # rt = time_to_seconds(competitor['race_time'])
                # if rt is not None:
                #     prelim_rp = (2000 - rt * 1200 / winner_time) * float(enhancement_factor)
                #     competitor['prelim_rp'] = max(prelim_rp, 10)  # Ensure prelim_rp is at least 10
                #     #print(f"Competitor {competitor['full_name']} prelim_rp: {competitor['prelim_rp']}")
                # else:
                #     competitor['prelim_rp'] = 0
                #     #print(f"Competitor {competitor['full_name']} has invalid race time, prelim_rp set to 0.")


        # 7.1
        # An outlier athlete is one whose preliminary calculated unweighted ranking points RP are more than 100 different from their average prior unweighted ranking points.
        for competitor in race_times:
            if competitor['prelim_rp'] is not None and competitor['average'] is not None:
                if abs(competitor['prelim_rp'] - competitor['average']) > 100:
                    competitor['outlier'] = True
                else:
                    competitor['outlier'] = False
            else:
                competitor['outlier'] = True
        

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
            #print(f"Winner's unweighted calculated score: {winners_unweighted_calculated_score}, IP: {ip}")
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
                    competitor['race_points'] = max(rp, 10)  # Ensure RP is at least 10
                    print(f"Competitor {competitor['full_name']} RP: {competitor['race_points']}")
                else:
                    competitor['race_points'] = 0
                    #print(f"Competitor {competitor['full_name']} has invalid race time, RP set to 0.")
        else:
            winner_time = min(time_to_seconds(competitor['race_time']) for competitor in race_times if time_to_seconds(competitor['race_time']) is not None)
            for competitor in race_times:
                rt = time_to_seconds(competitor['race_time'])
                if rt is not None:
                    rp = (2000 - rt * (2000-my_min) / winner_time) # * float(ip)  # IP is already included in the winner's RP
                    competitor['race_points'] = max(rp, 10)  # Ensure RP is at least 10
                    #print(f"Competitor {competitor['full_name']} RP: {competitor['race_points']}")
                else:
                    competitor['race_points'] = 0
                    #print(f"Competitor {competitor['full_name']} has invalid race time, RP set to 0.")

        # save rankings to database
        insert_new_results(race_times)

        calculated = datetime.now(sydney_tz)
        event_stats = [ calculated, mt, st, mp, sp, rule, my_min, my_max, rr_count, enhancement_factor]
        # save event_stats to database
        insert_event_statistics(event['id'], event_stats)
        if ip_change:
            print(f"IP was adjusted for the winner's points to be in the correct range. IP: {ip}")
            update_event_ip(race_code, ip)

        # clean up race_tmp table
        delete_from_race_tmp(race_code)

    else:
        print(f"race times not found for {race_code}")

    print(f"Finished calculating rankings at: {datetime.now(sydney_tz)}")

    return


def rank_athletes(athletes, ranking_date):

    twelve_months_ago = ranking_date - timedelta(days=365)

    # Ensure athlete['date'] and athlete['race_points'] are in the correct format
    for athlete in athletes:
        if isinstance(athlete['date'], str):
            athlete['date'] = datetime.strptime(athlete['date'], '%Y-%m-%d').date()
        athlete['race_points'] = float(athlete['race_points'])
        athlete['athlete_id'] = str(athlete['athlete_id'])  # Convert athlete_id to string
        if athlete['list']:
            athlete['list'] = str.lower(athlete['list'])
        else:
            print(f"athlete '{athlete['full_name']}' has no list")
        if athlete['discipline']:
            athlete['discipline'] = str.lower(athlete['discipline'])
        else:
            print(f"athlete '{athlete['full_name']}' has no discipline")
        # make sure that names like Henri du\xa0Toit are converted to Henri du Toit
        athlete['full_name'] = athlete['full_name'].replace(u'\xa0', u' ')

    # filter out athlete records for juniors who are no longer eligible
    # yob must exist to be eligible for junior ranking
    ranking_year = ranking_date.year
    
    athletes = [
        athlete for athlete in athletes
        if not (athlete['list'].lower().startswith('junior') and (athlete['yob'] is None or ranking_year - athlete['yob'] >= 21))
    ]

    # Helper function to aggregate athletes based on discipline
    def aggregate_athletes(athletes, discipline=None):
        start_date = twelve_months_ago
        end_date = ranking_date
        prior_period = 90 #days
        start_date_prior_period = start_date - timedelta(days=prior_period)
        end_date_prior_period = end_date - timedelta(days=prior_period)

        aggregated_athletes = {}
        for athlete in athletes:
            # get the race_points for the current period
            if start_date <= athlete['date'] <= end_date:
                if discipline is None or athlete['discipline'] == discipline:
                    key = (athlete['full_name'], athlete['club_name'], athlete['state'], athlete['list'], athlete['athlete_id'], athlete['yob'])
                    if key not in aggregated_athletes:
                        aggregated_athletes[key] = {'race_points': [], 'prior_points': []}
                    aggregated_athletes[key]['race_points'].append(athlete['race_points'])

            # get prior race_points for the prior period
            if start_date_prior_period <= athlete['date'] <= end_date_prior_period:
                if discipline is None or athlete['discipline'] == discipline:
                    key = (athlete['full_name'], athlete['club_name'], athlete['state'], athlete['list'], athlete['athlete_id'], athlete['yob'])
                    if key not in aggregated_athletes:
                        aggregated_athletes[key] = {'race_points': [], 'prior_points': []}
                    prior_points = athlete['race_points']
                    aggregated_athletes[key]['prior_points'].append(prior_points)

        final_aggregated_athletes = []
        for key, points in aggregated_athletes.items():
            race_points = sorted(points['race_points'], reverse=True)[:5]
            prior_points = sorted(points['prior_points'], reverse=True)[:5]
            sum_top_5_race_points = sum(race_points)
            sum_top_5_prior_points = sum(prior_points)
            final_aggregated_athletes.append({
            'full_name': key[0],
            'club_name': key[1],
            'state': key[2],
            'list': key[3],
            'athlete_id': key[4],  
            'yob': key[5],
            'sum_top_5_prior_points': sum_top_5_prior_points,
            'sum_top_5_race_points': sum_top_5_race_points
            })

        # Sort by sum_top_5_prior_points within each list
        for list_name in set(athlete['list'] for athlete in final_aggregated_athletes):
            list_athletes = [athlete for athlete in final_aggregated_athletes if athlete['list'] == list_name]
            list_athletes.sort(key=lambda x: x['sum_top_5_prior_points'], reverse=True)
            # Store the ranking based on sum_top_5_prior_points and calculate the delta
            for idx, athlete in enumerate(list_athletes):
                athlete['prior_points_rank'] = idx + 1

            list_athletes.sort(key=lambda x: x['sum_top_5_race_points'], reverse=True)
            # Store the ranking based on sum_top_5_race_points
            for idx, athlete in enumerate(list_athletes):
                athlete['race_points_rank'] = idx + 1
                athlete['delta'] = athlete['race_points_rank'] - athlete['prior_points_rank']

        # finally sort final_aggregated_athletes by list and then sum_top_5_race_points
        final_aggregated_athletes.sort(key=lambda x: (x['list'], x['sum_top_5_race_points']), reverse=True)  

        return final_aggregated_athletes

    # Aggregating athletes
    final_aggregated_athletes = {
        'all': aggregate_athletes(athletes),
        'sprint': aggregate_athletes(athletes, discipline='sprint'),
        'middle/long': aggregate_athletes(athletes, discipline='middle/long')
    }

    return final_aggregated_athletes

######################################################################################

def recalibrate(end_date, my_list, years=1):
    
    if end_date >= datetime.strptime('01/01/2020', '%d/%m/%Y').date():
        print(f"Starting to recalibrate {my_list} for {years} year(s) to {end_date} at: {datetime.now(sydney_tz)}")

        list = my_list
        if list:
            # recalibrate each list
            print(list)
            # get athlete_list, average, SD for athletes with WRE points in list in years to end_date
            wre_athlete_list, wre_mp, wre_sp = load_wre_scores(mylist=list, start_date=end_date - timedelta(days=365*years), end_date=end_date)
            #print(f"athlete_list: {wre_athlete_list}")
            #print(f"wre_mp: {wre_mp}")
            #print(f"wre_sp: {wre_sp}")

            # get athlete_list, average, SD for all athletes with AUS points in list in years to end_date
            aus_mp, aus_sp = load_aus_scores(mylist=list, start_date=end_date - timedelta(days=365*years), end_date=end_date)
            #print(f"aus_mp: {aus_mp}")
            #print(f"aus_sp: {aus_sp}")


            if wre_mp and wre_sp and aus_mp and aus_sp:
                # apply recalibration to AUS results for this list and year
                # new score = (original - aus_mp)/aus_sp * wre_sp + wre_mp
                recalibrate_aus_scores(mylist=list, start_date_dt=end_date - timedelta(days=365*years), end_date_dt=end_date, wre_mp=wre_mp, wre_sp=wre_sp, aus_mp=aus_mp, aus_sp=aus_sp)
            else:
                print("not enough data to recalibrate")

            # re-check the new aus_mp and aus_sp
            # get athlete_list, average, SD for all athletes with AUS points in list in year
            aus_mp, aus_sp = load_aus_scores(mylist=list, start_date=end_date - timedelta(days=365*years), end_date=end_date)
            #print(f"calibrated aus_mp: {aus_mp}")
            #print(f"calibrated aus_sp: {aus_sp}")

        data = {}
        data['full_name'] = "recalibration done"
    else:
        # end_date is in the past prior to 2020
        print(f"End date {end_date} is in the past. No further calibration needed.")
        print(f"Calibrate {my_list} against avg and sd from 2018 & 2024.")

        list = my_list
        if list:
            # recalibrate each list
            print(list)
            # get average, SD for athletes with AUS points in AUS races list between 2018 & 2024
            aus_mp_base, aus_sp_base = load_aus_scores_aus(mylist=list, start_date=datetime.strptime('01/01/2018', '%d/%m/%Y').date(), end_date=datetime.strptime('31/12/2024', '%d/%m/%Y').date())
            print(f"aus_mp_base: {aus_mp_base}")
            print(f"aus_sp_base: {aus_sp_base}")
            if list in ['junior men','junior women']:
                if aus_mp_base > 150:
                    aus_mp_base = 150
                    print(f"aus_mp_base capped at 150")
            else:
                if aus_sp_base > 200:
                    aus_sp_base = 200
                    print(f"aus_sp_base capped at 200") 
            # get average, SD for all athletes with AUS points in AUS races in list in year to end_date
            aus_mp, aus_sp = load_aus_scores_aus(mylist=list, start_date=end_date - timedelta(days=365*years), end_date=end_date)
            print(f"aus_mp: {aus_mp}")
            print(f"aus_sp: {aus_sp}")

            if aus_mp_base and aus_sp_base and aus_mp and aus_sp:
                # apply recalibration to AUS results for this list and year
                # new score = (original - aus_mp)/aus_sp * wre_sp + wre_mp
                recalibrate_aus_scores(mylist=list, start_date_dt=end_date - timedelta(days=365*years), end_date_dt=end_date, wre_mp=aus_mp_base, wre_sp=aus_sp_base, aus_mp=aus_mp, aus_sp=aus_sp)
                #print("recalibrate_aus_scores not implemented")
            else:
                print("not enough data to recalibrate")

            # re-check the new aus_mp and aus_sp
            # get athlete_list, average, SD for all athletes with AUS points in list in year
            aus_mp, aus_sp = load_aus_scores_aus(mylist=list, start_date=end_date - timedelta(days=365*years), end_date=end_date)
            print(f"calibrated aus_mp: {aus_mp}")
            print(f"calibrated aus_sp: {aus_sp}")

        data = {}
        data['full_name'] = "recalibration done"

    print(f"Finished recalibrating {my_list} for {years} year(s) at: {datetime.now(sydney_tz)}")
    return data
