import requests
from bs4 import BeautifulSoup
import json
import duckdb
import re
import time
import os

def init_database():
    """Initialize the database with fresh tables"""
    # Start with a clean database file
    db_path = 'climbing.db'
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = duckdb.connect(db_path)
    
    # Create tables
    conn.execute('''
        CREATE TABLE IF NOT EXISTS climbing_areas (
            id INTEGER PRIMARY KEY,
            name VARCHAR,
            description TEXT,
            location VARCHAR,
            latitude DOUBLE,
            longitude DOUBLE,
            parent_id INTEGER,
            url VARCHAR
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS routes (
            id INTEGER PRIMARY KEY,
            name VARCHAR,
            grade VARCHAR,
            type VARCHAR,
            description TEXT,
            protection VARCHAR,
            location VARCHAR,
            latitude DOUBLE,
            longitude DOUBLE,
            area_id INTEGER,
            url VARCHAR,
            FOREIGN KEY (area_id) REFERENCES climbing_areas(id)
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS route_photos (
            id INTEGER PRIMARY KEY,
            route_id INTEGER,
            url VARCHAR,
            caption VARCHAR,
            FOREIGN KEY (route_id) REFERENCES routes(id)
        )
    ''')
    
    return conn

# Initialize database
conn = init_database()

# Global counters for IDs
area_id = 1
route_id = 1
photo_id = 1

def get_area_info(soup):
    """Extract area information from the soup object"""
    info = {
        'name': '',
        'description': '',
        'location': '',
        'latitude': None,
        'longitude': None
    }
    
    # Get name
    name_elem = soup.find('h1')
    if name_elem:
        info['name'] = name_elem.text.strip()
    
    # Get description
    description_elem = soup.find('div', class_='fr-view')
    if description_elem:
        info['description'] = description_elem.text.strip()
    
    # Get location
    location_elem = soup.find('div', class_='description-details')
    if location_elem:
        info['location'] = location_elem.text.strip()
    
    # Get coordinates
    map_div = soup.find('div', id='map-detail')
    if map_div:
        lat_match = re.search(r'lat\s*=\s*([\d.-]+)', str(map_div))
        lng_match = re.search(r'lng\s*=\s*([\d.-]+)', str(map_div))
        if lat_match and lng_match:
            info['latitude'] = float(lat_match.group(1))
            info['longitude'] = float(lng_match.group(1))
    
    # If still no coordinates, try the map div
    if info['latitude'] is None or info['longitude'] is None:
        map_div = soup.find('div', id='map')
        if map_div:
            # Look for data attributes
            lat_attr = map_div.get('data-lat')
            lng_attr = map_div.get('data-lng')
            if lat_attr and lng_attr:
                try:
                    info['latitude'] = float(lat_attr)
                    info['longitude'] = float(lng_attr)
                except ValueError:
                    pass
    
    # If still no coordinates, try the map URL
    if info['latitude'] is None or info['longitude'] is None:
        map_link = soup.find('a', href=re.compile(r'google.*maps'))
        if map_link:
            coords_match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', map_link['href'])
            if coords_match:
                try:
                    info['latitude'] = float(coords_match.group(1))
                    info['longitude'] = float(coords_match.group(2))
                except ValueError:
                    pass
    
    # Get area metadata
    area_type = ''
    elevation = ''
    season = ''
    approach_time = ''
    
    table = soup.find('table', class_='description-details')
    if table:
        rows = table.find_all('tr')
        for row in rows:
            label = row.find('td', class_='label')
            value = row.find('td', class_='text')
            if label and value:
                label_text = label.text.strip().lower()
                value_text = value.text.strip()
                if 'type' in label_text:
                    area_type = value_text
                elif 'elevation' in label_text:
                    elevation = value_text
                elif 'season' in label_text:
                    season = value_text
                elif 'approach' in label_text:
                    approach_time = value_text
    
    return {
        'description': description_text,
        'latitude': lat,
        'longitude': lng,
        'type': area_type,
        'elevation': elevation,
        'season': season,
        'approach_time': approach_time
    }

