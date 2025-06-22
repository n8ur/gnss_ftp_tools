#!/usr/bin/env python3

############################################################
# convert_trimble.py v.20250622.1
# copyright 2025 John Ackermann N8UR jra@febo.com
#
# Simple program to convert Trimble T00/T02/T04 files to
# RINEX format. Does no header editing.
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
# RINEX.  Does no header editing.

import os
import sys
import subprocess
import tempfile

def convert_trimble_to_rinex(infile):
    """Convert Trimble .T00/.T02/.T04 file to RINEX format.
    
    Args:
        infile (str): Path to input Trimble file (.T00/.T02/.T04)
        
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
    if len(sys.argv) != 2:
        print("Usage: python convert_trimble.py <input_file>")
        print("Example: python convert_trimble.py data.T00")
        sys.exit(1)
        
    infile = sys.argv[1]
    success = convert_trimble_to_rinex(infile)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 
