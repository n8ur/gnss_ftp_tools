#!/usr/bin/env python3

############################################################
# ftp_funcs.py v.20250624.1
# copyright 2025 John Ackermann N8UR jra@febo.com
#
# Functions for FTP operations with GNSS receivers including
# file downloads, receiver type identification, and data processing.
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
import tempfile
import datetime as dt
from ftplib import FTP
from ftplib import all_errors as ftp_errors
import socket
import re
from enum import Enum
import zipfile
import shutil
import logging
from gnss_file_tools import format_filesize
from conversion_funcs import convert_netrs, edit_rinex_header

logger = logging.getLogger(__name__)

class FTPConnection:
    def __init__(self, fqdn, timeout=30):
        self.fqdn = fqdn
        self.timeout = timeout
        self.ftp = None

    def __enter__(self):
        try:
            self.ftp = FTP(self.fqdn, "anonymous", timeout=self.timeout)
            return self.ftp
        except socket.gaierror as e:
            logger.error(f"Could not resolve hostname '{self.fqdn}': {e}")
            raise
        except socket.timeout as e:
            logger.error(f"Connection to '{self.fqdn}' timed out: {e}")
            raise
        except ConnectionRefusedError as e:
            logger.error(f"Connection to '{self.fqdn}' was refused (FTP service not running or port blocked): {e}")
            raise
        except ftp_errors as e:
            logger.error(f"FTP connection failed: {e}")
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.ftp:
            try:
                self.ftp.quit()
            except:
                pass


def with_ftp_connection(fqdn, operation, timeout=30):
    """
    Execute an operation with an FTP connection, handling all common error cases.
    
    Args:
        fqdn (str): The FTP server hostname
        operation (callable): A function that takes an FTP connection as its argument
        timeout (int): Connection timeout in seconds
        
    Returns:
        The result of the operation, or None if the operation failed
    """
    try:
        with FTPConnection(fqdn, timeout) as ftp:
            return operation(ftp)
    except (socket.gaierror, socket.timeout, ConnectionRefusedError, ftp_errors) as e:
        return None
    except Exception as e:
        logger.error(f"Unexpected error during FTP operation: {e}")
        return None


class ReceiverType(Enum):
    NETRS = "NetRS"
    NETR8 = "NetR8"
    NETR9 = "NetR9"
    MOSAIC = "Mosaic"
    UNKNOWN = "Unknown"


def parse_directory_listing(ftp, path):
    """Helper function to get and parse directory listing"""
    try:
        # Save current directory
        current_dir = ftp.pwd()
        ftp.cwd(path)
        dir_contents = []
        ftp.retrlines("LIST", lambda x: dir_contents.append(x))
        
        dirs = []
        for line in dir_contents:
            parts = line.split()
            if len(parts) >= 9 and parts[0].startswith("d"):
                dirname = " ".join(parts[8:])
                dirs.append(dirname)
        
        # Restore original directory
        ftp.cwd(current_dir)
        return dirs
    except Exception as e:
        logger.error(f"Error listing directory {path}: {e}")
        return []


def get_target_files(remote_files, receiver_type):
    """Get target files based on receiver type"""
    if receiver_type in [ReceiverType.NETR8, ReceiverType.NETR9]:
        return [f for f in remote_files if f.endswith(".RINEX.2.11.zip")]
    elif receiver_type == ReceiverType.NETRS:
        return [f for f in remote_files if f.endswith((".T00", ".T02"))]
    elif receiver_type == ReceiverType.MOSAIC:
        return [f for f in remote_files if f.lower().endswith("o")]
    return []


def get_temp_extension(receiver_type):
    """Get temporary file extension based on receiver type"""
    if receiver_type in [ReceiverType.NETR8, ReceiverType.NETR9]:
        return ".RINEX.2.11.zip"
    elif receiver_type == ReceiverType.MOSAIC:
        return ".o"
    else:  # NetRS
        return ".T00"


