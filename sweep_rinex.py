#!/usr/bin/env python3

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


def get_doy_from_filename(filename):
    """Extract day of year from filename patterns like YYYYMMDD, YYYYDDD, or stationDDD0.YYo"""
    try:
        # Try stationDDD0.YYo pattern (e.g., n8ur1590.25o) first
        match = re.search(r"[a-zA-Z0-9]+(\d{3})0\.(\d{2})o", filename)
        if match:
            doy = int(match.group(1))
            year = 2000 + int(match.group(2))  # Convert YY to YYYY
            return year, doy

        # Try YYYYMMDD pattern
        if len(filename) >= 8:
            date_str = filename[:8]
            date = datetime.datetime.strptime(date_str, "%Y%m%d")
            return date.year, date.timetuple().tm_yday

        # Try YYYYDDD pattern
        if len(filename) >= 7:
            year = int(filename[:4])
            doy = int(filename[4:7])
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
        logging.error(f"Failed to create directory {target_dir}: {e}")
        return None


def move_file_safely(src_path, dest_dir, filename):
    """Safely move a file using a temporary file as intermediate step"""
    temp_file = None
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

        logging.info(f"Moved {filename} to {dest_dir}")
        return True

    except Exception as e:
        logging.error(f"Error moving {filename}: {e}")
        # Clean up temporary file if it exists
        if temp_file and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        return False


def process_user_directory(user_dir):
    """Process files in a user's upload directory"""
    # We want to skip processing the 'haystack' directory itself
    if os.path.basename(user_dir) == "haystack":
        logging.info("Skipping sweep of the destination directory 'haystack'.")
        return

    uploads_path = os.path.join(user_dir, UPLOADS_DIR)
    if not os.path.exists(uploads_path):
        return

    try:
        files = os.listdir(uploads_path)
    except Exception as e:
        logging.error(f"Error reading directory {uploads_path}: {e}")
        return

    if not files:
        return

    logging.info(f"Found files in {uploads_path}")

    for filename in files:
        src_path = os.path.join(uploads_path, filename)
        if not os.path.isfile(src_path):
            continue

        year, doy = get_doy_from_filename(filename)
        if not year or not doy:
            logging.warning(
                f"Could not determine year/doy from filename: {filename}"
            )
            continue

        target_dir = create_directory_structure(year, doy)
        if not target_dir:
            continue

        move_file_safely(src_path, target_dir, filename)


def main():
    """Main function to sweep RINEX files"""
    start_time = time.time()
    logging.info("Starting RINEX file sweep")

    # The script will automatically create the destination directory if needed
    # but it's good practice to ensure its parent exists and has correct perms.

    try:
        user_dirs = [
            d
            for d in os.listdir(SFTP_USERS_BASE_DIR)
            if os.path.isdir(os.path.join(SFTP_USERS_BASE_DIR, d))
        ]
    except Exception as e:
        logging.error(f"Error reading SFTP users directory: {e}")
        sys.exit(1)

    for user in user_dirs:
        user_dir = os.path.join(SFTP_USERS_BASE_DIR, user)
        process_user_directory(user_dir)

    elapsed_time = time.time() - start_time
    logging.info(f"RINEX file sweep completed in {elapsed_time:.2f} seconds")


if __name__ == "__main__":
    main()
