#! /usr/bin/env -S python3 -u

############################################################
# get_gnss_ftp.py v.20250610.1
# copyright 2025 John Ackermann N8UR jra@febo.com
#
# Program to pull data files from Trimble or Sepentrio receiver, 
# convert them to RINEX format if necessary, and then push them to 
# a central server.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

import os
import sys
import subprocess
import tempfile
import argparse
import datetime as dt
from ftplib import FTP
from ftplib import all_errors as ftp_errors
import paramiko
import shutil
import zipfile
import glob
import re  # Add regex import
import socket
import gzip
import logging
import stat

# Configure logging
def setup_logging():
    # Define log locations
    system_log = '/var/log/get_gnss_ftp.log'
    user_log = os.path.expanduser('~/.local/log/get_gnss_ftp.log')
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Create handlers
    handlers = []
    
    # Try system log first
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(system_log), exist_ok=True)
        # Try to create/access the log file
        with open(system_log, 'a') as f:
            pass
        # If successful, set up system log handler
        system_handler = logging.FileHandler(system_log)
        system_handler.setFormatter(formatter)
        handlers.append(system_handler)
        logger = logging.getLogger(__name__)
        logger.info(f"Logging to system log: {system_log}")
    except (PermissionError, OSError) as e:
        # If system log fails, try user log
        try:
            # Create user log directory if it doesn't exist
            os.makedirs(os.path.dirname(user_log), exist_ok=True)
            user_handler = logging.FileHandler(user_log)
            user_handler.setFormatter(formatter)
            handlers.append(user_handler)
            logger = logging.getLogger(__name__)
            logger.info(f"System log access denied, logging to user log: {user_log}")
        except Exception as e:
            # If both fail, just use console
            logger = logging.getLogger(__name__)
            logger.warning(f"Could not set up file logging: {e}")
            logger.warning("Logging to console only")
    
    # Always add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    handlers.append(console_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        handlers=handlers
    )
    
    return logging.getLogger(__name__)

# Set up logging
logger = setup_logging()

# This points to where the modules live
MODULES_DIR = "/usr/local/lib/gnss_ftp"
if MODULES_DIR not in sys.path:
    sys.path.insert(0, MODULES_DIR)

from gnsscal import *
from gnss_file_tools import *
from ftp_funcs import download_gnss_file, download_all_new_files, identify_receiver_type, process_downloaded_file, ReceiverType
from sftp_funcs import get_host_key, upload_to_sftp
from conversion_funcs import convert_netrs

