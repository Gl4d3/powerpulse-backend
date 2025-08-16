#!/usr/bin/env python3
"""
Test runner script for PowerPulse Analytics.
"""
import subprocess
import sys
import os
from pathlib import Path


def run_tests(test_type: str = "all", coverage: bool = True, verbose: bool = True):
    """Run tests with specified options."""
    
    # Change to the project directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    
    # Build pytest command
    cmd = ["python", "-m", "pytest"]
    
    if test_type == "unit":
        cmd.extend(["tests/unit/"])
    elif test_type == "integration":
        cmd.extend(["tests/integration/"])
    elif test_type == "all":
        cmd.extend(["tests/"])
    else:
        print(f"Unknown test type: {test_type}")
        return False
    
    if coverage:
        cmd.extend(["--cov=.", "--cov-report=term-missing"])
    
    if verbose:
        cmd.extend(["-v"])
    
    # Add additional options
    cmd.extend([
        "--tb=short",
        "--disable-warnings"
    ])
    
    print(f"Running tests: {' '.join(cmd)}")
    print("=" * 50)
    
    try:
        result = subprocess.run(cmd, check=True)
        print("=" * 50)
        print("✅ All tests passed!")
        return True
    except subprocess.CalledProcessError as e:
        print("=" * 50)
        print(f"❌ Tests failed with exit code: {e.returncode}")
        return False
    except FileNotFoundError:
        print("❌ pytest not found. Please install test dependencies:")
        print("   pip install -r requirements-test.txt")
        return False


def install_test_deps():
    """Install test dependencies."""
    print("Installing test dependencies...")
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements-test.txt"
        ], check=True)
        print("✅ Test dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install test dependencies")
        return False


def main():
    """Main test runner function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run PowerPulse Analytics tests")
    parser.add_argument(
        "--type", 
        choices=["all", "unit", "integration"], 
        default="all",
        help="Type of tests to run (default: all)"
    )
    parser.add_argument(
        "--no-coverage", 
        action="store_true",
        help="Disable coverage reporting"
    )
    parser.add_argument(
        "--quiet", 
        action="store_true",
        help="Reduce verbosity"
    )
    parser.add_argument(
        "--install-deps", 
        action="store_true",
        help="Install test dependencies before running tests"
    )
    
    args = parser.parse_args()
    
    if args.install_deps:
        if not install_test_deps():
            sys.exit(1)
    
    success = run_tests(
        test_type=args.type,
        coverage=not args.no_coverage,
        verbose=not args.quiet
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
