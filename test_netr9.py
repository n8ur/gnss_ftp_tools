#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from conversion_funcs import validate_and_fix_rinex_header_line

# Test the exact problematic NetR9 line
test_line = "NetR9 5.48Receiver Operator   20250622 000000 UTC PGM / RUN BY / DATE"

print(f"Original: '{test_line}'")
print(f"Length: {len(test_line)}")

# Show where the label is
label = 'PGM / RUN BY / DATE'
label_pos = test_line.find(label)
print(f"Label position: {label_pos}")
print(f"Label should be at column 61 (position 60)")

# Test the function
fixed = validate_and_fix_rinex_header_line(test_line)
print(f"Fixed: '{fixed}'")
print(f"Changed: {fixed != test_line}")
print(f"Length: {len(fixed)}")

if fixed != test_line:
    print(f"Fixed label position: {fixed.find(label)}")
    print(f"Data portion (cols 1-60): '{fixed[:60]}'")
    print(f"Label portion (cols 61-80): '{fixed[60:80]}'")
else:
    print("No change made") 