class TECMeasurementFiles(MeasurementFilesBase):
    """Class for TEC application with different directory structure"""
    def __init__(self, m_path, date_1=0, date_2=0, today=False, station_name=None):
        # First calculate all paths without creating directories
        super().__init__(m_path, date_1, date_2)
        self.today = today
        # Override m_name with the provided station name
        if station_name:
            self.m_name = station_name
        # Recalculate paths with the new station name
        self.calc_path_names()
        # Then explicitly create only TEC-specific directories
        self.create_tec_dirs()

    def create_tec_dirs(self):
        """Create only directories needed for TEC application"""
        try:
            # Create base directories
            os.makedirs(self.dnld_base, exist_ok=True)
            os.makedirs(self.m_path, exist_ok=True)
            os.makedirs(self.processed_dir, exist_ok=True)
        except Exception as e:
            print("Couldn't create directory:", e)
            print("Exiting...")
            sys.exit()

    def calc_path_names(self):
        """Override path calculation for TEC application to use simpler directory structure"""
        # Calculate daily download file paths
        self.dnld_base = self.m_path + "download/" 
        
        # For today's file, use today's GPS day of week
        if self.today:
            self.daily_dnld_file = self.m_week_name + "_" + \
                self.today_gps_dow_str + ".obs.partial"
        else:
            # New file naming format: <station>_<doy>0.yyo
            self.daily_dnld_file = self.m_name.lower() + "_" + str(self.doy_num).zfill(3) + "0." + \
                str(self.year_num)[-2:] + "o"
            
        self.daily_dnld_dir = self.dnld_base  # Changed to use base directory
        self.daily_dnld_path = self.daily_dnld_dir + self.daily_dnld_file

        # Add processed directory path
        self.processed_dir = self.m_path + "processed/"

        # Count files if directory exists
        try:
            self.num_files = len(glob.glob(self.daily_dnld_dir + '/*', recursive=False))
        except:
            self.num_files = 0

        # Calculate daily zip name
        self.daily_dnld_zip = self.m_week_name
        if self.num_files == 7:
            self.daily_dnld_zip += "_daily.zip"
        else:
            if self.num_files == 1:
                self.daily_dnld_zip += \
                    "_" + str(self.num_files) + "_file_daily.zip"
            else:
                self.daily_dnld_zip += \
                    "_" + str(self.num_files) + "_files_daily.zip"
        self.daily_dnld_zip_path = self.dnld_base + self.daily_dnld_zip
        
        # Calculate weekly rinex file paths
        self.weekly_rinex_file = self.m_name + "__" + self.gps_week_str
        if self.num_files == 7:
            self.weekly_rinex_file += "_weekly.obs"
        else:
            if self.num_files == 1:
                self.weekly_rinex_file += \
                    "_" + str(self.num_files) + "_file_weekly.obs"
            else:
                self.weekly_rinex_file += \
                    "_" + str(self.num_files) + "_files_weekly.obs"

        self.weekly_rinex_dir = self.m_path + "weekly/"
        self.weekly_rinex_path = self.weekly_rinex_dir + self.weekly_rinex_file
        self.weekly_rinex_zip = self.weekly_rinex_file + ".zip"
        self.weekly_rinex_zip_path = \
            self.weekly_rinex_dir + self.weekly_rinex_zip

def options_get_netrs_ftp():
    parser = argparse.ArgumentParser(description='Get Trimble NetRS FTP file')

    parser.add_argument('-m','--measurement_path',
        type=str,required=True,
        help="Measurement path")
    parser.add_argument('-f','--fqdn',
        type=str,required=True,
        help="FQDN of receiver")
    parser.add_argument('-s','--station',
        help='Station name (required)',
        required=True)
    parser.add_argument('-y','--year',
        type=int,required=False,default=0,
        help="Year to process (defaults to yesterday's year if not specified)")
    parser.add_argument('-d','--day_of_year',
        type=int,required=False,default=0,
        help="Day of year to process (defaults to yesterday's day of year if not specified)")
    parser.add_argument('--start_doy',
        type=int,required=False,default=0,
        help="First day of year to process")
    parser.add_argument('--end_doy',
        type=int,required=False,default=0,
        help="End day of year to process")
    parser.add_argument('-a','--all_new',
        action='store_true',required=False,default=0,
        help="Download all new RINEX files")
    parser.add_argument('-t','--today',
        action='store_true',required=False,default=0,
        help="Get today's file (may be partial)")
    parser.add_argument('--organization',
        help='Organization/agency name (required)',
        required=True)
    parser.add_argument('--user',
        help='Operator/user name (required)',
        required=True)
    parser.add_argument('--marker_num',
        help='Monument/marker number (optional)')
    parser.add_argument('--antenna_number',
        help='Antenna number (optional)')
    parser.add_argument('--antenna_type',
        help='Antenna type (required)',
        required=True)
    station_location = parser.add_mutually_exclusive_group(required=True)
    station_location.add_argument('--station_cartesian',
        help='Station location in WGS84 cartesian coordinates (X Y Z in meters, space-separated)')
    station_location.add_argument('--station_llh',
        help='Station location in WGS84 llh coordinates (latitude longitude height in decimal degrees and meters, space-separated)')
    # Add new arguments for SFTP upload
    parser.add_argument('--sftp_host',
        type=str,required=False,
        help="SFTP server hostname or IP")
    parser.add_argument('--sftp_user',
        type=str,required=False,
        help="SFTP username")
    parser.add_argument('--sftp_pass',
        type=str,required=False,
        help="SFTP password")

    args = parser.parse_args()
    
    return args

