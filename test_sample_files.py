#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from conversion_funcs import validate_and_fix_rinex_header_line

def test_file_headers(filename):
    """Test header fixing on a specific file"""
    print(f"\n{'='*80}")
    print(f"Testing file: {filename}")
    print(f"{'='*80}")
    
    try:
        with open(f"sample/{filename}", 'r') as f:
            lines = f.readlines()
        
        # Find and test the REC # / TYPE / VERS line
        for i, line in enumerate(lines, 1):
            line_content = line.rstrip('\r\n')
            if 'REC # / TYPE / VERS' in line_content:
                print(f"\nFound REC # / TYPE / VERS line at line {i}:")
                print(f"Original: '{line_content}'")
                print(f"Length: {len(line_content)}")
                
                # Show the field breakdown
                if len(line_content) >= 60:
                    rec_num = line_content[0:20]
                    rec_type = line_content[20:40]
                    rec_vers = line_content[40:60]
                    label = line_content[60:80] if len(line_content) >= 80 else line_content[60:]
                    
                    print(f"Field breakdown:")
                    print(f"  Receiver # (cols 1-20):   '{rec_num}' (len: {len(rec_num)})")
                    print(f"  Receiver type (cols 21-40): '{rec_type}' (len: {len(rec_type)})")
                    print(f"  Receiver version (cols 41-60): '{rec_vers}' (len: {len(rec_vers)})")
                    print(f"  Label (cols 61-80): '{label}' (len: {len(label)})")
                    
                    # Debug: Check if label field starts with space
                    if len(line_content) >= 80:
                        label_field = line_content[60:80]
                        print(f"  Label field (cols 61-80): '{label_field}' (len: {len(label_field)})")
                        print(f"  Label field starts with space: {label_field.startswith(' ')}")
                        print(f"  Label field contains 'REC # / TYPE / VERS': {'REC # / TYPE / VERS' in label_field}")
                    
                    # Check for leading space in version field
                    if rec_vers.startswith(' '):
                        print(f"  *** ISSUE: Version field starts with a space! ***")
                    else:
                        print(f"  Version field does not start with a space - OK")
                
                # Apply the fix
                fixed_line = validate_and_fix_rinex_header_line(line_content)
                changed = fixed_line != line_content
                
                print(f"\nAfter fix:")
                print(f"Fixed:    '{fixed_line}'")
                print(f"Changed:  {changed}")
                print(f"Length:   {len(line_content)} -> {len(fixed_line)}")
                
                if changed:
                    # Show the fixed field breakdown
                    if len(fixed_line) >= 60:
                        rec_num_fixed = fixed_line[0:20]
                        rec_type_fixed = fixed_line[20:40]
                        rec_vers_fixed = fixed_line[40:60]
                        label_fixed = fixed_line[60:80] if len(fixed_line) >= 80 else fixed_line[60:]
                        
                        print(f"Fixed field breakdown:")
                        print(f"  Receiver # (cols 1-20):   '{rec_num_fixed}' (len: {len(rec_num_fixed)})")
                        print(f"  Receiver type (cols 21-40): '{rec_type_fixed}' (len: {len(rec_type_fixed)})")
                        print(f"  Receiver version (cols 41-60): '{rec_vers_fixed}' (len: {len(rec_vers_fixed)})")
                        print(f"  Label (cols 61-80): '{label_fixed}' (len: {len(label_fixed)})")
                
                break  # Only process the first occurrence
        
        # Also check for any other header lines that might be problematic
        print(f"\nChecking for other potentially problematic header lines...")
        for i, line in enumerate(lines, 1):
            line_content = line.rstrip('\r\n')
            if 'END OF HEADER' in line_content:
                print(f"Found END OF HEADER at line {i}")
                break
            if len(line_content) > 80:
                print(f"Line {i} is longer than 80 chars: '{line_content[:80]}...'")
                
    except FileNotFoundError:
        print(f"File {filename} not found in sample directory")
    except Exception as e:
        print(f"Error processing {filename}: {e}")

def test_direct_function():
    """Test the function directly with the problematic line"""
    print("\n" + "="*80)
    print("Direct function test")
    print("="*80)
    
    from conversion_funcs import validate_and_fix_rinex_header_line
    
    test_line = "4906K34356          Trimble NetR8       48.01                REC # / TYPE / VERS"
    print(f"Test line: '{test_line}'")
    print(f"Length: {len(test_line)}")
    
    # Check the label field
    if len(test_line) >= 80:
        label_field = test_line[60:80]
        print(f"Label field (cols 61-80): '{label_field}' (len: {len(label_field)})")
        print(f"Label field starts with space: {label_field.startswith(' ')}")
        print(f"Label field contains 'REC # / TYPE / VERS': {'REC # / TYPE / VERS' in label_field}")
    
    # Test the function
    fixed = validate_and_fix_rinex_header_line(test_line)
    print(f"Fixed: '{fixed}'")
    print(f"Changed: {fixed != test_line}")
    
    if fixed != test_line:
        print(f"Fixed label field: '{fixed[60:80]}'")
    else:
        print("Function did not change the line - debugging why:")
        # Debug the function logic
        label = 'REC # / TYPE / VERS'
        if label in test_line:
            print(f"  Label found in line")
            if len(test_line) >= 80:
                label_field = test_line[60:80]
                print(f"  Label field: '{label_field}'")
                print(f"  Starts with space: {label_field.startswith(' ')}")
                print(f"  Contains label: {'REC # / TYPE / VERS' in label_field}")
                if label_field.startswith(' ') and label in label_field:
                    print(f"  Condition should be True - function should fix this")
                else:
                    print(f"  Condition is False - that's why no fix")

def fix_and_save_file(input_filename, output_filename):
    """Apply header fix to all lines and save to output file."""
    from conversion_funcs import validate_and_fix_rinex_header_line
    with open(f"sample/{input_filename}", 'r') as fin, open(f"sample/{output_filename}", 'w') as fout:
        for line in fin:
            line_content = line.rstrip('\r\n')
            fixed_line = validate_and_fix_rinex_header_line(line_content)
            fout.write(fixed_line + '\n')
    print(f"Saved fixed file as sample/{output_filename}")

def main():
    """Test all sample files"""
    files = [
        "mosaic-t1_1730.25o",
        "netrs-1202506220000a.obs", 
        "n8ga-netr8202506220000A.25O",
        "netr9-1___202506220000A.25O"
    ]
    
    print("Testing header-fixing function against all sample files")
    print("Focusing on REC # / TYPE / VERS line and leading space in version field")
    
    for filename in files:
        test_file_headers(filename)
    
    # Add direct function test
    test_direct_function()
    
    # Save fixed NetR9 file for user inspection
    fix_and_save_file("netr9-1___202506220000A.25O", "netr9-1___202506220000A.fixed.25O")

if __name__ == "__main__":
    main() 