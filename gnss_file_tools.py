#!/usr/bin/env -S python3 -u

#################################################
# gnss_file_tools.py v.20250622.1
# copyright 2025 John Ackermann N8UR jra@febo.com
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
import time
import shutil
import errno
import glob
import random
import zipfile
from pprint import pprint
from gnsscal import *
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from tempfile import NamedTemporaryFile

# NOTE: final corrections are available about 17 days after
# the end of each gps_week (e.g., each Wednesday), so we make
# names for current week as well as two weeks back. 

class MeasurementFilesBase:
    # m_path, date_1, date_2 are required
    def __init__(self, m_path, date_1=0, date_2=0):
        self.curr_leap = 18

        self.get_today_yesterday()
        ######################################################
        # NAMING CONVENTIONS:
        # numeric values (day of year, etc.) in integer form 
        # have "_num" appended, e.g., "doy_num". formatted
        # strings have "_str" appended, e.g., "doy_str"
        #
        # gps day of week 0 = Sunday
        #
        # NOTE: changed 20221209 -- if year/doy or
        # gps_week/dow are non-zero, use date
        # entered in  calculations, NOT the prior date;
        # vars with "prior" give prior full week or prior day
        #
        # attribute names for individual unzipped file
        # names end with "file".  Individual zipped base file
        # attributes end with "zip".  Attributes ending with
        # "path" are absolute path names of files.
        ######################################################


        # datetime object used for calculations
        self.dt = datetime(1,1,1)

        ######################################################
        self.m_path = os.path.abspath(m_path)
        # basename only works if no trailing "/"
        self.m_name = os.path.basename(m_path.rstrip('/'))
        # but we want one at end of path
        self.m_path = os.path.abspath(m_path.rstrip('/')) + "/"

        ######################################################
        # date_1 is either current year, or gps week
        # date_2 is either current day of year, or gps day of week
        #
        # CHEATS:
        # -- if date_1 = "yesterday" or date_1, date_2 are both 0, use yesterday's date
        # -- if date_1 = "today", use today's date
        if str(date_1).lower() == 'yesterday' or (int(date_1) == 0 and int(date_2) == 0):
            date_1 = self.yesterday_year_num
            date_2 = self.yesterday_doy_num
            self.dt = self.yesterday
        elif str(date_1).lower() == 'today':
            date_1 = self.today_year_num
            date_2 = self.today_doy_num
            self.dt = self.today

        date_1 = int(date_1)
        date_2 = int(date_2)

        # it's a gps week and dow
        if date_1 > 2100 and 0 <= date_2 <= 6:
            # turn gps_week and gps_dow into datetime object
            self.dt = gpswd2date(date_1,date_2)
            self.gps_week_num = date_1
            self.gps_dow_num = date_2
            self.year_num = int(self.dt.year)
            self.doy_num = int(self.dt.timetuple().tm_yday)

        # or it's a calendar year and doy
        elif date_1 > 1980 and 0 <= date_2 <= 366:  
            # turn year and doy into gps week and dow
            (x,y) = yrdoy2gpswd(date_1,date_2)
            # Create datetime object from year and day of year
            self.dt = datetime(date_1, 1, 1) + timedelta(days=date_2-1)  # Subtract 1 because day of year is 1-based
            self.gps_week_num = int(x)
            self.gps_dow_num = int(y)
            self.year_num = date_1
            self.doy_num = date_2

        # or it's bogus
        else:
            print("invalid date:",date_1,date_2)
            sys.exit()

        # month and day of month numbers
        self.month_num = int(self.dt.month)
        self.day_num = int(self.dt.day)

        # total gps days (gps_week_num * 7 + gps_dow)
        self.gps_days_num = (self.gps_week_num * 7) + self.gps_dow_num
        self.prior_gps_days_num = self.gps_days_num - 1
        # prior week and day
        # FIXME -- below doesn't work on first day of year!
        self.prior_doy_num = self.doy_num - 1
        self.prior_gps_week_num = self.gps_week_num - 1
        self.prior_gps_dow_num = self.gps_dow_num - 1

        # gps week and dow of today
        (self.today_gps_week_num,self.today_gps_dow_num) = \
            yrdoy2gpswd(self.today_year_num,self.today_doy_num)
        self.today_gps_days_num = \
            (self.today_gps_week_num * 7) + self.today_gps_dow_num

        # gps week and dow of last full day
        (self.yesterday_gps_week_num,self.yesterday_gps_dow_num) = \
            yrdoy2gpswd(self.yesterday_year_num,self.yesterday_doy_num)
        self.yesterday_gps_days_num = \
            (self.yesterday_gps_week_num * 7) + self.yesterday_gps_dow_num

        # week numbering is amusing;
        # we have four choices:
        #self.week_num = int(dt.strftime("%U"))      # Sunday is first day
        #self.week_num = int(dt.strftime("%V"))      # Monday is first day
        #self.week_num = int(dt.strftime("%W"))      # ISO 8601
        self.week_num = int(self.doy_num // 7) + 1   # from Jan 1;floor div
        self.prior_week_num = self.week_num - 1

        # we might need to know leapseconds to
        # make sure what GPS week/dow really is
        self.curr_leap = int(self.curr_leap)

        ###############################################
        # at this point we know the year, day of year,
        # gps week, and gps day of week

        # make formatted versions of calendar
        # versions, two and four place if appropriate
        # of calendar values as four- and two-place strings
        self.yyyy_str = '{:04d}'.format(self.year_num)
        self.yy_str = self.yyyy_str[2:]
        self.doy_str = '{:03d}'.format(self.doy_num)
        self.prior_doy_str = '{:03d}'.format(self.prior_doy_num)
        self.mm_str = '{:02d}'.format(self.month_num)
        self.dd_str = '{:02d}'.format(self.day_num)
        self.ddd_str = '{:03d}'.format(self.day_num)

        # make formatted versions of gps week and day
        self.gps_week_str = '{:04d}'.format(self.gps_week_num)
        self.prior_gps_week_str = '{:04d}'.format(self.prior_gps_week_num)
        self.gps_dow_str = '{:02d}'.format(self.gps_dow_num)
        self.prior_gps_dow_str = '{:02d}'.format(self.prior_gps_dow_num)
        self.gps_days_str = '{:05d}'.format(self.gps_days_num)
        self.prior_gps_days_str = '{:05d}'.format(self.prior_gps_days_num)

        self.today_gps_week_str = '{:04d}'.format(self.today_gps_week_num)
        self.today_gps_dow_str = '{:02d}'.format(self.today_gps_dow_num)
        self.today_gps_days_str = '{:05d}'.format(self.today_gps_days_num)

        self.yesterday_gps_week_str = \
            '{:04d}'.format(self.yesterday_gps_week_num)
        self.yesterday_gps_dow_str = '{:02d}'.format(self.yesterday_gps_dow_num)
        self.yesterday_gps_days_str = \
            '{:05d}'.format(self.yesterday_gps_days_num)

        # name for weekly files, both current and prior
        self.m_week_name = self.m_name + '__' + self.gps_week_str
        self.m_prior_week_name = \
            self.m_name + '__' + self.prior_gps_week_str

        # CRITICAL CHANGE: Just generate the paths, but DO NOT create directories
        self.calc_path_names()
        
    # Get date now, and yesterday
    def get_today_yesterday(self):
        self.today = datetime.utcnow()
        self.today_year_num = int(self.today.year)
        self.today_month_num = int(self.today.month)
        self.today_day_num = int(self.today.day)
        self.today_doy_num = int(self.today.strftime('%j')) 
        self.yesterday = self.today - timedelta(days = 1)
        self.yesterday_year_num = int(self.yesterday.year)
        self.yesterday_month_num = int(self.yesterday.month)
        self.yesterday_day_num = int(self.yesterday.day)
        self.yesterday_doy_num = int(self.yesterday.strftime('%j'))
        
    # Calculate all paths but DO NOT create directories
    def calc_path_names(self):
        # Calculate daily download file paths
        self.dnld_base = self.m_path + "download/" 
        self.daily_dnld_file = self.m_week_name + "_" + \
            self.gps_dow_str + ".obs"
        self.daily_dnld_dir = self.dnld_base + self.m_week_name + '_daily/'
        self.daily_dnld_path = self.daily_dnld_dir + self.daily_dnld_file

        # Count files if directory exists
        try:
            self.num_files = len(glob.glob(self.daily_dnld_dir + '/*', recursive=False))
        except:
            self.num_files = 0

        # Calculate daily zip name
        self.daily_dnld_zip = self.m_week_name
        if self.num_files == 7:
            self.daily_dnld_zip += "_daily.zip"
        else:
            if self.num_files == 1:
                self.daily_dnld_zip += \
                    "_" + str(self.num_files) + "_file_daily.zip"
            else:
                self.daily_dnld_zip += \
                    "_" + str(self.num_files) + "_files_daily.zip"
        self.daily_dnld_zip_path = self.dnld_base + self.daily_dnld_zip
        
        # Calculate weekly rinex file paths
        self.weekly_rinex_file = self.m_name + "__" + self.gps_week_str
        if self.num_files == 7:
            self.weekly_rinex_file += "_weekly.obs"
        else:
            if self.num_files == 1:
                self.weekly_rinex_file += \
                    "_" + str(self.num_files) + "_file_weekly.obs"
            else:
                self.weekly_rinex_file += \
                    "_" + str(self.num_files) + "_files_weekly.obs"

        self.weekly_rinex_dir = self.m_path + "weekly/"
        self.weekly_rinex_path = self.weekly_rinex_dir + \
            self.weekly_rinex_file
        self.weekly_rinex_zip = self.weekly_rinex_file + ".zip"
        self.weekly_rinex_zip_path = \
            self.weekly_rinex_dir + self.weekly_rinex_zip

        # Calculate output paths
        self.output_path_final = self.m_path + 'final/'
        self.output_path_rapid = self.m_path + 'rapid/'
        self.output_path_ultra = self.m_path + 'ultra/'

        self.pos_file_final = self.m_name + '_pos_final.dat'
        self.pos_path_final = self.output_path_final + \
            'misc/' + self.pos_file_final
        self.pos_file_rapid = self.m_name + '_pos_rapid.dat'
        self.pos_path_rapid = self.output_path_rapid + \
            'misc/' + self.pos_file_rapid
        self.pos_file_ultra = self.m_name + '_pos_ultra.dat'
        self.pos_path_ultra = self.output_path_ultra + \
            'misc/' + self.pos_file_ultra

        self.offset_file_final = self.m_name + '_offset_final.dat'
        self.offset_path_final = self.output_path_final + \
            'misc/' + self.offset_file_final
        self.offset_file_rapid = self.m_name + '_offset_rapid.dat'
        self.offset_path_rapid = self.output_path_rapid + \
            'misc/' + self.offset_file_rapid
        self.offset_file_ultra = self.m_name + '_offset_ultra.dat'
        self.offset_path_ultra = self.output_path_ultra + \
            'misc/' + self.offset_file_ultra


class NRCanMeasurementFiles(MeasurementFilesBase):
    """Original class that creates the NRCan tool directory structure"""
    def __init__(self, m_path, date_1=0, date_2=0):
        # First calculate all paths without creating directories
        super().__init__(m_path, date_1, date_2)
        # Then explicitly create directories
        self.create_nrcan_dirs()
        
    def create_nrcan_dirs(self):
        """Create all directories needed for NRCan tools"""
        try:
            # Create weekly directories
            os.makedirs(self.weekly_rinex_dir, exist_ok=True)
            os.makedirs(self.m_path + '/weekly/final', exist_ok=True)
            
            # Create download directories
            os.makedirs(self.dnld_base, exist_ok=True)
            os.makedirs(self.daily_dnld_dir, exist_ok=True)
            
            # Create standard output directories
            os.makedirs(self.output_path_final, exist_ok=True)
            os.makedirs(self.output_path_final + '/clk', exist_ok=True)
            os.makedirs(self.output_path_final + '/sum', exist_ok=True)
            os.makedirs(self.output_path_final + '/misc', exist_ok=True)
            os.makedirs(self.output_path_final + '/zip', exist_ok=True)

            os.makedirs(self.output_path_rapid, exist_ok=True)
            os.makedirs(self.output_path_rapid + '/clk', exist_ok=True)
            os.makedirs(self.output_path_rapid + '/sum', exist_ok=True)
            os.makedirs(self.output_path_rapid + '/misc', exist_ok=True)
            os.makedirs(self.output_path_rapid + '/zip', exist_ok=True)

            os.makedirs(self.output_path_ultra, exist_ok=True)
            os.makedirs(self.output_path_ultra + '/clk', exist_ok=True)
            os.makedirs(self.output_path_ultra + '/sum', exist_ok=True)
            os.makedirs(self.output_path_ultra + '/misc', exist_ok=True)
            os.makedirs(self.output_path_ultra + '/zip', exist_ok=True)
        except Exception as e:
            print("Couldn't create directory:", e)
            print("Exiting...")
            sys.exit()


# For backward compatibility with scripts that import MeasurementFiles directly
MeasurementFiles = NRCanMeasurementFiles

#################### End of MeasurementFiles Classes #########################
# Following are a bunch of random functions
# used elsewhere in the nrcan_tools suite
######################################################################

# number formatting 
# format in exponential notation, stripping trailing zeroes
def format_e(n):
    a = '%E' % n
    return a.split('E')[0].rstrip('0').rstrip('.') + 'E' + a.split('E')[1]

# format in decimal notation with 'places' decimal places
def format_dec(n,places):
    a = "{0:+.{1}f}".format(n, places)
    return a

def format_nanos(n):
    a = "{:>8.4f} ns".format(n * 1e9)
    return a

def format_filesize(num, suffix="B"):
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"

# this will adjust float val by randomly +/-
# 1 digit at position places (12 = 1 ps)
def tweak_picos(val,places):
    if places == 11:
        adj_val = val + ((random.randint(0,1)*2-1) / 1e11)
    if places == 12:
        adj_val = val + ((random.randint(0,1)*2-1) / 1e12)
    if places == 13:
        adj_val = val + ((random.randint(0,1)*2-1) / 1e13)
    if places == 14:
        adj_val = val + ((random.randint(0,1)*2-1) / 1e14)
    return adj_val

##### date/time handlers #####

# is iso_str a valid ISO datetime string
def iso_valid(iso_str):
    try:
        datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
    except:
        return False
    return True

# return datetime object from ISO8601 string
def make_dt_from_iso(instring):
    if iso_valid(instring):
        return datetime.fromisoformat(instring)
    else:
        return datetime.min

# return ISO8601 string from datetime object
def make_iso_from_dt(dt):
    try:
        return str(dt.isoformat("T"))
    except:
        print("Bad Epoch:",dt)
        sys.exit()
        return "Bad Epoch"

# read data line from .clk file and return
# datetime object of the epoch
def make_dt_from_clk(instring):
    fields = instring.split()
    year = fields[2]
    month = fields[3]
    day = fields[4]
    hour = fields[5]
    minute = fields[6]
    seconds = fields[7]
    # trash is the clock offset; don't use it here
    (seconds,trash) = seconds.split('.')

    return datetime(int(year), int(month), int(day), \
        int(hour), int(minute), int(seconds))

# return ISO timestamp from clock record
def make_iso_from_clk(instring):
    dt = make_dt_from_clk(instring)
    iso = make_iso_from_dt(dt)
    if iso_valid(iso):
        return(iso)
    else:
        return None

# return unix timestamp from clock record
def make_timestamp_from_clk(instring):
    return make_dt_from_clk(instring)


# return unix timestamp as integer from datetime object
def make_timestamp_from_dt(dt):
    return int(dt.timestamp())

# return unix timestamp from ISO8601 string
def make_timestamp_from_ISO(instring):
    return make_dt_from_iso(instring)

# subtract datetime object dt2 from dt1 and return
# difference in integer seconds
def get_delta_seconds(dt1, dt2):
    duration = dt1 - dt2    
    duration_in_s = int(duration.total_seconds())
    return(duration_in_s)

# return day of year as string from datetime object
def make_doy_from_dt(dt):
    doy = dt.strftime('%j')
    return doy.zfill(3)

# return day of year as string from ISO8601
def make_doy_from_iso(instring):
    dt = make_dt_from_iso(instring)
    return(make_doy_from_dt)

# return DDD:HH:MM:SS string from integer seconds
def make_DDHHMMSS_from_seconds(t_secs):
    try:
        val = int(t_secs)
    except ValueError:
        return "!!!ERROR: ARGUMENT NOT AN INTEGER!!!"
    pos = abs( int(t_secs) )
    day = pos / (3600*24)
    rem = pos % (3600*24)
    hour = rem / 3600
    rem = rem % 3600
    mins = rem / 60
    secs = rem % 60
    res = '%03d:%02d:%02d:%02d' % (day, hour, mins, secs)
    if int(t_secs) < 0:
        res = "-%s" % res
    return res

# find the last daily rinex that has been
# downloaded to <measurement_name>/download
def find_last_daily_rinex(path):
    # Use MeasurementFilesBase to avoid creating directories
    m = MeasurementFilesBase(path, 0, 0)
    days = []
    weeks = []
    zips = []

    # Check if dnld_base exists before scanning
    if not os.path.exists(m.dnld_base):
        print("Download directory does not exist.")
        return 0, 0, 0, 0

    # find the number of weekly directories
    dirs = [f.path for f in os.scandir(m.dnld_base) if f.is_dir()]
    for f in dirs:
        # this filters out any bak, etc. directories
        if os.path.basename(f).startswith(m.m_name):
            weeks.append(f)
    # numeric sort
    weeks.sort(key=lambda f: int(''.join(filter(str.isdigit, f))))
    # get the last week and dow numbers
    if len(weeks) > 0:
        latest_week = weeks[-1]
        latest_week_num = int(latest_week.split('__')[1][:4])
        days = [f.path for f in os.scandir(latest_week) if f.is_file()]
        if not days:
            print("No daily files found in latest week directory.")
            return 0, 0, 0, 0
        days.sort(key=lambda f: int(''.join(filter(str.isdigit, f))))
        latest_dow_file = days[-1]
        # extract the day of week whether in DD or D format
        # and using either my old or my new filename convention
        date_part = os.path.basename(latest_dow_file). \
            partition("__")[2].partition(".obs")[0]
        date_part = date_part.partition("daily")[0]
        latest_gps_week_num,latest_gps_dow_num = date_part.split("_")
        latest_gps_week_num = int(latest_gps_week_num)
        latest_gps_dow_num = int(latest_gps_dow_num)
    else:
        # if none, find the last weekly zip (this assumes it's a full week!)
        zips = glob.glob(m.dnld_base + "*.zip")
        if len(zips) > 0:
            zips.sort(key=lambda f: int(''.join(filter(str.isdigit, f))))
            latest_gps_week = zips[-1]
            latest_gps_week_num = latest_gps_week.split('__')[1][:4]
            # assume zipped week is full week
            latest_gps_dow_num = 6
        else:
            return 0, 0, 0, 0
    latest_year, latest_doy = \
        gpswd2yrdoy(int(latest_gps_week_num), int(latest_gps_dow_num))
    print("Latest GPS week, day of week, calendar year, and day of year:", \
        latest_gps_week_num, latest_gps_dow_num, latest_year, latest_doy)
    return latest_gps_week_num, latest_gps_dow_num, latest_year, latest_doy

# find the last weekly rinex that has
# been made in <measurement_name>/weekly
def find_last_weekly_rinex(path):
    # Use MeasurementFilesBase to avoid creating directories
    m = MeasurementFilesBase(path, 0, 0)
    
    if not os.path.exists(m.weekly_rinex_dir):
        print("Weekly directory does not exist.")
        return 0
        
    files = glob.glob(m.m_path + "/weekly/*.obs*")
    if not files:
        print("No weekly RINEX files found.")
        return 0
        
    files.sort(key=lambda f: int(''.join(filter(str.isdigit, f))))
    latest_gps_week = files[-1]
    latest_gps_week_num = latest_gps_week.split('__')[1][:4]
        
    print("Latest GPS week:", latest_gps_week_num)
    return latest_gps_week_num

# get the gps week and day of week from a measurement file
def find_file_week_and_day(infile):
    # get rid of measurement name
    date_part = os.path.basename(infile).partition("__")[2]
    # get rid of extension
    date_part = date_part.partition(".obs")[0]
    date_part = date_part.split("_",2)[:2]
    # split week and dow
    gps_week,gps_dow = date_part
    gps_week = int(gps_week)
    gps_dow = int(gps_dow)
    return gps_week, gps_dow

def find_this_gps_week():
    today = datetime.utcnow()
    today_year = int(today.year)
    today_doy = int(today.strftime('%j')) 
    # turn year and doy into gps week and dow
    (x,y) = yrdoy2gpswd(today_year,today_doy)
    return int(x)

# read  phase file (offset, epoch, doy) return dt of first epoch
def get_first_epoch(phase_file):
    first_epoch= datetime.min
    with open(phase_file,'r') as f:
        for line in f:
            line = f.readline()
            if line.startswith('#'):
                continue
            parts = line.split()
            if len(parts) > 1:
                if iso_valid(parts[1]):
                    first_epoch = make_dt_from_iso(parts[1])
                    break
    return first_epoch

# read  phase file (offset, epoch, doy) return dt of final epoch
def get_final_epoch(phase_file):
    final_epoch= datetime.min
    with open(phase_file,'r') as f:
        for line in f:
            if line.startswith('#'):
                continue
        parts = line.split()
        if len(parts) > 1:
            if iso_valid(parts[1]):
                final_epoch = make_dt_from_iso(parts[1])
    return final_epoch

# read  phase file (offset, epoch, doy) and return total number of epochs
def get_epoch_count(phase_file):
    count = 0
    with open(phase_file,'r') as f:
        for line in f:
            if line.startswith('#'):
                continue
            parts = line.split()
            if len(parts) > 1:
                if iso_valid(parts[1]):
                    count = count + 1
    return count


def get_tau(phase_file):
    first = get_first_epoch(phase_file)
    final = get_final_epoch(phase_file)
    count = get_epoch_count(phase_file)
    duration = get_delta_seconds(final, first)
    tau = int(duration / count)
    return tau


def dms_to_decimal(degrees, minutes, seconds):
    """
    Convert degrees, minutes, seconds to decimal degrees.
    
    Args:
        degrees (float): Degrees (can be negative)
        minutes (float): Minutes (0-59)
        seconds (float): Seconds (0-59.999...)
        
    Returns:
        float: Decimal degrees
    """
    # Handle negative coordinates (south latitude or west longitude)
    sign = -1 if degrees < 0 else 1
    abs_degrees = abs(degrees)
    
    decimal = sign * (abs_degrees + minutes/60.0 + seconds/3600.0)
    return decimal


def parse_dms_coordinates(dms_string):
    """
    Parse a DMS coordinate string and convert to decimal degrees.
    
    Args:
        dms_string (str): Space-separated string in format:
                         "lat_deg lat_min lat_sec lon_deg lon_min lon_sec height"
                         
    Returns:
        tuple: (lat_decimal, lon_decimal, height) or None if parsing fails
    """
    try:
        coords = dms_string.split()
        if len(coords) != 7:
            return None
            
        lat_deg, lat_min, lat_sec, lon_deg, lon_min, lon_sec, height = map(float, coords)
        
        # Validate ranges
        if not (-90 <= lat_deg <= 90) or not (0 <= lat_min < 60) or not (0 <= lat_sec < 60):
            return None
        if not (-180 <= lon_deg <= 180) or not (0 <= lon_min < 60) or not (0 <= lon_sec < 60):
            return None
            
        # Convert to decimal degrees (preserve signs)
        lat_decimal = dms_to_decimal(lat_deg, lat_min, lat_sec)
        lon_decimal = dms_to_decimal(lon_deg, lon_min, lon_sec)
        
        return lat_decimal, lon_decimal, height
        
    except (ValueError, TypeError):
        return None


def format_dms_coordinates(lat_decimal, lon_decimal, height):
    """
    Convert decimal degrees to DMS format string.
    
    Args:
        lat_decimal (float): Latitude in decimal degrees
        lon_decimal (float): Longitude in decimal degrees  
        height (float): Height in meters
        
    Returns:
        str: DMS format string "lat_deg lat_min lat_sec lon_deg lon_min lon_sec height"
    """
    def decimal_to_dms(decimal):
        """Convert decimal degrees to degrees, minutes, seconds"""
        sign = -1 if decimal < 0 else 1
        abs_decimal = abs(decimal)
        
        degrees = int(abs_decimal)
        minutes_float = (abs_decimal - degrees) * 60
        minutes = int(minutes_float)
        seconds = (minutes_float - minutes) * 60
        
        return sign * degrees, minutes, seconds
    
    lat_deg, lat_min, lat_sec = decimal_to_dms(lat_decimal)
    lon_deg, lon_min, lon_sec = decimal_to_dms(lon_decimal)
    
    return f"{lat_deg} {lat_min} {lat_sec:.6f} {lon_deg} {lon_min} {lon_sec:.6f} {height}"


def parse_natural_dms_coordinates(natural_string):
    """
    Parse a natural DMS coordinate string with direction indicators.
    Accepts both '33 N' and '33N' (and similar for E/W).
    
    Args:
        natural_string (str): String in format like "39 42 0 N 84 10 0 W 247.1"
                             or "39 42 0N 84 10 0W 247.1"
                             or "39 42 0 N 84 10 0 W 247.1"
                             
    Returns:
        tuple: (lat_decimal, lon_decimal, height) or None if parsing fails
    """
    try:
        parts = natural_string.split()
        # Flatten tokens like '33N' into ['33', 'N']
        expanded = []
        for p in parts:
            if len(p) > 1 and p[-1].upper() in ['N', 'S', 'E', 'W'] and p[:-1].replace('.', '', 1).replace('-', '', 1).isdigit():
                expanded.append(p[:-1])
                expanded.append(p[-1])
            else:
                expanded.append(p)
        parts = expanded
        if len(parts) != 9:  # lat_deg lat_min lat_sec lat_dir lon_deg lon_min lon_sec lon_dir height
            return None
            
        lat_deg, lat_min, lat_sec, lat_dir, lon_deg, lon_min, lon_sec, lon_dir, height = parts
        
        # Convert to float
        lat_deg, lat_min, lat_sec = float(lat_deg), float(lat_min), float(lat_sec)
        lon_deg, lon_min, lon_sec = float(lon_deg), float(lon_min), float(lon_sec)
        height = float(height)
        
        # Apply direction signs
        if lat_dir.upper() in ['S', 'SOUTH']:
            lat_deg = -lat_deg
        elif lat_dir.upper() not in ['N', 'NORTH']:
            return None
            
        if lon_dir.upper() in ['W', 'WEST']:
            lon_deg = -lon_deg
        elif lon_dir.upper() not in ['E', 'EAST']:
            return None
        
        # Validate ranges
        if not (-90 <= lat_deg <= 90) or not (0 <= lat_min < 60) or not (0 <= lat_sec < 60):
            return None
        if not (-180 <= lon_deg <= 180) or not (0 <= lon_min < 60) or not (0 <= lon_sec < 60):
            return None
            
        # Convert to decimal degrees
        lat_decimal = dms_to_decimal(lat_deg, lat_min, lat_sec)
        lon_decimal = dms_to_decimal(lon_deg, lon_min, lon_sec)
        
        return lat_decimal, lon_decimal, height
        
    except (ValueError, TypeError):
        return None


if __name__ == '__main__':
    # m_path, date_1, date_2
    if len(sys.argv) == 4:
        testObj = MeasurementFiles(sys.argv[1], sys.argv[2], \
            sys.argv[3])
    elif len(sys.argv) == 3:
        testObj = MeasurementFiles(sys.argv[1], sys.argv[2])
    elif len(sys.argv) == 2:
        testObj = MeasurementFiles(sys.argv[1])
    else:
        print("Need at least one command line argument!")
        sys.exit()
    pprint(vars(testObj))
