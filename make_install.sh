#!/bin/bash

# A simple script to create a distributable tar.gz package.
# It archives the contents of the 'install' directory, following
# symbolic links to include the actual files.

# --- Configuration ---
# The directory containing the staged installation files.
INSTALL_DIR="install"

# The desired name for the final archive file.
# Using the current date in the filename is a good practice.
DATE=$(date "+%Y-%m-%d")
ARCHIVE_NAME="get_gnss_ftp-${DATE}.tar.gz"

# --- Script Logic ---

# Check if the install directory exists before we start.
if [ ! -d "$INSTALL_DIR" ]; then
  echo "Error: Directory '$INSTALL_DIR/' not found."
  echo "Please run this script from the directory that contains '$INSTALL_DIR/'."
  exit 1
fi

echo "Creating package from '$INSTALL_DIR/' directory..."
echo "Output file will be: $ARCHIVE_NAME"

# Create the tar archive.
#
# FLAGS EXPLAINED:
# c = create a new archive
# z = compress the archive with gzip
# v = verbose mode (lists files as they are processed)
# h = dereference (follow) symbolic links, archiving the files they point to
# f = specifies the archive filename
#
# OPTIONS EXPLAINED:
# -C "$INSTALL_DIR" = Change to the INSTALL_DIR directory before adding files.
#                     This prevents the 'install/' path from being in the archive.
# .                 = Add all files from the current directory (which -C changed to INSTALL_DIR)

tar -czvhf "$ARCHIVE_NAME" -C "$INSTALL_DIR" .

# Check the exit code of the tar command to confirm success.
if [ $? -eq 0 ]; then
  echo "" # Add a newline for cleaner output
  echo "Success! Package created: $(pwd)/$ARCHIVE_NAME"
  echo "You can inspect its contents with: tar -tvf $ARCHIVE_NAME"
else
  echo "" # Add a newline for cleaner output
  echo "Error: Failed to create the archive."
  exit 1
fi

exit 0
