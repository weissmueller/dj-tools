
import requests
from bs4 import BeautifulSoup
import json
import pandas as pd
import re
from datetime import datetime

class BeatportScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
        }

    def scrape(self, url, include_mix_name=False):
        """
        Scrapes a Beatport Top 100 URL and returns a DataFrame.
        """
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            return {"error": f"Failed to fetch URL: {str(e)}"}

        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Beatport stores data in a script tag with id __NEXT_DATA__
        next_data_tag = soup.find('script', id='__NEXT_DATA__')
        
        if not next_data_tag:
            return {"error": "Could not find data on page (Anti-bot protection?)."}
            
        try:
            data = json.loads(next_data_tag.string)
        except json.JSONDecodeError:
            return {"error": "Failed to parse page data structure."}

        # Navigate to the track list
        # Path is usually: props -> pageProps -> dehydratedState -> queries -> [0] -> state -> data -> results
        try:
            queries = data.get('props', {}).get('pageProps', {}).get('dehydratedState', {}).get('queries', [])
            if not queries:
                return {"error": "No query data found in page."}
            
            # Find the query that contains 'results' which is likely the track list
            track_list = []
            genre_name = "Unknown"
            
            for q in queries:
                state_data = q.get('state', {}).get('data', {})
                if state_data and 'results' in state_data:
                    track_list = state_data['results']
                    if 'genre' in state_data:
                        genre_name = state_data['genre']['name']
                    elif 'genre' in state_data.get('facets', {}): 
                         # Sometimes genre info is elsewhere, but let's try to infer from first track
                         pass
                    break
            
            if not track_list:
                return {"error": "No tracks found in the data structure."}

        except Exception as e:
            return {"error": f"Error traversing data structure: {str(e)}"}
            
        # Parse tracks into list of dicts
        parsed_tracks = []
        track_list_name = "Unknown Playlist"

        # Try to find the name in the queries
        # Often it's in the same query as the results, or a separate one for 'track-list' details
        try:
             for q in queries:
                state_data = q.get('state', {}).get('data', {})
                if state_data:
                    # Check for 'name' directly if it's the main object
                    if 'name' in state_data and isinstance(state_data['name'], str):
                        potential_name = state_data['name']
                        if potential_name and potential_name != "Unknown":
                            track_list_name = potential_name
                            # Don't break immediately, might be a better one (e.g. strict playlist name vs genre)
                            # But usually the one with 'results' is the best bet if it has a name.
                            if 'results' in state_data:
                                break
                    # Fallback: check for 'genre' -> 'name'
                    if 'genre' in state_data and 'name' in state_data['genre']:
                        if track_list_name == "Unknown Playlist":
                             track_list_name = f"Top 100 {state_data['genre']['name']}"

        except:
            pass
            
        for t in track_list:
            # Extract basic info
            track_name = t.get('name', 'Unknown')
            mix_name = t.get('mix_name', '')
            
            # Decided by user input
            if include_mix_name and mix_name:
                final_track_name = f"{track_name} ({mix_name})"
            else:
                final_track_name = track_name
                
            # Artists
            artists = t.get('artists', [])
            artist_names = [a.get('name') for a in artists]
            artist_str = ", ".join(artist_names)
            
            # Album
            album = t.get('release', {})
            album_name = album.get('name', '')
            album_image = t.get('image', {}).get('uri', '')
            
            # Date
            publish_date = t.get('publish_date', '')  # Format 2024-02-09
            
            # Duration (Beatport gives "4:16" usually or ms in 'length_ms' sometimes)
            # Checking the JSON inspector from earlier... 
            # If it's a string "mm:ss", convert to ms.
            length = t.get('length', '0:00')
            duration_ms = 0
            if isinstance(length, str) and ':' in length:
                parts = length.split(':')
                if len(parts) == 2:
                    duration_ms = (int(parts[0]) * 60 + int(parts[1])) * 1000
                elif len(parts) == 3: # hh:mm:ss? unlikely for tracks but possible
                    duration_ms = (int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])) * 1000
            elif isinstance(length, int):
                duration_ms = length # assume ms if int
            
            # Create row matching the specific CSV format
            # "Track URI","Track Name","Artist URI(s)","Artist Name(s)","Album URI","Album Name",
            # "Album Artist URI(s)","Album Artist Name(s)","Album Release Date","Album Image URL",
            # "Disc Number","Track Number","Track Duration (ms)","Track Preview URL","Explicit",
            # "Popularity","ISRC","Added By","Added At"
            
            row = {
                "Track URI": "", # Spotify specific
                "Track Name": final_track_name,
                "Artist URI(s)": "",
                "Artist Name(s)": artist_str,
                "Album URI": "",
                "Album Name": album_name,
                "Album Artist URI(s)": "",
                "Album Artist Name(s)": "", # Could infer from artists
                "Album Release Date": publish_date,
                "Album Image URL": album_image,
                "Disc Number": "1",
                "Track Number": "1", # Don't have this easily, defaulting
                "Track Duration (ms)": str(duration_ms),
                "Track Preview URL": t.get('sample_url', ''),
                "Explicit": "false", 
                "Popularity": "0",
                "ISRC": "", # Beatport doesn't always expose this easily in the list
                "Added By": "BeatportScraper",
                "Added At": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
            }
            parsed_tracks.append(row)

        df = pd.DataFrame(parsed_tracks)
        return {
            "df": df,
            "genre": genre_name,
            "name": track_list_name,
            "count": len(parsed_tracks)
        }
