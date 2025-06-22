#!/bin/bash

############################################################
# get_gnss_ftp.sh v.20250622.1
# copyright 2025 John Ackermann N8UR jra@febo.com
#
# Shell script wrapper for get_gnss_ftp.py to pull data files
# from Trimble or Sepentrio receiver and process them.
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

/usr/local/bin/get_gnss_ftp.py \
    -m ./ -f netr9-1-admin.febo.com \
    --station hs00 \
    --organization "HamSci TEC Project" \
    --user "John Ackermann N8UR" \
    --antenna_type "TRM41249.00" \
    --station_llh "39.72 -84.17 247.1" \
    --sftp_host files.tapr.org --sftp_user xxxx --sftp_pass xxxx
