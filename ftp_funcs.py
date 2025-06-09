#!/usr/bin/env python3

import os
import sys
import tempfile
import datetime as dt
from ftplib import FTP
from ftplib import all_errors as ftp_errors
import socket
import re
from enum import Enum
import zipfile
import shutil
from gnss_file_tools import format_filesize
from conversion_funcs import convert_trimble

class ReceiverType(Enum):
    NETRS = "NetRS"
    NETR8 = "NetR8"
    NETR9 = "NetR9"
    MOSAIC = "Mosaic"
    UNKNOWN = "Unknown"

def identify_receiver_type(ftp):
    """
    Identify the type of GNSS receiver based on FTP server characteristics.
    
    Args:
        ftp: An active FTP connection
        
    Returns:
        ReceiverType: The identified receiver type
    """
    try:
        # Get the welcome message
        welcome_msg = ftp.getwelcome()
        
        # Check for NetRS (has wu-2.6.2 in welcome message)
        if "wu-2.6.2" in welcome_msg:
            print(f"Identified receiver type: {ReceiverType.NETRS.value}")
            return ReceiverType.NETRS
            
        # Check for Mosaic (has Pure-FTPd in welcome message)
        if "Pure-FTPd" in welcome_msg:
            print(f"Identified receiver type: {ReceiverType.MOSAIC.value}")
            return ReceiverType.MOSAIC
            
        # For NetR8 and NetR9, we need to check directory structure
        try:
            # Get list of directories
            directories = []
            ftp.retrlines('LIST', lambda x: directories.append(x.split()[-1]))
            
            # Check for External/Internal structure
            if 'External' in directories and 'Internal' in directories:
                # Check both Internal and External directories
                for storage_dir in ['Internal', 'External']:
                    try:
                        ftp.cwd(storage_dir)
                        # Get list of date-formatted directories (YYYYMM)
                        date_dirs = []
                        ftp.retrlines('LIST', lambda x: date_dirs.append(x.split()[-1]))
                        
                        # Find the first valid date directory
                        for date_dir in date_dirs:
                            if len(date_dir) == 6 and date_dir.isdigit():
                                try:
                                    ftp.cwd(date_dir)
                                    files = []
                                    ftp.retrlines('LIST', lambda x: files.append(x))
                                    
                                    # Check for asterisk sizes which indicate NetR9
                                    has_asterisk_sizes = any('*' in line for line in files)
                                    
                                    # Check for .T01 or .T02 extensions
                                    has_t01_t02 = any('.T01' in line or '.T02' in line for line in files)
                                    
                                    if has_asterisk_sizes:
                                        print(f"Identified receiver type: {ReceiverType.NETR9.value}")
                                        return ReceiverType.NETR9
                                    elif has_t01_t02:
                                        print(f"Identified receiver type: {ReceiverType.NETR8.value}")
                                        return ReceiverType.NETR8
                                        
                                except ftp_errors:
                                    pass
                                finally:
                                    try:
                                        ftp.cwd('..')
                                    except ftp_errors:
                                        pass
                                    
                    except ftp_errors:
                        pass
                    finally:
                        try:
                            ftp.cwd('/')
                        except ftp_errors:
                            pass
                        
        except ftp_errors:
            pass
            
        return ReceiverType.UNKNOWN
        
    except Exception as e:
        print(f"Error identifying receiver type: {e}")
        return ReceiverType.UNKNOWN

