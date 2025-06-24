#!/usr/bin/env python3

# Let me examine the actual RINEX format
# According to RINEX specification, header lines have:
# - Data portion (variable length, but typically 60 characters)
# - Comment field (last 20 characters, left-justified)

test_line = "N8GA_NETR8                                                  MARKER NAME"
print(f"Original: '{test_line}' (length: {len(test_line)})")

# Let's see what the actual data portion should be
# In RINEX, the marker name should be in the first 60 characters
print(f"First 60 chars: '{test_line[:60]}'")
print(f"Last 20 chars:  '{test_line[-20:]}'")

# The issue is that the function is treating the last 20 chars as comment field
# But in this case, the marker name extends into what should be the comment field
# A proper RINEX line should have the marker name in the first 60 chars, 
# and the comment in the last 20 chars

# Let's see what a proper RINEX line should look like:
proper_line = "N8GA_NETR8                                         MARKER NAME"
print(f"\nProper format: '{proper_line}' (length: {len(proper_line)})")
print(f"First 60 chars: '{proper_line[:60]}'")
print(f"Last 20 chars:  '{proper_line[-20:]}'")

# The problem is that the original line has the marker name extending beyond 60 chars
# The function should NOT be modifying this - it should only fix lines longer than 80 chars
# and remove leading spaces from the comment field

print(f"\nIs original line > 80 chars? {len(test_line) > 80}")
print(f"Does comment field have leading spaces? {test_line[-20:].startswith(' ')}")

# The function should NOT change this line because:
# 1. It's not longer than 80 characters (71 chars)
# 2. The comment field doesn't have leading spaces to remove 