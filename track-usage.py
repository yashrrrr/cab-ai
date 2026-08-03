#!/usr/bin/env python3
"""
LiteLLM API Usage Tracker
Checks current API key usage and tracks spending over time
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path

# ANSI color codes
GREEN = '\033[0;32m'
BLUE = '\033[0;34m'
YELLOW = '\033[1;33m'
RED = '\033[0;31m'
CYAN = '\033[0;36m'
NC = '\033[0m'  # No Color

HISTORY_FILE = Path.home() / '.litellm_usage_history.json'

def load_history():
    """Load usage history from file"""
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_history(history):
    """Save usage history to file"""
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"{YELLOW}Warning: Could not save history: {e}{NC}")

def get_current_usage():
    """Make API call and get current usage"""
    auth_token = os.getenv('ANTHROPIC_AUTH_TOKEN')
    base_url = os.getenv('ANTHROPIC_BASE_URL')

    if not auth_token:
        print(f"{RED}Error: ANTHROPIC_AUTH_TOKEN environment variable is not set{NC}")
        sys.exit(1)

    if not base_url:
        print(f"{RED}Error: ANTHROPIC_BASE_URL environment variable is not set{NC}")
        sys.exit(1)

    cert_file = "./RnDliteLLM_cert.pem"
    cert_args = []
    if os.path.exists(cert_file):
        cert_args = ['--cacert', cert_file]

    # Make API call
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

    max_budget = headers.get('x-litellm-key-max-budget')
    key_spend = headers.get('x-litellm-key-spend')
    last_cost = headers.get('x-litellm-response-cost-original')
    version = headers.get('x-litellm-version')

    if not max_budget or not key_spend:
        print(f"{RED}Error: Could not retrieve usage information{NC}")
        sys.exit(1)

    return {
        'max_budget': float(max_budget),
        'key_spend': float(key_spend),
        'last_cost': float(last_cost) if last_cost else 0.0,
        'version': version,
        'timestamp': datetime.now().isoformat(),
        'base_url': base_url
    }

def estimate_reset_date(history):
    """Try to estimate budget reset date from history"""
    if len(history) < 2:
        return None

    # Look for a spend decrease (indicates a reset)
    for i in range(len(history) - 1, 0, -1):
        if history[i]['key_spend'] < history[i-1]['key_spend']:
            reset_date = datetime.fromisoformat(history[i]['timestamp'])
            return reset_date

    return None

def main():
    print(f"{BLUE}=== LiteLLM API Usage Tracker ==={NC}\n")

    # Get current usage
    current = get_current_usage()

    # Load history
    history = load_history()

    # Add current to history
    history.append(current)

    # Keep only last 1000 entries
    if len(history) > 1000:
        history = history[-1000:]

    # Save updated history
    save_history(history)

    # Calculate stats
    max_budget = current['max_budget']
    key_spend = current['key_spend']
    remaining = max_budget - key_spend
    percent_used = (key_spend / max_budget) * 100 if max_budget > 0 else 0

    # Display current usage
    print(f"{GREEN}Current API Key Usage:{NC}")
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

    # Historical analysis
    if len(history) > 1:
        print(f"{CYAN}Usage History:{NC}")
        print("=" * 40)

        # Check for reset
        reset_date = estimate_reset_date(history)
        if reset_date:
            days_since_reset = (datetime.now() - reset_date).days
            print(f"{'Last Reset:':<20} {reset_date.strftime('%Y-%m-%d %H:%M')}")
            print(f"{'Days Since Reset:':<20} {days_since_reset}")
        else:
            print(f"{'Tracking Since:':<20} {datetime.fromisoformat(history[0]['timestamp']).strftime('%Y-%m-%d %H:%M')}")

        # Spending rate
        if len(history) >= 2:
            first_entry = history[0]
            time_diff = datetime.now() - datetime.fromisoformat(first_entry['timestamp'])
            days = time_diff.total_seconds() / 86400

            if days > 0:
                daily_rate = key_spend / days
                days_to_limit = remaining / daily_rate if daily_rate > 0 else float('inf')

                print(f"{'Daily Spend Rate:':<20} ${daily_rate:.4f}/day")
                if days_to_limit < float('inf'):
                    print(f"{'Days to Limit:':<20} ~{int(days_to_limit)} days")

        print("=" * 40)

    # Additional info
    print(f"\n{BLUE}Additional Info:{NC}")
    print(f"{'Last Call Cost:':<20} ${current['last_cost']:.6f}")
    print(f"{'LiteLLM Version:':<20} {current['version']}")
    print(f"{'Proxy URL:':<20} {current['base_url']}")
    print(f"{'History Entries:':<20} {len(history)} records")

    # Budget duration note
    print(f"\n{BLUE}Budget Reset Policy:{NC}")
    print("  Budget duration info is not available via API.")
    print("  Contact your admin to check: budget_duration setting")
    print("  Common values: '1d', '7d', '30d', 'monthly'")

    # Warnings
    if percent_used > 80:
        print(f"\n{RED}[!] Warning: Budget usage is above 80%{NC}")
    elif percent_used > 50:
        print(f"\n{YELLOW}[!] Notice: Budget usage is above 50%{NC}")
    else:
        print(f"\n{GREEN}[OK] Budget is healthy{NC}")

    print(f"\n{CYAN}Tip: Run this script regularly to track spending patterns{NC}")

if __name__ == '__main__':
    main()
