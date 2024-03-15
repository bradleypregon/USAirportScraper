from bs4 import BeautifulSoup
import requests
import pandas as pd
import re
import json

wiki_site = "https://en.wikipedia.org"
wikiPage = "https://en.wikipedia.org/wiki/List_of_airports_in_the_United_States"

def make_soup(link):
    get_page = requests.get(link)
    html = get_page.content
    soup = BeautifulSoup(html, 'html.parser')
    return soup

def get_airports_table(soup):
    results = soup.find('table', attrs={'class': 'wikitable'})
    return results

def dms_to_dd(d, m, s, direction):
    dd = int(d) + float(m)/60 + float(s)/3600
    dd = round(dd, 5)
    if direction == "W":
        return -dd
    return dd
                    
def process_airport_name(airport_name):
    # substrings
    # (secondary airport name)
    # (also see [other airport])
    # (was [former airport name])
    # (formerly public use)
    # (closed), (closed indefinitely), (closed year-range) 
    
    if "(was" in airport_name:
        split = airport_name.split('(was')
        split2 = split[1].split(')')
        return { 
            "name": split[0].rstrip(),
            "fka": split2[0].lstrip()
        }
        
    elif "(also see" in airport_name:
        split = airport_name.split('(also')
        return { 
            "name": split[0].rstrip()
        }
    elif " / " in airport_name and "(closed" not in airport_name:
        split = airport_name.split('/')
        return {
            "name": split[0].rstrip()
        }
    elif "(" in airport_name and "(closed" not in airport_name:
        split = airport_name.split('(')
        split2 = split[1].split(')')
        return { 
            "name": split[0].rstrip(),
            "aka": split2[0]
        }
    elif "[" in airport_name and "(closed" not in airport_name:
        split = airport_name.split('[')
        return { 
            "name": split[0].rstrip()
        }
    elif "(formerly" in airport_name:
        return False
    else:
        return {
            "name": airport_name.rstrip()
        }

def convert_SML(role, enplanements):
    # P-L - Commercial Large: > 1% of U.S. enplanements
    # P-M - Commercial Medium 0.25% < N < 1% of U.S. enplanements
    # P-S - Commercial Small 0.05% < N < 0.25% of U.S. enplanements
    
    # P-N - Commercial Nonhub < 0.05% of U.S. enplanements, but > 10,000
    # CS - Commercial Service Nonprimary, at least 2,500 boardings
    # R - Reliever, relieve congestion at large commercial airports
    # GA - General Aviation
    
    # Large: P-L, P-M, P-S
    # Medium: P-N, CS
    # Small: R, GA
    # If R or GA has > 5,000, make it medium
    
    # check if role exists or if enplanements is 0
    if (role == "") or (enplanements == 0):
        return "Small"

    if role in ("P-L", "P-M"):
        return "Large"
    elif role in ("P-S"):
        return "Medium"
    elif role in ("P-N", "CS"):
        return "Medium"
    elif role in ("R", "GA"):
        return "Small"
    elif (role in ("R", "GA")) and (enplanements > 5,000):
        return "Medium"
    else:
        return "Small"

def scrape_airports(airports):
    # City Served, FAA, IATA, ICAO, Airport Name, Role, Enplanements
    tr_elements = airports.find_all('tr')
    airportList = []
    state = ""
    city = ""
    
    df = pd.DataFrame()

    for tr in tr_elements:
        if tr.find('td') and tr.find('a'):
            line_items = tr.find_all('td')

            if tr.find('td').find('a', {'class': 'new'}):
                continue
            if "closed" in line_items[4].text.strip().lower():
                continue

            try:
                airport_url = line_items[4].find('a')['href']
            except:
                continue

            airport_wiki_url = wiki_site + airport_url
            airport_wiki_soup = make_soup(airport_wiki_url)

            try:
                coords = get_coordinates(airport_wiki_soup)
            except:
                continue

            try:
                enplanements = line_items[6].text.strip() 
            except:
                enplanements = 0
            
            try:
                role = line_items[5].text.strip()
            except:
                role = ""
            size = convert_SML(role, enplanements)

            processed_airport_name = process_airport_name(line_items[4].text.strip())
            if processed_airport_name == False:
                continue
            
            # format as geojson
            airport = { 
                "coordinates": { 
                    "lat": coords[0],
                    "long": coords[1]
                },
                "properties": {
                    "airportName": processed_airport_name,
                    "cityServed": line_items[0].find('a').get('title'),
                    "faa": line_items[1].text.strip(),
                    "iata": line_items[2].text.strip(),
                    "icao": line_items[3].text.strip(),
                    "size": size,
                }
            }
            print(airport['properties']['airportName']['name'])
            airportList.append(airport)

    return airportList

def get_coordinates(soup):
    #soup = make_soup(url)
    # <span class="latitude">33º33'50"N</span>
    # <span class="longitude">086º45'08"W</span>
    rawLat = soup.find("span", {"class": "latitude"})
    rawLong = soup.find("span", {"class": "longitude"})
    # '33°33′50″N', '086°45′08″W'

    lat = rawLat.text.replace("′", "'").replace("″", "\"")
    lon = rawLong.text.replace("′", "'").replace("″", "\"")

    deg, minutes, seconds, direction = re.split('[°\'"]', lat)
    lat = dms_to_dd(deg, minutes, seconds, direction)
    
    deg, minutes, seconds, direction = re.split('[°\'"]', lon)
    lon = dms_to_dd(deg, minutes, seconds, direction)

    return ((lat, lon))

def extract_state(soup):
    spanElements = soup.find_all('span')
    for span in spanElements:
        if re.search(r"List of airports in \w+", span.text):
            return span.text.strip()
    return None

if __name__ == '__main__':
    print("---Running---")
    soup = make_soup(wikiPage)
    result = soup.find('table', attrs={'class': 'wikitable'})
    td_elements = result.find_all('td')

    accumulated_data = []

    for td in td_elements:
        if td.find('cite') and td.find('a'):
            
            a_tag = td.find('a')
            href = a_tag['href']
            page_url = wiki_site + href
            
            soup = make_soup(page_url)
            state = extract_state(soup)
            print("")
            print(state)
            print("")
            
            airports_table = get_airports_table(soup)
            scraped_airports = scrape_airports(airports_table)
            
            for apt in scraped_airports:
                accumulated_data.append(apt)
            #accumulated_data.append(scraped_airports)
            
    
    dump = json.dumps(accumulated_data)
    f = open("output.json", "w")
    f.write(dump)
    f.close()
