#!/usr/bin/env python3

############################################################
# conversion_funcs.py v.20250622.1
# copyright 2025 John Ackermann N8UR jra@febo.com
#
# Functions for converting GNSS receiver files to RINEX format
# and editing RINEX file headers with station metadata.
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
import subprocess
import tempfile
import logging

logger = logging.getLogger(__name__)

def fix_netr8_rec_line(line_content):
    """Fix NetR8 REC # / TYPE / VERS line - remove leading space before label."""
    label = 'REC # / TYPE / VERS'
    if label in line_content:
        label_field = line_content[60:80]
        logger.debug(f"NetR8 fix: label_field = {repr(label_field)}")
        if label_field.startswith(' ') and label in label_field:
            logger.debug(f"NetR8 fix: Found leading space, fixing line")
            data_portion = line_content[:60]
            fixed_line = f"{data_portion}{label}"
            fixed_line = fixed_line.ljust(80)
            logger.debug(f"NetR8 fix: Original = {repr(line_content)}")
            logger.debug(f"NetR8 fix: Fixed = {repr(fixed_line)}")
            return fixed_line
        else:
            logger.debug(f"NetR8 fix: No leading space found or label not in field")
    else:
        logger.debug(f"NetR8 fix: Label not found")
    return line_content

def fix_netr9_pgm_line(line_content):
    """Fix NetR9 PGM / RUN BY / DATE line - move label to column 61."""
    label = 'PGM / RUN BY / DATE'
    if label in line_content:
        # Find the position of the label
        label_pos = line_content.find(label)
        # Take everything before the label as data portion
        data_portion = line_content[:label_pos].rstrip()
        # Pad data portion to exactly 60 characters
        data_portion = data_portion.ljust(60)
        # Append label starting at column 61 and trim to 80 characters
        fixed_line = f"{data_portion}{label}"
        if len(fixed_line) > 80:
            fixed_line = fixed_line[:80]
        return fixed_line
    return line_content

def validate_and_fix_rinex_header_line(line_content):
    """Fix: For 'REC # / TYPE / VERS', ensure label starts at column 61 (no leading space), left-justified. For 'PGM / RUN BY / DATE', move label to column 61, remove any duplicate, and keep line <= 80 chars."""
    logger.debug(f"validate_and_fix_rinex_header_line called with: {repr(line_content)}")
    
    # Apply NetR8 fix first
    fixed_line = fix_netr8_rec_line(line_content)
    if fixed_line != line_content:
        logger.debug(f"NetR8 fix applied: {repr(fixed_line)}")
        return fixed_line
    
    # Apply NetR9 fix
    fixed_line = fix_netr9_pgm_line(line_content)
    if fixed_line != line_content:
        logger.debug(f"NetR9 fix applied: {repr(fixed_line)}")
        return fixed_line
    
    # Truncate lines longer than 80 characters
    if len(line_content) > 80:
        logger.debug(f"Truncating line longer than 80 characters")
        return line_content[:80]
    
    logger.debug(f"No fixes applied, returning original")
    return line_content

