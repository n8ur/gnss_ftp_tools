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
            comment_text = comment_field.lstrip()
            if comment_text:
                return f"{data_portion}{comment_text}"
    
    return line_content

# Test the specific line that was failing
test_line = "N8GA_NETR8                                                  MARKER NAME"
print(f"Original: '{test_line}' (length: {len(test_line)})")

fixed_line = validate_and_fix_rinex_header_line(test_line)
print(f"Fixed:    '{fixed_line}' (length: {len(fixed_line)})")

if fixed_line != test_line:
    print("*** CHANGED ***")
    print(f"Comment field was: '{test_line[-20:]}'")
    print(f"Comment field now: '{fixed_line[-20:]}'")
else:
    print("No change needed") 