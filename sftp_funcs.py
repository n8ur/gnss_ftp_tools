#!/usr/bin/env python3

############################################################
# sftp_funcs.py v.20250622.1
# copyright 2025 John Ackermann N8UR jra@febo.com
#
# Functions for SFTP operations including host key management
# and file uploads to SFTP servers.
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
import paramiko
import socket
import shutil
import gzip
import zipfile
import logging

# Suppress paramiko's INFO level messages
logging.getLogger("paramiko").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

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
        logger.error(f"Error getting host key: {str(e)}")
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
            logger.error(f"Could not resolve SFTP hostname '{sftp_host}'")
            return
        except socket.timeout:
            logger.error(f"Connection to SFTP server '{sftp_host}' timed out")
            return
        except paramiko.AuthenticationException:
            logger.error(f"Authentication failed for SFTP server '{sftp_host}'")
            return
        except paramiko.SSHException as e:
            logger.error(f"Error connecting to SFTP server '{sftp_host}': {e}")
            return
        except Exception as e:
            logger.error(f"Error connecting to SFTP server '{sftp_host}': {e}")
            return
        
        # Create processed directory if it doesn't exist
        processed_dir = os.path.join(measurement_path, "processed")
        os.makedirs(processed_dir, exist_ok=True)
        
        # Get all files from download directory
        download_dir = os.path.join(measurement_path, "download")
        files = os.listdir(download_dir)
        if not files:
            logger.warning("No files found in download directory")
            return
            
        logger.info(f"Found {len(files)} files to upload")
        
        # Create SSH client with auto-accept of unknown hosts
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            ssh.connect(sftp_host, username=sftp_user, password=sftp_pass)
            logger.debug("SFTP connection established")
            sftp = ssh.open_sftp()
            logger.debug("SFTP session opened")
        except Exception as e:
            logger.error(f"Error establishing SFTP connection: {e}")
            return
            
        # Check uploads directory
        uploads_dir = "uploads"
        try:
            sftp.stat(uploads_dir)
        except Exception as e:
            logger.error(f"Error accessing uploads directory: {e}")
            return
        
        # Upload each file
        for file in files:
            local_path = os.path.join(download_dir, file)
            if os.path.isfile(local_path):
                try:
                    logger.debug(f"Processing {file} for upload...")
                    
                    # Create gzipped version of the file for SFTP upload
                    gzip_path = local_path + '.gz'
                    with open(local_path, 'rb') as f_in:
                        with gzip.open(gzip_path, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    
                    # Upload the gzipped file
                    remote_path = f"{uploads_dir}/{os.path.basename(gzip_path)}"
                    logger.info(f"Uploading {os.path.basename(gzip_path)}...")
                    sftp.put(gzip_path, remote_path)
                    
                    # Create zip file in processed directory
                    zip_path = os.path.join(processed_dir, file + '.zip')
                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        zipf.write(local_path, file)
                    
                    # Remove the original file and temporary gzip file
                    os.remove(local_path)
                    os.remove(gzip_path)
                    
                    logger.info(f"Uploaded {file} and stored in processed directory")
                except Exception as e:
                    logger.error(f"Error processing {file}: {e}")
                    continue
        
        sftp.close()
        logger.debug("SFTP session closed.")
        ssh.close()
        logger.info("SFTP upload completed")
        
    except Exception as e:
        logger.error(f"SFTP error: {e}") 