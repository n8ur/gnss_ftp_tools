#!/bin/bash

/usr/local/bin/get_gnss_ftp.py \
    -m /data/n8ur -f netrs-1-admin.febo.com -s n8ur-netrs-1 \
    --sftp_host files.tapr.org --sftp_user #### --sftp_pass ####
/usr/local/bin/get_gnss_ftp.py \
    -m /data/n8ur -f netr9-1-admin.febo.com -s n8ur-netr9-1 \
    --sftp_host files.tapr.org --sftp_user n8ur-sftp --sftp_pass ####
/usr/local/bin/get_gnss_ftp.py \
    -m /data/n8ur -f mosaic-t1-admin.febo.com -s n8ur-mosaic-t1 \
    --sftp_host files.tapr.org --sftp_user n8ur-sftp --sftp_pass ####
