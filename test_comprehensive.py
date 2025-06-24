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
    
    # Ensure proper RINEX format: data in columns 1-60, comment in columns 61-80
    if len(line_content) >= 20:
        # Truncate data portion to 60 characters if needed
        data_portion = line_content[:-20][:60]  # First 60 chars of data portion
        comment_field = line_content[-20:]       # Last 20 chars (comment field)
        
        # Remove leading spaces from comment field
        if comment_field.startswith(' '):
            comment_text = comment_field.lstrip()
            if comment_text:
                return f"{data_portion}{comment_text}"
            else:
                # If comment field is all spaces, just return data portion
                return data_portion
        else:
            # No leading spaces in comment field, just ensure data portion is 60 chars
            return f"{data_portion}{comment_field}"
    
    return line_content

# Test various header line types
test_lines = [
    # NetR8 problematic line
    "N8GA_NETR8                                                  MARKER NAME",
    # Other lines from the error log
    "N8GA                                                        MARKER NUMBER",
    "TRM41249.00     NONE                    ANT # / TYPE",
    "539802.6777 -4849660.2573  4094102.7248                  APPROX POSITION XYZ",
    "8    C1    L1    S1    P1    C2    L2    S2    P2      # / TYPES OF OBSERV",
    "30.000                                                  INTERVAL",
    "2025     6    22     0     0    0.0000000     GPS         TIME OF FIRST OBS",
    # Line that's too long (>80 chars)
    "THIS IS A VERY LONG LINE THAT EXCEEDS EIGHTY CHARACTERS AND SHOULD BE TRUNCATED TO FIT WITHIN THE LIMIT",
    # Line with no leading spaces in comment
    "NORMAL DATA                                               MARKER NAME",
    # Line with all spaces in comment field
    "EMPTY COMMENT                                              ",
]

print("Testing RINEX header line validation and correction:")
print("=" * 60)

for i, line in enumerate(test_lines, 1):
    print(f"\nTest {i}:")
    print(f"Original: '{line}' (length: {len(line)})")
    
    fixed = validate_and_fix_rinex_header_line(line)
    print(f"Fixed:    '{fixed}' (length: {len(fixed)})")
    
    if fixed != line:
        print("*** CHANGED ***")
        if len(fixed) != len(line):
            print(f"Length changed: {len(line)} -> {len(fixed)}")
    else:
        print("No change needed") 