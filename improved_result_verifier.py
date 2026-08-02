from __future__ import annotations
import json, re, os
from html import unescape
from pathlib import Path
from urllib.request import Request, urlopen
from datetime import datetime, timedelta, timezone
import time

ROOT = Path(__file__).parent
DATA = ROOT / 'data'
RESULT_URL = 'https://cp.zgzcw.com/dc/getKaijiangFootBall.action'

# Extended team map (add more as needed)
TEAM_MAP = {
    # Existing + more
    "瓦勒伦加": ["Vålerenga", "Valerenga", "Valerenga IF"],
    "汉坎": ["HamKam", "Hamarkameratene"],
    "博德闪耀": ["Bodø/Glimt", "Bodo/Glimt", "Bodo Glimt"],
    "利勒斯特": ["Lillestrøm", "Lillestrom"],
    "纽约城": ["New York City FC", "NYCFC"],
    "多伦多": ["Toronto FC"],
    "江原FC": ["Gangwon FC", "Gangwon"],
    "富川FC": ["Bucheon FC", "Bucheon FC 1995"],
    "全北现代": ["Jeonbuk Hyundai Motors", "Jeonbuk", "Jeonbuk Hyundai"],
    "首尔FC": ["FC Seoul", "Seoul"],
    "浦项制铁": ["Pohang Steelers", "Pohang"],
    "金泉尚武": ["Gimcheon Sangmu", "Sangmu"],
    # Add more leagues as they appear
}

def load(p, d):
    try:
        return json.loads(p.read_text(encoding='utf8'))
    except:
        return d

def save(p, x):
    p.write_text(json.dumps(x, ensure_ascii=False, indent=2), encoding='utf8')

def clean(x):
    return re.sub(r'\s+', ' ', unescape(re.sub(r'<[^>]+>', ' ', x))).strip()

def norm(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())

def same(cn, got):
    if not cn or not got:
        return False
    cn_n = norm(cn)
    got_n = norm(got)
    if cn_n == got_n or cn_n in got_n or got_n in cn_n:
        return True
    for alias in TEAM_MAP.get(cn, []):
        if norm(alias) in got_n or got_n in norm(alias):
            return True
    return False

def china_result_rows():
    """Try China lottery site (often blocked)"""
    try:
        req = Request(RESULT_URL, headers={'User-Agent': 'Mozilla/5.0 (compatible; SportsEVResearch/1.0)'})
        with urlopen(req, timeout=15) as r:
            raw = r.read().decode('utf8', 'replace')
        out = []
        # Improved regex
        for row in re.findall(r'<tr[^>]*>.*?</tr>', raw, re.I | re.S):
            c = [clean(x) for x in re.findall(r'<td[^>]*>(.*?)</td>', row, re.I | re.S)]
            if len(c) < 6:
                continue
            code_match = re.match(r'周[一二三四五六日]\d{3}', c[0])
            if not code_match:
                continue
            score = None
            for x in c:
                m = re.search(r'(\d+)\s*:\s*(\d+)', x)
                if m:
                    score = m
                    break
            if score:
                out.append({
                    'code': c[0],
                    'home': c[3] if len(c) > 3 else '',
                    'away': c[5] if len(c) > 5 else '',
                    'score': f"{score.group(1)}:{score.group(2)}",
                    'hg': int(score.group(1)),
                    'ag': int(score.group(2))
                })
        return out
    except Exception as e:
        print(f"[china_result_rows] blocked or error: {e}")
        return []

def fetch_api_football_result(fixture_id: int):
    """Primary reliable source"""
    key = os.getenv('API_FOOTBALL_KEY', '').strip()
    if not key or not fixture_id:
        return None
    try:
        url = f"https://v3.football.api-sports.io/fixtures?id={fixture_id}"
        req = Request(url, headers={'x-apisports-key': key})
        with urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode())
        if data.get('response'):
            f = data['response'][0]
            score = f.get('score', {}).get('fulltime', {})
            hg = score.get('home')
            ag = score.get('away')
            if hg is not None and ag is not None:
                return {'hg': hg, 'ag': ag, 'score': f'{hg}:{ag}'}
    except Exception as e:
        print(f"[API-Football] error for {fixture_id}: {e}")
    return None

def fetch_livescore_fallback(home, away, date_str):
    """Lightweight fallback using public scores (example - can be expanded)"""
    # In real use, you could call a free score API here
    # For now we return None to rely on seeds + API-Football
    return None

def result_for(record: dict):
    """Main entry point - tries multiple sources in priority order"""
    key = record.get('key')
    if not key:
        return None

    # 1. Manual verified seed (highest priority)
    seeds = load(DATA / 'verified_results_seed.json', {})
    seed = seeds.get(key)
    if seed and seed.get('score'):
        return {
            'score': seed['score'],
            'outcome': seed.get('outcome', _outcome_from_score(seed['score'])),
            'source': 'verified_seed',
            'verified': len(seed.get('verified_sources', [])) >= 2,
            'sources': seed.get('verified_sources', ['manual'])
        }

    # 2. API-Football (if fixture_id exists)
    api = None
    if record.get('fixture_id'):
        api = fetch_api_football_result(record['fixture_id'])

    # 3. China lottery (often blocked, but try)
    china = None
    china_rows = china_result_rows()
    for x in china_rows:
        if x['code'] == record.get('code') and same(record.get('home'), x['home']) and same(record.get('away'), x['away']):
            china = x
            break

    # Prefer double-verified
    if api and china and api['score'] == china['score']:
        hg, ag = api['hg'], api['ag']
        out = '主胜' if hg > ag else '客胜' if ag > hg else '平'
        return {'score': api['score'], 'outcome': out, 'source': 'api+zgzcw', 'verified': True, 'sources': ['api_football', 'zgzcw']}

    if api:
        hg, ag = api['hg'], api['ag']
        out = '主胜' if hg > ag else '客胜' if ag > hg else '平'
        return {'score': api['score'], 'outcome': out, 'source': 'api_single', 'verified': False, 'sources': ['api_football']}

    # 4. Last resort: try to match with existing verified seeds by approximate time
    return None

def _outcome_from_score(score_str):
    try:
        hg, ag = map(int, score_str.split(':'))
        return '主胜' if hg > ag else '客胜' if ag > hg else '平'
    except:
        return '平'

def bulk_settle(ledger):
    """Helper: settle all finished matches"""
    results = {}
    for rec in ledger:
        res = result_for(rec)
        if res:
            results[rec['key']] = res
    return results

if __name__ == '__main__':
    print("Testing improved result verifier...")
    # You can run this standalone to debug
    ledger = load(DATA / 'prediction_ledger.json', [])
    for r in ledger[-5:]:
        res = result_for(r)
        print(r.get('code'), r.get('home'), 'vs', r.get('away'), '->', res)