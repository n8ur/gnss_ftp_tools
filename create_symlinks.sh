#!/bin/bash

# Get the absolute path of the current directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Define the target directories
LOCAL_LIB="/usr/local/lib/gnss_ftp"
INSTALL_LIB="/home/jra/gnss_ftp/install/usr/local/lib/gnss_ftp"
SYSTEMD_DIR="/etc/systemd/system"
INSTALL_SYSTEMD_DIR="/home/jra/gnss_ftp/install/etc/systemd/system"
LOCAL_BIN="/usr/local/bin"
INSTALL_BIN="/home/jra/gnss_ftp/install/usr/local/bin"

# Create target directories if they don't exist
sudo mkdir -p "$LOCAL_LIB"
sudo mkdir -p "$INSTALL_LIB"
sudo mkdir -p "$SYSTEMD_DIR"
sudo mkdir -p "$INSTALL_SYSTEMD_DIR"
sudo mkdir -p "$LOCAL_BIN"
sudo mkdir -p "$INSTALL_BIN"

# List of Python library files to create symlinks for
FILES=(
    "conversion_funcs.py"
    "ftp_funcs.py"
    "gnss_file_tools.py"
    "gnsscal.py"
    "sftp_funcs.py"
)

# Create symlinks for Python library files
for file in "${FILES[@]}"; do
    # Create symlink in /usr/local/lib/gnss_ftp
    sudo ln -sf "$SCRIPT_DIR/$file" "$LOCAL_LIB/$file"
    echo "Created symlink for $file in $LOCAL_LIB"
    
    # Create symlink in install directory
    sudo ln -sf "$SCRIPT_DIR/$file" "$INSTALL_LIB/$file"
    echo "Created symlink for $file in $INSTALL_LIB"
done

# Create symlinks for systemd files
SYSTEMD_FILES=(
    "gnss_ftp.service"
    "gnss_ftp.timer"
)

for file in "${SYSTEMD_FILES[@]}"; do
    # Create symlink in /etc/systemd/system
    sudo ln -sf "$SCRIPT_DIR/$file" "$SYSTEMD_DIR/$file"
    echo "Created symlink for $file in $SYSTEMD_DIR"
    
    # Create symlink in install directory
    sudo ln -sf "$SCRIPT_DIR/$file" "$INSTALL_SYSTEMD_DIR/$file"
    echo "Created symlink for $file in $INSTALL_SYSTEMD_DIR"
done

# Create symlink for the main Python script and config script
sudo ln -sf "$SCRIPT_DIR/get_gnss_ftp.py" "$LOCAL_BIN/get_gnss_ftp.py"
sudo ln -sf "$SCRIPT_DIR/get_gnss_ftp.sh" "$LOCAL_BIN/get_gnss_ftp.sh"
echo "Created symlink for get_gnss_ftp.py and get_gnss_ftp.sh in $LOCAL_BIN"

sudo ln -sf "$SCRIPT_DIR/get_gnss_ftp.py" "$INSTALL_BIN/get_gnss_ftp.py"
sudo ln -sf "$SCRIPT_DIR/get_gnss_ftp.sh" "$INSTALL_BIN/get_gnss_ftp.sh"
echo "Created symlink for get_gnss_ftp.py and get_gnss_ftp.sh  in $INSTALL_BIN"

# Copy binary files from bin directory
BIN_FILES=(
    "runpkr00"
    "teqc"
)

for file in "${BIN_FILES[@]}"; do
    # Copy to /usr/local/bin
    sudo cp -f "$SCRIPT_DIR/bin/$file" "$LOCAL_BIN/$file"
    sudo chmod +x "$LOCAL_BIN/$file"
    echo "Copied $file to $LOCAL_BIN"
    
    # Copy to install directory
    sudo cp -f "$SCRIPT_DIR/bin/$file" "$INSTALL_BIN/$file"
    sudo chmod +x "$INSTALL_BIN/$file"
    echo "Copied $file to $INSTALL_BIN"
done

echo "All symlinks and binary files have been created successfully!" 