def extract_date_from_filename(filename, receiver_type):
    """Extract year and doy from filename based on receiver type.
    
    Args:
        filename (str): The filename to extract date from
        receiver_type (ReceiverType): The type of receiver
        
    Returns:
        tuple: (year, doy) or (None, None) if date couldn't be extracted
    """
    try:
        if receiver_type == ReceiverType.MOSAIC:
            # Mosaic format: n8ur1570.25o -> year=2025, doy=157
            match = re.match(r'.*?(\d{3})0\.(\d{2})o', filename)
            if match:
                doy = int(match.group(1))
                year = 2000 + int(match.group(2))
                return year, doy
        elif receiver_type in [ReceiverType.NETR8, ReceiverType.NETR9]:
            # NetR8/NetR9 format: netr9-1___202506160000A.RINEX.2.11.zip -> year=2025, doy=157
            # Look for 8 digits (YYYYMMDD) followed by 4 digits and A
            match = re.search(r'(\d{8})\d{4}A\.RINEX\.2\.11\.zip$', filename)
            if match:
                date_str = match.group(1)
                year = int(date_str[:4])
                month = int(date_str[4:6])
                day = int(date_str[6:8])
                # Validate month and day
                if 1 <= month <= 12 and 1 <= day <= 31:
                    date = dt.datetime(year, month, day)
                    doy = date.timetuple().tm_yday
                    return year, doy
        else:  # NetRS
            # NetR8/NetR9/NetRS format: YYYYMMDD in filename
            # For NetRS, the format is like netrs-1202506060000a.T00
            # The date portion is at the end: YYYYMMDDHHMMa.T00
            match = re.search(r'(\d{8})\d{4}a\.T00$', filename)
            if match:
                date_str = match.group(1)
                year = int(date_str[:4])
                month = int(date_str[4:6])
                day = int(date_str[6:8])
                # Validate month and day
                if 1 <= month <= 12 and 1 <= day <= 31:
                    date = dt.datetime(year, month, day)
                    doy = date.timetuple().tm_yday
                    return year, doy
    except (ValueError, AttributeError) as e:
        logger.error(f"Error extracting date from {filename}: {e}")
    
    return None, None


def check_welcome_message(ftp):
    """Check FTP welcome message for receiver type indicators"""
    welcome_msg = ftp.getwelcome()
    if "wu-2.6.2" in welcome_msg:
        return ReceiverType.NETRS
    if "Pure-FTPd" in welcome_msg:
        return ReceiverType.MOSAIC
    return None


def check_directory_structure(ftp):
    """Check directory structure for receiver type indicators"""
    directories = []
    ftp.retrlines("LIST", lambda x: directories.append(x.split()[-1]))
    
    if "External" in directories:
        return ReceiverType.NETR9
    elif "Internal" in directories:
        return ReceiverType.NETR8
    return None


def identify_receiver_type(ftp):
    """Identify receiver type using multiple methods"""
    # First try welcome message
    receiver_type = check_welcome_message(ftp)
    if receiver_type:
        return receiver_type
        
    # Then try directory structure
    receiver_type = check_directory_structure(ftp)
    if receiver_type:
        return receiver_type
        
    return ReceiverType.UNKNOWN


def mosaic_get_data_dirs(ftp, m=None):
    """Get all data directories for Mosaic receiver"""
    root_dirs = parse_directory_listing(ftp, "/")
    if not root_dirs:
        return []

    # Function to recursively search for YYdoy directories
    def find_yydoy_dirs(current_path, max_depth=3, current_depth=0):
        if current_depth >= max_depth:
            return []

        try:
            dirs = parse_directory_listing(ftp, current_path)
            
            yydoy_dirs = []
            for dirname in dirs:
                if len(dirname) == 5 and dirname[:2].isdigit() and dirname[2:].isdigit():
                    yydoy_dirs.append(f"{current_path}/{dirname}")
                else:
                    # Recursively check subdirectories
                    subdirs = find_yydoy_dirs(f"{current_path}/{dirname}", max_depth, current_depth + 1)
                    yydoy_dirs.extend(subdirs)
            
            return yydoy_dirs
        except Exception as e:
            logger.error(f"Error checking directory {current_path}: {str(e)}")
            return []

    # Search for YYdoy directories starting from each root directory
    all_yydoy_dirs = []
    for root_dir in root_dirs:
        yydoy_dirs = find_yydoy_dirs(f"/{root_dir}")
        all_yydoy_dirs.extend(yydoy_dirs)
    
    return all_yydoy_dirs


