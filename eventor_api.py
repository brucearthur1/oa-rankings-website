import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv 
import os 
from database import test_race_exist, store_events, store_race_tmp, confirm_discipline
from eventor import deduct_list_name_from_class_name
from rankings import calculate_race_rankings
import xml.etree.ElementTree as ET


def filter_api_event(event):
    include_event = False
    if 'relay' not in event['long_desc'].lower() and \
        ('school' not in event['long_desc'].lower() or event['event_classification'] == 'nat' ) and \
        (event['event_classification'] == 'champs' or event['event_classification'] == 'nat' or \
         event['event_classification'] == 'int' or \
#         event['event_classification'] == 'loc' or \
         (event['event_classification'] == 'sta' and 'nol' in event['long_desc'].lower()) or \
         (event['event_classification'] == 'sta' and 'national' in event['long_desc'].lower()) or \
         (event['event_classification'] == 'sta' and 'champ' in event['long_desc'].lower())) :
        include_event = True
    return include_event



def filter_classes(my_classes):
    # my_classes is a list of my_class dictionaries
    # Filter out classes that are not relevant
    filtered_classes = []
    for my_class in my_classes:
        if any(keyword in my_class['class_name'].lower() for keyword in ["men", "women", "elite", "21e", "20e", "21a", "20a", "18a", "sport", "sb", "sg"]) and \
            all(substring not in my_class['class_name'].lower() for substring in ["21as", "20as"]) :
            filtered_classes.append(my_class)
    return filtered_classes




def call_eventor_api(url):
    load_dotenv() 
    try:
        OAOrgId1Key = os.getenv('OAOrgId1Key')
        OVkey = os.getenv('OVkey')
        headers = {'ApiKey': OAOrgId1Key}
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        try:
            import xml.etree.ElementTree as ET
            data = ET.fromstring(response.content)
            data = ET.tostring(data, encoding='unicode')
        except ET.ParseError:
            data = response.text
        
        import xml.dom.minidom
        dom = xml.dom.minidom.parseString(data)
        pretty_xml_as_string = dom.toprettyxml()
        print(pretty_xml_as_string)
        
        return data
    
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")





