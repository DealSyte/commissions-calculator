#!/usr/bin/env python3
"""
Validate that test_scenarios_business_summary.md stays in sync with test_integration_scenarios.py.

This script checks:
1. All test classes in the test file are documented
2. All test methods are referenced in the doc
3. Warns about documented tests that no longer exist

Run: python scripts/validate_test_docs_sync.py
"""

import re
import sys
from pathlib import Path


def extract_test_classes_and_methods(test_file: Path) -> dict[str, list[str]]:
    """Extract test class names and their test methods from the test file."""
    content = test_file.read_text()
    
    classes = {}
    current_class = None
    
    for line in content.split('\n'):
        # Match class definitions
        class_match = re.match(r'^class (Test\w+)', line)
        if class_match:
            current_class = class_match.group(1)
            classes[current_class] = []
            continue
        
        # Match test methods
        if current_class:
            method_match = re.match(r'^\s+def (test_\w+)', line)
            if method_match:
                classes[current_class].append(method_match.group(1))
    
    return classes


def extract_documented_tests(doc_file: Path) -> tuple[set[str], set[str]]:
    """Extract class names and method names referenced in the documentation."""
    content = doc_file.read_text()
    
    # Find test classes mentioned (e.g., **Test Class**: `TestPreferredRateOverride`)
    classes = set(re.findall(r'\*\*Test Class\*\*:\s*`(Test\w+)`', content))
    
    # Find test methods mentioned (e.g., **Test Method**: `test_preferred_rate_overrides_lehman`)
    methods = set(re.findall(r'\*\*Test Method\*\*:\s*`(test_\w+)`', content))
    
    return classes, methods


def main():
    # Find project root (where this script is in scripts/)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    test_file = project_root / 'tests' / 'test_integration_scenarios.py'
    doc_file = project_root / 'docs' / 'test_scenarios_business_summary.md'
    
    # Check files exist
    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        sys.exit(1)
    
    if not doc_file.exists():
        print(f"❌ Doc file not found: {doc_file}")
        sys.exit(1)
    
    # Extract test classes and methods
    test_classes = extract_test_classes_and_methods(test_file)
    doc_classes, doc_methods = extract_documented_tests(doc_file)
    
    # Flatten test methods for comparison
    all_test_methods = set()
    for methods in test_classes.values():
        all_test_methods.update(methods)
    
    # Check for missing documentation
    errors = []
    warnings = []
    
    # Check classes
    missing_classes = set(test_classes.keys()) - doc_classes
    extra_classes = doc_classes - set(test_classes.keys())
    
    for cls in missing_classes:
        errors.append(f"Missing class documentation: {cls}")
    
    for cls in extra_classes:
        warnings.append(f"Documented class no longer exists: {cls}")
    
    # Check methods
    missing_methods = all_test_methods - doc_methods
    extra_methods = doc_methods - all_test_methods
    
    for method in missing_methods:
        errors.append(f"Missing method documentation: {method}")
    
    for method in extra_methods:
        warnings.append(f"Documented method no longer exists: {method}")
    
    # Print results
    print("=" * 60)
    print("Test Documentation Sync Validation")
    print("=" * 60)
    print(f"\nTest file: {test_file.name}")
    print(f"Doc file:  {doc_file.name}")
    print(f"\nTest classes found: {len(test_classes)}")
    print(f"Test methods found: {len(all_test_methods)}")
    print(f"Documented classes: {len(doc_classes)}")
    print(f"Documented methods: {len(doc_methods)}")
    
    if errors:
        print(f"\n❌ ERRORS ({len(errors)}):")
        for error in sorted(errors):
            print(f"   - {error}")
    
    if warnings:
        print(f"\n⚠️  WARNINGS ({len(warnings)}):")
        for warning in sorted(warnings):
            print(f"   - {warning}")
    
    if not errors and not warnings:
        print("\n✅ All tests are documented and in sync!")
    
    print("\n" + "=" * 60)
    
    # Summary by class
    print("\nCoverage by Class:")
    for cls, methods in sorted(test_classes.items()):
        class_status = "✅" if cls in doc_classes else "❌"
        print(f"\n  {class_status} {cls}")
        for method in methods:
            method_status = "✅" if method in doc_methods else "❌"
            print(f"      {method_status} {method}")
    
    # Exit with error code if issues found
    if errors:
        sys.exit(1)
    
    sys.exit(0)


if __name__ == '__main__':
    main()
