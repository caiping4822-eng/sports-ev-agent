#!/usr/bin/env python3
"""
Quick script to force-add today's settled results when automatic sources fail.
Run this locally or in GitHub Actions after matches finish.

Examples:
  python force_add_today_results.py
"""

import json
from pathlib import Path
from datetime import datetime, timedelta

ROOT = Path(__file__).parent
DATA = ROOT / 'data'
SEED = DATA / 'verified_results_seed.json'

# === EDIT THIS SECTION EVERY DAY ===
TODAY_RESULTS = [
    # Format: (code, score, outcome, sources)
    # Example from previous day:
    # ("周五001|2026-07-31 17:00", "0:3", "客胜", ["sofascore", "fotmob"]),
    # ("周五002|2026-07-31 19:00", "4:0", "主胜", ["espn", "vg"]),
    # ("周五003|2026-07-31 07:30", "1:1", "平", ["washingtonpost"]),
    # ("周六003|2026-08-01 18:30", "1:2", "客胜", ["soccerstats"]),
    
    # === ADD YOUR RESULTS HERE ===
    # ("周六001|2026-08-01 18:30", "0:1", "客胜", ["livescore"]),
    # ("周六002|2026-08-01 18:30", "1:1", "平", ["sofascore"]),
]

def load_seeds():
    if SEED.exists():
        return json.loads(SEED.read_text(encoding='utf8'))
    return {}

def save_seeds(seeds):
    DATA.mkdir(exist_ok=True)
    SEED.write_text(json.dumps(seeds, ensure_ascii=False, indent=2), encoding='utf8')

def main():
    if not TODAY_RESULTS:
        print("No results in TODAY_RESULTS. Edit the script first.")
        return

    seeds = load_seeds()
    added = 0

    for code, score, outcome, sources in TODAY_RESULTS:
        key = code  # you can make it more robust
        seeds[key] = {
            "score": score,
            "outcome": outcome,
            "verified_sources": sources,
            "added_at": datetime.now().isoformat(),
            "note": "Manually forced"
        }
        added += 1
        print(f"Added: {code} → {score} ({outcome})")

    save_seeds(seeds)
    print(f"\n✅ {added} results added to verified_results_seed.json")
    print("Next steps:")
    print("  1. python settlement_manager.py")
    print("  2. python statistics_report.py   (or the enhanced version)")
    print("  3. git add data/ docs/ && git commit -m 'Force settle results' && git push")

if __name__ == "__main__":
    main()