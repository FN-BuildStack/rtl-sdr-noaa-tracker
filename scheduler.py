import os
import time
import json
import subprocess
import urllib.request
import ntplib
from pyorbital.orbital import Orbital
from datetime import datetime, timezone, timedelta

# --- TECHNICAL CONFIGURATION ---
TLE_FILE = 'noaa.tle'
CONFIG_FILE = 'station_config.json'
NORAD_ID = "33591"   # Immutable NORAD ID for NOAA 19
FREQ = "137.1M"
MIN_ELEVATION = 25   # Minimum elevation to start capture

def load_or_setup_config():
    """Loads existing configuration or runs a setup wizard for first-time users."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
            
    print("=========================================")
    print("   SATELLITE STATION - FIRST TIME SETUP  ")
    print("=========================================")
    print("Please enter your exact location data.")
    print("This will be saved to config.json and will run autonomously next time.\n")
    
    try:
        lat = float(input("Enter your Latitude (e.g., 1.21): "))
        lon = float(input("Enter your Longitude (e.g., -77.28): "))
        alt_m = float(input("Enter your Altitude in meters (e.g., 2500): "))
        tz = float(input("Enter your UTC offset in hours (e.g., -5 for EST/Colombia): "))
        
        config = {
            "LAT": lat,
            "LON": lon,
            "ALT_KM": alt_m / 1000.0,  # Pyorbital requires kilometers
            "UTC_OFFSET": tz
        }
        
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
            
        print("\n[+] Configuration saved successfully.")
        print("=========================================\n")
        return config
        
    except ValueError:
        print("\n[!] Error: Please enter valid numeric values. Run the script again.")
        exit(1)

def update_tle():
    """Downloads exact TLE data for the specific NORAD ID directly"""
    url = f"https://celestrak.org/NORAD/elements/gp.php?CATNR={NORAD_ID}&FORMAT=tle"
    print(f"[*] Downloading precise TLE data for NORAD ID {NORAD_ID}...")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/plain'
        }
        
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            tle_data = response.read()
            
            if b"Invalid" in tle_data or len(tle_data) < 100:
                print(f"[!] Warning: API rejected the request. Server says: {tle_data.decode('utf-8', errors='ignore')}")
                return
                
            with open(TLE_FILE, 'wb') as out_file:
                out_file.write(tle_data)
                
        print("[+] TLE database updated successfully.")
    except Exception as e:
        print(f"[!] Critical error updating TLE: {e}")

def get_exact_sat_name(tle_file, norad_id):
    """Searches the TLE file for the immutable NORAD ID and extracts whatever name it uses today"""
    try:
        with open(tle_file, 'r') as f:
            lines = f.readlines()
            for i in range(len(lines)):
                if lines[i].startswith(f"1 {norad_id}"):
                    return lines[i-1].strip()
    except Exception as e:
        print(f"[!] Error reading TLE file: {e}")
    return None

def get_real_utc_time():
    """Fetches atomic time from internet NTP servers to bypass local VM clock errors."""
    try:
        client = ntplib.NTPClient()
        response = client.request('pool.ntp.org', version=3, timeout=2)
        return datetime.fromtimestamp(response.tx_time, timezone.utc)
    except Exception as e:
        return datetime.now(timezone.utc)

def decode_image(wav_file):
    """Converts the recorded WAV audio into a processed PNG image"""
    output_png = wav_file.replace(".wav", ".png")
    print(f"[*] DECODING IMAGE: {output_png}")
    cmd = f"./noaa-apt {wav_file} -o {output_png}"
    try:
        subprocess.run(cmd, shell=True, check=True)
        print(f"[+] Satellite image successfully generated: {output_png}")
    except Exception as e:
        print(f"[-] Error during image decoding: {e}")

def capture_signal(duration, filename):
    """Orchestrates the DSP pipeline: RTL_FM -> SOX -> WAV -> PNG"""
    print(f"[*] INITIATING CAPTURE: {filename} ({duration}s)")
    cmd = (
        f"timeout {duration} rtl_fm -f {FREQ} -s 60k -g 0 -p 0 - | "
        f"sox -t raw -e signed-integer -b 16 -c 1 -r 60k - {filename}.wav channels 1 rate 11025"
    )
    try:
        subprocess.run(cmd, shell=True, check=True)
        print(f"[+] Capture saved successfully.")
        decode_image(f"{filename}.wav")
    except Exception as e:
        print(f"[-] Error in capture process: {e}")

def monitor():
    """Main autonomous control loop using internet time and dynamic names"""
    # Initialize configuration wizard
    config = load_or_setup_config()
    my_lat = config["LAT"]
    my_lon = config["LON"]
    my_alt = config["ALT_KM"]
    tz_offset = config["UTC_OFFSET"]

    update_tle()

    exact_sat_name = get_exact_sat_name(TLE_FILE, NORAD_ID)
    
    if not exact_sat_name:
        print(f"[!] Error: NORAD ID {NORAD_ID} not found in {TLE_FILE}.")
        return
        
    print(f"[*] Satellite identified as: '{exact_sat_name}'")

    try:
        orb = Orbital(exact_sat_name, tle_file=TLE_FILE)
    except KeyError:
        print(f"[!] Error: Pyorbital could not parse '{exact_sat_name}'.")
        return

    print(f"[*] Autonomous Station Active. Monitoring {exact_sat_name} (NTP Sync ON)...")

    while True:
        try:
            # 1. Fetch real atomic time
            now_utc_aware = get_real_utc_time()
            
            # Use user-defined timezone offset for accurate terminal display
            local_tz = timezone(timedelta(hours=tz_offset))
            now_local_str = now_utc_aware.astimezone(local_tz).strftime('%H:%M:%S')
            
            # 2. Remove timezone awareness for pyorbital compatibility
            now_utc_naive = now_utc_aware.replace(tzinfo=None)
            
            # 3. Calculate elevation using the naive UTC time
            az, el = orb.get_observer_look(now_utc_naive, my_lon, my_lat, my_alt)
            
            if el > MIN_ELEVATION:
                timestamp = now_utc_naive.strftime("%Y%m%d_%H%M%S")
                filename = f"NOAA19_{timestamp}_El_{int(el)}deg"
                
                print(f"\n[*] Satellite at {el:.2f} deg - Initiating block capture...")
                capture_signal(180, filename)
            else:
                print(f"[{now_local_str}] {exact_sat_name} on standby (Elevation: {el:.2f} deg)", end='\r')
                time.sleep(10)
                
        except KeyboardInterrupt:
            print("\n[*] Stopping station safely...")
            break
        except Exception as e:
            print(f"\n[!] Error in monitoring loop: {e}")
            time.sleep(10)

if __name__ == "__main__":
    monitor()
