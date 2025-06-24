#!/usr/bin/env python3

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
    
    header_label = line_content[-20:].strip()
    data_portion = line_content[:-20]
    
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
        # This is a complex format with 3 floating point numbers
        # For now, just ensure it fits in 60 characters
        position = data_portion[:60].strip()
        return f"{position:<60}{header_label:>20}"
        
    elif header_label == "ANTENNA: DELTA H/E/N":
        # Format: 3F14.4 - Antenna height and eccentricities
        # This is a complex format with 3 floating point numbers
        # For now, just ensure it fits in 60 characters
        delta = data_portion[:60].strip()
        return f"{delta:<60}{header_label:>20}"
        
    elif header_label == "WAVELENGTH FACT L1/2":
        # Format: 2I6,I6 - Wavelength factors for L1 and L2
        # This is a complex format with integer fields
        # For now, just ensure it fits in 60 characters
        wavelength = data_portion[:60].strip()
        return f"{wavelength:<60}{header_label:>20}"
        
    elif header_label == "# / TYPES OF OBSERV":
        # Format: I6,9(4X,A1,A1) - Number and types of observations
        # This is a complex format that can have continuation lines
        # For now, just ensure it fits in 60 characters
        obs_types = data_portion[:60].strip()
        return f"{obs_types:<60}{header_label:>20}"
        
    elif header_label == "INTERVAL":
        # Format: F10.3 - Observation interval in seconds
        interval = data_portion[:10].strip()
        return f"{interval:<10}{'':<50}{header_label:>20}"
        
    elif header_label == "TIME OF FIRST OBS":
        # Format: 5I6,F13.7,5X,A3 - Time of first observation
        # This is a complex format with date/time fields
        # For now, just ensure it fits in 60 characters
        time_obs = data_portion[:60].strip()
        return f"{time_obs:<60}{header_label:>20}"
        
    elif header_label == "TIME OF LAST OBS":
        # Format: 5I6,F13.7,5X,A3 - Time of last observation
        # This is a complex format with date/time fields
        # For now, just ensure it fits in 60 characters
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
        # This is a complex format that can have continuation lines
        # For now, just ensure it fits in 60 characters
        prn_obs = data_portion[:60].strip()
        return f"{prn_obs:<60}{header_label:>20}"
        
    elif header_label == "END OF HEADER":
        # Format: 60X - Last record in header section
        return f"{'':<60}{header_label:>20}"
        
    elif header_label == "COMMENT":
        # Format: A60 - Comment line(s)
        comment = data_portion[:60].strip()
        return f"{comment:<60}{header_label:>20}"
        
    else:
        # Unknown header type - just ensure proper format
        data = data_portion[:60].strip()
        return f"{data:<60}{header_label:>20}"

# Test the problematic NetR8 lines
test_lines = [
    "N8GA_NETR8                                                  MARKER NAME",
    "N8GA                                                        MARKER NUMBER",
    "TRM41249.00     NONE                    ANT # / TYPE",
    "539802.6777 -4849660.2573  4094102.7248                  APPROX POSITION XYZ",
    "8    C1    L1    S1    P1    C2    L2    S2    P2      # / TYPES OF OBSERV",
    "30.000                                                  INTERVAL",
    "2025     6    22     0     0    0.0000000     GPS         TIME OF FIRST OBS",
]

print("Testing new RINEX 2.11-based header validation function:")
print("=" * 70)

for i, line in enumerate(test_lines, 1):
    print(f"\nTest {i}:")
    print(f"Original: '{line}' (length: {len(line)})")
    
    fixed = validate_and_fix_rinex_header_line(line)
    print(f"Fixed:    '{fixed}' (length: {len(fixed)})")
    
    if fixed != line:
        print("*** CHANGED ***")
        print(f"Length: {len(line)} -> {len(fixed)}")
        
        # Show the breakdown
        if len(fixed) >= 20:
            print(f"Data portion: '{fixed[:-20]}'")
            print(f"Header label: '{fixed[-20:]}'")
    else:
        print("No change needed") 