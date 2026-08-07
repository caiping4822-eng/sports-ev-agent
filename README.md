# Sports EV Agent - Daily Update & Cumulative Statistics Patch

This patch fixes the issue where finished matches are not settled and the statistics panel does not update.

## Files in this patch

- `improved_result_verifier.py`          → Better result fetching (multi-source)
- `enhanced_statistics_report.py`       → Proper cumulative stats by league + odds band
- `add_verified_result.py`              → Quick single-match manual settlement
- `force_add_today_results.py`          → Batch manual settlement
- `force_settle_today.py`               → **ONE-CLICK** force settlement for today (recommended)
- `daily-agent-updated.yml`             → Improved GitHub Actions workflow
- `HOW_TO_KEEP_STATS_UPDATED.md`        → Full instructions

## Quick Start

### 1. Apply the patch

```bash
# Unzip into your repo root
unzip ev-agent-daily-update-patch.zip
cp -r patch/* .
```

Or manually copy the files.

### 2. Replace the workflow

Replace `.github/workflows/daily-agent.yml` with `daily-agent-updated.yml`

### 3. Use the one-key script (best way)

```bash
# Automatic mode (uses API-Football if available)
python force_settle_today.py

# Manual mode (recommended when sources are blocked)
python force_settle_today.py --manual

# Only specific matches
python force_settle_today.py --codes "周六001,周六003" --manual

# After any settlement
git add data/ docs/
git commit -m "Force settle + cumulative stats"
git push
```

### 4. Run full pipeline locally (optional)

```bash
python settlement_manager.py
python enhanced_statistics_report.py
```

## What you get

- Daily automatic runs (improved)
- **Real cumulative statistics** (never resets)
- Per-league breakdown
- Per-odds-band breakdown
- Easy manual override when automatic fails

See `HOW_TO_KEEP_STATS_UPDATED.md` for full details.

---
Created for https://caiping4822-eng.github.io/sports-ev-agent/
