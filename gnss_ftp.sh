#!/bin/bash

/usr/local/bin/get_netrs_ftp.py \
    -m /data/<my_station> -f my.host.name -s MyStation \
    --sftp_host tec-logger.febo.com --sftp_user MyUser --sftp_pass MyPasswd