def netr8_get_data_dirs(ftp):
    """Get all data directories for NetR8 receiver"""
    date_dirs = []
    try:
        # Check Internal directory
        dirs = parse_directory_listing(ftp, "Internal")
        for dirname in dirs:
            if len(dirname) == 6 and dirname.isdigit():
                date_dirs.append(("internal", dirname))
    except Exception as e:
        logger.error(f"Error accessing Internal directory: {e}")
    
    return date_dirs


def netr9_get_data_dirs(ftp):
    """Get all data directories for NetR9 receiver"""
    date_dirs = []
    try:
        # Check both Internal and External directories
        for dir_type in ["Internal", "External"]:
            try:
                # Make sure we're in root directory
                ftp.cwd("/")
                dirs = parse_directory_listing(ftp, dir_type)
                for dirname in dirs:
                    if len(dirname) == 6 and dirname.isdigit():
                        date_dirs.append((dir_type.lower(), dirname))
            except Exception as e:
                logger.error(f"Error accessing {dir_type} directory: {e}")
    except Exception as e:
        logger.error(f"Error checking NetR9 directories: {e}")
    
    return date_dirs


def netrs_get_data_dirs(ftp):
    """Get all data directories for NetRS receiver"""
    date_dirs = []
    try:
        # Get list of directories in root
        dirs = parse_directory_listing(ftp, "/")
        for dirname in dirs:
            if len(dirname) == 6 and dirname.isdigit():
                date_dirs.append(("root", dirname))
    except Exception as e:
        logger.error(f"Error listing root directory: {e}")
    
    return date_dirs


