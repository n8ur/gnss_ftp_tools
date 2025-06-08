#! /usr/bin/env -S python3 -u

############################################################
# get_netrs.ftp.py v.20250608.1
# copyright 2025 John Ackermann N8UR jra@febo.com
#
# Program to pull .T00 data files from a Trimble NetRS receiver, 
# convert them to RINEX format, and then push them to a central
# server.
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

# This points to where the modules live
MODULES_DIR = "/usr/local/lib/trimble_ftp"
if MODULES_DIR not in sys.path:
    sys.path.insert(0, MODULES_DIR)

from gnsscal import *
from gnss_file_tools import *

class TECMeasurementFiles(MeasurementFilesBase):
    """Class for TEC application with different directory structure"""
    def __init__(self, m_path, date_1=0, date_2=0, today=False):
        # First calculate all paths without creating directories
        super().__init__(m_path, date_1, date_2)
        self.today = today
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
            self.daily_dnld_file = self.m_week_name + "_" + \
                self.gps_dow_str + ".obs"
            
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
    parser = argparse.ArgumentParser()

    parser.add_argument('-m','--measurement_path',
        type=str,required=True,
        help="Measurement path")
    parser.add_argument('-f','--fqdn',
        type=str,required=True,
        help="FQDN of receiver")
    parser.add_argument('-s','--station',
        type=str,required=True,
        help="Receiver station name")
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
        type=str,required=False,default="-Unknown-",
        help="Organization name (max 40 chars, defaults to '-Unknown-')")
    parser.add_argument('--user',
        type=str,required=False,default="-Unknown-",
        help="User name (max 20 chars, defaults to '-Unknown-')")
    parser.add_argument('--marker_num',
        type=str,required=False,default="-Unknown-",
        help="Marker number (max 20 chars, defaults to '-Unknown-')")
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

def convert_trimble(infile, outfile, station, organization=None, user=None, marker_num=None):
    """Convert Trimble .T00 or .T02 file to RINEX format"""
    tmpfile = tempfile.NamedTemporaryFile(suffix='.tgd',delete=False)
    # convert .T00/.T02 file into intermediate .tgd file
    args = ['/usr/local/bin/runpkr00', '-g', '-d', '-v',
        infile, tmpfile.name]
    try:
        subprocess.run(args, \
            stdout = subprocess.DEVNULL, stderr = subprocess.DEVNULL)
    except Exception as e:
        print("Couldn't run runpkr00, error:",e)
        return
    tmpfile.flush()
    tmpfile.seek(0)
   
    # Process station name: uppercase and trim whitespace, truncate to 60 characters
    marker_name = station.upper().strip()[:60]
   
    # convert tgd to RINEX
    with open(outfile,'w') as f:
        # Build teqc command with options
        args = [
            '/usr/local/bin/teqc',
            '+C2',
            '-R',
            '-O.mo', marker_name
        ]
        
        # Add organization if provided
        if organization:
            org_name = organization.upper().strip()[:40]
            args.extend(['-O.ag', org_name])
            
        # Add user if provided
        if user:
            user_name = user.upper().strip()[:20]
            args.extend(['-O.o', user_name])
            
        # Add marker number if provided
        if marker_num:
            marker_number = marker_num.upper().strip()[:20]
            args.extend(['-O.mn', marker_number])
            
        # Add input file
        args.append(tmpfile.name)
        
        try:
            subprocess.run(args, stdout = f, stderr = subprocess.DEVNULL)
        except Exception as e:
            print("Couldn't run teqc, error:",e)
            return
    s = outfile.split('/')
    s = s[len(s)-2] + '/' + s[len(s)-1]
    size = os.path.getsize(outfile)
    tmpfile.close()
    os.unlink(tmpfile.name)
    return True

####################################################################
# main function
# fqdn = FQDN of rx hostname
# station_ID = station name (used in filenames)
# measurement_path is where files go

def get_host_key(hostname):
    """Get the host key for the given hostname, accepting it if not known"""
    try:
        # Try to get the host key from the system's known_hosts
        host_keys = paramiko.util.load_host_keys(os.path.expanduser('~/.ssh/known_hosts'))
        if hostname in host_keys:
            return host_keys[hostname]
        
        # If not found, connect and get the key
        transport = paramiko.Transport((hostname, 22))
        transport.start_client()
        key = transport.get_remote_server_key()
        
        # Save the key to known_hosts
        host_keys[hostname] = key
        host_keys.save(os.path.expanduser('~/.ssh/known_hosts'))
        
        return key
    except Exception as e:
        print(f"Error getting host key: {str(e)}")
        return None

