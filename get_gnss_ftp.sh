#!/bin/bash

/usr/local/bin/get_gnss_ftp.py \
    -m ./ -f netr9-1-admin.febo.com \
    --station hs00-n8ur-netr9-1 \
    --organization "HamSci TEC Project" \
    --user "John Ackermann N8UR" \
    --antenna_type "TRM41249.00" \
    --station_llh "39.7285210 -84.1782042 247.686" \
    --sftp_host files.tapr.org --sftp_user n8ur-sftp --sftp_pass 9192MHz

/usr/local/bin/get_gnss_ftp.py \
    -m ./ -f netrs-1-admin.febo.com \
    --station hs00-n8ur-netrs-1 \
    --organization "HamSci TEC Project" \
    --user "John Ackermann N8UR" \
    --antenna_type "TRM41249.00" \
    --station_llh "39.7285210 -84.1782042 247.686" \
    --sftp_host files.tapr.org --sftp_user n8ur-sftp --sftp_pass 9192MHz

/usr/local/bin/get_gnss_ftp.py \
    -m ./ -f mosaic-t1-admin.febo.com \
    --station hs00-n8ur-mosaic-t1 \
    --organization "HamSci TEC Project" \
    --user "John Ackermann N8UR" \
    --antenna_type "TRM41249.00" \
    --station_llh "39.7285210 -84.1782042 247.686" \
    --sftp_host files.tapr.org --sftp_user n8ur-sftp --sftp_pass 9192MHz