def download_gnss_file(
    fqdn, gps_dirname, internal_gps_dirname, base_filename, today=False, m=None
):
    """Download a file from the receiver FTP server"""
    def download_operation(ftp):
        # First identify the receiver type
        receiver_type = identify_receiver_type(ftp)
        if not receiver_type:
            logger.error("Could not identify receiver type")
            return None, None, None
        logger.info(f"Detected receiver type: {receiver_type.value}")

        # Create a temporary file with the appropriate extension
        if receiver_type in [ReceiverType.NETR8, ReceiverType.NETR9]:
            temp_ext = ".RINEX.2.11.zip"
        elif receiver_type == ReceiverType.MOSAIC:
            # Get the year suffix dynamically from the TECMeasurementFile if available
            if m:
                temp_ext = f".{m.yy_str}o"
            else:
                temp_ext = ".o"  # Generic observation file extension if no year info
        else:  # NetRS
            temp_ext = ".T00"

        dnld_file = tempfile.NamedTemporaryFile(
            suffix=temp_ext, delete=False
        )

        try:
            # Try Mosaic directory structure first (if that's what we have)
            if receiver_type == ReceiverType.MOSAIC:
                try:
                    # For Mosaic, we need to find YYdoy directories
                    # Get the year and doy from the TECMeasurementFile
                    if m:
                        yydoy = f"{m.yy_str}{m.doy_str}"
                    else:
                        # Fallback to extracting from base_filename if m is not available
                        year_short = base_filename[2:4]

                    # Get list of root directories
                    root_dirs = []
                    try:
                        ftp.cwd("/")
                        dir_contents = []
                        ftp.retrlines("LIST", lambda x: dir_contents.append(x))

                        # Extract just the directory names
                        for line in dir_contents:
                            parts = line.split()
                            if len(parts) >= 9 and parts[0].startswith(
                                "d"
                            ):  # Only directories
                                dirname = " ".join(parts[8:])
                                root_dirs.append(dirname)
                    except Exception as e:
                        logger.error(f"Error listing root directory: {str(e)}")

                    # Function to recursively search for YYdoy directories
                    def find_yydoy_dir(
                        current_path, target_yydoy, max_depth=3, current_depth=0
                    ):
                        if current_depth >= max_depth:
                            return None

                        try:
                            ftp.cwd(current_path)

                            # List contents
                            dir_contents = []
                            ftp.retrlines(
                                "LIST", lambda x: dir_contents.append(x)
                            )

                            # Extract directories
                            dirs = []
                            for line in dir_contents:
                                parts = line.split()
                                if len(parts) >= 9 and parts[0].startswith(
                                    "d"
                                ):  # Only directories
                                    dirname = " ".join(parts[8:])
                                    dirs.append(dirname)

                            # Check if any directory matches YYdoy pattern
                            for dirname in dirs:
                                if (
                                    len(dirname) == 5
                                    and dirname.startswith(target_yydoy[:2])
                                    and dirname[2:].isdigit()
                                ):
                                    # This looks like a YYdoy directory
                                    if dirname == target_yydoy:
                                        return f"{current_path}/{dirname}"

                            # Recursively check subdirectories
                            for dirname in dirs:
                                result = find_yydoy_dir(
                                    f"{current_path}/{dirname}",
                                    target_yydoy,
                                    max_depth,
                                    current_depth + 1,
                                )
                                if result:
                                    return result

                            return None
                        except Exception as e:
                            logger.error(
                                f"Error checking directory {current_path}: {str(e)}"
                            )
                            return None

                    # Search for YYdoy directory starting from each root directory
                    yydoy_path = None
                    for root_dir in root_dirs:
                        path = find_yydoy_dir(f"/{root_dir}", yydoy)
                        if path:
                            yydoy_path = path
                            break

                    if not yydoy_path:
                        logger.error(f"Could not find YYdoy directory for {yydoy}")
                        return None, None, None

                    # Now we have the path to the YYdoy directory
                    # Look for RINEX observation files (ending with 'o')
                    try:
                        ftp.cwd(yydoy_path)

                        dir_contents = []
                        ftp.retrlines(
                            "LIST", lambda x: dir_contents.append(x)
                        )

                        # Extract filenames
                        file_list = []
                        for line in dir_contents:
                            parts = line.split()
                            if (
                                len(parts) >= 9
                            ):  # Standard Unix-like listing format
                                filename = " ".join(
                                    parts[8:]
                                )  # Filename is everything after the date/time
                                file_list.append(filename)

                        # Look for RINEX observation files which end with year+o (e.g., 25o, 24o)
                        # We'll check for both current year patterns and also common RINEX observation patterns
                        obs_patterns = []
                        if m:
                            obs_patterns.append(f".{m.yy_str}o")  # .25o
                            obs_patterns.append(f".{m.yy_str}O")  # .25O

                        # Always include generic pattern as fallback
                        obs_patterns.append("o")  # Generic ending with 'o'

                        remote_files = []
                        for pattern in obs_patterns:
                            pattern_files = [
                                f
                                for f in file_list
                                if f.lower().endswith(pattern.lower())
                            ]
                            remote_files.extend(pattern_files)

                        # Remove duplicates
                        remote_files = list(set(remote_files))

                        if remote_files:
                            remote_file = remote_files[0]
                            logger.info(f"Starting download of {remote_file}...")
                            ftp.retrbinary(
                                f"RETR {remote_file}", dnld_file.write
                            )
                            dnld_file.flush()
                            size = os.path.getsize(dnld_file.name)
                            return dnld_file, remote_file, receiver_type
                        else:
                            logger.error(
                                f"No RINEX observation files found in {yydoy_path}"
                            )
                    except Exception as e:
                        logger.error(
                            f"Error accessing YYdoy directory {yydoy_path}: {str(e)}"
                        )

                    logger.error("Could not find file in Mosaic directory structure")
                    return None, None, None
                except Exception as e:
                    logger.error(
                        f"Error traversing Mosaic directory structure: {str(e)}"
                    )

                    logger.error("Could not find file in Mosaic directory structure")
                    return None, None, None
            # Try NetR8/NetR9 directory structure
            elif receiver_type in [ReceiverType.NETR8, ReceiverType.NETR9]:
                try:
                    ftp.cwd(internal_gps_dirname)

                    # Extract just the filenames from the directory listing
                    dir_contents = []
                    ftp.retrlines(
                        "LIST", lambda x: dir_contents.append(x)
                    )

                    file_list = []
                    for line in dir_contents:
                        # Parse the line to extract just the filename at the end
                        parts = line.split()
                        if (
                            len(parts) >= 9
                        ):  # Standard Unix-like listing format
                            filename = " ".join(
                                parts[8:]
                            )  # Filename is everything after the date/time
                            file_list.append(filename)

                    # Filter for .RINEX.2.11.zip files
                    remote_files = [
                        f
                        for f in file_list
                        if f.endswith(".RINEX.2.11.zip")
                    ]

                    # Filter files by date if we have m
                    if m and remote_files:
                        # Extract date from base_filename (YYYYMMDD)
                        target_date = base_filename[:8]
                        # Try to find a file with the correct date in its name
                        matching_files = [
                            f for f in remote_files if target_date in f
                        ]
                        if matching_files:
                            remote_files = matching_files

                    if remote_files:
                        remote_file = remote_files[0]
                        logger.info(f"Starting download of {remote_file} (converting on-the-fly)...")
                        ftp.retrbinary(
                            f"RETR {remote_file}", dnld_file.write
                        )
                        dnld_file.flush()
                        size = os.path.getsize(dnld_file.name)
                        return dnld_file, remote_file, receiver_type
                except Exception as e:
                    logger.error(
                        f"Error accessing NetR8/9 directory {internal_gps_dirname}: {str(e)}"
                    )

                # Try looking in root level directory as well
                try:
                    ftp.cwd("/")

                    # Extract just the filenames from the directory listing
                    dir_contents = []
                    ftp.retrlines(
                        "LIST", lambda x: dir_contents.append(x)
                    )

                    file_list = []
                    for line in dir_contents:
                        # Parse the line to extract just the filename at the end
                        parts = line.split()
                        if (
                            len(parts) >= 9
                        ):  # Standard Unix-like listing format
                            filename = " ".join(
                                parts[8:]
                            )  # Filename is everything after the date/time
                            file_list.append(filename)

                    # Filter for .RINEX.2.11.zip files
                    remote_files = [
                        f
                        for f in file_list
                        if f.endswith(".RINEX.2.11.zip")
                    ]

                    # Filter files by date if we have m
                    if m and remote_files:
                        # Extract date from base_filename (YYYYMMDD)
                        target_date = base_filename[:8]
                        # Try to find a file with the correct date in its name
                        matching_files = [
                            f for f in remote_files if target_date in f
                        ]
                        if matching_files:
                            remote_files = matching_files

                    if remote_files:
                        remote_file = remote_files[0]
                        logger.info(f"Starting download of {remote_file} (converting on-the-fly)...")
                        ftp.retrbinary(
                            f"RETR {remote_file}", dnld_file.write
                        )
                        dnld_file.flush()
                        size = os.path.getsize(dnld_file.name)
                        return dnld_file, remote_file, receiver_type
                except Exception as e:
                    logger.error(f"Error accessing root directory: {str(e)}")

                logger.error("Could not find file in NetR8/9 directory structure")
                return None, None, None
            else:  # NetRS
                try:
                    ftp.cwd(gps_dirname)

                    # Extract just the filenames from the directory listing
                    dir_contents = []
                    ftp.retrlines(
                        "LIST", lambda x: dir_contents.append(x)
                    )

                    file_list = []
                    for line in dir_contents:
                        # Parse the line to extract just the filename at the end
                        parts = line.split()
                        if (
                            len(parts) >= 9
                        ):  # Standard Unix-like listing format
                            filename = " ".join(
                                parts[8:]
                            )  # Filename is everything after the date/time
                            file_list.append(filename)

                    # Filter for T00 files
                    remote_files = [f for f in file_list if f.endswith(".T00")]

                    # Filter files by date if we have m
                    if m and remote_files:
                        # Extract date from base_filename (YYYYMMDD)
                        target_date = base_filename[:8]
                        # Try to find a file with the correct date in its name
                        matching_files = [
                            f for f in remote_files if target_date in f
                        ]
                        if matching_files:
                            remote_files = matching_files

                    if remote_files:
                        remote_file = remote_files[0]
                        logger.info(f"Starting download of {remote_file}...")
                        ftp.retrbinary(
                            f"RETR {remote_file}", dnld_file.write
                        )
                        dnld_file.flush()
                        size = os.path.getsize(dnld_file.name)
                        return dnld_file, remote_file, receiver_type
                except Exception as e:
                    logger.error(
                        f"Error accessing NetRS directory {gps_dirname}: {str(e)}"
                    )

                logger.error("Could not find file in NetRS directory structure")
                return None, None, None

        except Exception as e:
            logger.error(f"Error downloading file: {str(e)}")
            return None, None, None

    return with_ftp_connection(fqdn, download_operation)


