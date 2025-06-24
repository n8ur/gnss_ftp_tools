#!/usr/bin/env python3

test_line = "N8GA_NETR8                                                  MARKER NAME"
print(f"Original: '{test_line}' (length: {len(test_line)})")

# Let me see what the last 20 characters actually are
comment_field = test_line[-20:]
print(f"Last 20 chars: '{comment_field}'")

# Does this comment field have leading spaces?
print(f"Starts with space: {comment_field.startswith(' ')}")

# If I remove leading spaces from this comment field:
if comment_field.startswith(' '):
    stripped = comment_field.lstrip()
    print(f"After lstrip: '{stripped}'")
    
    # The function should return data_portion + stripped_comment
    data_portion = test_line[:-20]
    result = data_portion + stripped
    print(f"Result: '{result}' (length: {len(result)})")
    
    # But this is wrong! The function is treating "         MARKER NAME" as the comment field
    # when it should be treating just "MARKER NAME" as the comment field
    
    # Let me see what a proper RINEX line should look like:
    # The marker name should be in the first 60 characters, comment in last 20
    proper_line = "N8GA_NETR8                                         MARKER NAME"
    print(f"\nProper format: '{proper_line}' (length: {len(proper_line)})")
    print(f"Proper data: '{proper_line[:60]}'")
    print(f"Proper comment: '{proper_line[-20:]}'")
    
    # The original line is malformed - the marker name extends into the comment field
    # But the function should NOT try to fix this - it should only remove leading spaces
    # from the comment field as it exists 