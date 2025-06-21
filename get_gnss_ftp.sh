#!/bin/bash

/usr/local/bin/get_gnss_ftp.py \
    -m ./ -f netr9-1-admin.febo.com \
    --station hs00-n8ur-netr9-1 \
    --organization "HamSci TEC Project" \
    --user "John Ackermann N8UR" \
    --antenna_type "TRM41249.00" \
    --station_llh "39.72 -84.17 247.1" \
    --sftp_host files.tapr.org --sftp_user xxxx --sftp_pass xxxx