####################################################################
# main function
# fqdn = FQDN of rx hostname
# station_ID = station name (used in filenames)
# measurement_path is where files go

def check_disk_space(path, min_free_mb=512):
    """Check if there's enough free disk space, purge old files if needed"""
    try:
        # Get free space in MB
        free_space = shutil.disk_usage(path).free / (1024**2)
        
        if free_space < min_free_mb:
            print(f"Warning: Low disk space ({free_space:.0f}MB free)")
            print("Purging oldest processed files...")
            
            # Get list of processed files sorted by modification time
            processed_dir = os.path.join(path, "processed")
            files = [(f, os.path.getmtime(os.path.join(processed_dir, f))) 
                    for f in os.listdir(processed_dir) 
                    if os.path.isfile(os.path.join(processed_dir, f))]
            files.sort(key=lambda x: x[1])  # Sort by modification time
            
            # Remove oldest files until we have enough space
            for file, _ in files:
                file_path = os.path.join(processed_dir, file)
                try:
                    os.remove(file_path)
                    print(f"Removed old file: {file}")
                    free_space = shutil.disk_usage(path).free / (1024**2)
                    if free_space >= min_free_mb:
                        break
                except Exception as e:
                    print(f"Error removing {file}: {str(e)}")
            
            print(f"Current free space: {free_space:.0f}MB")
            
    except Exception as e:
        print(f"Error checking disk space: {str(e)}")

def zip_processed_files(measurement_path):
    """Zip files in the processed directory"""
    try:
        processed_dir = os.path.join(measurement_path, "processed")
        if not os.path.exists(processed_dir):
            return
            
        # Get list of unzipped files
        files = [f for f in os.listdir(processed_dir) 
                if os.path.isfile(os.path.join(processed_dir, f)) 
                and not f.endswith('.zip')]
        
        if not files:
            return
            
        # Create zip file with same name as original file
        for file in files:
            file_path = os.path.join(processed_dir, file)
            zip_name = file + '.zip'
            zip_path = os.path.join(processed_dir, zip_name)
            
            print(f"Creating zip archive: {zip_name}")
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(file_path, file)
                # Remove original file after zipping
                os.remove(file_path)
                print(f"Added {file} to archive")
                
            print(f"Created zip archive: {zip_name}")
        
    except Exception as e:
        print(f"Error creating zip archive: {str(e)}")