def download_all_new_files(fqdn, measurement_path, station, args, measurement_class):
    """
    Download all new RINEX files from the FTP server.

    Args:
        fqdn (str): FQDN of the receiver
        measurement_path (str): Path where files will be stored
        station (str): Station name
        args: Command line arguments containing organization, user, marker_num, etc.
        measurement_class: The class to use for creating measurement file objects

    Returns:
        bool: True if successful, False otherwise
    """
    def download_operation(ftp):
        # First identify the receiver type
        receiver_type = identify_receiver_type(ftp)
        if not receiver_type:
            logger.error("Could not identify receiver type")
            return False

        logger.info(f"Identified receiver type: {receiver_type.value}")

        # Get data directories based on receiver type
        if receiver_type == ReceiverType.MOSAIC:
            data_dirs = mosaic_get_data_dirs(ftp)
            if not data_dirs:
                logger.error("No YYdoy directories found")
                return False
            logger.info(f"Found {len(data_dirs)} YYdoy directories")
        elif receiver_type == ReceiverType.NETR8:
            data_dirs = netr8_get_data_dirs(ftp)
            if not data_dirs:
                logger.error("No date directories found in Internal")
                return False
            logger.info(f"Found {len(data_dirs)} date directories in Internal")
        elif receiver_type == ReceiverType.NETR9:
            data_dirs = netr9_get_data_dirs(ftp)
            if not data_dirs:
                logger.error("No date directories found in Internal/External")
                return False
            logger.info(f"Found {len(data_dirs)} date directories in Internal/External")
        else:  # NetRS
            data_dirs = netrs_get_data_dirs(ftp)
            if not data_dirs:
                logger.error("No date directories found")
                return False
            logger.info(f"Found {len(data_dirs)} date directories")

        # Process each directory
        for dir_info in data_dirs:
            try:
                # Construct the full path based on directory type
                if isinstance(dir_info, tuple):
                    dir_type, date_dir = dir_info
                    if dir_type == "internal":
                        full_path = f"Internal/{date_dir}"
                    elif dir_type == "external":
                        full_path = f"External/{date_dir}"
                    else:
                        full_path = date_dir
                else:
                    # For NetRS, the directory is already the full path
                    full_path = dir_info

                try:
                    # For NetR8 and NetR9, we need to be in root directory first
                    if receiver_type in [ReceiverType.NETR8, ReceiverType.NETR9]:
                        ftp.cwd("/")
                    ftp.cwd(full_path)
                    logger.info(f"Processing directory: {full_path}")
                except ftp_errors as e:
                    logger.error(f"Couldn't access directory {full_path}: {e}")
                    continue

                # Get list of files in current directory
                dir_contents = []
                ftp.retrlines("LIST", lambda x: dir_contents.append(x))
                
                remote_files = []
                for line in dir_contents:
                    # Parse the line to extract just the filename at the end
                    parts = line.split()
                    if len(parts) >= 9:  # Standard Unix-like listing format
                        filename = " ".join(parts[8:])  # Filename is everything after the date/time
                        remote_files.append(filename)

                # Filter for target files based on receiver type
                target_files = get_target_files(remote_files, receiver_type)

                if not target_files:
                    logger.info(f"No target files found in {full_path}")
                    continue

                logger.info(f"Found {len(target_files)} target files in {full_path}")

                # Process each file
                for remote_file in target_files:
                    try:
                        # Extract date information from filename
                        year, doy = extract_date_from_filename(remote_file, receiver_type)
                        if not year or not doy:
                            logger.error(f"Could not extract date information from {remote_file}")
                            continue

                        # Create measurement file object for this file
                        m = measurement_class(measurement_path, year, doy, station_name=station)

                        # Create tempfile with appropriate extension
                        temp_ext = get_temp_extension(receiver_type)
                        dnld_file = tempfile.NamedTemporaryFile(suffix=temp_ext, delete=False)

                        # Download the file
                        try:
                            logger.info(f"Starting download of {remote_file}...")
                            response = ftp.retrbinary("RETR " + remote_file, dnld_file.write, 1024)
                            dnld_file.flush()  # Ensure all data is written to disk
                        except ftp_errors as e:
                            logger.error(f"Couldn't download {remote_file}: {e}")
                            os.remove(dnld_file.name)
                            continue

                        # Check if download was successful
                        if not response.startswith("226"):
                            logger.error(f"Transfer error for {remote_file}. File may be incomplete.")
                            os.remove(dnld_file.name)
                            continue

                        # Check file size
                        tmpsize = os.path.getsize(dnld_file.name)
                        if tmpsize == 0:
                            logger.error(f"Downloaded file {remote_file} was empty")
                            os.remove(dnld_file.name)
                            continue

                        # Process the downloaded file
                        if process_downloaded_file(dnld_file, receiver_type, station, args, m):
                            # Get file sizes for logging
                            zip_size = os.path.getsize(dnld_file.name)
                            rinex_size = os.path.getsize(m.daily_dnld_path) if os.path.exists(m.daily_dnld_path) else 0
                            
                            if receiver_type == ReceiverType.NETRS:
                                logger.info(f"Downloaded {remote_file} ({format_filesize(zip_size)}) and converted to RINEX ({format_filesize(rinex_size)})")
                            elif receiver_type in [ReceiverType.NETR8, ReceiverType.NETR9]:
                                logger.info(f"Downloaded {remote_file} ({format_filesize(zip_size)}) and extracted RINEX from zip ({format_filesize(rinex_size)})")
                            else:  # MOSAIC
                                logger.info(f"Downloaded {remote_file} ({format_filesize(zip_size)}) (RINEX file)")
                        else:
                            logger.error(f"Downloaded {remote_file} but processing failed")

                        os.remove(dnld_file.name)

                    except Exception as e:
                        logger.error(f"Error processing {remote_file}: {e}")
                        continue

                # Go back to root directory for next iteration
                ftp.cwd("/")

            except Exception as e:
                logger.error(f"Error processing directory {dir_info}: {e}")
                continue

        return True

    return with_ftp_connection(fqdn, download_operation)