def get_route_info(soup, url=''):
    """Extract route information from the soup object. Returns None for bouldering routes."""
    route_info = {
        'name': '',
        'grade': '',
        'type': '',
        'height': '',
        'pitches': 0,
        'first_ascent': '',
        'description': '',
        'protection': '',
        'url': url,
        'latitude': None,
        'longitude': None,
        'photos': [],
        'location_description': ''
    }
    grade = ''
    route_type = ''
    height = ''
    pitches = 0
    first_ascent = ''
    description = ''
    protection = ''
    
    # Try to extract coordinates from the map
    scripts = soup.find_all('script')
    for script in scripts:
        if script.string and 'mapCenter' in script.string:
            # Look for mapCenter coordinates
            coords_match = re.search(r'mapCenter:\s*{\s*lat:\s*(-?\d+\.\d+),\s*lng:\s*(-?\d+\.\d+)\s*}', script.string)
            if coords_match:
                try:
                    route_info['latitude'] = float(coords_match.group(1))
                    route_info['longitude'] = float(coords_match.group(2))
                    break
                except ValueError:
                    pass
            
            # Look for marker coordinates
            marker_match = re.search(r'marker:\s*{\s*lat:\s*(-?\d+\.\d+),\s*lng:\s*(-?\d+\.\d+)\s*}', script.string)
            if marker_match:
                try:
                    route_info['latitude'] = float(marker_match.group(1))
                    route_info['longitude'] = float(marker_match.group(2))
                    break
                except ValueError:
                    pass

    # If still no coordinates, try the map div
    if route_info['latitude'] is None or route_info['longitude'] is None:
        map_div = soup.find('div', id='map')
        if map_div:
            lat_attr = map_div.get('data-lat')
            lng_attr = map_div.get('data-lng')
            if lat_attr and lng_attr:
                try:
                    route_info['latitude'] = float(lat_attr)
                    route_info['longitude'] = float(lng_attr)
                except ValueError:
                    pass
    
    # Get location description
    location_section = soup.find('div', class_='location')
    if location_section:
        route_info['location_description'] = location_section.text.strip()
    
    # Get photos
    photo_section = soup.find('div', class_='photos')
    if photo_section:
        photos = []
        for img in photo_section.find_all('img'):
            if img.get('src'):
                photo_url = img['src']
                # Convert to full resolution URL if needed
                if 'smallMed' in photo_url:
                    photo_url = photo_url.replace('smallMed', 'large')
                photo_caption = img.get('alt', '')
                photos.append({
                    'url': photo_url,
                    'caption': photo_caption
                })
        route_info['photos'] = photos
    map_div = soup.find('div', class_='map-wrapper')
    if map_div:
        map_iframe = map_div.find('iframe')
        if map_iframe and 'src' in map_iframe.attrs:
            src = map_iframe['src']
            # Extract coordinates from the iframe src
            import re
            coords = re.search(r'loc=([0-9.-]+),([0-9.-]+)', src)
            if coords:
                route_info['latitude'] = float(coords.group(1))
                route_info['longitude'] = float(coords.group(2))
    
    # Get route type first to filter out bouldering
    route_type_elem = soup.find('tr', {'th': lambda t: t and 'Type:' in t.text})
    if route_type_elem:
        route_type = route_type_elem.find('td').text.strip().lower()
        if 'boulder' in route_type:
            return None  # Skip bouldering routes
        route_info['type'] = route_type

    # Get route name
    name_elem = soup.find('h1')
    if name_elem:
        route_info['name'] = name_elem.text.strip()
        # Remove any edit links text
        if 'Suggest Change' in name:
            name = name.split('Suggest Change')[0].strip()
    
    # Get route grade
    grade_div = soup.find('div', class_='mr-2')
    if grade_div:
        grade_span = grade_div.find('span', class_='rateYDS')
        if grade_span:
            grade = grade_span.text.strip()
    
    # Get route metadata
    table = soup.find('table', class_='description-details')
    if table:
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 2:
                label_text = cells[0].text.strip().lower()
                value_text = cells[1].text.strip()
                if 'type:' in label_text:
                    route_type = value_text
                elif 'height:' in label_text:
                    height = value_text
                elif 'pitches:' in label_text:
                    try:
                        pitches = int(value_text)
                    except ValueError:
                        pass
                elif 'fa:' in label_text:
                    first_ascent = value_text
                elif 'protection:' in label_text:
                    protection = value_text
    
    # Get route description
    desc_div = soup.find('div', class_='description')
    if desc_div:
        description = desc_div.text.strip()
    
    # If we still don't have the grade, try to find it in the page title
    if not grade:
        title = soup.find('title')
        if title:
            title_text = title.text.strip()
            grade_match = re.search(r'V\d+|5\.\d+[+-]?\w*', title_text)
            if grade_match:
                grade = grade_match.group(0)
    
    # If we still don't have the type, try to determine it from the grade
    if not route_type:
        if grade and grade.startswith('V'):
            route_type = 'Boulder'
        elif grade and grade.startswith('5.'):
            route_type = 'Sport'
    
    return {
        'name': name,
        'grade': grade,
        'type': route_type,
        'height': height,
        'pitches': pitches,
        'first_ascent': first_ascent,
        'description': description,
        'protection': protection
    }

