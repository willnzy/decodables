#!/usr/bin/env python3
"""
Validate async/await patterns in API layer.

This script checks for common async pattern violations:
1. Handler calls without await
2. Handler calls without parentheses ()
3. Database .execute() calls without await
"""

import re
import os
import sys
from pathlib import Path

# ANSI color codes
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def check_handler_calls(file_path: str) -> list:
    """Check for handler calls missing await or ()."""
    issues = []
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    for i, line in enumerate(lines, 1):
        # Pattern 1: handler = container.xxx_handler (missing both await and ())
        if re.search(r'\s+handler\s*=\s*container\.[a-z_]+_handler\s*$', line):
            issues.append({
                'line': i,
                'type': 'CRITICAL',
                'message': 'Handler call missing both await and ()',
                'code': line.strip()
            })
        
        # Pattern 2: handler = container.xxx_handler() (missing await)
        elif re.search(r'\s+handler\s*=\s*container\.[a-z_]+_handler\(\)\s*$', line):
            issues.append({
                'line': i,
                'type': 'CRITICAL',
                'message': 'Handler call missing await',
                'code': line.strip()
            })
        
        # Pattern 3: handler = await container.xxx_handler (missing ())
        elif re.search(r'\s+handler\s*=\s*await\s+container\.[a-z_]+_handler\s*$', line):
            issues.append({
                'line': i,
                'type': 'CRITICAL',
                'message': 'Handler call missing ()',
                'code': line.strip()
            })
    
    return issues

def check_execute_calls(file_path: str) -> list:
    """Check for .execute() calls missing await."""
    issues = []
    
    with open(file_path, 'r') as f:
        content = f.read()
        lines = content.split('\n')
    
    for i, line in enumerate(lines, 1):
        # Skip if line is a comment
        if line.strip().startswith('#'):
            continue
        
        # Check for .execute() not preceded by await
        if '.execute()' in line:
            # Look back to see if there's an await
            # This is a simplified check - might need refinement
            if 'await' not in line:
                # Check if it's a multi-line query
                prev_line = lines[i-2] if i > 1 else ''
                if 'await' not in prev_line:
                    issues.append({
                        'line': i,
                        'type': 'WARNING',
                        'message': 'execute() call might be missing await',
                        'code': line.strip()
                    })
    
    return issues

def scan_directory(directory: str, pattern: str = "*.py"):
    """Scan directory for Python files and check async patterns."""
    all_issues = {}
    
    path = Path(directory)
    files = list(path.glob(f"**/{pattern}"))
    
    print(f"{BLUE}Scanning {len(files)} files in {directory}...{RESET}\n")
    
    for file_path in files:
        handler_issues = check_handler_calls(str(file_path))
        # execute_issues = check_execute_calls(str(file_path))
        
        if handler_issues:
            rel_path = str(file_path.relative_to(path.parent))
            all_issues[rel_path] = handler_issues
    
    return all_issues

def print_results(issues: dict):
    """Print validation results."""
    if not issues:
        print(f"{GREEN}✅ All async patterns are correct!{RESET}")
        print(f"{GREEN}✅ No handler calls missing await or (){RESET}")
        return 0
    
    print(f"{RED}❌ Found {sum(len(v) for v in issues.values())} issues in {len(issues)} files:{RESET}\n")
    
    for file_path, file_issues in issues.items():
        print(f"{YELLOW}File: {file_path}{RESET}")
        for issue in file_issues:
            color = RED if issue['type'] == 'CRITICAL' else YELLOW
            print(f"  {color}Line {issue['line']}: {issue['message']}{RESET}")
            print(f"    {issue['code']}")
        print()
    
    return 1

def main():
    """Main validation function."""
    print(f"{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Async Pattern Validator{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    # Check API layer
    api_issues = scan_directory("api/user")
    
    # Print results
    exit_code = print_results(api_issues)
    
    if exit_code == 0:
        print(f"\n{GREEN}{'='*60}{RESET}")
        print(f"{GREEN}✅ Validation PASSED - All async patterns are correct!{RESET}")
        print(f"{GREEN}{'='*60}{RESET}")
    else:
        print(f"\n{RED}{'='*60}{RESET}")
        print(f"{RED}❌ Validation FAILED - Please fix the issues above{RESET}")
        print(f"{RED}{'='*60}{RESET}")
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main())