def edit_rinex_header(infile, m, station, organization, user, antenna_type, 
                     station_cartesian=None, station_llh=None, 
                     marker_num=None, antenna_number=None):
    """Edit RINEX file header with station metadata.
    
    Args:
        infile (str): Path to input RINEX file
        m (TECMeasurementFiles): Measurement file object containing path information
        station (str): Station name
        organization (str): Organization/agency name
        user (str): Operator/user name
        antenna_type (str): Antenna type
        station_cartesian (str, optional): Station location in WGS84 cartesian coordinates [x,y,z] in meters
        station_llh (str, optional): Station location in WGS84 llh coordinates [lat,lon,height] in decimal degrees and meters
        marker_num (str, optional): Monument/marker number
        antenna_number (str, optional): Antenna number
        
    Returns:
        bool: True if successful, False otherwise

    teqc header editing arguments:
        -O.ag   agency (organization)
        -O.mo   monument (marker/station) name
        -O.mn   monument number
        -O.o    operator (user) name
        -O.an   antenna number
        -O.at   antenna type
        -O.px   approximate antenna location (WGS84 cartesian, meters)
        -O.pg   approximate antenna location (WGS84 llh, decimal degrees, ellipsoid height)
    """
    # First, check and fix the header if needed
    try:
        with open(infile, 'r') as f:
            lines = f.readlines()
            
        # Check if file has END OF HEADER marker
        if 'END OF HEADER' not in ''.join(lines):
            logger.warning("No END OF HEADER marker found, adding one...")
            # Find the first data line (starts with a number)
            data_start = 0
            for i, line in enumerate(lines):
                if line.strip() and line[0].isdigit():
                    data_start = i
                    break
            
            # Insert END OF HEADER before data
            lines.insert(data_start, '                                                            END OF HEADER\n')
            
        # Fix malformed PGM/RUN BY/DATE line if needed
        for i, line in enumerate(lines):
            if 'PGM / RUN BY / DATE' in line:
                # Check if line is malformed (not properly formatted with 20-char fields)
                if len(line.strip()) > 60:  # Should be 60 chars + newline
                    # Extract components
                    parts = line.split()
                    if len(parts) >= 3:
                        pgm = parts[0][:20].ljust(20)  # First part is PGM
                        run_by = parts[1][:20].ljust(20)  # Second part is RUN BY
                        # Date should be in format YYYYMMDD HHMMSS UTC
                        date_str = ' '.join(parts[2:])
                        if len(date_str) > 20:
                            date_str = date_str[:20]
                        date_str = date_str.ljust(20)
                        
                        # Replace the line with properly formatted version
                        lines[i] = f'{pgm}{run_by}{date_str}PGM / RUN BY / DATE\n'
                    break
        
        # Apply minimal header fixes only where needed
        for i, line in enumerate(lines):
            # Skip data lines (lines starting with numbers)
            if line.strip() and line[0].isdigit():
                continue
                
            # Skip empty lines
            if not line.strip():
                continue
                
            # Get line content without newline
            line_content = line.rstrip('\r\n')
            
            # Stop processing after END OF HEADER
            if 'END OF HEADER' in line:
                break
                
            # Apply minimal fixes only for obviously malformed lines
            logger.debug(f"Processing header line {i+1}: {repr(line_content)}")
            fixed_line = validate_and_fix_rinex_header_line(line_content)
            if fixed_line != line_content:
                # Apply the fix if the lines are different
                logger.warning(f"Fixed malformed header line: {line_content.strip()}")
                logger.warning(f"Corrected to: {fixed_line.strip()}")
                lines[i] = fixed_line + '\n'
            else:
                logger.debug(f"No fix needed for line {i+1}")
        
        # Write fixed content to a temporary file
        temp_file = tempfile.mktemp(suffix='.fixed')
        with open(temp_file, 'w') as f:
            f.writelines(lines)
        
        # Use the fixed file for teqc
        infile = temp_file
            
    except Exception as e:
        logger.error(f"Error fixing RINEX header: {e}")
        return False

    # Build teqc command with options
    args = [
        '/usr/local/bin/teqc'
    ]
    
    # Process station name: uppercase and trim whitespace, truncate to 60 characters
    marker_name = station.upper().strip()[:60]
    args.extend(['-O.mo', marker_name])
    
    # Add organization: uppercase and trim whitespace, truncate to 40 characters
    org_name = organization.upper().strip()[:40]
    args.extend(['-O.ag', org_name])
    
    # Add user: uppercase and trim whitespace, truncate to 20 characters
    user_name = user.upper().strip()[:20]
    args.extend(['-O.o', user_name])
    
    # Add antenna type: uppercase and trim whitespace
    antenna_type = antenna_type.upper().strip()
    args.extend(['-O.at', antenna_type])
    
    # Add marker number if provided, otherwise use spaces
    if marker_num:
        marker_number = marker_num.upper().strip()[:20]
    else:
        marker_number = ' ' * 20  # 20 spaces for empty marker number
    args.extend(['-O.mn', marker_number])
    
    # Add antenna number if provided
    if antenna_number:
        antenna_number = antenna_number.upper().strip()[:20]
        args.extend(['-O.an', antenna_number])
    
    # Add station location (either cartesian or geodetic)
    if station_cartesian:
        # Split by whitespace
        coords = station_cartesian.split()
        if len(coords) == 3:
            try:
                # Convert to float and add to teqc arguments
                x, y, z = map(float, coords)
                args.extend(['-O.px', str(x), str(y), str(z)])
            except ValueError:
                logger.warning("Invalid cartesian coordinates format. Coordinates must be numeric values.")
    elif station_llh:
        # Split by whitespace
        coords = station_llh.split()
        if len(coords) == 3:
            try:
                # Convert to float and add to teqc arguments
                lat, lon, height = map(float, coords)
                args.extend(['-O.pg', str(lat), str(lon), str(height)])
            except ValueError:
                logger.warning("Invalid geodetic coordinates format. Coordinates must be numeric values.")
    
    # Add input file
    args.append(infile)
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(m.daily_dnld_path), exist_ok=True)
    
    # Run teqc to edit the header
    try:
        # First check if input file exists and has content
        if not os.path.exists(infile):
            logger.error(f"Input file {infile} does not exist")
            return False
            
        input_size = os.path.getsize(infile)
        if input_size == 0:
            logger.error(f"Input file {infile} is empty")
            return False
        
        # Run teqc and capture output
        result = subprocess.run(args, capture_output=True, text=True)
        
        # Check if command was successful
        if result.returncode != 0:
            logger.error(f"Error running teqc: {result.stderr}")
            return False
            
        # Write the output to the file
        with open(m.daily_dnld_path, 'w') as f:
            f.write(result.stdout)
            
        # Verify output file was created and has content
        if not os.path.exists(m.daily_dnld_path):
            logger.error(f"Output file {m.daily_dnld_path} was not created")
            return False
            
        output_size = os.path.getsize(m.daily_dnld_path)
        if output_size == 0:
            logger.error(f"Output file {m.daily_dnld_path} is empty")
            return False
        
        # Clean up temporary files
        if temp_file and temp_file != infile:
            try:
                os.remove(temp_file)
            except:
                pass
                
        return True
        
    except Exception as e:
        logger.error(f"Couldn't run teqc to edit RINEX header: {e}")
        # Clean up temporary files
        if temp_file and temp_file != infile:
            try:
                os.remove(temp_file)
            except:
                pass
        return False

