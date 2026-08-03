# LiteLLM API Usage Scripts

Two scripts to monitor your LiteLLM API key budget and spending.

## Scripts Overview

### 1. **check-usage.py** - Quick Usage Check
Simple script for a quick snapshot of your current API usage.

**Run:**
```bash
python check-usage.py
# or on Windows:
check-usage.bat
```

**Shows:**
- Current spend vs max budget
- Remaining budget
- Percentage used
- Last call cost
- LiteLLM version

**Best for:** Quick checks when you just want to know your current balance.

---

### 2. **track-usage.py** - Usage Tracker with History
Enhanced script that tracks usage over time and estimates spending patterns.

**Run:**
```bash
python track-usage.py
# or on Windows:
track-usage.bat
```

**Shows:**
- Everything from check-usage.py, PLUS:
- Last budget reset date (estimated from history)
- Days since last reset
- Daily spending rate
- Estimated days until budget limit
- Number of tracked records

**History Storage:**
- Saves to `~/.litellm_usage_history.json`
- Keeps last 1000 entries
- Automatically detects budget resets (when spend decreases)

**Best for:** 
- Regular monitoring to understand spending patterns
- Estimating when your budget will reset
- Tracking spending trends over time

---

## How It Works

Both scripts work by:
1. Making a minimal API call to LiteLLM (costs ~$0.0001)
2. Reading usage info from response headers:
   - `x-litellm-key-max-budget`: Your total budget limit
   - `x-litellm-key-spend`: Your current spending

---

## Budget Reset Information

**Important:** Budget reset date/duration is NOT available via API headers because your virtual API key only has access to LLM API routes, not admin/info endpoints.

### To Find Your Budget Duration:

1. **Contact your LiteLLM admin** and ask for:
   - Budget duration setting for your key
   - Common values: `'1d'`, `'7d'`, `'30d'`, `'monthly'`

2. **Use track-usage.py regularly** to:
   - Detect resets automatically (spend drops to near-zero)
   - Estimate reset schedule from pattern

### Typical Reset Schedules:
- **Daily (`1d`)**: Resets every 24 hours
- **Weekly (`7d`)**: Resets every 7 days
- **Monthly (`30d` or `monthly`)**: Resets on same day each month

---

## Current Status

**Max Budget:** $100.00  
**Proxy URL:** https://llmproxy.ustrnd.com  
**LiteLLM Version:** 1.83.9

---

## Requirements

- Python 3.6+
- `curl` command available
- Environment variables set:
  - `ANTHROPIC_AUTH_TOKEN`: Your LiteLLM API key
  - `ANTHROPIC_BASE_URL`: https://llmproxy.ustrnd.com
- Certificate file: `./RnDliteLLM_cert.pem` (optional, but recommended)

---

## Usage Recommendations

### For Quick Checks:
```bash
python check-usage.py
```

### For Daily Monitoring:
```bash
# Run once per day
python track-usage.py

# Or set up a scheduled task (Windows Task Scheduler / cron)
```

### To View Spending History:
The history is stored in JSON format at `~/.litellm_usage_history.json`

```bash
# View raw history
cat ~/.litellm_usage_history.json

# Or on Windows
type %USERPROFILE%\.litellm_usage_history.json
```

---

## Troubleshooting

### "ANTHROPIC_AUTH_TOKEN not set"
Make sure you've exported the environment variable:
```bash
export ANTHROPIC_AUTH_TOKEN="your-key-here"
```

### Certificate errors
If you get SSL/TLS errors, make sure `RnDliteLLM_cert.pem` is in the current directory.

### No history shown
Run `track-usage.py` multiple times over several days to build history.

---

## Cost Note

Each check costs approximately **$0.0001** (one-hundredth of a cent) since it makes a minimal 5-token API call for testing purposes.