def upload_to_sftp(measurement_path, sftp_host, sftp_user, sftp_pass):
    """Upload all files from download directory to SFTP server"""
    try:
        # Test SFTP connection first
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(sftp_host, username=sftp_user, password=sftp_pass, timeout=30)
            ssh.close()
        except socket.gaierror:
            print(f"Error: Could not resolve SFTP hostname '{sftp_host}'")
            return
        except socket.timeout:
            print(f"Error: Connection to SFTP server '{sftp_host}' timed out")
            return
        except paramiko.AuthenticationException:
            print(f"Error: Authentication failed for SFTP server '{sftp_host}'")
            return
        except paramiko.SSHException as e:
            print(f"Error connecting to SFTP server '{sftp_host}': {e}")
            return
        except Exception as e:
            print(f"Error connecting to SFTP server '{sftp_host}': {e}")
            return
        
        # Create processed directory if it doesn't exist
        processed_dir = os.path.join(measurement_path, "processed")
        os.makedirs(processed_dir, exist_ok=True)
        
        # Get all files from download directory
        download_dir = os.path.join(measurement_path, "download")
        files = os.listdir(download_dir)
        if not files:
            print("No files found in download directory")
            return
            
        print(f"Found {len(files)} files to upload")
        
        # Create SSH client with auto-accept of unknown hosts
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            ssh.connect(sftp_host, username=sftp_user, password=sftp_pass)
            sftp = ssh.open_sftp()
        except Exception as e:
            print(f"Error establishing SFTP connection: {e}")
            return
            
        # Check uploads directory
        uploads_dir = "uploads"
        try:
            sftp.stat(uploads_dir)
        except Exception as e:
            print(f"Error accessing uploads directory: {e}")
            return
        
        # Upload each file
        for file in files:
            local_path = os.path.join(download_dir, file)
            if os.path.isfile(local_path):
                try:
                    print(f"Uploading {file}...")
                    remote_path = f"{uploads_dir}/{file}"
                    sftp.put(local_path, remote_path)
                    
                    # Move file to processed directory
                    os.rename(local_path, os.path.join(processed_dir, file))
                    print(f"Uploaded and moved {file} to processed directory")
                except Exception as e:
                    print(f"Error processing {file}: {e}")
                    continue
        
        sftp.close()
        ssh.close()
        print("SFTP upload completed")
        
    except Exception as e:
        print(f"SFTP error: {e}")

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
    print("get_netrs_ftp.py:")    # id for logging
    os.umask(0o002)        # o-w
    
    if all_new:
        print("Downloading all new RINEX files")
        # Create initial MeasurementFiles object to get current date info
        m = TECMeasurementFiles(measurement_path, 0, 0)  # This will use yesterday's date
        
        try:
            # Test FTP connection first
            try:
                with FTP(fqdn, 'anonymous', timeout=30) as ftp:
                    pass  # Just test the connection
            except socket.gaierror:
                print(f"Error: Could not resolve hostname '{fqdn}'")
                return
            except socket.timeout:
                print(f"Error: Connection to '{fqdn}' timed out")
                return
            except ConnectionRefusedError:
                print(f"Error: Connection to '{fqdn}' was refused (FTP service not running or port blocked)")
                return
            except ftp_errors as e:
                print(f"Error connecting to FTP server '{fqdn}': {e}")
                return
            
            # If we get here, FTP connection is good, proceed with download
            with FTP(fqdn, 'anonymous') as ftp:
                # First, get list of all directories
                directories = []
                try:
                    # Try to list directories in root
                    ftp.retrlines('LIST', lambda x: directories.append(x.split()[-1]))
                except ftp_errors as e:
                    print(f"Error listing root directory: {e}")
                    return
                
                # Check if we have an Internal directory
                has_internal = 'Internal' in directories
                
                # Get all date-formatted directories
                date_dirs = []
                
                # First check root level
                for d in directories:
                    if len(d) == 6 and d.isdigit():
                        date_dirs.append(('root', d))
                
                # Then check Internal directory if it exists
                if has_internal:
                    try:
                        ftp.cwd('Internal')
                        internal_dirs = []
                        ftp.retrlines('LIST', lambda x: internal_dirs.append(x.split()[-1]))
                        for d in internal_dirs:
                            if len(d) == 6 and d.isdigit():
                                date_dirs.append(('internal', d))
                        ftp.cwd('/')  # Go back to root
                    except ftp_errors as e:
                        print(f"Error accessing Internal directory: {e}")
                
                if not date_dirs:
                    print("No date-formatted directories found")
                    return
                
                print(f"Found {len(date_dirs)} date directories")
                
                # Process each directory
                for dir_type, date_dir in date_dirs:
                    try:
                        # Construct the full path based on directory type
                        if dir_type == 'internal':
                            full_path = f"Internal/{date_dir}"
                        else:
                            full_path = date_dir
                            
                        try:
                            ftp.cwd(full_path)
                            print(f"Processing directory: {full_path}")
                        except ftp_errors as e:
                            print(f"Couldn't access directory {full_path}: {e}")
                            continue
                        
                        # Get list of files in current directory
                        remote_files = []
                        ftp.retrlines('LIST', lambda x: remote_files.append(x.split()[-1]))
                        
                        # Filter for .T00 and .T02 files
                        trimble_files = [f for f in remote_files if f.endswith(('.T00', '.T02'))]
                        
                        if not trimble_files:
                            print(f"No Trimble files found in {full_path}")
                            continue
                            
                        print(f"Found {len(trimble_files)} Trimble files in {full_path}")
                        
                        # Process each file
                        for remote_file in trimble_files:
                            try:
                                # Create tempfile with appropriate extension
                                dnld_file = tempfile.NamedTemporaryFile(suffix=os.path.splitext(remote_file)[1], delete=False)
                                
                                # Download the file
                                try:
                                    response = ftp.retrbinary('RETR ' + remote_file, dnld_file.write, 1024)
                                except ftp_errors as e:
                                    print(f"Couldn't download {remote_file}: {e}")
                                    os.remove(dnld_file.name)
                                    continue
                                
                                # Check if download was successful
                                if not response.startswith('226'):
                                    print(f"Transfer error for {remote_file}. File may be incomplete.")
                                    os.remove(dnld_file.name)
                                    continue
                                
                                # Check file size
                                tmpsize = os.path.getsize(dnld_file.name)
                                if tmpsize == 0:
                                    print(f"Downloaded file {remote_file} was empty")
                                    os.remove(dnld_file.name)
                                    continue
                                
                                # Create output filename based on the date from directory name
                                year = int(date_dir[:4])
                                month = int(date_dir[4:])
                                
                                # Use regex to find date pattern YYYYMMDDHHMM followed by a letter
                                date_pattern = r'(\d{12})([a-zA-Z])\.(T00|T02)'
                                match = re.search(date_pattern, remote_file)
                                if match:
                                    date_str = match.group(1)  # Get the YYYYMMDDHHMM part
                                    day = int(date_str[6:8])  # Extract DD from YYYYMMDD
                                else:
                                    print(f"Could not find date pattern in filename {remote_file}")
                                    os.remove(dnld_file.name)
                                    continue
                                
                                # Create MeasurementFiles object for this date
                                m = TECMeasurementFiles(measurement_path, year, 
                                    dt.datetime(year, month, day).timetuple().tm_yday)
                                
                                # Convert and save the file
                                if convert_trimble(dnld_file.name, m.daily_dnld_path, station, args.organization, args.user, args.marker_num):
                                    print(f"Downloaded {remote_file} and converted to RINEX")
                                    s = m.daily_dnld_path.split('/')
                                    s = s[len(s)-2] + '/' + s[len(s)-1]
                                    size = os.path.getsize(m.daily_dnld_path)
                                    print("Saved as " + s + " (" + format_filesize(size) + ")")
                                else:
                                    print(f"Downloaded {remote_file} but couldn't convert to RINEX")
                                
                                os.remove(dnld_file.name)
                                
                            except Exception as e:
                                print(f"Error processing {remote_file}: {e}")
                                continue
                        
                        # Go back to root directory for next iteration
                        ftp.cwd('/')
                        
                    except Exception as e:
                        print(f"Error processing directory {date_dir}: {e}")
                        continue
        
        except Exception as e:
            print(f"FTP error: {e}")
            return
        
        # If SFTP parameters are provided, upload all downloaded files
        if sftp_host and sftp_user and sftp_pass:
            print("\nUploading files to SFTP server...")
            upload_to_sftp(measurement_path, sftp_host, sftp_user, sftp_pass)
        else:
            print("\nSkipping SFTP upload - server details not provided")
        
        # Check disk space and purge if needed
        check_disk_space(measurement_path)
        
        # Zip processed files
        zip_processed_files(measurement_path)
        
        return
    
    # Regular single file download code continues here...
    # Create TECMeasurementFiles object with the provided year and doy
    m = TECMeasurementFiles(measurement_path, year, doy, today)

    print("Year, day of year, GPS week, GPS day of week:", \
        m.year_num, m.doy_num, m.gps_week_str, m.gps_dow_str)
    
    if today:
        print("Getting today's file (may be partial)")
    else:
        # don't try to download a future date!
        if m.gps_days_num > m.today_gps_days_num:
            print("Trying to download future day!")
            print("GPS week:",m.gps_week_str,"day of week:",m.gps_dow_str)
            print("Today is:",m.today_gps_week_str,m.today_gps_dow_str)
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
    
    full_filename = None

    try:
        # Create tempfile with appropriate extension based on what we find
        dnld_file = tempfile.NamedTemporaryFile(suffix='.T00',delete=False)
    except:
        print("Couldn't create tempfile.  Exiting!")
        return

    # now get the file
    try:
        with FTP(fqdn, 'anonymous') as ftp:
            # Try NetRS directory structure first
            try:
                ftp.cwd(gps_dirname)
                print(f"Using NetRS directory structure: {gps_dirname}")
            except ftp_errors as e:
                # If that fails, try NetR9 directory structure
                try:
                    ftp.cwd(internal_gps_dirname)
                    print(f"Using NetR9 directory structure: {internal_gps_dirname}")
                except ftp_errors as e:
                    print("Couldn't change to either remote directory:")
                    print(e)
                    return

            # get directory contents and find the file with the right base filename
            try:
                remote_files = []
                # Get raw directory listing
                raw_list = []
                ftp.retrlines('LIST', raw_list.append)
                
                # Parse the listing to get just the filenames
                for line in raw_list:
                    # Split on whitespace and get the last element (filename)
                    parts = line.split()
                    if len(parts) >= 9:  # Standard FTP LIST format has at least 9 parts
                        filename = parts[-1]
                        remote_files.append(filename)
                
                for remote_file in remote_files:
                    # Skip files that are still being written (end in .A) unless today flag is set
                    if remote_file.endswith('.A') and not today:
                        continue
                        
                    # Find the position of our date pattern in the filename
                    date_pos = remote_file.find(base_filename)
                    if date_pos >= 0:  # If we found the date pattern
                        # Check if there's an 'a' or 'A' after the date pattern
                        if (date_pos + len(base_filename) < len(remote_file) and
                            remote_file[date_pos + len(base_filename)].lower() == 'a' and
                            (remote_file.endswith('.T00') or remote_file.endswith('.T02') or 
                             (today and (remote_file.endswith('.T00.A') or remote_file.endswith('.T02.A'))))):
                            full_filename = remote_file
                            # Update tempfile extension to match the found file
                            dnld_file.close()
                            os.unlink(dnld_file.name)
                            dnld_file = tempfile.NamedTemporaryFile(suffix=os.path.splitext(remote_file)[1], delete=False)
                            break
            except ftp_errors as e:
                print("Couldnt list files in remote directory:")
                print(e)
                return
            if not full_filename:
                print(f"Error: No .T00 or .T02 file found in '{gps_dirname}' or '{internal_gps_dirname}' containing date pattern '{base_filename}' and ending with 'a' or 'A'")
                sys.exit()

            # we're downloading in binary mode whether ascii or .T00 format
            try:
                response = ftp.retrbinary('RETR ' + full_filename, \
                    dnld_file.write, 1024)
            except ftp_errors as e:
                print("Couldn't download:")
                print(e)
                return
            # rewind tmpfile
            dnld_file.seek(0)
            # Check the response code
            if response.startswith('226'):  # Transfer complete
                print("Downloaded",full_filename)
            else:
                print("Transfer error. File may be incomplete or corrupt.")

    except socket.gaierror:
        print(f"Error: Could not resolve hostname '{fqdn}'")
        return
    except socket.timeout:
        print(f"Error: Connection to '{fqdn}' timed out")
        return
    except ConnectionRefusedError:
        print(f"Error: Connection to '{fqdn}' was refused (FTP service not running or port blocked)")
        return
    except ftp_errors as e:
        print(f"Error connecting to FTP server '{fqdn}': {e}")
        return
    except Exception as e:
        print(f"Unexpected error connecting to '{fqdn}': {e}")
        return

    # was there any data downloaded?
    tmpsize = os.path.getsize(dnld_file.name)
    if tmpsize > 0:
        if convert_trimble(dnld_file.name, m.daily_dnld_path, station, args.organization, args.user, args.marker_num) == True:
            print("Downloaded",full_filename,"and converted to RINEX")
        else:
            print("Downloaded",full_filename,"but couldn't convert to RINEX!")
        s = m.daily_dnld_path.split('/')
        s = s[len(s)-2] + '/' + s[len(s)-1]
        size = os.path.getsize(m.daily_dnld_path)
        print("Saved as " + s + " (" + format_filesize(size) + ")")
    else:
        os.remove(dnld_file.name)
        print("Downloaded file was empty.  Exiting:")
        return

    os.remove(dnld_file.name)

    # If SFTP parameters are provided, upload files
    if sftp_host and sftp_user and sftp_pass:
        print("\nUploading files to SFTP server...")
        upload_to_sftp(measurement_path, sftp_host, sftp_user, sftp_pass)
    else:
        print("\nSkipping SFTP upload - server details not provided")

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