def download_trimble_file(fqdn, gps_dirname, internal_gps_dirname, base_filename, today=False, m=None):
    """Download a file from the Trimble FTP server"""
    with FTP(fqdn, 'anonymous') as ftp:
        # First identify the receiver type
        receiver_type = identify_receiver_type(ftp)
        if not receiver_type:
            return None, None
            
        # Create a temporary file with the appropriate extension
        if receiver_type == ReceiverType.NETR9:
            temp_ext = '.RINEX.2.11.zip'
        elif receiver_type == ReceiverType.MOSAIC:
            # Get the year suffix dynamically from the TECMeasurementFile if available
            if m:
                # Extract the 2-digit year from the full year
                year_short = str(m.year_num)[-2:]
                temp_ext = f'.{year_short}o'
            else:
                temp_ext = '.o'  # Generic observation file extension if no year info
        else:  # NetRS
            temp_ext = '.T00'
            
        dnld_file = tempfile.NamedTemporaryFile(suffix=temp_ext, delete=False)
        
        try:
            # Try Mosaic directory structure first (if that's what we have)
            if receiver_type == ReceiverType.MOSAIC:
                try:
                    # For Mosaic, we need to find YYdoy directories
                    # Get the year and doy from the TECMeasurementFile
                    if m:
                        year_short = str(m.year_num)[-2:]  # 2-digit year from TECMeasurementFile
                        doy_str = str(m.doy_num).zfill(3)  # 3-digit DOY from TECMeasurementFile
                        yydoy = f"{year_short}{doy_str}"
                    else:
                        # Fallback to extracting from base_filename if m is not available
                        year_short = base_filename[2:4]
                    
                    # Get list of root directories
                    root_dirs = []
                    try:
                        ftp.cwd('/')
                        dir_contents = []
                        ftp.retrlines('LIST', lambda x: dir_contents.append(x))
                        
                        # Extract just the directory names
                        for line in dir_contents:
                            parts = line.split()
                            if len(parts) >= 9 and parts[0].startswith('d'):  # Only directories
                                dirname = ' '.join(parts[8:])
                                root_dirs.append(dirname)
                    except Exception as e:
                        print(f"Error listing root directory: {str(e)}")
                        
                    # Function to recursively search for YYdoy directories
                    def find_yydoy_dir(current_path, year_short, max_depth=3, current_depth=0):
                        if current_depth >= max_depth:
                            return None
                            
                        try:
                            ftp.cwd(current_path)
                            
                            # List contents
                            dir_contents = []
                            ftp.retrlines('LIST', lambda x: dir_contents.append(x))
                            
                            # Extract directories
                            dirs = []
                            for line in dir_contents:
                                parts = line.split()
                                if len(parts) >= 9 and parts[0].startswith('d'):  # Only directories
                                    dirname = ' '.join(parts[8:])
                                    dirs.append(dirname)
                                    
                            # Check if any directory matches YYdoy pattern
                            for dirname in dirs:
                                if len(dirname) == 5 and dirname.startswith(year_short) and dirname[2:].isdigit():
                                    # This looks like a YYdoy directory
                                    return f"{current_path}/{dirname}"
                                    
                            # Recursively check subdirectories
                            for dirname in dirs:
                                result = find_yydoy_dir(f"{current_path}/{dirname}", year_short, 
                                                       max_depth, current_depth + 1)
                                if result:
                                    return result
                                    
                            return None
                        except Exception as e:
                            print(f"Error checking directory {current_path}: {str(e)}")
                            return None
                            
                    # Search for YYdoy directory starting from each root directory
                    yydoy_path = None
                    for root_dir in root_dirs:
                        path = find_yydoy_dir(f"/{root_dir}", year_short)
                        if path:
                            yydoy_path = path
                            break
                            
                    if not yydoy_path:
                        print(f"Could not find YYdoy directory for {year_short}")
                        return None, None
                        
                    # Now we have the path to the YYdoy directory
                    # Look for RINEX observation files (ending with 'o')
                    try:
                        ftp.cwd(yydoy_path)
                        
                        dir_contents = []
                        ftp.retrlines('LIST', lambda x: dir_contents.append(x))
                        
                        # Extract filenames
                        file_list = []
                        for line in dir_contents:
                            parts = line.split()
                            if len(parts) >= 9:  # Standard Unix-like listing format
                                filename = ' '.join(parts[8:])  # Filename is everything after the date/time
                                file_list.append(filename)
                                
                        # Look for RINEX observation files which end with year+o (e.g., 25o, 24o)
                        # We'll check for both current year patterns and also common RINEX observation patterns
                        obs_patterns = []
                        if m:
                            # If we have m, use the year from it
                            year_short = str(m.year_num)[-2:]
                            obs_patterns.append(f".{year_short}o")  # .25o
                            obs_patterns.append(f".{year_short}O")  # .25O
                        
                        # Always include generic pattern as fallback
                        obs_patterns.append("o")                 # Generic ending with 'o'
                        
                        remote_files = []
                        for pattern in obs_patterns:
                            pattern_files = [f for f in file_list if f.lower().endswith(pattern.lower())]
                            remote_files.extend(pattern_files)
                            
                        # Remove duplicates
                        remote_files = list(set(remote_files))
                        
                        if remote_files:
                            remote_file = remote_files[0]
                            print(f"Downloading {remote_file}...")
                            ftp.retrbinary(f'RETR {remote_file}', dnld_file.write)
                            dnld_file.flush()
                            size = os.path.getsize(dnld_file.name)
                            print(f"Downloaded {remote_file} ({format_filesize(size)})")
                            return dnld_file, remote_file
                        else:
                            print(f"No RINEX observation files found in {yydoy_path}")
                    except Exception as e:
                        print(f"Error accessing YYdoy directory {yydoy_path}: {str(e)}")
                except Exception as e:
                    print(f"Error traversing Mosaic directory structure: {str(e)}")
                    
                print("Could not find file in Mosaic directory structure")
                return None, None
            # Try NetR9 directory structure
            elif receiver_type == ReceiverType.NETR9:
                try:
                    ftp.cwd(internal_gps_dirname)
                    
                    # Extract just the filenames from the directory listing
                    dir_contents = []
                    ftp.retrlines('LIST', lambda x: dir_contents.append(x))
                    
                    file_list = []
                    for line in dir_contents:
                        # Parse the line to extract just the filename at the end
                        parts = line.split()
                        if len(parts) >= 9:  # Standard Unix-like listing format
                            filename = ' '.join(parts[8:])  # Filename is everything after the date/time
                            file_list.append(filename)
                    
                    # Filter for RINEX.2.11.zip files
                    remote_files = [f for f in file_list if f.endswith('.RINEX.2.11.zip')]
                    
                    if remote_files:
                        remote_file = remote_files[0]
                        print(f"Downloading {remote_file} (converting on-the-fly)...")
                        ftp.retrbinary(f'RETR {remote_file}', dnld_file.write)
                        dnld_file.flush()
                        size = os.path.getsize(dnld_file.name)
                        print(f"Downloaded {remote_file} ({format_filesize(size)})")
                        return dnld_file, remote_file
                except Exception as e:
                    print(f"Error accessing NetR9 directory {internal_gps_dirname}: {str(e)}")
                    
                # Try looking in root level directory as well
                try:
                    ftp.cwd('/')
                    
                    # Extract just the filenames from the directory listing
                    dir_contents = []
                    ftp.retrlines('LIST', lambda x: dir_contents.append(x))
                    
                    file_list = []
                    for line in dir_contents:
                        # Parse the line to extract just the filename at the end
                        parts = line.split()
                        if len(parts) >= 9:  # Standard Unix-like listing format
                            filename = ' '.join(parts[8:])  # Filename is everything after the date/time
                            file_list.append(filename)
                    
                    # Filter for RINEX.2.11.zip files
                    remote_files = [f for f in file_list if f.endswith('.RINEX.2.11.zip')]
                    
                    if remote_files:
                        remote_file = remote_files[0]
                        print(f"Downloading {remote_file} (converting on-the-fly)...")
                        ftp.retrbinary(f'RETR {remote_file}', dnld_file.write)
                        dnld_file.flush()
                        size = os.path.getsize(dnld_file.name)
                        print(f"Downloaded {remote_file} ({format_filesize(size)})")
                        return dnld_file, remote_file
                except Exception as e:
                    print(f"Error accessing root directory: {str(e)}")
                    
                print("Could not find file in NetR9 directory structure")
                return None, None
            else:  # NetRS
                try:
                    ftp.cwd(gps_dirname)
                    
                    # Extract just the filenames from the directory listing
                    dir_contents = []
                    ftp.retrlines('LIST', lambda x: dir_contents.append(x))
                    
                    file_list = []
                    for line in dir_contents:
                        # Parse the line to extract just the filename at the end
                        parts = line.split()
                        if len(parts) >= 9:  # Standard Unix-like listing format
                            filename = ' '.join(parts[8:])  # Filename is everything after the date/time
                            file_list.append(filename)
                    
                    # Filter for T00 files
                    remote_files = [f for f in file_list if f.endswith('.T00')]
                    
                    if remote_files:
                        remote_file = remote_files[0]
                        print(f"Downloading {remote_file}...")
                        ftp.retrbinary(f'RETR {remote_file}', dnld_file.write)
                        dnld_file.flush()
                        size = os.path.getsize(dnld_file.name)
                        print(f"Downloaded {remote_file} ({format_filesize(size)})")
                        return dnld_file, remote_file
                except Exception as e:
                    print(f"Error accessing NetRS directory {gps_dirname}: {str(e)}")
                    
                print("Could not find file in NetRS directory structure")
                return None, None
                    
        except Exception as e:
            print(f"Error downloading file: {str(e)}")
            return None, None
            
    return None, None

