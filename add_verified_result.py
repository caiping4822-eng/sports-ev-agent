#!/usr/bin/env python3
"""
Easy helper to manually add verified results (bypasses blocked sources).

Usage:
  python add_verified_result.py "周五001|2026-07-31 17:00" "0:3" "客胜" --sources "sofascore,espn"

This will update verified_results_seed.json and you can commit + push.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent
DATA = ROOT / 'data'
SEED_FILE = DATA / 'verified_results_seed.json'

def load_seeds():
    if SEED_FILE.exists():
        return json.loads(SEED_FILE.read_text(encoding='utf8'))
    return {}

def save_seeds(seeds):
    DATA.mkdir(exist_ok=True)
    SEED_FILE.write_text(json.dumps(seeds, ensure_ascii=False, indent=2), encoding='utf8')

def main():
    if len(sys.argv) < 4:
        print("Usage:")
        print('  python add_verified_result.py "周五001|2026-07-31 17:00" "0:3" "客胜" [--sources "sofascore,espn"]')
        sys.exit(1)

    key = sys.argv[1]
    score = sys.argv[2]
    outcome = sys.argv[3]
    sources = ["manual"]

    if "--sources" in sys.argv:
        idx = sys.argv.index("--sources")
        if idx + 1 < len(sys.argv):
            sources = [s.strip() for s in sys.argv[idx+1].split(",")]

    seeds = load_seeds()
    seeds[key] = {
        "score": score,
        "outcome": outcome,
        "verified_sources": sources,
        "added_at": datetime.now().isoformat(),
        "note": "Manually verified"
    }

    save_seeds(seeds)
    print(f"✅ Added/updated seed for {key}")
    print(f"   {score} ({outcome}) from {sources}")
    print("Now run: python settlement_manager.py && python statistics_report.py")
    print("Then commit data/verified_results_seed.json")

if __name__ == '__main__':
    main()