def api_events_from_eventor(end_date_str, days_prior):
    print("Started api_events_from_eventor:", datetime.now())

    new_events = []

    # get the event page
    #events_url = f"https://eventor.orienteering.asn.au/Events?competitionTypes=level1%2Clevel2%2Clevel3&classifications=International%2CNational%2CChampionship%2CRegional%2CLocal&disciplines=Foot&startDate=%7B+start_date+%7D&endDate=%7B+end_date+%7D&map=false&mode=List&showMyEvents=false&cancelled=false&isExpanded=true"

    #api_url = "https://eventor.orienteering.asn.au/api/events?fromDate=2014-04-01&toDate=2014-04-30"  # Replace with your API URL
    #api_url = "https://eventor.orienteering.asn.au/api/results/event?eventId=21784"  # Replace with your API URL
    #api_url = "https://eventor.orienteering.asn.au/api/organisation/1"  # 9 = OV,  70 = MFR, 2 = OA, 1 = IOF
    #api_url = "https://eventor.orienteering.asn.au/api/organisation/apiKey"   # works for OV key but not OA key
    #An error occurred: 403 Client Error: Forbidden for url: https://eventor.orienteering.asn.au/api/persons/organisations/2
    #api_url = "https://eventor.orienteering.asn.au/api/persons/organisations/9"  # 9 = OV  works for OV key but not OA key
    #api_url = "https://eventor.orienteering.asn.au/api/memberships?organisationId=12&year=2025&includeContactDetails=true"  #forbidden for OA key
    #api_url = "https://eventor.orienteering.org/api/results/event?eventId=8395" #IOF
    #api_url = f"https://eventor.orienteering.asn.au/api/events?fromDate={start_date_str}&toDate={end_date_str}&classificationIds={classificationIds}&includeAttributes=true"


    # Define the start date for scraping
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")  # Convert end_date to datetime
    start_date = end_date - timedelta(days=days_prior)
    start_date_str = start_date.strftime("%Y-%m-%d")  # Convert start_date back to string
    classificationIds = "1,2,3,6" # Comma-separated list of event classification IDs, where 1=championship event, 2=national event, 3=state event, 4=local event, 5=club event, 6=international event. Omit to include all events.

    api_url = f"https://eventor.orienteering.asn.au/api/events?fromDate={start_date_str}&toDate={end_date_str}&classificationIds={classificationIds}" 
    xml_data = call_eventor_api(api_url)

    import xml.etree.ElementTree as ET

    # Parse the XML data
    root = ET.fromstring(xml_data)

    # Find all <Event> elements within <EventList>
    for event_xml in root.findall("./Event"):
        discipline_id = event_xml.find("DisciplineId")
        if discipline_id is not None and discipline_id.text == "1":
            event_id = event_xml.find("EventId").text if event_xml.find("EventId") is not None else None
            event_name = event_xml.find("Name").text if event_xml.find("Name") is not None else None
            classification_id = event_xml.find("EventClassificationId").text if event_xml.find("EventClassificationId") is not None else None
            if classification_id == "1":
                event_classification = "champs"
            elif classification_id == "2":
                event_classification = "nat"
            elif classification_id == "3":
                event_classification = "sta"
            elif classification_id == "4":
                event_classification = "loc"
            elif classification_id == "0":
                event_classification = "int"
            else:
                event_classification = "unknown"

            event_date = event_xml.find("StartDate/Date").text if event_xml.find("StartDate/Date") is not None else None

            event_dict = {
                "event_code": event_id,
                "event_date": event_date,
                "long_desc": event_name,
                "event_classification": event_classification
            }

            include_event = filter_api_event(event_dict)
            if include_event:
                #new_events.append(race)

                new_races = []
                for race in event_xml.findall("./EventRace"):
                    race_distance = race.attrib.get("raceDistance", "Unknown")
                    race_id = race.find("EventRaceId").text if race.find("EventRaceId") is not None else None
                    race_date = race.find("RaceDate/Date").text if race.find("RaceDate/Date") is not None else None
                    race_name = race.find("Name").text if race.find("Name") is not None else ""

                    # Check if results exist
                    race_results_exist = False
                    for key in event_xml.findall(".//Key"):
                        if key.text and key.text.startswith(f"officialResult_{race_id}"):
                            race_results_exist = True
                            break
                    if race_results_exist:
                        # don't know the class_id yet, so use CLASS_ID as a placeholder
                        results_href = f"/Events/ResultList?eventId={event_id}&eventClassId=CLASS_ID&eventRaceId={race_id}&overallResults=False"
                        # Add the event details to the new_events list
                        race = {
                            "race_distance": race_distance,
                            "race_id": race_id,
                            "race_date": race_date,
                            "stage_name": race_name, 
                            "results_href": results_href
                        }
                        new_races.append(race)
                    else:
                        results_href = None
                        break
                
                if len(new_races) > 0:
                    event_dict["races"] = new_races

                    # try to find the classes for this event
                    api_url = f"https://eventor.orienteering.asn.au/api/eventclasses?eventId={event_id}"
                    xml_data = call_eventor_api(api_url)
                    
                    # Parse the XML data
                    class_root = ET.fromstring(xml_data)
                    classes = []
                    for event_class in class_root.findall("./EventClass"):
                        class_id = event_class.find("EventClassId").text if event_class.find("EventClassId") is not None else None
                        class_name = event_class.find("ClassShortName").text if event_class.find("ClassShortName") is not None else None
                        if class_id and class_name:
                            classes.append({"class_id": class_id, "class_name": class_name})
                    # filter the classes
                    filtered_classes = filter_classes(classes)  
                    #print(f"{filtered_classes=}")

                    event_dict["classes"] = filtered_classes

                    new_events.append(event_dict)


    #print(f"{new_events=}")
    print("Finished api_events_from_eventor:", datetime.now())   

    classes_ready_for_processing = []
    for event in new_events:
        for race in event["races"]:
            for my_class in event["classes"]:
                #print(f"{my_class=}")
                #

                race_code = "au" + event['event_code'].lower() + my_class['class_name'].lower().replace(" ", "") + race['race_id'].lower()
                # check to see if race has already been uploaded

                race_exists = test_race_exist(race_code)
                #race_exists = False

                results_link = race['results_href'].replace("CLASS_ID", my_class['class_id'])
                if race['stage_name'] is not None:
                    long_desc = event['long_desc'] + " " + race['stage_name']
                else:
                    long_desc = event['long_desc']

                new_race = {
                    'event_date': race['race_date'],
                    'long_desc': long_desc,
                    'short_desc': event['event_code'],   
                    'results_href': results_link,            
                    #'event_discipline': event['event_discipline'],
                    'event_classification': event['event_classification'],
                    #'event_format': event['event_format'],
                    'event_distance': race['race_distance'],
                    'event_class': my_class['class_name'].replace(" ", ""),
                    'event_exists': race_exists,
                    'stage_name': race['stage_name'],
                    'eventClassId': my_class['class_id'],
                    'eventRaceId': race['race_id']
                }
                if new_race:
                    classes_ready_for_processing.append(new_race)

    return classes_ready_for_processing



