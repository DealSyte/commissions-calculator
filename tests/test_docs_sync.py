"""
Test to ensure business documentation stays in sync with integration tests.

This test will fail if:
- A test class/method is added without updating the business summary
- A documented test no longer exists
"""

import re
from pathlib import Path

import pytest


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def extract_test_classes_and_methods(test_file: Path) -> dict[str, list[str]]:
    """Extract test class names and their test methods from the test file."""
    content = test_file.read_text()

    classes = {}
    current_class = None

    for line in content.split('\n'):
        class_match = re.match(r'^class (Test\w+)', line)
        if class_match:
            current_class = class_match.group(1)
            classes[current_class] = []
            continue

        if current_class:
            method_match = re.match(r'^\s+def (test_\w+)', line)
            if method_match:
                classes[current_class].append(method_match.group(1))

    return classes


def extract_documented_tests(doc_file: Path) -> tuple[set[str], set[str]]:
    """Extract class names and method names referenced in the documentation."""
    content = doc_file.read_text()

    classes = set(re.findall(r'\*\*Test Class\*\*:\s*`(Test\w+)`', content))
    methods = set(re.findall(r'\*\*Test Method\*\*:\s*`(test_\w+)`', content))

    return classes, methods


class TestDocumentationSync:
    """Ensure test documentation stays in sync with actual tests."""

    @pytest.fixture
    def test_file(self) -> Path:
        return get_project_root() / 'tests' / 'test_integration_scenarios.py'

    @pytest.fixture
    def doc_file(self) -> Path:
        return get_project_root() / 'docs' / 'test_scenarios_business_summary.md'

    def test_doc_files_exist(self, test_file: Path, doc_file: Path):
        """Both files must exist."""
        assert test_file.exists(), f"Test file not found: {test_file}"
        assert doc_file.exists(), f"Documentation file not found: {doc_file}"

    def test_all_test_classes_documented(self, test_file: Path, doc_file: Path):
        """All test classes in the test file should be documented."""
        test_classes = extract_test_classes_and_methods(test_file)
        doc_classes, _ = extract_documented_tests(doc_file)

        missing = set(test_classes.keys()) - doc_classes
        assert not missing, (
            f"Test classes not documented in business summary: {missing}\n"
            f"Please update docs/test_scenarios_business_summary.md"
        )

    def test_all_test_methods_documented(self, test_file: Path, doc_file: Path):
        """All test methods in the test file should be documented."""
        test_classes = extract_test_classes_and_methods(test_file)
        _, doc_methods = extract_documented_tests(doc_file)

        all_methods = set()
        for methods in test_classes.values():
            all_methods.update(methods)

        missing = all_methods - doc_methods
        assert not missing, (
            f"Test methods not documented in business summary: {missing}\n"
            f"Please update docs/test_scenarios_business_summary.md"
        )

    def test_no_stale_class_documentation(self, test_file: Path, doc_file: Path):
        """Documented classes should exist in the test file."""
        test_classes = extract_test_classes_and_methods(test_file)
        doc_classes, _ = extract_documented_tests(doc_file)

        stale = doc_classes - set(test_classes.keys())
        assert not stale, (
            f"Documented classes no longer exist: {stale}\n"
            f"Please update docs/test_scenarios_business_summary.md"
        )

    def test_no_stale_method_documentation(self, test_file: Path, doc_file: Path):
        """Documented methods should exist in the test file."""
        test_classes = extract_test_classes_and_methods(test_file)
        _, doc_methods = extract_documented_tests(doc_file)

        all_methods = set()
        for methods in test_classes.values():
            all_methods.update(methods)

        stale = doc_methods - all_methods
        assert not stale, (
            f"Documented methods no longer exist: {stale}\n"
            f"Please update docs/test_scenarios_business_summary.md"
        )
