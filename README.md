# Trimble NetRS GNSS Data Downloader

This program automates the process of downloading GNSS data from Trimble
NetRS/NetR8/NetR9 receivers, converting it to RINEX format, and
optionally uploading it to a central server via SFTP.

## Features

- Downloads GNSS data files (.T00/.T02) from Trimble NetRS/NetR8/NetR9
  receivers
- Converts Trimble format to RINEX format
- Supports both NetRS and NetR9 directory structures
- Can download historical data or today's partial data
- Optional SFTP upload to central server
- Automatic disk space management
- Automatic file compression

## Prerequisites

- Python 3.x
- Required Debian packages:
  - python3-paramiko (for SFTP functionality)
  - qemu-user-static (for running Intel binaries on ARM)
  - binfmt-support (for binary format support)

- Required third-party programs:
  - runpkr00 (for Trimble file conversion)
  - teqc (for RINEX conversion) 
NOTE:  These two programs are (so far as I can tell) free to use 
but not open source because they rely on proprietary information from 
GNSS manufacturers.

*runpakr00* is a very old Trimble program that has not been updated in
many years.  The executable versions you might find on-line likely will
not run on modern Linux systems.  I tracked down a legitimate copy of
the core library file in object form and was able to build a 
statically-linked i32-bit executable using that.  It seems to run
on current Linux systems.

*teqc* was developed by UNAVCO and reached end-of-life a few years ago.
Executables for various platforms are available for download at
https://www.unavco.org/software/data-processing/teqc/teqc.html.
The version provided here is statically linked to improve the chances
of it working with emulation (see next paragraph).

Both these programs are for Intel architecture but will run on a 
Raspberry Pi ARM system using the qemu emulator.  Install qemu and 
binfmt support:
sudo apt-get install qemu-user binfmt-support
After that, the programs should run from the command line without
further fuss.

- Access to the GNSS receiver's FTP server
- (Optional) SFTP server credentials for central data upload

## Installation

1. Install required Debian packages:
sudo apt-get install python3-paramiko

2. If running on Raspberry Pi or other ARM system, install qemu support:
sudo apt-get install qemu-user binfmt-support

3. Extract the package to the root directory: 
sudo tar xzf get_trimble_ftp-2025-06-07.tar.gz -C / 

This will:
- Create */data* directory for GNSS data storage
- Install program modules in */usr/local/lib/tec*
- Copy the main program as well as runpkr00 and teqc to */usr/local/bin*
- Install systemd service files in */etc/systemd/system*

## Usage

### Basic Usage

bash get_netrs_ftp.py -m /data/<my_station> \
    -f my.host.name -s MyStation \
    --sftp_host tec-logger.febo.com \
    --sftp_user MyUser \
    --sftp_pass MyPasswd

### Command Line Arguments

Required arguments:
- *-m, --measurement_path*: Base directory for storing downloaded files
- *-f, --fqdn*: Fully Qualified Domain Name or IP address of the GNSS
  receiver
- *-s, --station*: Station name (used in filenames)

Optional arguments:
- *-y, --year*: Year to process (defaults to yesterday's year)
- *-d, --day_of_year*: Day of year to process (defaults to yesterday)
- *--start_doy*: First day of year to process
- *--end_doy*: End day of year to process
- *-a, --all_new*: Download all new RINEX files
- *-t, --today*: Get today's file (may be partial)
- *--sftp_host*: SFTP server hostname or IP
- *--sftp_user*: SFTP username
- *--sftp_pass*: SFTP password

### Examples

1. Download yesterday's data without sftp upload:
get_netrs_ftp -m /data/gnss -f gnss1.example.com -s STN1

2. Download specific date:
bash get_netrs_ftp -m /data/gnss -f gnss1.example.com -s STN1 -y 2024 -d 123

3. Download today's partial data:
get_netrs_ftp -m /data/gnss -f gnss1.example.com -s STN1 -t

4. Download all new data and upload to SFTP server:
get_netrs_ftp -m /data/gnss -f gnss1.example.com -s STN1 -a \
--sftp_host sftp.example.com --sftp_user user --sftp_pass password

## Directory Structure

The program creates the following directory structure under the
measurement path:
- *download/*: Raw downloaded files
- *processed/*: Processed and converted files
- *weekly/*: Weekly RINEX files (NOT YET IMPLEMENTED)

## Automation

The package includes systemd service files for automated operation. To
set up daily downloads:

1. Edit the run script to configure your receiver: ***bash sudo nano
/usr/local/bin/trimble_ftp.sh ***

2. Check the service status: ***bash sudo systemctl status trimble_ftp
***

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

## Notes -- to be integrated above
1.  The "runpkr00" package is statically linked using a proprietary library
provided by Trimble.  It is an i386 32 bit program, but will run on the
rasperry pi if you have the "qemu-user" and "binfmt-support" packages
installed.

2.  The "teqc" program is the *statically* linked version for the Raspberry
Pi as the dynamically linked one doesn't seem to work.  It was downloaded
from https://www.unavco.org/software/data-processing/teqc/teqc.html

3.  The "gnsscal" module is from https://pypi.org/project/gnsscal/
You could install this via pip, but then you have to deal with the "break
system files" hoohaw that Debian now puts you through.

4.  Install paramiko for sftp: "sudo apt install python3-maramiko"

5.  The code assumes that the NetRS "system name" is the same as the
hostname.  This needs to be correct in order for file downloads to work
properly.