def get_netrs_ftp(measurement_path, fqdn, station, year, doy, sftp_host=None, sftp_user=None, sftp_pass=None, today=False, all_new=False):
    logger.debug("Starting get_netrs_ftp.py")    # Changed to debug
    os.umask(0o002)        # o-w
    
    if all_new:
        logger.info("Downloading all new RINEX files")
        # Create initial MeasurementFiles object to get current date info
        m = TECMeasurementFiles(measurement_path, 0, 0, station_name=station)  # This will use yesterday's date
        
        # Use the new module to download all new files
        if not download_all_new_files(fqdn, measurement_path, station, args, TECMeasurementFiles):
            logger.error("Failed to download all new files")
            return
        
        # If SFTP parameters are provided, upload all downloaded files
        if sftp_host and sftp_user and sftp_pass:
            logger.info("Uploading files to SFTP server...")
            upload_to_sftp(measurement_path, sftp_host, sftp_user, sftp_pass)
        else:
            logger.debug("Skipping SFTP upload - server details not provided")
        
        # Check disk space and purge if needed
        check_disk_space(measurement_path)
        
        # Zip processed files
        zip_processed_files(measurement_path)
        
        return
    
    # Regular single file download code continues here...
    # Create TECMeasurementFiles object with the provided year and doy
    m = TECMeasurementFiles(measurement_path, year, doy, today, station)

    logger.info(f"Year: {m.year_num}, DoY: {m.doy_num}, GPS week: {m.gps_week_str}, GPS DoW: {m.gps_dow_str}")
    
    if today:
        logger.info("Getting today's file (may be partial)")
    else:
        # don't try to download a future date!
        if m.gps_days_num > m.today_gps_days_num:
            logger.error("Trying to download future day!")
            logger.error(f"GPS week: {m.gps_week_str}, day of week: {m.gps_dow_str}")
            logger.error(f"Today is: {m.today_gps_week_str} {m.today_gps_dow_str}")
            sys.exit()
    
    # Use the date components from the TECMeasurementFiles object
    # Try both NetRS and NetR9 directory structures
    gps_dirname = m.yyyy_str + m.mm_str + "/"
    internal_gps_dirname = "Internal/" + gps_dirname
    
    # For today's file, we need to use tomorrow's date in the filename
    if today:
        # Get tomorrow's date components
        tomorrow = dt.datetime(m.year_num, 1, 1) + dt.timedelta(days=m.doy_num)
        base_filename = tomorrow.strftime("%Y%m%d") + "0000"
    else:
        base_filename = m.yyyy_str + m.mm_str + m.dd_str + "0000"
    
    # Use the new module to download the file
    dnld_file, full_filename = download_gnss_file(fqdn, gps_dirname, internal_gps_dirname, base_filename, today, m)
    
    if not dnld_file or not full_filename:
        logger.error("Failed to download file")
        return

    # was there any data downloaded?
    tmpsize = os.path.getsize(dnld_file.name)
    if tmpsize > 0:
        # Get the receiver type
        with FTP(fqdn, 'anonymous') as ftp:
            receiver_type = identify_receiver_type(ftp)
            
        if process_downloaded_file(dnld_file, receiver_type, station, args, m):
            if receiver_type == ReceiverType.NETRS:
                logger.info(f"Downloaded {full_filename} and converted to RINEX")
            elif receiver_type in [ReceiverType.NETR8, ReceiverType.NETR9]:
                logger.info(f"Downloaded {full_filename} and extracted RINEX from zip")
            else:  # MOSAIC
                logger.info(f"Downloaded {full_filename} (RINEX file)")
            s = m.daily_dnld_path.split('/')
            s = s[len(s)-2] + '/' + s[len(s)-1]
            if os.path.exists(m.daily_dnld_path):
                size = os.path.getsize(m.daily_dnld_path)
                logger.debug(f"Saved as {s} ({format_filesize(size)})")
            else:
                logger.error(f"Expected output file not found at {m.daily_dnld_path}")
        else:
            logger.error(f"Downloaded {full_filename} but couldn't convert to RINEX!")
    else:
        os.remove(dnld_file.name)
        logger.error("Downloaded file was empty. Exiting.")
        return

    os.remove(dnld_file.name)

    # If SFTP parameters are provided, upload files
    if sftp_host and sftp_user and sftp_pass:
        logger.info("Uploading files to SFTP server...")
        upload_to_sftp(measurement_path, sftp_host, sftp_user, sftp_pass)
    else:
        logger.debug("Skipping SFTP upload - server details not provided")

    # Check disk space and purge if needed
    check_disk_space(measurement_path)
    
    # Zip processed files
    zip_processed_files(measurement_path)

    try:
        running_standalone
    except NameError:
        return

if __name__ == '__main__':
    args = options_get_netrs_ftp()
    
    # Create a temporary MeasurementFiles object to get dates
    temp_m = MeasurementFilesBase(args.measurement_path, 0, 0)
    
    # If year and doy are not specified, calculate the appropriate date
    if args.year == 0 and args.day_of_year == 0:
        if args.today:
            args.year = temp_m.year_num
            args.day_of_year = temp_m.doy_num
        else:
            args.year = temp_m.yesterday_year_num
            args.day_of_year = temp_m.yesterday_doy_num
    
    get_netrs_ftp(args.measurement_path, \
        args.fqdn, args.station, args.year, args.day_of_year,
        args.sftp_host, args.sftp_user, args.sftp_pass, args.today, args.all_new)
    sys.exit()
