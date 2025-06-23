# GNSS Data Downloader

This program automates the process of downloading GNSS data from Trimble
NetRS/NetR8/NetR9 and Septentrio Mosaic receivers, converting it to 
RINEX format, and optionally uploading it to a central server via SFTP.

## Features

- Downloads GNSS data files (.T00/.T02) from Trimble NetRS/NetR8/NetR9
  receivers and RINEX files directly from Sepentrio Mosaic receivers
- Converts Trimble format to RINEX format
- Can download historical data or today's partial data
- Optional SFTP upload to central server
- Automatic disk space management
- Automatic file compression

## Prerequisites

- Access to the GNSS receiver's FTP server
- SFTP server credentials for central data upload

- Python 3.x
- Required Debian packages:
  - python3-paramiko (for SFTP functionality)
- To run on Raspberry Pi (ARM):
  - qemu-user-static (for running Intel binaries on ARM)
  - binfmt-support (for binary format support)

- Required third-party programs:
  - runpkr00 (for Trimble file conversion)
  - teqc (for RINEX conversion) 

## Notes About the Third-Party Programs

The runpkr00 program was written by Trimble and teqc was written by 
the UNAVCO project.  Both are free to use but not open source because 
they rely on proprietary information from GNSS manufacturers.  Both 
are for Intel architecture but will run (slowly!) on a Raspberry Pi 
ARM system using the qemu emulator.  On the Raspberry Pi, install qemu 
and binfmt support as shown below.  After that, the programs should run 
from the command line without further fuss.

"runpkr00" has not seen a public update in a long time, and the versions
commonly found don't work with modern Linux systems.  I was able to find
a version of the critical library and build a statically-linked 32 bit
executable with that.  That is the version provided here.

The "teqc" program provided is the *statically* linked one for Centos
systems downloaded from 
https://www.unavco.org/software/data-processing/teqc/teqc.html

The "gnsscal" module is from https://pypi.org/project/gnsscal/
You could install this via pip, but then you have to deal with the "break
system files" hoohaw that Debian now puts you through.  To make things
easier, I just include it in the locally-installed modules directory
/usr/local/lib/gnss_ftp.

## Installation

1. Install required Debian packages:
sudo apt-get install python3-paramiko

2. If running on Raspberry Pi or other ARM system, install qemu support:
sudo apt-get install qemu-user binfmt-support

3. Extract the package to the root directory: 
sudo tar xzf get_trimble_ftp-2025-06-07.tar.gz -C / 

This will:
- Create */data* directory for GNSS data storage
- Install program modules in */usr/local/lib/trimble_ftp*
- Copy the main program as well as runpkr00 and teqc to */usr/local/bin*
- Install systemd service files in */etc/systemd/system*

## Usage

get_gnss_ftp.py -m /data/<my_station> \
    -f my.host.name -s MyStation \
    --organization "My Organization" \
    --user "John Smith" \
    --antenna_type "TRM59800.00     NONE" \
    --station_llh "42.3601 -71.0589 10.0" \
    --sftp_host files.tapr.org \
    --sftp_user MyUser \
    --sftp_pass MyPasswd

### Command Line Arguments

Required arguments:
- *-m, --measurement_path*: Base directory for storing downloaded files
- *-f, --fqdn*: Receiver's Fully Qualified Domain Name or IP address
- *-s, --station*: Station name (used in filenames and as RINEX marker name)
- *--organization*: Organization/agency name (max 40 chars)
- *--user*: Operator/user name (max 20 chars)
- *--antenna_type*: Antenna type (required)
- *--station_cartesian* OR *--station_llh*: Station location coordinates (mutually exclusive, one required)
  - *--station_cartesian*: WGS84 cartesian coordinates (X Y Z in meters, space-separated)
  - *--station_llh*: WGS84 llh coordinates. Accepts:
    - Decimal degrees: "latitude longitude height" (e.g., "42.3601 -71.0589 10.0")
    - DMS (signed): "lat_deg lat_min lat_sec lon_deg lon_min lon_sec height" (e.g., "39 42 0 -84 10 0 247.1")
    - DMS with direction: "lat_deg lat_min lat_sec N/S lon_deg lon_min lon_sec E/W height" (e.g., "39 42 0 N 84 10 0 W 247.1")
    - DMS with attached direction: "lat_deg lat_min lat_secN lon_deg lon_min lon_secW height" (e.g., "43 31 33N 79 23 13W 100.0")
    - Mixed spacing is also supported (e.g., "43 31 33N 79 23 13 W 100.0")

Optional arguments:
- *-y, --year*: Year to process (defaults to yesterday's year)
- *-d, --day_of_year*: Day of year to process (defaults to yesterday)
- *--start_doy*: First day of year to process
- *--end_doy*: End day of year to process
- *-a, --all_new*: Download all new RINEX files
- *-t, --today*: Get today's file (may be partial)
- *--marker_num*: Monument/marker number (max 20 chars)
- *--antenna_number*: Antenna number
- *--sftp_host*: SFTP server hostname or IP
- *--sftp_user*: SFTP username
- *--sftp_pass*: SFTP password

### Examples

1. Decimal degrees:
   --station_llh "42.3601 -71.0589 10.0"
2. DMS (signed):
   --station_llh "39 42 0 -84 10 0 247.1"
3. DMS with direction (space):
   --station_llh "39 42 0 N 84 10 0 W 247.1"
4. DMS with attached direction:
   --station_llh "43 31 33N 79 23 13W 100.0"
5. DMS with mixed spacing:
   --station_llh "43 31 33N 79 23 13 W 100.0"

## Directory Structure

The program creates the following directory structure the
measurement path (by default, */data*):
- *download/*: Raw downloaded files
- *processed/*: Processed and converted files

## Auxiliary Programs
The package includes a few auxiliary programs:

1.  convert_trimble.py reads a Trimble T00 format data file and converts
it to a RINEX file.  It does not perform any header editing and is a simple
wrapper around the runpkr00 and teqc programs to generate a quick-and-dirty
RINEX file.  Run it as:  ./convert_trimble.py <input_file>.T00

2.  sweep_rinex.py is used at the central server to do a daily sweep of
files uploaded by participating stations, moving those files to a 
directory where the Haystack team can retrieve them.  make_sftp_user.sh 
is a tool for creating users with upload permissions.  Neither of these 
programs are used by receiver sites.  They are included here to keep all
the components of the system in one place.

## Automation

The package includes systemd service files for automated operation. To
set up daily downloads:

1. Edit the run script to configure your receiver:
sudo nano /usr/local/bin/gnss_ftp.sh

2. Enable the systemd timer that will run the program daily:
sudo systemctl daemon-reload
sudo systemctl enable --now gnss_ftp.timer

The service is configured to run daily at 0230 UTC to download the
previous day's data.

## Error Handling

The program includes error handling for:
- FTP connection issues
- File conversion errors
- Disk space management
- SFTP upload failures

## License

This program is free software; you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation; either version 3 of the License, or (at your
option) any later version.

## Author

John Ackermann N8UR (jra@febo.com) 