def load_race_from_eventor_api_by_ids(eventId, eventClassId, eventRaceId):
    print(f"starting load_from_eventor_api_by_ids")
    new_results = []
    new_events = []

    # Call the Eventor API to get the event details
    api_url = f"https://eventor.orienteering.asn.au/api/event/{eventId}"
    root = call_eventor_api(api_url)

    event_code = eventId
    # Parse the XML data
    root = ET.fromstring(root)  # Parse the string into an XML element

    event_name_element = root.find("Name")
    if event_name_element is not None:
        event_name = event_name_element.text
    start_date_element = root.find("StartDate/Date")
    if start_date_element is not None:
        event_date_str = start_date_element.text
    
    for race in root.findall("EventRace"):
        if race.find("EventRaceId") is not None and race.find("EventRaceId").text == eventRaceId:
            race_date_element = race.find("RaceDate/Date")
            if race_date_element is not None:
                race_date_str = race_date_element.text
            race_name_element = race.find("Name")
            if race_name_element is not None:
                race_name = race_name_element.text
            break
    if race_name is not None:
        full_name = event_name + " " + race_name
    else:
        full_name = event_name

    # get the class name that matches eventClassId for this event
    my_class = None
    api_url = f"https://eventor.orienteering.asn.au/api/eventclasses?eventId={eventId}"
    class_root = call_eventor_api(api_url)
    class_root = ET.fromstring(class_root)  # Parse the string into an XML element

    for event_class in class_root.findall("./EventClass"):
        class_id = event_class.find("EventClassId").text if event_class.find("EventClassId") is not None else None
        if class_id == eventClassId:
            my_class = event_class.find("Name").text if event_class.find("Name") is not None else None
            break

    my_list_name = deduct_list_name_from_class_name(my_class)
    my_class_no_space = my_class.replace(" ", "")

    # Convert event_date_str to "YYYY-MM-DD" format
    race_date = datetime.strptime(race_date_str, '%Y-%m-%d').strftime('%d/%m/%Y')
    new_event = {
        'date': race_date,
        'short_desc': "au" + event_code.lower() + my_class_no_space.lower() + eventRaceId.lower(),
        'long_desc': full_name,
        'class': my_class,
        'short_file': "au" + event_code.lower() + my_class_no_space.lower(),
        'ip': 1,
        'list': my_list_name,
        'eventor_id': event_code,
        'iof_id': None,
        'discipline': 'Middle/Long'  #can get this from eventor
    }
    new_events.append(new_event)


    # get results for the specified class
    api_url = f"https://eventor.orienteering.asn.au/api/results/event?eventId={eventId}"
    result_root = call_eventor_api(api_url)
    result_root = ET.fromstring(result_root)  # Parse the string into an XML element

    # Parse the XML data
    for class_result in result_root.findall("./ClassResult"):
        class_id = class_result.find("EventClass/EventClassId").text if class_result.find("EventClass/EventClassId") is not None else None
        if class_id == eventClassId:
            for person_result in class_result.findall("./PersonResult"):
                person = person_result.find("Person")
                if person is not None:
                    athlete_name = person.find("PersonName/Given").text if person.find("PersonName/Given") is not None else ""
                    athlete_name = (athlete_name or "") + " " + person.find("PersonName/Family").text if person.find("PersonName/Family") is not None else ""

                    organisation = person_result.find("Organisation")
                    club = organisation.find("ShortName").text if organisation is not None and organisation.find("ShortName") is not None else ""

                    for race_result in person_result.findall("RaceResult"):
                        race_result_id = race_result.find("EventRaceId").text if race_result.find("EventRaceId") is not None else None
                        if race_result_id == eventRaceId:
                            result = race_result.find("Result")
                            if result is not None:
                                competitor_status = result.find("CompetitorStatus").attrib.get("value", None)
                                if competitor_status == "OK":
                                    race_time = result.find("Time").text if result.find("Time") is not None else None
                                    if race_time and ":" in race_time and race_time.count(":") == 1:
                                        race_time = "0:" + race_time
                                elif competitor_status == "DidNotStart":
                                    break
                                else:
                                    race_time = competitor_status
                                race_place = result.find("ResultPosition").text if result.find("ResultPosition") is not None else None

                                my_class = my_class.replace(" ", "")
                                new_result = {
                                    'race_code': "au" + eventId.lower() + my_class.lower() + eventRaceId.lower(),
                                    'place': race_place,
                                    'athlete_name': athlete_name,
                                    'club': club,
                                    'race_time': race_time,
                                    'race_points': 0
                                }
                                new_results.append(new_result)
                            break

    print(f"{new_results=}")
    return new_events, new_results


