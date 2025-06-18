#!/usr/bin/env python3

import os
import sys
import subprocess
import tempfile
import logging

logger = logging.getLogger(__name__)

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
            
        # Write fixed content to a temporary file
        temp_file = infile + '.fixed'
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
        if infile.endswith('.fixed'):
            try:
                os.remove(infile)
            except:
                pass
                
        return True
        
    except Exception as e:
        logger.error(f"Couldn't run teqc to edit RINEX header: {e}")
        # Clean up temporary files
        if infile.endswith('.fixed'):
            try:
                os.remove(infile)
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
