from __future__ import annotations
import json,re
from pathlib import Path
ROOT=Path(__file__).parent;DATA=ROOT/'data';DOCS=ROOT/'docs'
def load(p,d):
 try:return json.loads(p.read_text(encoding='utf8'))
 except:return d
def main():
 p=DOCS/'index.html'
 if not p.exists():return
 d=load(DATA/'decision_daily.json',{});audit=load(DATA/'settlement_audit.json',{});gaps=[]
 for x in d.get('decisions',[]):
  for g in x.get('gaps',[]):
   if g not in gaps:gaps.append(g)
 if audit.get('unmatched'):gaps.append('锁定记录仍有 '+str(len(audit['unmatched']))+' 场未匹配赛果')
 section='<!-- QUALITY_UI_START --><div class="card quality"><h2>数据状态总览</h2><p><b>当前数据缺口：</b>'+(' ｜ '.join(gaps) if gaps else '无重大缺口')+'</p><p class="small">缺口不会被AI补造。严格EV只在外部机构、赛果匹配、伤停来源达到条件后启用。</p></div><!-- QUALITY_UI_END -->'
 html=p.read_text(encoding='utf8');html=re.sub(r'<!-- QUALITY_UI_START -->.*?<!-- QUALITY_UI_END -->','',html,flags=re.S);html=html.replace('</header><main>','</header><main>'+section)
 # Add CSS/JS once. Research and per-match decision cards collapse, while final summary remains visible.
 addon='''<!-- COMPACT_UI_START --><style>.research,.decision{border-left:3px solid #2563eb;padding:10px;margin:9px 0;background:#f8fbff}.research.compact,.decision.compact{max-height:130px;overflow:hidden}.toggle-detail{margin:4px 0;border:0;background:#e8eef7;color:#174a83;border-radius:5px;padding:5px 9px;cursor:pointer}.quality{background:#fff7ed;border-left:5px solid #f59e0b}</style><script>document.querySelectorAll('.research,.decision').forEach(function(x){if(x.dataset.compact)return;x.dataset.compact='1';x.classList.add('compact');var b=document.createElement('button');b.className='toggle-detail';b.textContent='展开详情';b.onclick=function(){var c=x.classList.toggle('compact');b.textContent=c?'展开详情':'收起详情'};x.parentNode.insertBefore(b,x.nextSibling);});</script><!-- COMPACT_UI_END -->'''
 html=re.sub(r'<!-- COMPACT_UI_START -->.*?<!-- COMPACT_UI_END -->','',html,flags=re.S);html=html.replace('</body>',addon+'</body>')
 p.write_text(html,encoding='utf8')
if __name__=='__main__':main()