def process_downloaded_file(
    downloaded_file, receiver_type, station, args, m
):
    """Process a downloaded file based on receiver type"""
    logger.debug(f"Processing downloaded file: {downloaded_file.name} for receiver type {receiver_type.value}")

    try:
        if receiver_type == ReceiverType.NETRS:
            # For NetRS, use convert_netrs
            if convert_netrs(
                downloaded_file.name,
                m.daily_dnld_path,
                args.user
            ):
                # Edit RINEX header with station metadata
                if edit_rinex_header(
                    m.daily_dnld_path,
                    m,
                    station,
                    args.organization,
                    args.user,
                    args.antenna_type,
                    args.station_cartesian,
                    args.station_llh,
                    args.marker_num,
                    args.antenna_number,
                    receiver_type.value
                ):
                    if os.path.exists(m.daily_dnld_path):
                        size = os.path.getsize(m.daily_dnld_path)
                        logger.debug(f"Extracted RINEX file {os.path.basename(m.daily_dnld_path)} ({format_filesize(size)})")
                    return True
                return False
            return False

        elif receiver_type in [ReceiverType.NETR8, ReceiverType.NETR9]:
            try:
                # For NetR8/NetR9, extract RINEX file from zip
                with zipfile.ZipFile(downloaded_file.name, "r") as zip_ref:
                    # List contents for debugging
                    logger.debug("Zip contents: " + str(zip_ref.namelist()))

                    # Find the RINEX observation file
                    # Look for files ending with two digits + O/o (e.g., .25O, .26O, .25o, .26o)
                    rinex_files = []
                    for f in zip_ref.namelist():
                        # Check for two digits followed by O or o (e.g., .25O, .26O, .25o, .26o)
                        if re.search(r'\.\d{2}[Oo]$', f):
                            rinex_files.append(f)
                    
                    if not rinex_files:
                        logger.error("No RINEX observation files found in zip")
                        return False

                    logger.debug(f"Found RINEX files: {rinex_files}")
                    logger.debug(f"Extracting observation file to {m.daily_dnld_path}")
                    zip_ref.extract(rinex_files[0], os.path.dirname(m.daily_dnld_path))
                    os.rename(
                        os.path.join(os.path.dirname(m.daily_dnld_path), rinex_files[0]),
                        m.daily_dnld_path,
                    )

                    if os.path.exists(m.daily_dnld_path):
                        size = os.path.getsize(m.daily_dnld_path)
                        logger.debug(f"Extracted RINEX file {os.path.basename(m.daily_dnld_path)} ({format_filesize(size)})")
                        # Edit RINEX header with station metadata
                        return edit_rinex_header(
                            m.daily_dnld_path,
                            m,
                            station,
                            args.organization,
                            args.user,
                            args.antenna_type,
                            args.station_cartesian,
                            args.station_llh,
                            args.marker_num,
                            args.antenna_number,
                            receiver_type.value
                        )
                    else:
                        logger.error("Extracted file not found")
                        return False

            except zipfile.BadZipFile:
                logger.error("Invalid zip file")
                return False
            except Exception as e:
                logger.error(f"Error extracting zip: {str(e)}")
                return False

        elif receiver_type == ReceiverType.MOSAIC:
            try:
                # For Mosaic, just copy the RINEX file
                shutil.copy2(downloaded_file.name, m.daily_dnld_path)

                if os.path.exists(m.daily_dnld_path):
                    size = os.path.getsize(m.daily_dnld_path)
                    logger.debug(f"Copied Mosaic RINEX observation file to {m.daily_dnld_path} ({format_filesize(size)})")
                    # Edit RINEX header with station metadata
                    return edit_rinex_header(
                        m.daily_dnld_path,
                        m,
                        station,
                        args.organization,
                        args.user,
                        args.antenna_type,
                        args.station_cartesian,
                        args.station_llh,
                        args.marker_num,
                        args.antenna_number,
                        receiver_type.value
                    )
                else:
                    logger.error("Failed to copy Mosaic RINEX observation file")
                    return False

            except Exception as e:
                logger.error(f"Error processing Mosaic file: {str(e)}")
                return False

        else:
            logger.error(f"Unsupported receiver type: {receiver_type.value}")
            return False

    except Exception as e:
        logger.error(f"Error processing downloaded file: {str(e)}")
        return False
