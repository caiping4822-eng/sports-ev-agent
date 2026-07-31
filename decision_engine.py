from __future__ import annotations
import json,re
from pathlib import Path
from html import escape
from recommendation_engine import build_decisions,global_forced,LABELS
ROOT=Path(__file__).parent;DATA=ROOT/'data';DOCS=ROOT/'docs'
def load(p,d):
 try:return json.loads(p.read_text(encoding='utf8'))
 except:return d
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')
def pct(x):return f'{x*100:.1f}%'
def facts(xs,empty='无'):return escape('；'.join(xs) or empty)
def method(d):
 adj=d['direction_adjustment']*100;pen=d['risk_penalty']*100
 return f"市场去水 {pct(d['market_p'][d['forced_i']])} → 基线保守 {pct(d['base_p'][d['forced_i']])} ｜ 确认事实主客调整 {adj:+.1f}pp ｜ 来源风险惩罚 -{pen:.1f}pp"
def details(d,per=False):
 i=d['forced_i'];pick=LABELS[i]
 head=(f"<p><b>本场强制娱乐：</b>{pick} @ {d['odds'][i]:.2f} ｜ <b>最终综合保守概率：</b>{pct(d['conservative_p'][i])} ｜ <b>保守EV：</b>{d['ev'][i]*100:.1f}%</p>" if per else f"<p><b>中国竞彩：</b>{pick} @ {d['odds'][i]:.2f} ｜ <b>最终综合保守概率：</b>{pct(d['conservative_p'][i])} ｜ <b>保守EV：</b>{d['ev'][i]*100:.1f}%</p>")
 return head+f"<p class='small'><b>综合机制：</b>{method(d)}</p><p><b>综合可信度：</b>{d['confidence']}分 / {d['conf_label']} ｜ <b>全局综合评分：</b>{d['global_score']*100:.1f} ｜ <b>严格EV：</b>{'候选' if d['strict'] else 'PASS'} ｜ <b>Kelly：</b>0%</p><p><b>联赛/杯赛背景：</b>{facts(d['context'],'源未返回')}</p><p><b>可验证战意依据：</b>{facts(d['motivation'],'源未返回')}</p><p><b>近期状态与赛程：</b>{facts(d['form_schedule'],'源未返回')}</p><p><b>已确认：</b>{facts(d['confirmed'])}</p><p><b>待确认：</b>{facts(d['uncertain'])}</p><p><b>主要风险：</b>{facts(d['risks'])}</p><p><b>数据缺口：</b>{facts(d['gaps'])}</p>"
def main():
 latest=load(DATA/'latest_zgzcw.json',{});bj=load(DATA/'latest_bjzs.json',{})
 decisions=build_decisions(latest.get('events',[]),bj);glob=global_forced(decisions);stricts=[d for d in decisions if d['strict']]
 if stricts:head='<h2>今日综合裁判结论：严格EV候选</h2>'+''.join("<div class='decision'><h3>"+escape(d['code'])+' '+escape(d['match'])+'</h3>'+details(d)+'</div>' for d in stricts)
 elif glob:
  i=glob['forced_i'];head=f"<h2>今日综合裁判结论</h2><p class='pick'>严格EV：无候选</p><p><b>全局强制娱乐推荐：</b>{escape(glob['code'])} {escape(glob['match'])} — {LABELS[i]} @ {glob['odds'][i]:.2f}</p><p>最终综合保守概率 {pct(glob['conservative_p'][i])} ｜ 保守EV {glob['ev'][i]*100:.1f}% ｜ 严格Kelly 0% ｜ 娱乐仓上限0.25%</p><div class='decision'><h3>{escape(glob['code'])} {escape(glob['match'])}</h3>{details(glob)}</div>"
 else:head='<h2>今日综合裁判结论</h2><p>当前无中国竞彩可售比赛或无足够数据。</p>'
 cards=''.join("<div class='decision'><h3>"+escape(d['code'])+' '+escape(d['match'])+'</h3>'+details(d,True)+'</div>' for d in decisions)
 section='<!-- DECISION_START --><div class="card decisionbox">'+head+'<h2>逐场综合裁判与强制娱乐结果</h2>'+cards+'</div><!-- DECISION_END -->'
 p=DOCS/'index.html'
 if p.exists():
  html=p.read_text(encoding='utf8');html=re.sub(r'<!-- DECISION_START -->.*?<!-- DECISION_END -->','',html,flags=re.S);html=html.replace('</header><main>','</header><main>'+section);p.write_text(html,encoding='utf8')
 dump(DATA/'decision_daily.json',{'pipeline_version':2,'decisions':decisions,'global_forced_code':glob.get('code') if glob else None})
if __name__=='__main__':main()
