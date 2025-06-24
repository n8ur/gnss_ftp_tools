#!/usr/bin/env python3

def validate_and_fix_rinex_header_line(line_content):
    """Validate and fix a RINEX header line according to basic structural requirements.
    
    Args:
        line_content (str): The header line content (without newline)
        
    Returns:
        str: The corrected line content, or original if no fixes needed
    """
    # Only fix lines longer than 80 characters
    if len(line_content) > 80:
        line_content = line_content[:80]
    
    # Left-justify comment text by removing leading spaces
    if len(line_content) >= 20:
        comment_field = line_content[-20:]
        data_portion = line_content[:-20]
        
        # If comment field has leading spaces, remove them
        if comment_field.startswith(' '):
            comment_text = comment_field.strip()
            if comment_text:
                # Just remove leading spaces, don't pad
                return f"{data_portion}{comment_text}"
    
    return line_content

# Test the specific line that's failing
test_line = "N8GA_NETR8                                                  MARKER NAME"
print(f"Original line: '{test_line}'")
print(f"Original length: {len(test_line)}")
print(f"Original comment field: '{test_line[-20:]}'")
print(f"Original data portion: '{test_line[:-20]}'")

fixed_line = validate_and_fix_rinex_header_line(test_line)
print(f"Fixed line: '{fixed_line}'")
print(f"Fixed length: {len(fixed_line)}")
print(f"Fixed comment field: '{fixed_line[-20:]}'")
print(f"Fixed data portion: '{fixed_line[:-20]}'")

# Test a few other lines from the error log
test_lines = [
    "N8GA                                                        MARKER NUMBER",
    "TRM41249.00     NONE                    ANT # / TYPE",
    "539802.6777 -4849660.2573  4094102.7248                  APPROX POSITION XYZ",
    "8    C1    L1    S1    P1    C2    L2    S2    P2      # / TYPES OF OBSERV",
    "30.000                                                  INTERVAL",
    "2025     6    22     0     0    0.0000000     GPS         TIME OF FIRST OBS"
]

print("\nTesting other lines:")
for line in test_lines:
    print(f"\nOriginal: '{line}' (length: {len(line)})")
    fixed = validate_and_fix_rinex_header_line(line)
    print(f"Fixed:    '{fixed}' (length: {len(fixed)})")
    if fixed != line:
        print("*** CHANGED ***") 