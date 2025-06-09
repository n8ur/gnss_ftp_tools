#!/usr/bin/env python3

import os
import sys
import subprocess
import tempfile

def convert_trimble(infile, outfile, station, organization=None, user=None, marker_num=None, station_location=None):
    """Convert Trimble .T00 or .T02 file to RINEX format"""
    tmpfile = tempfile.NamedTemporaryFile(suffix='.tgd',delete=False)
    # convert .T00/.T02 file into intermediate .tgd file
    args = ['/usr/local/bin/runpkr00', '-g', '-d', '-v',
        infile, tmpfile.name]
    try:
        subprocess.run(args, \
            stdout = subprocess.DEVNULL, stderr = subprocess.DEVNULL)
    except Exception as e:
        print("Couldn't run runpkr00, error:",e)
        return
    tmpfile.flush()
    tmpfile.seek(0)
   
    # Process station name: uppercase and trim whitespace, truncate to 60 characters
    marker_name = station.upper().strip()[:60]
   
    # convert tgd to RINEX
    with open(outfile,'w') as f:
        # Build teqc command with options
        args = [
            '/usr/local/bin/teqc',
            '+C2',
            '-R',
            '-O.mo', marker_name
        ]
        
        # Add organization if provided
        if organization:
            org_name = organization.upper().strip()[:40]
            args.extend(['-O.ag', org_name])
            
        # Add user if provided
        if user:
            user_name = user.upper().strip()[:20]
            args.extend(['-O.o', user_name])
            
        # Add marker number if provided
        if marker_num:
            marker_number = marker_num.upper().strip()[:20]
            args.extend(['-O.mn', marker_number])
            
        # Add station location if provided
        if station_location:
            # Remove brackets if present and split by comma
            coords = station_location.strip('[]').split(',')
            if len(coords) == 3:
                try:
                    # Convert to float and add to teqc arguments
                    x, y, z = map(float, coords)
                    args.extend(['-O.px', str(x), str(y), str(z)])
                except ValueError:
                    print("Warning: Invalid station location format. Coordinates must be numeric values.")
            
        # Add input file
        args.append(tmpfile.name)
        
        try:
            subprocess.run(args, stdout = f, stderr = subprocess.DEVNULL)
        except Exception as e:
            print("Couldn't run teqc, error:",e)
            return
    s = outfile.split('/')
    s = s[len(s)-2] + '/' + s[len(s)-1]
    size = os.path.getsize(outfile)
    tmpfile.close()
    os.unlink(tmpfile.name)
    return True 