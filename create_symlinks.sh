#!/bin/bash

# Get the absolute path of the current directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Define the target directories
LOCAL_LIB="/usr/local/lib/gnss_ftp"
INSTALL_LIB="/home/jra/gnss_ftp/install/usr/local/lib/gnss_ftp"

# Create target directories if they don't exist
sudo mkdir -p "$LOCAL_LIB"
sudo mkdir -p "$INSTALL_LIB"

# List of files to create symlinks for
FILES=(
    "conversion_funcs.py"
    "ftp_funcs.py"
    "gnss_file_tools.py"
    "gnsscal.py"
    "sftp_funcs.py"
)

# Create symlinks in both locations
for file in "${FILES[@]}"; do
    # Create symlink in /usr/local/lib/gnss_ftp
    sudo ln -sf "$SCRIPT_DIR/$file" "$LOCAL_LIB/$file"
    echo "Created symlink for $file in $LOCAL_LIB"
    
    # Create symlink in install directory
    sudo ln -sf "$SCRIPT_DIR/$file" "$INSTALL_LIB/$file"
    echo "Created symlink for $file in $INSTALL_LIB"
done

echo "All symlinks have been created successfully!" 