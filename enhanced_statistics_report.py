from __future__ import annotations
import json
from collections import defaultdict
from pathlib import Path
from html import escape
from datetime import datetime

ROOT = Path(__file__).parent
DATA = ROOT / 'data'
DOCS = ROOT / 'docs'

def load(path, default):
    try:
        return json.loads(path.read_text(encoding='utf8'))
    except:
        return default

def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf8')

def odds_band(odds: float) -> str:
    if odds < 1.80:
        return '<1.80'
    if odds < 2.00:
        return '1.80—1.99'
    if odds < 2.50:
        return '2.00—2.49'
    if odds < 3.00:
        return '2.50—2.99'
    if odds < 4.00:
        return '3.00—3.99'
    return '4.00+'

def calculate_metrics(rows):
    if not rows:
        return 0, 0, 0.0, 0.0, 0.0
    count = len(rows)
    wins = sum(1 for r in rows if r.get('win'))
    hit_rate = wins / count
    total_profit = sum(r.get('profit', 0) for r in rows)
    roi = total_profit / count
    avg_odds = sum(r.get('odds', 0) for r in rows) / count
    return count, wins, hit_rate, roi, avg_odds

def main():
    DATA.mkdir(exist_ok=True)

    ledger = load(DATA / 'prediction_ledger.json', [])
    settlements = {s['key']: s for s in load(DATA / 'settlement_history.json', []) if isinstance(s, dict) and s.get('key')}

    # Enrich ledger with league if missing
    for rec in ledger:
        if not rec.get('league') or rec.get('league') in ['未知联赛', '-', '历史未记录']:
            rec['league'] = rec.get('league', 'K League 1')  # fallback

    real_locks = []
    historical = []

    for rec in ledger:
        forced = rec.get('forced') if isinstance(rec.get('forced'), dict) else None
        settled = settlements.get(rec.get('key'))
        settled_forced = settled.get('forced') if isinstance(settled, dict) and isinstance(settled.get('forced'), dict) else None

        if not forced or not settled_forced:
            continue

        try:
            odds = float(forced.get('odds', 0))
            profit = float(settled_forced.get('profit_units', 0))
            if odds <= 0:
                continue
        except (TypeError, ValueError):
            continue

        is_historical = bool(settled_forced.get('historical')) or forced.get('type') == 'historical_simulation'

        item = {
            'key': rec.get('key'),
            'league': rec.get('league', '未知联赛'),
            'odds': odds,
            'win': bool(settled_forced.get('win')),
            'profit': profit,
            'kickoff': rec.get('kickoff'),
            'selection': forced.get('selection'),
        }

        if is_historical:
            historical.append(item)
        else:
            real_locks.append(item)

    # === OVERALL METRICS ===
    real_count, real_wins, real_hit, real_roi, real_avg = calculate_metrics(real_locks)
    hist_count, hist_wins, hist_hit, hist_roi, hist_avg = calculate_metrics(historical)

    # === BY LEAGUE (REAL) ===
    league_groups = defaultdict(list)
    for item in real_locks:
        league_groups[item['league']].append(item)

    league_html_rows = []
    for league in sorted(league_groups.keys()):
        rows = league_groups[league]
        c, w, hr, roi, ao = calculate_metrics(rows)
        league_html_rows.append(f"<tr><td>{escape(league)}</td><td>{c}</td><td>{w}</td><td>{hr*100:.1f}%</td><td>{roi*100:.1f}%</td><td>{ao:.2f}</td></tr>")

    # === BY ODDS BAND (REAL) ===
    band_groups = defaultdict(list)
    for item in real_locks:
        band = odds_band(item['odds'])
        band_groups[band].append(item)

    band_html_rows = []
    for band in ['1.80—1.99', '2.00—2.49', '2.50—2.99', '3.00—3.99', '4.00+']:
        if band in band_groups:
            rows = band_groups[band]
            c, w, hr, roi, ao = calculate_metrics(rows)
            band_html_rows.append(f"<tr><td>{band}</td><td>{c}</td><td>{w}</td><td>{hr*100:.1f}%</td><td>{roi*100:.1f}%</td><td>{ao:.2f}</td></tr>")

    # === HISTORICAL BY LEAGUE ===
    hist_league_rows = []
    hist_league_groups = defaultdict(list)
    for item in historical:
        hist_league_groups[item['league']].append(item)
    for league in sorted(hist_league_groups.keys()):
        rows = hist_league_groups[league]
        c, w, hr, roi, ao = calculate_metrics(rows)
        hist_league_rows.append(f"<tr><td>{escape(league)}</td><td>{c}</td><td>{w}</td><td>{hr*100:.1f}%</td><td>{roi*100:.1f}%</td><td>{ao:.2f}</td></tr>")

    # Build the full statistics section
    stats_section = f"""
<!-- STATS_SECTION_START -->
## 分联赛、赔率区间与累计统计（累计口径，永不清零）

**真实锁定（仅计入赛前锁定 + 已结算）**  
{real_count} 场 ｜ 命中 {real_wins} 场 ｜ 命中率 **{real_hit*100:.1f}%** ｜ ROI **{real_roi*100:.1f}%** ｜ 平均赔率 {real_avg:.2f}

**历史回放（仅供研究，不计入真实表现）**  
{hist_count} 场 ｜ 命中 {hist_wins} 场 ｜ 命中率 {hist_hit*100:.1f}% ｜ 模拟ROI {hist_roi*100:.1f}% ｜ 平均赔率 {hist_avg:.2f}

**样本门槛说明**：30场以下仅记录；30-99场观察；100场以上才开始正式评价策略。

### 真实锁定：按联赛

| 联赛 | 场数 | 命中 | 命中率 | ROI | 平均赔率 |
|------|------|------|--------|-----|----------|
{''.join(league_html_rows) or '<tr><td colspan="6">暂无样本</td></tr>'}

### 真实锁定：按赔率区间

| 赔率区间 | 场数 | 命中 | 命中率 | ROI | 平均赔率 |
|----------|------|------|--------|-----|----------|
{''.join(band_html_rows) or '<tr><td colspan="6">暂无样本</td></tr>'}

### 历史回放：按联赛（研究用）

| 联赛 | 场数 | 命中 | 命中率 | 模拟ROI | 平均赔率 |
|------|------|------|--------|---------|----------|
{''.join(hist_league_rows) or '<tr><td colspan="6">暂无样本</td></tr>'}

**更新时间**：{datetime.now().strftime('%Y-%m-%d %H:%M')} CST  
累计统计每次运行都会从 `prediction_ledger.json` + `settlement_history.json` 完整重新计算。
<!-- STATS_SECTION_END -->
"""

    # Save raw data for debugging
    save(DATA / 'performance_stats.json', {
        'real_locks': real_locks,
        'historical': historical,
        'summary': {
            'real': {'count': real_count, 'wins': real_wins, 'hit_rate': real_hit, 'roi': real_roi},
            'historical': {'count': hist_count, 'wins': hist_wins, 'hit_rate': hist_hit, 'roi': hist_roi}
        },
        'updated_at': datetime.now().isoformat()
    })

    # Inject into the page
    page = DOCS / 'index.html'
    if page.exists():
        html = page.read_text(encoding='utf8')

        # Remove old stats section
        html = re.sub(r'<!-- STATS_SECTION_START -->.*?<!-- STATS_SECTION_END -->', '', html, flags=re.S)

        # Insert the new section (try to find a good anchor)
        if '## 分联赛、赔率区间与样本统计' in html:
            html = re.sub(r'## 分联赛、赔率区间与样本统计.*?(?=\n## |$)', stats_section, html, flags=re.S)
        else:
            # Fallback: append before </main> or at the end
            if '</main>' in html:
                html = html.replace('</main>', stats_section + '\n</main>')
            else:
                html += '\n' + stats_section

        page.write_text(html, encoding='utf8')
        print("✅ Statistics section injected into docs/index.html")

    print(f"Real locks: {real_count} | Historical: {hist_count}")
    print("Enhanced statistics report finished.")

if __name__ == '__main__':
    import re
    main()