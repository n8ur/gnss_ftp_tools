#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from conversion_funcs import validate_and_fix_rinex_header_line

# Test the exact problematic line
test_line = "4906K34356          Trimble NetR8       48.01                REC # / TYPE / VERS"

print(f"Original: '{test_line}'")
print(f"Length: {len(test_line)}")

# Check the label field
label_field = test_line[60:80]
print(f"Label field: '{label_field}'")
print(f"Starts with space: {label_field.startswith(' ')}")

# Test the function
fixed = validate_and_fix_rinex_header_line(test_line)
print(f"Fixed: '{fixed}'")
print(f"Changed: {fixed != test_line}")

if fixed != test_line:
    print(f"Fixed label field: '{fixed[60:80]}'")
else:
    print("No change made") 