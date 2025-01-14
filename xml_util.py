import xml.etree.ElementTree as ET

def load_athletes_from_xml():
    # Parse the XML file
    tree = ET.parse('xml/competitors.xml')
    root = tree.getroot()

    # Define the namespace dictionary 
    namespaces = {'ns': 'http://www.orienteering.org/datastandard/3.0'}
    
    # Extract data from the XML
    athletes = []
    for competitor in root.findall('ns:Competitor', namespaces):
        person = competitor.find('ns:Person', namespaces)

        # Extract fields from Person
        eventor_id = person.find('ns:Id', namespaces)
        eventor_id = eventor_id.text if eventor_id is not None else None

        sex = person.get('sex')

        family = person.find('.//ns:Family', namespaces)
        family = family.text if family is not None else None

        given = person.find('.//ns:Given', namespaces)
        given = given.text if given is not None else None

        athlete = given + " " + family

        birthdate = person.find('ns:BirthDate', namespaces)
        birthdate = birthdate.text if birthdate is not None else None

        nationality = person.find('.//ns:Nationality', namespaces)
        nationality_code = nationality.get('code') if nationality is not None else None

        # Extract Organisation Id 
        organisation = competitor.find('ns:Organisation', namespaces) 
        if organisation is not None:
            organisation_id = organisation.find('ns:Id', namespaces) 
            organisation_id = organisation_id.text if organisation_id is not None else None 
        else: 
            organisation_id = None

        #                  eventor_id, athlete, given, family, gender, yob, nationality_code, club_id
        athletes.append((eventor_id, athlete, given, family, sex, birthdate[0:4], nationality_code, organisation_id))

    return athletes


def load_clubs_from_xml():
    # Parse the XML file
    tree = ET.parse('xml/organisations.xml')
    root = tree.getroot()

    # Define the namespace dictionary 
    namespaces = {'ns': 'http://www.orienteering.org/datastandard/3.0'}
    
    # Extract data from the XML
    clubs = []
    for club in root.findall('ns:Organisation', namespaces):
        club_type = club.get('type')
        id = club.find('ns:Id', namespaces).text
        name = club.find('ns:Name', namespaces).text
        short_name = club.find('ns:ShortName', namespaces).text
        country = club.find('ns:Country', namespaces).text

        # Apply additional logic for setting state 
        state = None 
        if country == 'Australia' and club_type == 'Club':
            if len(short_name) >= 4:
                if short_name[3] == 'V':
                    state = 'VIC' 
                elif short_name[3] == 'N':
                    state = 'NSW' 
                elif short_name[3] == 'A':
                    state = 'ACT'
                if short_name[3] == 'Q':
                    state = 'QLD' 
                elif short_name[3] == 'S':
                    state = 'SA' 
                elif short_name[3] == 'W':
                    state = 'WA'
                elif short_name[3] == 'T':
                    state = 'TAS'

        clubs.append((club_type, id, name, short_name, state, country))

    return clubs


