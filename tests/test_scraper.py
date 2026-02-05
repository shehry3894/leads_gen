#!/usr/bin/env python3
"""
Test script for scraping validation.
Automatically provides inputs to main.py for testing.
"""
import subprocess
import sys

# Test query and parameters
TEST_QUERY = "gyms in New York"
MAX_RESULTS = "3"  # Will be overridden by TRIAL mode anyway

print(f"Starting scraper test with query: {TEST_QUERY}")
print(f"Max results: {MAX_RESULTS} (TRIAL mode will limit to 3)")
print("=" * 60)

# Run main.py with automatic inputs
process = subprocess.Popen(
    [sys.executable, "main.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1
)

# Provide inputs
inputs = f"{TEST_QUERY}\n{MAX_RESULTS}\n"
stdout, _ = process.communicate(input=inputs, timeout=120)

print(stdout)
print("=" * 60)
print(f"Process exit code: {process.returncode}")
