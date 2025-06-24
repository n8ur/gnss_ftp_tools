#!/usr/bin/env python3

test_line = "N8GA_NETR8                                                  MARKER NAME"
print(f"Original: '{test_line}' (length: {len(test_line)})")

comment_field = test_line[-20:]
print(f"Comment field: '{comment_field}' (length: {len(comment_field)})")
print(f"Comment field starts with space: {comment_field.startswith(' ')}")

# Let me see what lstrip() does
stripped = comment_field.lstrip()
print(f"After lstrip: '{stripped}' (length: {len(stripped)})")

# The issue is that the comment field is "         MARKER NAME"
# This has 9 leading spaces, then "MARKER NAME" (11 chars)
# So the total is 20 chars, which is correct for the comment field
# But the function should remove the leading spaces

# Let me test the function step by step
data_portion = test_line[:-20][:60]  # First 60 chars of data portion
comment_field = test_line[-20:]       # Last 20 chars (comment field)

print(f"\nData portion: '{data_portion}' (length: {len(data_portion)})")
print(f"Comment field: '{comment_field}' (length: {len(comment_field)})")

if comment_field.startswith(' '):
    comment_text = comment_field.lstrip()
    print(f"Comment text after lstrip: '{comment_text}' (length: {len(comment_text)})")
    if comment_text:
        result = f"{data_portion}{comment_text}"
        print(f"Result: '{result}' (length: {len(result)})")
    else:
        result = data_portion
        print(f"Result (no comment): '{result}' (length: {len(result)})")
else:
    result = f"{data_portion}{comment_field}"
    print(f"Result (no leading spaces): '{result}' (length: {len(result)})") 