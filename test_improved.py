#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from conversion_funcs import validate_and_fix_rinex_header_line

def validate_and_fix_rinex_header_line(line_content):
    """Validate and fix a RINEX header line according to RINEX 2.11 specification.
    
    Args:
        line_content (str): The header line content (without newline)
        
    Returns:
        str: The corrected line content, or original if no fixes needed
    """
    # First, ensure line doesn't exceed 80 characters
    if len(line_content) > 80:
        line_content = line_content[:80]
    
    # Extract the header label (columns 61-80)
    if len(line_content) < 20:
        return line_content  # Line too short to have a header label
    
    # Look for known header labels in the last 20 characters
    last_20 = line_content[-20:]
    known_labels = [
        "MARKER NAME", "MARKER NUMBER", "OBSERVER / AGENCY", "REC # / TYPE / VERS",
        "ANT # / TYPE", "APPROX POSITION XYZ", "ANTENNA: DELTA H/E/N",
        "WAVELENGTH FACT L1/2", "# / TYPES OF OBSERV", "INTERVAL",
        "TIME OF FIRST OBS", "TIME OF LAST OBS", "RCV CLOCK OFFS APPL",
        "LEAP SECONDS", "# OF SATELLITES", "PRN / # OF OBS", "END OF HEADER",
        "COMMENT", "RINEX VERSION / TYPE", "PGM / RUN BY / DATE"
    ]
    
    header_label = None
    for label in known_labels:
        if label in last_20:
            header_label = label
            break
    
    if not header_label:
        return line_content  # No known header label found
    
    # Extract data portion (everything before the header label)
    label_start = line_content.rfind(header_label)
    if label_start == -1:
        return line_content  # Header label not found
    
    data_portion = line_content[:label_start]
    
    # Process based on header type
    if header_label == "MARKER NAME":
        # Format: A60 - Name of antenna marker
        marker_name = data_portion[:60].strip()
        return f"{marker_name:<60}{header_label:>20}"
        
    elif header_label == "MARKER NUMBER":
        # Format: A20 - Number of antenna marker
        marker_number = data_portion[:20].strip()
        return f"{marker_number:<20}{header_label:>20}"
        
    elif header_label == "OBSERVER / AGENCY":
        # Format: A20,A40 - Name of observer / agency
        observer = data_portion[:20].strip()
        agency = data_portion[20:60].strip()
        return f"{observer:<20}{agency:<40}{header_label:>20}"
        
    elif header_label == "REC # / TYPE / VERS":
        # Format: 3A20 - Receiver number, type, and version
        rec_num = data_portion[:20].strip()
        rec_type = data_portion[20:40].strip()
        rec_vers = data_portion[40:60].strip()
        return f"{rec_num:<20}{rec_type:<20}{rec_vers:<20}{header_label:>20}"
        
    elif header_label == "ANT # / TYPE":
        # Format: 2A20 - Antenna number and type
        ant_num = data_portion[:20].strip()
        ant_type = data_portion[20:40].strip()
        return f"{ant_num:<20}{ant_type:<20}{'':<20}{header_label:>20}"
        
    elif header_label == "APPROX POSITION XYZ":
        # Format: 3F14.4 - Approximate marker position (WGS84)
        position = data_portion[:60].strip()
        return f"{position:<60}{header_label:>20}"
        
    elif header_label == "ANTENNA: DELTA H/E/N":
        # Format: 3F14.4 - Antenna height and eccentricities
        delta = data_portion[:60].strip()
        return f"{delta:<60}{header_label:>20}"
        
    elif header_label == "WAVELENGTH FACT L1/2":
        # Format: 2I6,I6 - Wavelength factors for L1 and L2
        wavelength = data_portion[:60].strip()
        return f"{wavelength:<60}{header_label:>20}"
        
    elif header_label == "# / TYPES OF OBSERV":
        # Format: I6,9(4X,A1,A1) - Number and types of observations
        obs_types = data_portion[:60].strip()
        return f"{obs_types:<60}{header_label:>20}"
        
    elif header_label == "INTERVAL":
        # Format: F10.3 - Observation interval in seconds
        interval = data_portion[:10].strip()
        return f"{interval:<10}{'':<50}{header_label:>20}"
        
    elif header_label == "TIME OF FIRST OBS":
        # Format: 5I6,F13.7,5X,A3 - Time of first observation
        time_obs = data_portion[:60].strip()
        return f"{time_obs:<60}{header_label:>20}"
        
    elif header_label == "TIME OF LAST OBS":
        # Format: 5I6,F13.7,5X,A3 - Time of last observation
        time_obs = data_portion[:60].strip()
        return f"{time_obs:<60}{header_label:>20}"
        
    elif header_label == "RCV CLOCK OFFS APPL":
        # Format: I6 - Receiver clock offset applied flag
        flag = data_portion[:6].strip()
        return f"{flag:<6}{'':<54}{header_label:>20}"
        
    elif header_label == "LEAP SECONDS":
        # Format: I6 - Number of leap seconds
        leap = data_portion[:6].strip()
        return f"{leap:<6}{'':<54}{header_label:>20}"
        
    elif header_label == "# OF SATELLITES":
        # Format: I6 - Number of satellites
        num_sats = data_portion[:6].strip()
        return f"{num_sats:<6}{'':<54}{header_label:>20}"
        
    elif header_label == "PRN / # OF OBS":
        # Format: 3X,A1,I2,9I6 - PRN and observation counts
        prn_obs = data_portion[:60].strip()
        return f"{prn_obs:<60}{header_label:>20}"
        
    elif header_label == "END OF HEADER":
        # Format: 60X - Last record in header section
        return f"{'':<60}{header_label:>20}"
        
    elif header_label == "COMMENT":
        # Format: A60 - Comment line(s)
        comment = data_portion[:60].strip()
        return f"{comment:<60}{header_label:>20}"
        
    elif header_label == "RINEX VERSION / TYPE":
        # Format: F9.2,11X,A1,19X,A1,19X,A1 - Version, file type, satellite system
        version_info = data_portion[:60].strip()
        return f"{version_info:<60}{header_label:>20}"
        
    elif header_label == "PGM / RUN BY / DATE":
        # Format: A20,A20,A20 - Program, run by, date
        pgm_info = data_portion[:60].strip()
        return f"{pgm_info:<60}{header_label:>20}"
        
    else:
        # Unknown header type - just ensure proper format
        data = data_portion[:60].strip()
        return f"{data:<60}{header_label:>20}"

