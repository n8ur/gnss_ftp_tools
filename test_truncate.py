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

# Test the specific line that was failing
test_line = "N8GA_NETR8                                                  MARKER NAME"
print(f"Original: '{test_line}' (length: {len(test_line)})")

# Show the breakdown
print(f"Data portion (first 51 chars): '{test_line[:-20]}'")
print(f"Comment field (last 20 chars): '{test_line[-20:]}'")

fixed_line = validate_and_fix_rinex_header_line(test_line)
print(f"Fixed:    '{fixed_line}' (length: {len(fixed_line)})")

if fixed_line != test_line:
    print("*** CHANGED ***")
    print(f"Data portion now: '{fixed_line[:-len(fixed_line[-20:])]}'")
    print(f"Comment field now: '{fixed_line[-20:]}'")
else:
    print("No change needed") 