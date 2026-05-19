import os
import json
from pyorbital.orbital import Orbital
from datetime import datetime

# --- TECHNICAL CONFIGURATION ---
TLE_FILE = 'noaa.tle'
CONFIG_FILE = 'station_config.json'
SATS = ['NOAA 15', 'NOAA 18', 'NOAA 19']

def load_config():
    """Loads location configuration if available, otherwise uses defaults."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    # Fallback to default testing coordinates if config is missing
    return {"LAT": 1.21, "LON": -77.28, "ALT_KM": 2.5}

def check_passes():
    """Calculates current elevation and next passes for weather satellites."""
    config = load_config()
    my_lat = config["LAT"]
    my_lon = config["LON"]
    my_alt = config["ALT_KM"]

    print(f"--- Satellite Report (Local TLE Mode): {datetime.now()} ---")
    
    for name in SATS:
        try:
            # Force pyorbital to read from the local file
            orb = Orbital(name, tle_file=TLE_FILE)
            az, el = orb.get_observer_look(datetime.utcnow(), my_lon, my_lat, my_alt)
            
            passes = orb.get_next_passes(datetime.utcnow(), 24, my_lon, my_lat, my_alt)
            
            print(f"\n[+] {name}:")
            print(f"    - Current Position: Alt {el:.2f} deg | Az {az:.2f} deg")
            
            if passes:
                next_p = passes[0]
                print(f"    - NEXT PASS: {next_p[0].strftime('%H:%M:%S')} UTC")
                
        except Exception as e:
            print(f"    - Error processing {name}: {e}")

if __name__ == "__main__":
    check_passes()
