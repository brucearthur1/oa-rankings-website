import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv 
import os 
from database import test_race_exist


def filter_api_event(event):
    include_event = False
    if 'relay' not in event['long_desc'].lower() and \
        ('school' not in event['long_desc'].lower() or event['event_classification'] == 'nat' ) and \
        (event['event_classification'] == 'champs' or event['event_classification'] == 'nat' or \
         event['event_classification'] == 'int' or \
         (event['event_classification'] == 'sta' and 'champ' in event['long_desc'].lower())) :
        include_event = True
    return include_event



def filter_classes(my_classes):
    # my_classes is a list of my_class dictionaries
    # Filter out classes that are not relevant
    filtered_classes = []
    for my_class in my_classes:
        if any(keyword in my_class['class_name'].lower() for keyword in ["men", "women", "elite", "21e", "20e", "21a", "20a", "18a", "sport", "sb", "sg"]) and \
            all(substring not in my_class['class_name'].lower() for substring in ["21as", "20as"]):
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
                        class_name = event_class.find("Name").text if event_class.find("Name") is not None else None
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