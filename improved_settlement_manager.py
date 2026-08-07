#!/usr/bin/env python3
"""
Improved Settlement Manager - v3
Prioritizes verified_results_seed.json
Cleans "昨日复盘" and "历史锁定" sections properly
Aggressively removes old garbage from HTML
"""

from __future__ import annotations
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from html import escape

ROOT = Path(__file__).parent
DATA = ROOT / 'data'
DOCS = ROOT / 'docs'
CST = timezone(timedelta(hours=8))

def load(p, d):
    try:
        return json.loads(p.read_text(encoding='utf8'))
    except:
        return d

def dump(p, x):
    p.write_text(json.dumps(x, ensure_ascii=False, indent=2), encoding='utf8')

def parse_kickoff(s):
    try:
        return datetime.strptime(s, '%Y-%m-%d %H:%M').replace(tzinfo=CST)
    except:
        return None

def main():
    ledger = load(DATA / 'prediction_ledger.json', [])
    seeds = load(DATA / 'verified_results_seed.json', {})
    now = datetime.now(CST)

    hist = []
    for r in ledger:
        key = r.get('key')
        seed = seeds.get(key)
        if seed:
            res = {
                'score': seed.get('score', ''),
                'outcome': seed.get('outcome', ''),
                'source': 'verified_seed（手动/种子）',
                'verified': True
            }
        else:
            res = None  # we rely on seeds for now

        if res:
            rec = {
                'key': key,
                'score': res['score'],
                'outcome': res['outcome'],
                'source': res['source'],
                'verified': res['verified'],
                'forced': None
            }
            fp = r.get('forced') if isinstance(r.get('forced'), dict) else None
            if fp:
                rec['forced'] = {
                    'selection': fp.get('selection'),
                    'odds': fp.get('odds'),
                    'probability': fp.get('probability', 0),
                    'win': fp.get('selection') == res['outcome'],
                    'profit_units': (fp.get('odds', 1) - 1) if fp.get('selection') == res['outcome'] else -1
                }
            hist.append(rec)

    dump(DATA / 'settlement_history.json', hist)

    # Build rows
    yesterday_rows = []
    history_rows = []

    for r in ledger:
        s = next((x for x in hist if x['key'] == r.get('key')), None)
        fp = r.get('forced') if isinstance(r.get('forced'), dict) else None
        sel = (fp or {}).get('selection', 'PASS')

        if s:
            if s.get('forced'):
                sf = s['forced']
                settle = f"{s['score']}（{s['outcome']}）/ {'命中' if sf['win'] else '未命中'} / {sf['profit_units']:+.2f}u"
            else:
                settle = f"{s['score']}（{s['outcome']}）/ 历史补录，不计入ROI"
            source = s['source']
        else:
            ko = parse_kickoff(r.get('kickoff', ''))
            if ko and ko > now:
                settle = f"未开赛（约{(ko-now).total_seconds()/3600:.1f}小时后）"
            else:
                settle = "已结束，待身份校验赛果"
            source = "—"

        row = f"<tr><td>{escape(r.get('code',''))}</td><td>{escape(r.get('home',''))} vs {escape(r.get('away',''))}</td><td>{escape(sel)}</td><td>{escape(settle)}</td><td>{escape(source)}</td></tr>"

        code = r.get('code', '')
        if any(x in code for x in ['周五','周六','周四']):
            yesterday_rows.append(row)
        history_rows.append(row)

    # Clean sections
    yesterday = f"""
<!-- YESTERDAY_REVIEW_START -->
## 昨日复盘与累计表现

**累计：** 已结算逐场强制推荐 {len([x for x in hist if x.get('forced')])} 场

<table border="1" cellpadding="4" style="border-collapse:collapse; width:100%; font-size:13px">
<tr style="background:#e8f4ff"><th>编号</th><th>比赛</th><th>赛前锁定</th><th>赛果</th><th>来源</th></tr>
{''.join(yesterday_rows[:18])}
</table>
<!-- YESTERDAY_REVIEW_END -->
"""

    history = f"""
<!-- HISTORY_LOCK_START -->
## 历史锁定、身份校验赛果与代理CLV

**累计：** 身份校验结算 {len([x for x in hist if x.get('verified')])} 场

<table border="1" cellpadding="4" style="border-collapse:collapse; width:100%; font-size:12px">
<tr style="background:#f5f5f5"><th>编号</th><th>中国竞彩对阵</th><th>赛前选择</th><th>90分钟结算</th><th>来源</th></tr>
{''.join(history_rows)}
</table>
<!-- HISTORY_LOCK_END -->
"""

    page = DOCS / 'index.html'
    if page.exists():
        h = page.read_text(encoding='utf8')

        # Aggressive cleanup
        h = re.sub(r'<!-- YESTERDAY_REVIEW_START -->.*?<!-- YESTERDAY_REVIEW_END -->', yesterday, h, flags=re.S)
        h = re.sub(r'<!-- HISTORY_LOCK_START -->.*?<!-- HISTORY_LOCK_END -->', history, h, flags=re.S)

        # Kill the broken bottom stats
        h = re.sub(r'## 分联赛、赔率区间与累计统计.*?(?=\n## |$)', '', h, flags=re.S)
        h = re.sub(r'## 分联赛、赔率区间与样本统计.*?(?=\n## |$)', '', h, flags=re.S)

        page.write_text(h, encoding='utf8')

    print("✅ Settlement fixed. Clean tables injected. Seeds prioritized.")
    print(f"Processed {len(ledger)} matches. Seeds used: {len(seeds)}")

if __name__ == '__main__':
    main()