#!/usr/bin/env python3
"""
LiteLLM API Usage Checker
Checks current API key usage by making a minimal API call
"""

import os
import sys
import json
import subprocess

# ANSI color codes
GREEN = '\033[0;32m'
BLUE = '\033[0;34m'
YELLOW = '\033[1;33m'
RED = '\033[0;31m'
NC = '\033[0m'  # No Color

def main():
    # Check environment variables
    auth_token = os.getenv('ANTHROPIC_AUTH_TOKEN')
    base_url = os.getenv('ANTHROPIC_BASE_URL')

    if not auth_token:
        print(f"{RED}Error: ANTHROPIC_AUTH_TOKEN environment variable is not set{NC}")
        sys.exit(1)

    if not base_url:
        print(f"{RED}Error: ANTHROPIC_BASE_URL environment variable is not set{NC}")
        sys.exit(1)

    # Find certificate file
    cert_file = "./RnDliteLLM_cert.pem"
    cert_args = []
    if os.path.exists(cert_file):
        cert_args = ['--cacert', cert_file]
    else:
        print(f"{YELLOW}Warning: Certificate file not found at {cert_file}{NC}")

    print(f"{BLUE}=== LiteLLM API Usage Check ==={NC}\n")

    # Make a minimal API call
    curl_cmd = [
        'curl', '-s', '-i',
        *cert_args,
        '-H', f'Authorization: Bearer {auth_token}',
        '-H', 'Content-Type: application/json',
        '-X', 'POST',
        f'{base_url}/v1/messages',
        '-d', json.dumps({
            'model': 'claude-sonnet-4-5-ISApp',
            'max_tokens': 5,
            'messages': [{'role': 'user', 'content': 'test'}]
        })
    ]

    try:
        result = subprocess.run(curl_cmd, capture_output=True, text=True)
        response = result.stdout
    except Exception as e:
        print(f"{RED}Error making API call: {e}{NC}")
        sys.exit(1)

    # Parse headers
    headers = {}
    for line in response.split('\n'):
        if ':' in line and line.startswith('x-litellm'):
            key, value = line.split(':', 1)
            headers[key.strip().lower()] = value.strip()

    # Extract usage information
    max_budget = headers.get('x-litellm-key-max-budget')
    key_spend = headers.get('x-litellm-key-spend')
    last_cost = headers.get('x-litellm-response-cost-original')
    version = headers.get('x-litellm-version')

    if not max_budget or not key_spend:
        print(f"{RED}Error: Could not retrieve usage information{NC}")
        print("\nResponse headers:")
        for key, value in headers.items():
            print(f"  {key}: {value}")
        sys.exit(1)

    # Convert to floats
    try:
        max_budget = float(max_budget)
        key_spend = float(key_spend)
        last_cost = float(last_cost) if last_cost else 0.0
    except ValueError as e:
        print(f"{RED}Error parsing usage values: {e}{NC}")
        sys.exit(1)

    # Calculate remaining and percentage
    remaining = max_budget - key_spend
    percent_used = (key_spend / max_budget) * 100 if max_budget > 0 else 0

    # Display results
    print(f"{GREEN}API Key Usage:{NC}")
    print("=" * 40)
    print(f"{'Max Budget:':<20} {BLUE}${max_budget:.2f}{NC}")
    print(f"{'Current Spend:':<20} {YELLOW}${key_spend:.4f}{NC} ({percent_used:.2f}%)")
    print(f"{'Remaining:':<20} {GREEN}${remaining:.4f}{NC}")
    print("=" * 40)

    # Usage bar
    bar_length = 50
    filled = int((percent_used / 100) * bar_length)
    empty = bar_length - filled

    bar_color = YELLOW if percent_used < 80 else RED
    print(f"\nUsage: [{bar_color}{'=' * filled}{NC}{'-' * empty}] {percent_used:.1f}%\n")

    # Additional info
    print(f"{BLUE}Additional Info:{NC}")
    print(f"{'Last Call Cost:':<20} ${last_cost:.6f}")
    print(f"{'LiteLLM Version:':<20} {version}")
    print(f"{'Proxy URL:':<20} {base_url}")

    # Warnings
    if percent_used > 80:
        print(f"\n{RED}[!] Warning: Budget usage is above 80%{NC}")
    elif percent_used > 50:
        print(f"\n{YELLOW}[!] Notice: Budget usage is above 50%{NC}")
    else:
        print(f"\n{GREEN}[OK] Budget is healthy{NC}")

if __name__ == '__main__':
    main()