def test_exact_error_line():
    """Test the exact line from the error message"""
    exact_line = "4906K34356          Trimble NetR8       48.01                REC # / TYPE / VERS"
    print(f"Testing exact error line:")
    print(f"Original: '{exact_line}'")
    print(f"Length: {len(exact_line)}")
    print(f"Contains 'REC # / TYPE / VERS': {'REC # / TYPE / VERS' in exact_line}")
    
    fixed = validate_and_fix_rinex_header_line(exact_line)
    print(f"Fixed:    '{fixed}'")
    print(f"Changed:  {fixed != exact_line}")
    print(f"Length:   {len(exact_line)} -> {len(fixed)}")
    
    # Show the breakdown
    if fixed != exact_line:
        print(f"Data portion: '{fixed[:-20]}'")
        print(f"Header label: '{fixed[-20:]}'")

def debug_line_structure():
    """Debug the exact structure of the NetR8 problematic line"""
    line = "4906K34356          Trimble NetR8       48.01                REC # / TYPE / VERS"
    print(f"Line length: {len(line)}")
    print(f"Last 20 chars: '{line[-20:]}'")
    print(f"Contains 'REC # / TYPE / VERS': {'REC # / TYPE / VERS' in line}")
    print(f"Label position: {line.find('REC # / TYPE / VERS')}")
    print(f"Label in last 20: {'REC # / TYPE / VERS' in line[-20:]}")
    
    # Show the structure
    print(f"Columns 1-60: '{line[:60]}'")
    print(f"Columns 61-80: '{line[60:80]}'")

def test_problematic_lines():
    """Test the specific problematic lines from the error log"""
    
    # Test cases from the actual error log
    test_cases = [
        # NetR8 problematic line
        "4906K34356          Trimble NetR8       48.01                REC # / TYPE / VERS",
        
        # NetRS problematic lines
        "teqc                2019Feb25           20250623 21:10:12UTCPGM / RUN BY / DATE",
        "sssrcrin-15.6.1x     22-JUN-25           00:00 PGM / RUN BY /PGM / RUN BY / DATE",
        
        # Lines that should NOT be changed (already correct)
        "2.11           OBSERVATION DATA    G (GPS)             RINEX VERSION / TYPE",
        "N8UR-RS1                                                    MARKER NAME",
        "498269.9476 -4886884.0246  4055009.1425                  APPROX POSITION XYZ",
        "8    L1    L2    C1    P1    C2    P2    S1    S2      # / TYPES OF OBSERV",
        "18                                                      LEAP SECONDS",
    ]
    
    print("Testing problematic lines from error log:")
    print("=" * 60)
    
    for i, original in enumerate(test_cases, 1):
        fixed = validate_and_fix_rinex_header_line(original)
        changed = fixed != original
        
        print(f"Test {i}:")
        print(f"  Original: '{original}'")
        print(f"  Fixed:    '{fixed}'")
        print(f"  Changed:  {changed}")
        print(f"  Length:   {len(original)} -> {len(fixed)}")
        print()

if __name__ == "__main__":
    test_exact_error_line()
    print("\n" + "="*60 + "\n")
    debug_line_structure()
    print("\n" + "="*60 + "\n")
    test_problematic_lines() 