def download_all_new_files(fqdn, measurement_path, station, args):
    """
    Download all new RINEX files from the FTP server.
    
    Args:
        fqdn (str): FQDN of the receiver
        measurement_path (str): Path where files will be stored
        station (str): Station name
        args: Command line arguments containing organization, user, marker_num, etc.
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Test FTP connection first
        try:
            with FTP(fqdn, 'anonymous', timeout=30) as ftp:
                pass  # Just test the connection
        except socket.gaierror:
            print(f"Error: Could not resolve hostname '{fqdn}'")
            return False
        except socket.timeout:
            print(f"Error: Connection to '{fqdn}' timed out")
            return False
        except ConnectionRefusedError:
            print(f"Error: Connection to '{fqdn}' was refused (FTP service not running or port blocked)")
            return False
        except ftp_errors as e:
            print(f"Error connecting to FTP server '{fqdn}': {e}")
            return False
        
        # If we get here, FTP connection is good, proceed with download
        with FTP(fqdn, 'anonymous') as ftp:
            # First, get list of all directories
            directories = []
            try:
                # Try to list directories in root
                ftp.retrlines('LIST', lambda x: directories.append(x.split()[-1]))
            except ftp_errors as e:
                print(f"Error listing root directory: {e}")
                return False
            
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
                return False
            
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
                            
                            # Process the downloaded file
                            if process_downloaded_file(dnld_file, receiver_type, measurement_path, station, args):
                                print(f"Downloaded {remote_file} and processed successfully")
                            else:
                                print(f"Downloaded {remote_file} but processing failed")
                            
                            os.remove(dnld_file.name)
                            
                        except Exception as e:
                            print(f"Error processing {remote_file}: {e}")
                            continue
                    
                    # Go back to root directory for next iteration
                    ftp.cwd('/')
                    
                except Exception as e:
                    print(f"Error processing directory {date_dir}: {e}")
                    continue
        
        return True
        
    except Exception as e:
        print(f"FTP error: {e}")
        return False 

def process_downloaded_file(downloaded_file, receiver_type, output_path, station, args):
    """Process a downloaded file based on receiver type"""
    print(f"Processing downloaded file: {downloaded_file.name} for receiver type {receiver_type.value}")
    
    try:
        if receiver_type == ReceiverType.NETRS:
            # For NetRS, use convert_trimble
            if convert_trimble(downloaded_file.name, output_path, station, args.organization, args.user, args.marker_num, args.station_location):
                return True
            return False
            
        elif receiver_type == ReceiverType.NETR9:
            # For NetR9, extract RINEX file from zip
            try:
                with zipfile.ZipFile(downloaded_file.name, 'r') as zip_ref:
                    # List contents for debugging
                    print("Zip contents:", zip_ref.namelist())
                    
                    # Find the RINEX observation file
                    rinex_files = [f for f in zip_ref.namelist() if f.endswith('.25O')]
                    if not rinex_files:
                        print("No RINEX observation files found in zip")
                        return False
                        
                    # Extract only the observation file
                    rinex_file = rinex_files[0]
                    print(f"Extracting observation file {rinex_file} to {output_path}")
                    
                    # Create output directory if it doesn't exist
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    
                    # Extract to a temporary file first
                    temp_path = output_path + '.temp'
                    with zip_ref.open(rinex_file) as source, open(temp_path, 'wb') as target:
                        target.write(source.read())
                    
                    # Rename to the expected name
                    if os.path.exists(temp_path):
                        os.rename(temp_path, output_path)
                        size = os.path.getsize(output_path)
                        print(f"Extracted and renamed observation file size: {format_filesize(size)}")
                        return True
                    else:
                        print("Extracted file not found")
                        return False
                        
            except zipfile.BadZipFile:
                print("Invalid zip file")
                return False
            except Exception as e:
                print(f"Error extracting zip: {str(e)}")
                return False
        
        elif receiver_type == ReceiverType.MOSAIC:
            # For Mosaic, files are already in RINEX format, just copy the file
            try:
                # Create output directory if it doesn't exist
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                # Copy the file to the output location
                shutil.copy2(downloaded_file.name, output_path)
                
                # Verify the file was copied
                if os.path.exists(output_path):
                    size = os.path.getsize(output_path)
                    print(f"Copied Mosaic RINEX observation file to {output_path} ({format_filesize(size)})")
                    return True
                else:
                    print("Failed to copy Mosaic RINEX observation file")
                    return False
                    
            except Exception as e:
                print(f"Error processing Mosaic file: {str(e)}")
                return False
                
        else:
            print(f"Unsupported receiver type: {receiver_type.value}")
            return False
            
    except Exception as e:
        print(f"Error processing downloaded file: {str(e)}")
        return False 