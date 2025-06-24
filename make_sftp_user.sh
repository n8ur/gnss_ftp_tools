#!/bin/bash

############################################################
# make_sftp_user.sh v.20250624.1
# copyright 2025 John Ackermann N8UR jra@febo.com
#
# Script to create SFTP users with chroot jail configuration
# for secure file uploads to the GNSS data collection system.
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

# Configuration
SFTP_GROUP="sftpusers"
# We've changed this from /home to a dedicated directory
USER_BASE_DIR="/sftp/users"

# --- SCRIPT START ---

echo "--- SFTP User Setup Script (Revised) ---"

# Check if the script is run as root
if [[ $EUID -ne 0 ]]; then
  echo "This script must be run as root."
  exit 1
fi

# Create the base directory for all SFTP users if it doesn't exist
if [ ! -d "$USER_BASE_DIR" ]; then
  echo "Base directory '$USER_BASE_DIR' does not exist. Creating it..."
  mkdir -p "$USER_BASE_DIR"
  chmod 755 "$USER_BASE_DIR"
  chown root:root "$USER_BASE_DIR"
  echo "Base directory created."
fi

# Ensure the sftpusers group exists
if ! getent group "$SFTP_GROUP" >/dev/null; then
  echo "Group '$SFTP_GROUP' does not exist. Creating it..."
  addgroup "$SFTP_GROUP"
  if [ $? -ne 0 ]; then
    echo "Error creating group '$SFTP_GROUP'. Exiting."
    exit 1
  fi
else
  echo "Group '$SFTP_GROUP' already exists."
fi

# Loop to add multiple users
while true; do
  read -p "Enter username for the new SFTP user (or 'quit' to finish): " USERNAME

  if [[ "$USERNAME" == "quit" ]]; then
    break
  fi

  if [[ -z "$USERNAME" ]]; then
    echo "Username cannot be empty. Please try again."
    continue
  fi

  if id -u "$USERNAME" >/dev/null 2>&1; then
    echo "User '$USERNAME' already exists. Please choose a different username."
    continue
  fi

  echo "Setting up user: $USERNAME"
  USER_HOME="$USER_BASE_DIR/$USERNAME"

  # 1. Create the user
  # --home specifies the new location
  # --shell makes it explicit this user cannot log in
  adduser --home "$USER_HOME" --shell "/usr/sbin/nologin" \
    --no-create-home --disabled-password --gecos "" "$USERNAME"

  usermod -G "$SFTP_GROUP" "$USERNAME"
  if [ $? -ne 0 ]; then
    echo "Error adding user '$USERNAME'. Exiting."
    exit 1
  fi
  echo "User '$USERNAME' created and added to group '$SFTP_GROUP'."

  # 2. Create and Adjust Home Directory Permissions for Chroot
  # The user's home directory itself must be owned by root
  mkdir -p "$USER_HOME"
  chown root:root "$USER_HOME"
  chmod 755 "$USER_HOME"
  echo "Set permissions for chroot jail '$USER_HOME'."

  # 3. Create the writable 'uploads' directory
  UPLOAD_DIR="$USER_HOME/uploads"
  mkdir -p "$UPLOAD_DIR"
  chown "$USERNAME":"$SFTP_GROUP" "$UPLOAD_DIR"
  chmod 775 "$UPLOAD_DIR"
  echo "Created writable directory '$UPLOAD_DIR' for user '$USERNAME'."

  # 4. Set Password (Optional, for SFTP password auth)
  read -p "Do you want to set a password for '$USERNAME'? (y/n): " SET_PASSWORD
  if [[ "$SET_PASSWORD" =~ ^[Yy]$ ]]; then
    passwd "$USERNAME"
  fi

  # 5. Add SSH Public Key (Recommended)
  read -p "Do you want to add an SSH public key for '$USERNAME'? (y/n): " ADD_SSH_KEY
  if [[ "$ADD_SSH_KEY" =~ ^[Yy]$ ]]; then
    read -p "Paste the SSH public key for '$USERNAME': " PUBLIC_KEY

    if [[ -n "$PUBLIC_KEY" ]]; then
      SSH_DIR="$USER_HOME/.ssh"
      AUTH_KEYS_FILE="$SSH_DIR/authorized_keys"

      mkdir -p "$SSH_DIR"
      chmod 700 "$SSH_DIR"
      touch "$AUTH_KEYS_FILE"
      chmod 600 "$AUTH_KEYS_FILE"
      echo "$PUBLIC_KEY" >>"$AUTH_KEYS_FILE"
      chown -R "$USERNAME":"$SFTP_GROUP" "$SSH_DIR"
      echo "SSH public key added for '$USERNAME'."
    else
      echo "No public key provided. Skipping SSH key setup."
    fi
  fi

  echo "--- User '$USERNAME' setup complete. ---"
  echo ""
done

echo "Configuration complete. Ensure your /etc/ssh/sshd_config is set up for this group."
echo "Example sshd_config:"
echo "Match Group $SFTP_GROUP"
echo "  ChrootDirectory %h"
echo "  ForceCommand internal-sftp"
echo "  AllowTcpForwarding no"
echo "  X11Forwarding no"
echo ""
echo "Then restart the SSH service: sudo systemctl restart ssh"
echo "--- Script Finished ---"