def scrape_mountain_project():
    """Main function to scrape Mountain Project"""
    global area_id, route_id, photo_id
    
    base_urls = [
        'https://www.mountainproject.com/area/105856477/marquette',
        'https://www.mountainproject.com/area/105856478/munising',
        'https://www.mountainproject.com/area/105856479/ishpeming'
    ]
    
    for url in base_urls:
        print(f"Processing {url}...")
        scrape_area(url)
    
    # Export the data to JSON for backup
    conn.execute("EXPORT DATABASE 'climbing.db'")
    
    print(f"\nScraping complete!")
    print(f"Processed {area_id-1} areas with {route_id-1} routes successfully")
    print("Data stored in climbing.db and exported to climbing_data.json")

def scrape_area(url, parent_id=None, depth=0, max_depth=2):
    """Scrape an area and its sub-areas, including individual route pages"""
    global area_id, route_id, photo_id
    
    if depth > max_depth:
        return None
    
    print("  " * depth + f"Fetching {url}...")
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Get area info
        area_info = get_area_info(soup)
        if not area_info['name']:
            print("  " * depth + "  Skipping area - no name found")
            return None
            
        print("  " * depth + f"Processing area: {area_info['name']}")
        
        # Insert area into database
        conn.execute('''
            INSERT INTO climbing_areas (id, name, description, location, latitude, longitude, url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', [area_id, area_info['name'], area_info['description'], area_info['location'],
              area_info['latitude'], area_info['longitude'], url])
        
        current_area_id = area_id
        area_id += 1
        
        # Get routes
        route_links = soup.find_all('a', class_='route-row')
        for link in route_links:
            route_url = 'https://www.mountainproject.com' + link['href']
            print("  " * (depth + 1) + f"Fetching route {route_url}...")
            
            try:
                route_response = requests.get(route_url)
                route_response.raise_for_status()
                route_soup = BeautifulSoup(route_response.text, 'html.parser')
                route_info = get_route_info(route_soup, route_url)
                
                if route_info and route_info['name']:
                    # Insert route into database
                    conn.execute('''
                        INSERT INTO routes (id, name, grade, type, description, protection,
                                          location, latitude, longitude, area_id, url)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', [route_id, route_info['name'], route_info['grade'], route_info['type'],
                          route_info['description'], route_info['protection'], route_info['location'],
                          route_info['latitude'], route_info['longitude'], current_area_id, route_info['url']])
                    
                    # Insert photos
                    for photo in route_info['photos']:
                        conn.execute('''
                            INSERT INTO route_photos (id, route_id, url, caption)
                            VALUES (?, ?, ?, ?)
                        ''', [photo_id, route_id, photo['url'], photo['caption']])
                        photo_id += 1
                    
                    route_id += 1
                    print("  " * (depth + 1) + f"  Added route: {route_info['name']}")
                
                time.sleep(1)  # Be nice to the server
            except Exception as e:
                print("  " * (depth + 1) + f"Error processing route {route_url}: {str(e)}")
                continue
        
        # Get sub-areas
        area_table = soup.find('table', {'id': 'left-nav-area-table'})
        if area_table:
            area_links = area_table.find_all('a')
            for link in area_links:
                sub_area_url = 'https://www.mountainproject.com' + link['href']
                scrape_area(sub_area_url, current_area_id, depth + 1, max_depth)
        
        time.sleep(1)  # Be nice to the server
        
    except Exception as e:
        print(f"Error scraping area {url}: {str(e)}")
        return None
    
    # If no routes found, try getting count from stats
    if number_of_routes == 0:
        stats_div = soup.find('div', class_='description')
        if stats_div:
            route_count_match = re.search(r'(\d+)\s+Total\s+Routes', stats_div.text)
            if route_count_match:
                number_of_routes = int(route_count_match.group(1))
    
    # If still no routes, try finding count in sidebar
    if number_of_routes == 0:
        left_nav_div = soup.find('div', class_='mp-sidebar')
        if left_nav_div:
            route_text = left_nav_div.find(string=re.compile(r'\d+ Routes'))
            if route_text:
                number_of_routes = int(re.search(r'\d+', route_text).group())
    
    # Get sub-areas
    sub_areas = []
    area_table = soup.find('table', id='left-nav-area-table')
    if area_table:
        area_links = area_table.find_all('a')
        for link in area_links:
            sub_url = link['href']
            sub_area = scrape_area(sub_url, depth + 1, max_depth)
            if sub_area:
                sub_areas.append(sub_area)
    
    # Combine route grades from sub-areas
    for sub_area in sub_areas:
        route_grades.extend(sub_area.get('grades', []))
        number_of_routes += sub_area.get('number_of_routes', 0)
    
    # Format grade range
    grade_range = ''
    if route_grades:
        def grade_sort_key(grade):
            grade = grade.strip()
            if grade.startswith('5.'):
                try:
                    return float(grade.replace('5.', ''))
                except ValueError:
                    return 0
            elif grade.startswith('V'):
                try:
                    return float(grade.replace('V', '').replace('+', '.3').replace('-', '.7'))
                except ValueError:
                    return 0
            else:
                try:
                    return float(grade.replace('+', '.3').replace('-', '.7'))
                except ValueError:
                    return 0
        
        route_grades = sorted(set(route_grades), key=grade_sort_key)
        grade_range = f"{route_grades[0]} - {route_grades[-1]}"
    
    return {
        'url': url,
        'description': description_text,
        'latitude': lat,
        'longitude': lng,
        'grades': route_grades,
        'grade_range': grade_range,
        'number_of_routes': number_of_routes
    }

