#!/usr/bin/env python3

############################################################
# convert_trimble.py v.20250624.1
# copyright 2025 John Ackermann N8UR jra@febo.com
#
# Simple program to convert Trimble T00/T02/T04 files to
# RINEX format. Edits antenna type in RINEX header.
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

# Simple program to convert Trimble T00/T02/T04 files to
# RINEX.  Edits antenna type in RINEX header.

import os
import sys
import subprocess
import tempfile
import argparse

# Import the edit_rinex_header function from conversion_funcs
from conversion_funcs import edit_rinex_header

def convert_trimble_to_rinex(infile, antenna_type=None):
    """Convert Trimble .T00/.T02/.T04 file to RINEX format.
    
    Args:
        infile (str): Path to input Trimble file (.T00/.T02/.T04)
        antenna_type (str, optional): Antenna type to set in RINEX header
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Check if input file exists
    if not os.path.exists(infile):
        print(f"Error: Input file {infile} does not exist")
        return False
        
    # Check if input file has valid extension
    valid_extensions = ['.T00', '.T02', '.T04']
    file_ext = os.path.splitext(infile)[1].upper()
    if file_ext not in valid_extensions:
        print(f"Error: Input file must have one of these extensions: {', '.join(valid_extensions)}")
        return False
    
    # Create output filename by replacing extension with .obs
    outfile = os.path.splitext(infile)[0] + '.obs'
    
    # Create temporary file for intermediate conversion
    tmpfile = tempfile.NamedTemporaryFile(suffix='.tgd', delete=False)
    
    try:
        # Convert .T00/.T02/.T04 file into intermediate .tgd file
        args = ['/usr/local/bin/runpkr00', '-g', '-d', '-v', infile, tmpfile.name]
        subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Convert tgd to RINEX
        with open(outfile, 'w') as f:
            args = ['/usr/local/bin/teqc', '+C2', '-R', tmpfile.name]
            subprocess.run(args, stdout=f, stderr=subprocess.DEVNULL)
            
        # Verify output file was created and has content
        if not os.path.exists(outfile):
            print(f"Error: Output file {outfile} was not created")
            return False
            
        output_size = os.path.getsize(outfile)
        if output_size == 0:
            print(f"Error: Output file {outfile} is empty")
            return False
        
        # If antenna type is provided, edit the RINEX header
        if antenna_type:
            print(f"Editing antenna type to: {antenna_type}")
            
            # Create a mock measurement object for the edit_rinex_header function
            class MockMeasurementFiles:
                def __init__(self, outfile):
                    # Ensure we have a proper path structure for the edit_rinex_header function
                    if os.path.dirname(outfile):
                        self.daily_dnld_path = outfile
                    else:
                        # If no directory, use current directory
                        self.daily_dnld_path = os.path.join('.', outfile)
            
            mock_m = MockMeasurementFiles(outfile)
            
            # Edit the RINEX header with antenna type
            success = edit_rinex_header(
                infile=outfile,
                m=mock_m,
                station="UNKNOWN",  # Default station name
                organization="UNKNOWN",  # Default organization
                user="UNKNOWN",  # Default user
                antenna_type=antenna_type
            )
            
            if success:
                print(f"Successfully edited antenna type in {outfile}")
            else:
                print(f"Warning: Failed to edit antenna type, keeping original file")
        
        print(f"Successfully converted {infile} to {outfile}")
        return True
        
    except Exception as e:
        print(f"Error during conversion: {e}")
        return False
        
    finally:
        # Clean up temporary file
        try:
            tmpfile.close()
            os.unlink(tmpfile.name)
        except:
            pass

def main():
    parser = argparse.ArgumentParser(description='Convert Trimble T00/T02/T04 files to RINEX format')
    parser.add_argument('input_file', help='Input Trimble file (.T00/.T02/.T04)')
    parser.add_argument('--antenna_type', required=True, help='Antenna type to set in RINEX header')
    
    args = parser.parse_args()
    
    success = convert_trimble_to_rinex(args.input_file, args.antenna_type)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 
