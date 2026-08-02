#!/usr/bin/env python3
"""
一键强制结算今天（及昨天）所有已结束比赛 + 更新累计统计

用法示例：
  # 自动模式（优先用 API-Football + 已有的种子）
  python force_settle_today.py

  # 手动输入比分模式（推荐当自动失败时使用）
  python force_settle_today.py --manual

  # 只结算特定编号
  python force_settle_today.py --codes "周六001,周六003"

  # 强制重新结算并更新统计
  python force_settle_today.py --force

运行后会自动：
1. 更新 verified_results_seed.json
2. 运行 settlement_manager.py
3. 运行 enhanced_statistics_report.py
4. 打印本次更新摘要

然后你可以直接 git commit & push
"""

import json
import sys
import os
import argparse
from pathlib import Path
from datetime import datetime, timedelta, timezone
import subprocess

ROOT = Path(__file__).parent
DATA = ROOT / 'data'
SEED_FILE = DATA / 'verified_results_seed.json'
LEDGER_FILE = DATA / 'prediction_ledger.json'

CST = timezone(timedelta(hours=8))

def load_json(p, default):
    try:
        return json.loads(p.read_text(encoding='utf8'))
    except:
        return default

def save_json(p, data):
    DATA.mkdir(exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf8')

def get_today_range():
    now = datetime.now(CST)
    today = now.date()
    yesterday = today - timedelta(days=1)
    return today, yesterday

def is_match_finished(kickoff_str: str) -> bool:
    try:
        ko = datetime.strptime(kickoff_str, "%Y-%m-%d %H:%M").replace(tzinfo=CST)
        return ko < datetime.now(CST)
    except:
        return False

def outcome_from_score(hg: int, ag: int) -> str:
    if hg > ag:
        return "主胜"
    elif ag > hg:
        return "客胜"
    else:
        return "平"

def main():
    parser = argparse.ArgumentParser(description="一键强制结算今天比赛")
    parser.add_argument("--manual", action="store_true", help="手动输入比分模式")
    parser.add_argument("--codes", type=str, default="", help="只处理指定编号，逗号分隔")
    parser.add_argument("--force", action="store_true", help="强制重新结算已有的")
    parser.add_argument("--dry-run", action="store_true", help="只显示不写入")
    args = parser.parse_args()

    today, yesterday = get_today_range()
    print(f"当前日期 (CST): {today}")
    print(f"将尝试结算 {yesterday} 和 {today} 的比赛\n")

    ledger = load_json(LEDGER_FILE, [])
    seeds = load_json(SEED_FILE, {})

    # 筛选今天/昨天的已结束比赛
    target_matches = []
    for rec in ledger:
        try:
            ko_date = datetime.strptime(rec['kickoff'], "%Y-%m-%d %H:%M").date()
        except:
            continue

        if ko_date not in (today, yesterday):
            continue
        if not args.force and rec.get('key') in seeds:
            continue  # 已有种子跳过，除非 --force
        if not is_match_finished(rec['kickoff']):
            continue

        target_matches.append(rec)

    if args.codes:
        codes = [c.strip() for c in args.codes.split(",")]
        target_matches = [m for m in target_matches if m.get('code') in codes]

    if not target_matches:
        print("没有找到需要结算的今天/昨天比赛。")
        return

    print(f"找到 {len(target_matches)} 场需要处理的比赛：")
    for m in target_matches:
        print(f"  {m.get('code')}  {m.get('home')} vs {m.get('away')}  {m.get('kickoff')}")

    updated = 0

    if args.manual:
        print("\n=== 手动输入模式 ===")
        print("请输入比分，格式：主:客 （例如 2:1）\n")

        for rec in target_matches:
            key = rec.get('key')
            code = rec.get('code')
            home = rec.get('home')
            away = rec.get('away')

            while True:
                score_input = input(f"{code} {home} vs {away} 比分 (主:客) 或回车跳过: ").strip()
                if not score_input:
                    break
                if ":" in score_input:
                    try:
                        hg, ag = map(int, score_input.split(":"))
                        outcome = outcome_from_score(hg, ag)
                        seeds[key] = {
                            "score": f"{hg}:{ag}",
                            "outcome": outcome,
                            "verified_sources": ["manual-force"],
                            "added_at": datetime.now().isoformat(),
                            "note": "force_settle_today.py manual"
                        }
                        updated += 1
                        print(f"  ✓ 已记录 {hg}:{ag} ({outcome})")
                        break
                    except:
                        print("  格式错误，请重新输入")
                else:
                    print("  格式错误，请用 主:客 格式")
    else:
        # 自动模式：优先用 API-Football
        print("\n=== 自动模式（尝试 API-Football） ===")
        from improved_result_verifier import result_for   # 依赖我们改进的脚本

        for rec in target_matches:
            res = result_for(rec)
            if res and res.get('score'):
                key = rec.get('key')
                seeds[key] = {
                    "score": res['score'],
                    "outcome": res['outcome'],
                    "verified_sources": res.get('sources', ["auto"]),
                    "added_at": datetime.now().isoformat(),
                    "note": "force_settle_today.py auto"
                }
                updated += 1
                print(f"  ✓ {rec.get('code')} → {res['score']} ({res['outcome']}) [{res.get('source')}]")
            else:
                print(f"  ✗ {rec.get('code')} 自动获取失败（可改用 --manual）")

    if updated == 0:
        print("\n没有更新任何记录。")
        return

    if args.dry_run:
        print(f"\n[DRY RUN] 将更新 {updated} 条记录")
        return

    save_json(SEED_FILE, seeds)
    print(f"\n✅ 已更新 {updated} 条 verified seed")

    # 运行结算和统计
    print("\n正在运行 settlement_manager.py ...")
    subprocess.run([sys.executable, "settlement_manager.py"], check=False)

    print("正在运行 enhanced_statistics_report.py ...")
    subprocess.run([sys.executable, "enhanced_statistics_report.py"], check=False)

    print("\n" + "="*60)
    print("✅ 一键强制结算完成！")
    print("下一步：")
    print("  git add data/ docs/")
    print("  git commit -m \"Force settle today's matches + cumulative stats\"")
    print("  git push")
    print("="*60)

if __name__ == "__main__":
    main()