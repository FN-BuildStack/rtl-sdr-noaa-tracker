# rtl-sdr-noaa-tracker

An autonomous, zero-touch Python ground station pipeline designed to track, capture, and decode Automatic Picture Transmission (APT) telemetry from NOAA weather satellites (NOAA 15, 18, and 19) using RTL-SDR hardware.

This project automates the entire radio frequency (RF) to digital signal processing (DSP) lifecycle: from predicting satellite passes using atomic time synchronization, to controlling the SDR hardware, downsampling the audio, and triggering the final image decoding.

## Features

* **Autonomous Tracking:** Utilizes `pyorbital` paired with NTP-synced atomic time (`ntplib`) to bypass local system clock drifts and calculate precise elevations.
* **Dynamic TLE Fetching:** Connects directly to Celestrak to download and parse the latest Two-Line Element (TLE) sets based on immutable NORAD IDs.
* **First-Run Wizard:** Geographic coordinates and local timezone offsets are configured once via CLI and securely stored in `station_config.json`, eliminating hardcoded values.
* **Segmented Capture:** Records telemetry in distinct temporal blocks (e.g., 3-minute intervals) mapped to elevation angles for granular signal degradation analysis.
* **Automated DSP Pipeline:** Orchestrates standard UNIX tools (`rtl_fm`, `sox`) and the `noaa-apt` decoder in a continuous stream.

## Hardware Requirements

* **SDR:** RTL-SDR Dongle (RTL2832U based, v3 or v4 recommended).
* **Antenna:** A V-Dipole antenna tuned to 137 MHz (elements extended to 53.4 cm, separated by 120 degrees, oriented horizontally with clear line-of-sight to the sky).

## Software Dependencies

The orchestrator relies on several system-level DSP and radio control tools.

### 1. System Packages (Debian/Ubuntu/Kali)
```bash
sudo apt update
sudo apt install rtl-sdr sox unzip
```

### 2. External Decoder (noaa-apt)

The final image generation relies on the `noaa-apt` binary by *martinber*. It must be downloaded and placed in the project root.

```bash
wget [https://github.com/martinber/noaa-apt/releases/download/v1.4.1/noaa-apt-1.4.1-x86_64-linux-gnu.zip](https://github.com/martinber/noaa-apt/releases/download/v1.4.1/noaa-apt-1.4.1-x86_64-linux-gnu.zip)
unzip noaa-apt-1.4.1-x86_64-linux-gnu.zip
mv noaa-apt-1.4.1-x86_64-linux-gnu/noaa-apt ./noaa-apt
chmod +x noaa-apt
rm -rf noaa-apt-1.4.1-x86_64-linux-gnu*
```

### 3. Python Requirements

It is recommended to run this inside a virtual environment (`venv`).

```bash
pip install pyorbital ntplib
```

## Installation & Setup

1. Clone this repository:

```bash
git clone [https://github.com/FN-BuildStack/rtl-sdr-noaa-tracker.git](https://github.com/FN-BuildStack/rtl-sdr-noaa-tracker.git)
cd rtl-sdr-noaa-tracker
```

2. Verify your hardware connection:

```bash
rtl_test
```

## Usage

### 1. The Orchestrator (`scheduler.py`)

This is the main daemon. Run it and leave it active. Upon the first execution, it will prompt you for your Ground Station coordinates (Latitude, Longitude, Altitude in meters, and UTC Offset) to generate the `station_config.json` file.

```bash
python3 scheduler.py
```

The script will download the TLE data, calculate the current satellite position, and enter a low-resource standby loop. Once the satellite breaches the minimum elevation threshold (default 25 degrees), it will automatically trigger the SDR hardware, record the WAV file, and decode the PNG image.

### 2. The Pass Predictor (`tracker.py`)

A utility script to manually check current satellite coordinates and print the exact UTC time for the next expected pass over your registered ground station.

```bash
python3 tracker.py
```

## Architecture / Signal Flow

1. `scheduler.py` detects elevation > 25°.
2. `rtl_fm` captures raw IQ data at 137.1 MHz, demodulates it to FM, and outputs raw audio at 60k sample rate.
3. The output is piped `|` directly into `sox`.
4. `sox` resamples the raw stream into an 11025 Hz, 16-bit Mono `.wav` file (APT standard).
5. Upon completion, `scheduler.py` calls `./noaa-apt` via a subprocess to process the synchronization pulses and output the final map overlay `.png`.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Disclaimer
This code is provided "as-is" for educational and amateur radio exploration purposes only. The author is not responsible for any legal issues, hardware damage, or interference with licensed radio transmissions that may arise from the use of this software. Always ensure you are operating within the radio frequency regulations and laws of your country.