def scrape_mountain_project():
    """Main function to scrape Mountain Project"""
    area_id = 1
    route_id = 1
    photo_id = 1
    base_urls = [
        'https://www.mountainproject.com/area/105856477/marquette',
        'https://www.mountainproject.com/area/105856478/munising',
        'https://www.mountainproject.com/area/105856479/ishpeming'
    ]
    
    # Known coordinates for key areas
    AREA_COORDS = {
        'Copper Country': (47.1164, -88.5463),
        'Horse Race Rapids': (46.4047, -87.6261),
        'Iron Mountain': (45.8203, -88.0657),
        'Laughing Whitefish Falls': (46.3894, -87.0639),
        'Little Huron River Range': (46.8539, -87.8514),
        'Little Norwich': (46.5481, -87.4106),
        'Mackinac Island': (45.8489, -84.6189),
        'Maple Hill': (46.5481, -87.4106),
        'Marquette (and Central UP) Bouldering': (46.5436, -87.3954),
        'Marquette (and Central UP) Roped': (46.5436, -87.3954),
        'Michigamme': (46.5333, -88.1000),
        'Montreal River': (46.9264, -90.3878),
        'Munising': (46.4111, -86.6489),
        'Narnia Trail Boulders': (46.5436, -87.3954),
        'Norwich Cemetery Bluff': (46.5481, -87.4106),
        'Norwich Ledge': (46.5481, -87.4106),
        'Old 41 boulders': (47.1164, -88.5463),
        'Rock River Wilderness (Eben Ice Caves)': (46.3500, -87.2167),
        'Silver Mountain': (46.7333, -87.9000),
        'Sturgeon River Gorge (Canyon Falls)': (46.7167, -88.4833)
    }
    
    # Get the main page
    print("Fetching main page...")
    response = requests.get('https://www.mountainproject.com/area/118171033/upper-peninsula')
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all area links
    area_links = soup.find_all('a', href=re.compile(r'/area/\d+/'))
    area_links = [link for link in area_links if not any(x in link.text.lower() for x in ['add to page', 'improve page'])]
    area_links = list(set(area_links))  # Remove duplicates
    
    print(f"Found {len(area_links)} areas to process")
    area_id = 1
    route_id = 1
    area_list = []
    route_list = []
    
    # Process each area
    for area_link in area_links:
        try:
            area_name = area_link.text.strip()
            area_url = area_link['href']
            print(f"Processing {area_name}...")
            
            # Get area page
            response = requests.get(area_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Get area information
            area_info = get_area_info(soup)
            
            # Get routes
            routes = []
            
            # Get routes from the route table
            route_table = soup.find('table', {'id': 'left-nav-route-table'})
            if route_table:
                route_rows = route_table.find_all('tr')[1:]  # Skip header row
                for row in route_rows:
                    route_link = row.find('a')
                    if route_link:
                        route_url = route_link['href']
                        print(f"  Fetching route {route_url}...")
                        route_response = requests.get(route_url)
                        route_soup = BeautifulSoup(route_response.text, 'html.parser')
                        route_info = get_route_info(route_soup)
                        if route_info['name']:
                            routes.append(route_info)
                        time.sleep(0.5)  # Be nice to the server
            
            # Also check for routes in sub-areas
            area_table = soup.find('table', {'id': 'left-nav-area-table'})
            if area_table:
                sub_links = area_table.find_all('a')
                for sub_link in sub_links:
                    sub_url = sub_link['href']
                    print(f"  Fetching sub-area {sub_url}...")
                    sub_response = requests.get(sub_url)
                    sub_soup = BeautifulSoup(sub_response.text, 'html.parser')
                    
                    # Get routes from sub-area
                    sub_route_table = sub_soup.find('table', {'id': 'left-nav-route-table'})
                    if sub_route_table:
                        sub_route_rows = sub_route_table.find_all('tr')[1:]  # Skip header row
                        for row in sub_route_rows:
                            route_link = row.find('a')
                            if route_link:
                                route_url = route_link['href']
                                print(f"    Fetching route {route_url}...")
                                route_response = requests.get(route_url)
                                route_soup = BeautifulSoup(route_response.text, 'html.parser')
                                route_info = get_route_info(route_soup, route_url)
                                if route_info['name']:
                                    routes.append(route_info)
                                time.sleep(0.5)  # Be nice to the server
            
            # Get sub-areas
            sub_areas = []
            area_table = soup.find('table', id='left-nav-area-table')
            if area_table:
                sub_links = area_table.find_all('a')
                for sub_link in sub_links:
                    sub_url = sub_link['href']
                    sub_response = requests.get(sub_url)
                    sub_soup = BeautifulSoup(sub_response.text, 'html.parser')
                    
                    # Get sub-area info
                    sub_info = get_area_info(sub_soup)
                    sub_info['name'] = sub_link.text.strip()
                    sub_info['url'] = sub_url
                    sub_info['parent_id'] = area_id
                    sub_areas.append(sub_info)
                    
                    # Get routes in sub-area
                    sub_routes_div = sub_soup.find('div', id='routes-div')
                    if sub_routes_div:
                        sub_route_divs = sub_routes_div.find_all('div', class_='route-table')
                        for route_div in sub_route_divs:
                            route_info = get_route_info(route_div, route_url)
                            if route_info['name']:
                                routes.append(route_info)
                    
                    time.sleep(1)  # Be nice to the server
            
            # Get coordinates from hardcoded values or area_info
            lat = lng = None
            if area_name in AREA_COORDS:
                lat, lng = AREA_COORDS[area_name]
            else:
                lat = area_info['latitude']
                lng = area_info['longitude']
            
            # Store area in database
            conn.execute('''
                INSERT INTO climbing_areas (
                    id, name, url, description, latitude, longitude,
                    type, elevation, season, approach_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', [area_id, area_name, area_url, area_info['description'],
                  lat, lng, area_info['type'], area_info['elevation'],
                  area_info['season'], area_info['approach_time']])
            
            # Store routes in database
            for route in routes:
                conn.execute('''
                    INSERT INTO routes (
                        id, area_id, name, grade, type, height,
                        pitches, first_ascent, description, protection,
                        latitude, longitude, location_description, url
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', [route_id, area_id, route['name'], route['grade'],
                      route['type'], route['height'], route['pitches'],
                      route['first_ascent'], route['description'],
                      route['protection'], route['latitude'], route['longitude'],
                      route['location_description'], route['url']])
                route_id += 1
            
            # Store sub-areas in database
            for sub_area in sub_areas:
                area_id += 1
                conn.execute('''
                    INSERT INTO climbing_areas (
                        id, name, url, description, latitude, longitude,
                        type, elevation, season, approach_time, parent_area_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', [area_id, sub_area['name'], sub_area['url'],
                      sub_area['description'], sub_area['latitude'],
                      sub_area['longitude'], sub_area['type'],
                      sub_area['elevation'], sub_area['season'],
                      sub_area['approach_time'], sub_area['parent_id']])
            
            area_id += 1
            print(f"Successfully processed {area_name} with {len(routes)} routes")
            
            # Be nice to the server
            time.sleep(2)
            
        except Exception as e:
            print(f"Error processing area {area_name if 'area_name' in locals() else 'unknown'}: {str(e)}")
            continue
    
    print(f"Processed {area_id-1} areas with {route_id-1} routes successfully")
    
    # Export to JSON
    conn.execute('SELECT * FROM climbing_areas')
    areas = [{
        'id': row[0],
        'name': row[1],
        'url': row[2],
        'description': row[3],
        'latitude': row[4],
        'longitude': row[5],
        'type': row[6],
        'elevation': row[7],
        'season': row[8],
        'approach_time': row[9],
        'parent_area_id': row[10] if len(row) > 10 else None
    } for row in conn.fetchall()]
    
    conn.execute('SELECT * FROM routes')
    routes = [{
        'id': row[0],
        'area_id': row[1],
        'name': row[2],
        'grade': row[3],
        'type': row[4],
        'height': row[5],
        'pitches': row[6],
        'first_ascent': row[7],
        'description': row[8],
        'protection': row[9],
        'latitude': row[10],
        'longitude': row[11],
        'location_description': row[12],
        'url': row[13]
    } for row in conn.fetchall()]
    
    # Get photos for each route
    conn.execute('SELECT * FROM route_photos')
    photos = [{
        'id': row[0],
        'route_id': row[1],
        'url': row[2],
        'caption': row[3]
    } for row in conn.fetchall()]
    
    # Associate photos with routes
    route_photos = {}
    for photo in photos:
        route_id = photo['route_id']
        if route_id not in route_photos:
            route_photos[route_id] = []
        route_photos[route_id].append({
            'url': photo['url'],
            'caption': photo['caption']
        })
    
    # Add photos to routes
    for route in routes:
        route['photos'] = route_photos.get(route['id'], [])
    
    data = {
        'areas': areas,
        'routes': routes
    }
    
    with open('climbing_data.json', 'w') as f:
        json.dump(data, f, indent=2)
    
    print("Scraping complete! Data stored in climbing.db and exported to climbing_data.json")

if __name__ == '__main__':
    try:
        scrape_mountain_project()
    finally:
        conn.close()
