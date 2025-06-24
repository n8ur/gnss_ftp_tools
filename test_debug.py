#!/usr/bin/env python3

# Let me understand what the function should actually do
test_line = "N8GA_NETR8                                                  MARKER NAME"
print(f"Original: '{test_line}' (length: {len(test_line)})")

# The function should ONLY:
# 1. Truncate lines longer than 80 characters (this line is 71 chars, so no change)
# 2. Remove leading spaces from comment field (last 20 chars)

comment_field = test_line[-20:]
data_portion = test_line[:-20]

print(f"Data portion: '{data_portion}' (length: {len(data_portion)})")
print(f"Comment field: '{comment_field}' (length: {len(comment_field)})")

# Does comment field have leading spaces?
print(f"Comment field starts with space: {comment_field.startswith(' ')}")

# If it has leading spaces, remove them but keep 20 chars
if comment_field.startswith(' '):
    comment_text = comment_field.lstrip()
    print(f"After lstrip: '{comment_text}' (length: {len(comment_text)})")
    
    # The user said NO PADDING, so just return the data portion + stripped comment
    result = data_portion + comment_text
    print(f"Result: '{result}' (length: {len(result)})")
else:
    print("No leading spaces in comment field")

# But wait - this would make the line shorter than 80 chars, which is allowed
# The user said lines can be shorter than 80 chars, so this should be fine 