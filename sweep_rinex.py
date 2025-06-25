#!/usr/bin/env python3

############################################################
# sweep_rinex.py v.20250624.1
# copyright 2025 John Ackermann N8UR jra@febo.com
#
# Program to sweep RINEX files from user upload directories
# and organize them into year/doy directory structure.
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

# NOTE -- this is backwards compatible with Python 3.5 as it
# does not use f vars the way the original version did.

import os
import sys
import shutil
import logging
import datetime
import glob
from pathlib import Path
import tempfile
import time
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/var/log/sweep_rinex.log"),
        logging.StreamHandler(),
    ],
)

# Constants
# This is where the swept files are deposited, in YY/DOY directories.
BASE_RINEX_DIR = "/sftp/users/haystack/data"

# This is the source where the script looks for user upload directories.
SFTP_USERS_BASE_DIR = "/sftp/users"
UPLOADS_DIR = "uploads"

# List of file prefixes to ignore (first 4 characters)
IGNORED_PREFIXES = ["hs00"]


def get_doy_from_filename(filename):
    """
    Extract day of year from filename patterns like YYYYMMDD, YYYYDDD,
    or stationDDD0.YYo, including compressed files.
    """
    try:
        # Look for the pattern: station name followed by DOY0.YYo
        # This handles the format: hsXXDOY0.YYo (e.g., hs000010.25o)
        # It looks for the pattern anywhere in the filename, ignoring
        # final extensions like .gz or .Z.
        match = re.search(r"[a-zA-Z0-9_-]+(\d{3})0\.(\d{2})o", filename)
        if match:
            doy = int(match.group(1))
            year_yy = int(match.group(2))
            # Handle century for 2-digit years. Assumes files from 1980-2079.
            year = 2000 + year_yy if year_yy < 80 else 1900 + year_yy
            return year, doy

        # Use regex for YYYYMMDD to find it anywhere in the name.
        # This pattern is checked before YYYYDDD to avoid ambiguity.
        match = re.search(r"(\d{4})(\d{2})(\d{2})", filename)
        if match:
            date_str = "".join(match.groups())
            date = datetime.datetime.strptime(date_str, "%Y%m%d")
            return date.year, date.timetuple().tm_yday

        # Use regex for YYYYDDD to find it anywhere in the name.
        match = re.search(r"(\d{4})(\d{3})", filename)
        if match:
            year = int(match.group(1))
            doy = int(match.group(2))
            return year, doy

    except (ValueError, IndexError):
        pass

    return None, None


def create_directory_structure(year, doy):
    """Create the year/doy directory structure if it doesn't exist"""
    target_dir = os.path.join(BASE_RINEX_DIR, str(year), str(doy).zfill(3))
    try:
        os.makedirs(target_dir, exist_ok=True)
        return target_dir
    except Exception as e:
        logging.error(
            "Failed to create directory {}: {}".format(target_dir, e)
        )
        return None


def move_file_safely(src_path, dest_dir, filename):
    """Safely move a file using a temporary file as intermediate step"""
    temp_file = None
    temp_path = None  # Initialize to prevent NameError in except block
    try:
        # Create temporary file in the destination directory
        temp_file = tempfile.NamedTemporaryFile(
            dir=dest_dir,
            prefix=".sweep_",
            suffix=os.path.splitext(filename)[1],
            delete=False,
        )
        temp_path = temp_file.name
        temp_file.close()

        # Copy the file to temporary location
        shutil.copy2(src_path, temp_path)

        # Verify the copy was successful
        if os.path.getsize(temp_path) != os.path.getsize(src_path):
            raise Exception("File size mismatch after copy")

        # Move the temporary file to final location
        final_path = os.path.join(dest_dir, filename)
        os.rename(temp_path, final_path)

        # Remove the original file only after successful move
        os.remove(src_path)

        return True

    except Exception as e:
        logging.error("Error moving {}: {}".format(filename, e))
        # Clean up temporary file if it exists
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        return False


def process_user_directory(user_dir):
    """Process files in a user's upload directory"""
    user_name = os.path.basename(user_dir)
    
    # We want to skip processing the 'haystack' directory itself
    if user_name == "haystack":
        logging.info("Skipping sweep of the destination directory 'haystack'.")
        return

    uploads_path = os.path.join(user_dir, UPLOADS_DIR)
    if not os.path.exists(uploads_path):
        return

    try:
        files = os.listdir(uploads_path)
    except Exception as e:
        logging.error("Error reading directory {}: {}".format(uploads_path, e))
        return

    if not files:
        return

    logging.info("Found {} files in user '{}' uploads directory: {}".format(len(files), user_name, uploads_path))

    for filename in files:
        src_path = os.path.join(uploads_path, filename)
        if not os.path.isfile(src_path):
            continue

        # Check if file should be ignored based on prefix
        if len(filename) >= 4:
            file_prefix = filename[:4]
            if file_prefix in IGNORED_PREFIXES:
                logging.info("User '{}': Ignoring file with prefix '{}': {}".format(user_name, file_prefix, filename))
                continue

        year, doy = get_doy_from_filename(filename)
        if not year or not doy:
            logging.warning(
                "User '{}': Could not determine year/doy from filename: {}".format(
                    user_name, filename
                )
            )
            continue

        target_dir = create_directory_structure(year, doy)
        if not target_dir:
            continue

        success = move_file_safely(src_path, target_dir, filename)
        if success:
            logging.info("User '{}': Successfully moved '{}' to {}".format(user_name, filename, target_dir))
        else:
            logging.error("User '{}': Failed to move '{}' to {}".format(user_name, filename, target_dir))


def main():
    """Main function to sweep RINEX files"""
    start_time = time.time()
    logging.info("Starting RINEX file sweep")

    try:
        user_dirs = [
            d
            for d in os.listdir(SFTP_USERS_BASE_DIR)
            if os.path.isdir(os.path.join(SFTP_USERS_BASE_DIR, d))
        ]
    except Exception as e:
        logging.error("Error reading SFTP users directory: {}".format(e))
        sys.exit(1)

    for user in user_dirs:
        user_dir = os.path.join(SFTP_USERS_BASE_DIR, user)
        process_user_directory(user_dir)

    elapsed_time = time.time() - start_time
    logging.info(
        "RINEX file sweep completed in {:.2f} seconds".format(elapsed_time)
    )


if __name__ == "__main__":
    main()