def convert_netrs(infile, outfile, user=None):
    """Convert Trimble .T00 or .T02 file to RINEX format"""
    tmpfile = tempfile.NamedTemporaryFile(suffix='.tgd',delete=False)
    # convert .T00/.T02 file into intermediate .tgd file
    args = ['/usr/local/bin/runpkr00', '-g', '-d', '-v',
        infile, tmpfile.name]
    try:
        subprocess.run(args, \
            stdout = subprocess.DEVNULL, stderr = subprocess.DEVNULL)
    except Exception as e:
        logger.error(f"Couldn't run runpkr00, error: {e}")
        return
    tmpfile.flush()
    tmpfile.seek(0)
   
    # convert tgd to RINEX
    with open(outfile,'w') as f:
        # Build teqc command with basic options
        args = [
            '/usr/local/bin/teqc',
            '+C2',
            '-R'
        ]
        
        # Add input file
        args.append(tmpfile.name)
        
        try:
            subprocess.run(args, stdout = f, stderr = subprocess.DEVNULL)
        except Exception as e:
            logger.error(f"Couldn't run teqc, error: {e}")
            return
    s = outfile.split('/')
    s = s[len(s)-2] + '/' + s[len(s)-1]
    size = os.path.getsize(outfile)
    tmpfile.close()
    os.unlink(tmpfile.name)
    return True 