#########################
# under construction
#########################
def api_events_from_eventor_and_calculate_rankings(end_date_str, days_prior):
    print("Started api_events_from_eventor_and_calculate_rankings:", datetime.now())

    new_events = []

    # Define the start date for scraping
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")  # Convert end_date to datetime
    start_date = end_date - timedelta(days=days_prior)
    start_date_str = start_date.strftime("%Y-%m-%d")  # Convert start_date back to string
    classificationIds = "1,2,3,6" # Comma-separated list of event classification IDs, where 1=championship event, 2=national event, 3=state event, 4=local event, 5=club event, 6=international event. Omit to include all events.

    api_url = f"https://eventor.orienteering.asn.au/api/events?fromDate={start_date_str}&toDate={end_date_str}&classificationIds={classificationIds}" 
    xml_data = call_eventor_api(api_url)

    # Parse the XML data
    root = ET.fromstring(xml_data)

    # Find all <Event> elements within <EventList>
    for event_xml in root.findall("./Event"):
        discipline_id = event_xml.find("DisciplineId")
        if discipline_id is not None and discipline_id.text == "1":
            event_id = event_xml.find("EventId").text if event_xml.find("EventId") is not None else None
            event_name = event_xml.find("Name").text if event_xml.find("Name") is not None else None
            classification_id = event_xml.find("EventClassificationId").text if event_xml.find("EventClassificationId") is not None else None
            if classification_id == "1":
                event_classification = "champs"
            elif classification_id == "2":
                event_classification = "nat"
            elif classification_id == "3":
                event_classification = "sta"
            elif classification_id == "4":
                event_classification = "loc"
            elif classification_id == "0":
                event_classification = "int"
            else:
                event_classification = "unknown"

            event_date = event_xml.find("StartDate/Date").text if event_xml.find("StartDate/Date") is not None else None

            event_dict = {
                "event_code": event_id,
                "event_date": event_date,
                "long_desc": event_name,
                "event_classification": event_classification
            }

            include_event = filter_api_event(event_dict)
            if include_event:
                # find any eligible classes for this event

                my_classes = []
                api_url = f"https://eventor.orienteering.asn.au/api/eventclasses?eventId={event_id}"
                class_root = call_eventor_api(api_url)
                class_root = ET.fromstring(class_root)  # Parse the string into an XML element

                for event_class in class_root.findall("./EventClass"):
                    class_id = event_class.find("EventClassId").text if event_class.find("EventClassId") is not None else None
                    class_name = event_class.find("ClassShortName").text if event_class.find("ClassShortName") is not None else None
                    if class_id and class_name:
                        class_name = class_name.replace(" ", "")
                        my_classes.append({"class_id": class_id, "class_name": class_name})
                # filter the classes
                filtered_classes = filter_classes(my_classes)

                if len(filtered_classes) > 0:
                    # the event contains some ranking classes
                    event_dict["classes"] = filtered_classes

                    new_races = []
                    for race in event_xml.findall("./EventRace"):
                        race_distance = race.attrib.get("raceDistance", "Unknown")
                        race_id = race.find("EventRaceId").text if race.find("EventRaceId") is not None else None
                        race_date = race.find("RaceDate/Date").text if race.find("RaceDate/Date") is not None else None
                        race_name = race.find("Name").text if race.find("Name") is not None else ""

                        # Check if results exist
                        race_results_exist = False
                        for key in event_xml.findall(".//Key"):
                            if key.text and key.text.startswith(f"officialResult_{race_id}"):
                                race_results_exist = True
                                break
                        if race_results_exist:

                            # check if this event/race/class has already been processed
                            for my_class in event_dict["classes"]:
                                race_code = "au" + event_dict['event_code'].lower() + my_class['class_name'].lower().replace(" ", "") + race_id.lower()
                                # check to see if race has already been uploaded

                                results_link = f"/Events/ResultList?eventId={event_id}&eventClassId={my_class['class_id']}&eventRaceId={race_id}&overallResults=False"
                                if race_name is not None:
                                    long_desc = event_dict['long_desc'] + " " + race_name
                                else:
                                    long_desc = event_dict['long_desc']

                                race_exists = test_race_exist(race_code)
                                if race_exists == False:
                                    # process rankings for this class/race

                                    my_list_name = deduct_list_name_from_class_name(my_class['class_name'])

                                    # Add the event details to the new_events list
                                    race = {
                                        "race_code": race_code,
                                        "race_distance": race_distance,
                                        "race_id": race_id,
                                        "class_id": my_class['class_id'],
                                        "class_name": my_class['class_name'],
                                        "list": my_list_name,
                                        "race_date": race_date,
                                        "stage_name": long_desc, 
                                        "results_href": results_link
                                    }
                                    new_races.append(race)
                    
                    if len(new_races) > 0:
                        event_dict["races"] = new_races

                        # get results for event in one API call
                        api_url = f"https://eventor.orienteering.asn.au/api/results/event?eventId={event_id}"
                        result_root = call_eventor_api(api_url)
                        result_root = ET.fromstring(result_root)
                        for race in event_dict['races']:
                            new_results = []
                            for class_result in result_root.findall("./ClassResult"):
                                class_id = class_result.find("EventClass/EventClassId").text if class_result.find("EventClass/EventClassId") is not None else None
                                if class_id == race['class_id']:
                                    for person_result in class_result.findall("./PersonResult"):
                                        person = person_result.find("Person")
                                        if person is not None:
                                            athlete_name = person.find("PersonName/Given").text if person.find("PersonName/Given") is not None else ""
                                            athlete_name = (athlete_name or "") + " " + person.find("PersonName/Family").text if person.find("PersonName/Family") is not None else ""

                                            organisation = person_result.find("Organisation")
                                            club = organisation.find("ShortName").text if organisation is not None and organisation.find("ShortName") is not None else ""

                                            # find the results in a multi-race event
                                            for race_result in person_result.findall("RaceResult"):
                                                race_result_id = race_result.find("EventRaceId").text if race_result.find("EventRaceId") is not None else None
                                                if race_result_id == race['race_id']:
                                                    result = race_result.find("Result")
                                                    if result is not None:
                                                        competitor_status = result.find("CompetitorStatus").attrib.get("value", None)
                                                        if competitor_status == "OK":
                                                            race_time = result.find("Time").text if result.find("Time") is not None else None
                                                            if race_time and "." in race_time:
                                                                race_time = race_time.split(".")[0]
                                                            if race_time and ":" in race_time and race_time.count(":") == 1:
                                                                minutes, seconds = race_time.split(":")
                                                                hours = int(minutes) // 60
                                                                minutes = int(minutes) % 60
                                                                race_time = f"{hours}:{minutes:02}:{seconds}"
                                                        elif competitor_status == "DidNotStart":
                                                            break
                                                        else:
                                                            race_time = competitor_status
                                                        race_place = result.find("ResultPosition").text if result.find("ResultPosition") is not None else None
                                                        class_name_no_spaces = race['class_name'].replace(" ", "")

                                                        new_result = {
                                                            'race_code': "au" + event_id.lower() + class_name_no_spaces.lower() + race['race_id'].lower(),
                                                            'place': race_place,
                                                            'athlete_name': athlete_name,
                                                            'club': club,
                                                            'race_time': race_time,
                                                            'race_points': 0
                                                        }
                                                        print(new_result)  # Debugging output
                                                        new_results.append(new_result)
                                                    break
                                            # find the results in a single race event
                                            result = person_result.find("Result")
                                            if result is not None:
                                                competitor_status = result.find("CompetitorStatus").attrib.get("value", None)
                                                if competitor_status == "OK":
                                                    race_time = result.find("Time").text if result.find("Time") is not None else None
                                                    if race_time and "." in race_time:
                                                        race_time = race_time.split(".")[0]
                                                    if race_time and ":" in race_time and race_time.count(":") == 1:
                                                        minutes, seconds = race_time.split(":")
                                                        hours = int(minutes) // 60
                                                        minutes = int(minutes) % 60
                                                        race_time = f"{hours}:{minutes:02}:{seconds}"
                                                elif competitor_status == "DidNotStart":
                                                    break
                                                else:
                                                    race_time = competitor_status
                                                race_place = result.find("ResultPosition").text if result.find("ResultPosition") is not None else None
                                                class_name_no_spaces = race['class_name'].replace(" ", "")

                                                new_result = {
                                                    'race_code': "au" + event_id.lower() + class_name_no_spaces.lower() + race['race_id'].lower(),
                                                    'place': race_place,
                                                    'athlete_name': athlete_name,
                                                    'club': club,
                                                    'race_time': race_time,
                                                    'race_points': 0
                                                }
                                                print(new_result)  # Debugging output
                                                new_results.append(new_result)
                                        

                            race['results'] = new_results            

                    new_events.append(event_dict)
                # completed data sourcing for this event

    pre_data_to_insert = []

    if new_events:  # Only proceed if new_events is not empty
        for event in new_events:
            print(f"store event: {event}")
            print(f"event_date: {event['event_date']}")
            # Convert event_date format if necessary
            if 'event_date' in event and isinstance(event['event_date'], str):
                try:
                    event_date = datetime.strptime(event['event_date'], '%d/%m/%Y')
                    event['event_date'] = event_date.strftime('%Y-%m-%d')
                except ValueError:
                    pass
            print(f"reformatted date: {event['event_date']}")
            if event.get('races'):  # Only proceed if event['races'] exists and is not empty
                for race in event['races']:
                    if race.get('results'):  # Check if there are any results for the race
                        
                        # store the race in the DB
                        race_to_insert = {
                            'date': race['race_date'],
                            'short_desc': race['race_code'],
                            'long_desc': race['stage_name'],
                            'class': race['class_name'],
                            'short_file': race['race_code'],
                            'ip': 1,
                            'list': race['list'],
                            'eventor_id': event['event_code'],
                            'iof_id': None,
                            'discipline': 'Middle/Long'
                        }
                        row = tuple(race_to_insert.values())
                        pre_data_to_insert.append(row)

        if pre_data_to_insert:
            store_events(pre_data_to_insert)

        # Store results in race_tmp in the DB
        for event in new_events:
            if event.get('races'):  # Check if there are any races in the event
                for race in event['races']:
                    if race.get('results'):  # Check if there are any results for the race
                        for result in race['results']:
                            try:
                                result['place'] = int(result['place'])
                            except (ValueError, TypeError):
                                result['place'] = 0
                        # Prepare results for insertion
                        data_to_insert = [{k: v for k, v in result.items() if k not in ['race_code', 'club']} for result in race['results']]
                        # Convert MM:SS to 00:MM:SS
                        for result in data_to_insert:
                            if isinstance(result['race_time'], str) and result['race_time'].startswith('-'):
                                result['race_time'] = "no time"
                                result['place'] = 0
                            if isinstance(result['race_time'], str) and ':' in result['race_time']:
                                parts = result['race_time'].split(':')
                                if len(parts) == 2:
                                    result['race_time'] = f"00:{result['race_time']}"
                        data_to_insert = [tuple(result.values()) for result in data_to_insert]
                        print(f"data_to_insert: {data_to_insert}")

                        store_race_tmp(race['race_code'], data_to_insert)

                        print(f"preparing to calculate")
                        print(race['race_code'])
                        calculate_race_rankings(race['race_code'])

                        my_year = datetime.strptime(race['race_date'], '%Y-%m-%d').year
                        if my_year:
                            print(my_year)
                            # Remember to review Discipline (discipline = 'Middle/Long' by default)
                            confirm_discipline(int(my_year))

    print("Finished process_and_store_eventor_event_by_class:", datetime.now())
    return new_events
