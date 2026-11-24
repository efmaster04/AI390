"""Build a local, self-contained Week 3 deck using Week 2's embedded design kit.

No uploads, hosting changes or network requests. The source deck is never edited.
Run with the standard library: python scripts/build_week3_presentation.py
Metrics come from real result files; incomplete work stays visibly pending.
"""
from __future__ import annotations
import base64
from copy import deepcopy
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'eval/results/week3/presentation_data.json'
OUT=ROOT/'docs/week3/index.html'


def read_json(path, default=None):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else (default or {})


def h(value):
    return escape(str(value), quote=True)


def short(value, maximum=240):
    text=str(value or '').strip()
    return text if len(text)<=maximum else text[:maximum].rsplit(' ',1)[0]+'…'


def value(item):
    return item.get('value') if isinstance(item,dict) else item


def fmt(item, digits=3):
    item=value(item)
    if item is None:return 'null'
    if isinstance(item,float):return f'{item:.{digits}f}'
    return str(item)


class AssetParser(HTMLParser):
    def __init__(self):
        super().__init__();self.divs=[];self.poses={}
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='div':self.divs.append(a)
        if tag=='img' and 'bk-mascot-pose' in a.get('class','') and self.divs:
            cls=self.divs[-1].get('class','')
            for pose in re.findall(r'bk-mascot--(\w+)',cls):
                if pose not in {'hero','aide'}:self.poses.setdefault(pose,a['src'])
    def handle_endtag(self,tag):
        if tag=='div' and self.divs:self.divs.pop()


CSS='''
/* Week 3 content uses the original 1920x1080 design kit, fonts and artwork. */
[data-composition-file] [data-hf-authored-id="root"]{position:absolute;inset:0}
.bk-title{font-size:60px!important;line-height:1.05!important}
#w3-next .w3-stack{gap:24px}#w3-next .w3-card{padding:22px 28px}#w3-next .w3-card h3{font-size:40px;margin-bottom:10px}#w3-next .w3-card p{font-size:30px;line-height:1.2}
#w3-demo-abstain .bk-term{min-height:320px!important}#w3-demo-abstain .w3-card{padding:20px 28px}#w3-demo-abstain .w3-card h3{font-size:40px;margin-bottom:8px}#w3-demo-abstain .w3-card p{font-size:28px;line-height:1.1}
.w3-content{position:absolute;left:96px;top:300px;width:1390px;height:650px}
.w3-content.w3-wide{width:1728px}
.w3-stack{display:flex;flex-direction:column;gap:34px}
.w3-row{display:flex;gap:32px;align-items:stretch}
.w3-content.w3-row{height:590px}
#w3-retrieval-metrics .w3-content.w3-row{height:620px}
.w3-row>.bk-panel{flex:1;min-width:0}
.w3-card{padding:34px 32px 26px;position:relative}
.w3-card p{font-size:36px;line-height:1.28}
.w3-card p+p{margin-top:14px}
.w3-card .bk-label{font-size:25px;margin-bottom:13px}
.w3-card h3{font-family:var(--font-display);font-weight:900;font-size:48px;line-height:1.12;margin-bottom:16px}
.w3-caption{font-size:29px;color:var(--ink-2);line-height:1.25}
.w3-caption strong{color:var(--ink)}
.w3-hero-number{font-family:var(--font-display);font-weight:900;font-size:134px;line-height:.95}
.w3-metric{font-family:var(--font-mono);font-weight:700;font-size:50px;white-space:nowrap}
.w3-evidence{font-size:34px;line-height:1.28;border-left:10px solid var(--teal);padding:16px 24px;background:var(--cream)}
.w3-footnote{position:absolute;left:96px;right:96px;bottom:104px;font-size:25px;line-height:1.25;color:var(--ink-2)}
.w3-mascot{left:1520px;top:620px;--h:300px}
.w3-chip{display:inline-block;padding:8px 16px;border:3px solid var(--ink);border-radius:10px;background:var(--cream);font-family:var(--font-mono);font-size:27px;line-height:1.25}
.w3-chip.good{background:var(--teal-soft)}.w3-chip.wait{background:var(--sun-soft)}.w3-chip.bad{background:var(--tomato-soft)}
.w3-grid{display:grid;grid-template-columns:1fr 1fr;gap:30px}
.w3-grid .bk-panel{padding:22px 26px;min-height:112px;display:flex;align-items:center;gap:20px}
.w3-id{font-family:var(--font-mono);font-size:28px;font-weight:700;white-space:nowrap}
.w3-grid .w3-deliv{font-size:30px;line-height:1.18}
.w3-grid .w3-status{display:block;font-size:23px;color:var(--ink-2);margin-top:5px}
.w3-flow{display:flex;align-items:center;gap:16px;flex-wrap:wrap}
.w3-flow .bk-panel{width:250px;min-height:150px;padding:26px 20px;text-align:center}
.w3-flow .bk-panel strong{font-size:33px;line-height:1.13;display:block}
.w3-flow .bk-panel small{font-size:23px;color:var(--ink-2);display:block;margin-top:13px}
.w3-flow .bk-arrow{width:45px;flex:none;margin:0 2px}
.w3-term{position:relative;left:0;top:0;width:1390px;height:auto;min-height:470px}
.w3-term .bk-term-body{font-size:31px;padding:24px 30px;line-height:1.3}
.w3-term .bk-term-en{font-size:29px}
.w3-term .bk-term-meta{font-size:24px}
.w3-table{border-collapse:separate;border-spacing:0;width:100%;font-family:var(--font-mono);font-size:29px;line-height:1.25}
.w3-table th,.w3-table td{text-align:left;padding:19px 19px;border-bottom:2px dashed rgba(22,19,16,.4)}
.w3-table th{font-size:25px;color:var(--ink-2);background:var(--tan)}
.w3-table tr:last-child td{border-bottom:none}.w3-table .best td{background:var(--teal-soft)}
.w3-bars{display:flex;flex-direction:column;gap:33px}
.w3-bar-label{display:flex;justify-content:space-between;font-size:32px;margin-bottom:9px}
.w3-bar-track{height:42px;border:3px solid var(--ink);background:var(--cream);border-radius:10px;overflow:hidden}
.w3-bar-fill{height:100%;background:var(--teal);transform-origin:left center}
.w3-pending{font-family:var(--font-mono);font-size:34px;color:var(--tomato-ink)}
.w3-claim{display:grid;grid-template-columns:1fr 300px;gap:20px;padding:20px 0;border-bottom:2px dashed var(--ink)}
.w3-claim:last-child{border-bottom:none}.w3-claim .w3-chip{align-self:start;text-align:center}
.w3-question-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:30px;width:1360px}
.w3-question-grid .bk-panel{height:420px;padding:36px 26px;display:flex;flex-direction:column;justify-content:space-between}
.w3-question-grid h3{font-family:var(--font-display);font-size:44px;line-height:1.12}
.w3-question-grid .w3-qnum{font-family:var(--font-display);font-size:104px}
.w3-qa{position:absolute;left:96px;top:315px;width:1400px;display:flex;flex-direction:column;gap:34px}
.w3-qa .bk-panel{padding:34px 36px;font-size:38px;line-height:1.27}
.w3-qa .bk-panel strong{color:var(--teal-ink)}
.w3-card a,.w3-footnote a{color:inherit}
#scoreboard .bk-title{font-size:58px}
#scoreboard #sb-foot{font-size:24px;line-height:1.23}
#scoreboard #sb-table .sb-row{font-size:25px}
#scoreboard #sb-table .sb-val{font-size:27px}
'''


def build():
    reference=(ROOT/'docs/index.html').read_text(encoding='utf-8')
    match=re.search(r'atob\("([A-Za-z0-9+/=]+)"\)',reference)
    if not match:raise ValueError('Week 2 composition payload not found')
    comp=base64.b64decode(match[1]).decode()
    parser=AssetParser();parser.feed(comp)
    data=read_json(DATA)
    retrieval=read_json(ROOT/'eval/results/week3/retrieval/summary.json')
    summaries=retrieval.get('summaries',{})
    base=summaries.get('hybrid_rerank',{})
    docs=read_json(ROOT/'data/corpus/manifest.json').get('documents',[])
    chunks=read_json(ROOT/'eval/results/week3/retrieval/chunks.json')
    scoreboard=read_json(ROOT/'eval/results/week3/scoreboard.json')
    scoreboard.update(data.get('scoreboard',{}))
    old=read_json(ROOT/'eval/results/week2/scoreboard.json')
    generated=data.get('generation',{})
    review=data.get('human_review',{})
    product=data.get('product',{})
    demo=data.get('demo',{})
    n_docs=len(docs);n_chunks=chunks.get('count')
    n_public_docs=sum('public' in d.get('access',[]) for d in docs)
    public_reviews=sum('public' in d.get('access',[]) and d.get('review_status')=='approved' for d in docs)
    multi_facet_count=data.get('multi_facet_count',3);cross_service_count=data.get('cross_service_count',2)
    n_answerable=base.get('n_answerable',32);n_controls=base.get('n_unanswerable_controls',6)
    reviews=sum(d.get('review_status')=='approved' for d in docs)
    if not review:review={'approved_documents':reviews,'total_documents':n_docs,'claim_labels_completed':0,'claim_labels_target':20,'kappa':None}
    def mascot(pose='isaret',style=''):
        src=parser.poses.get(pose) or next(iter(parser.poses.values()))
        return f'<div class="bk-mascot bk-mascot--aide bk-mascot--{pose} w3-mascot w3-anim" style="{style}"><img class="bk-mascot-pose" src="{src}" alt=""></div>'
    def card(title,body,cls='',step=0):
        return f'<section class="bk-panel w3-card {cls} w3-step-{step}"><span class="bk-tab">{title}</span>{body}</section>'
    def foot(text):return f'<p class="w3-footnote w3-step-2">{text}</p>'
    def term(question,answer,source=None,kind='recorded run'):
        return f'<div class="bk-term w3-term w3-step-0"><div class="bk-term-bar"><i></i><i></i><i></i><b>{h(kind)}</b></div><div class="bk-term-body"><span class="bk-term-line"><b class="bk-term-you">you&gt;</b> {h(short(question,220))}</span><span class="bk-term-line w3-step-1"><b class="bk-term-bot">beldesk&gt;</b> {h(short(answer,580))}</span>'+ (f'<span class="bk-term-meta w3-step-2">{h(source)}</span>' if source else '')+'</div></div>'
    slides=[]
    def add(sid,title,label,body,seconds,notes,repo='',pose='isaret',wide=False):
        slides.append(dict(id=sid,title=title,label=label,body=body,seconds=seconds,notes=notes,repo=repo,pose=pose,wide=wide))
    # 0:00-2:00 — what we built, with a recorded demonstration.
    cover_start=comp.index('<div class="bk-stage">',comp.index('data-composition-file="scenes/cover.html"'))
    cover_end=comp.index('  </div></div>',cover_start)
    cover=comp[cover_start:cover_end].replace('WEEK 02','WEEK 03').replace('01 / 20','01 / 18').replace('Week 2 —','Week 3 —').replace('Prompts and the evaluation harness','Retrieval-augmented generation').replace('Case file / 02','Case file / 03')
    add('cover','Beldesk — Week 3','Opening',cover,10,'EFE · 10 s. Beldesk helps residents report municipal problems and ask service questions in Turkish and English. This week we added retrieval and source-grounded answers.',pose=None)
    labels=[('W3.1','Corpus',f'{n_docs} synthetic documents; review status shown'),('W3.2','Chunking',f'{fmt(n_chunks)} section-aware chunks'),('W3.3','Hybrid search','BM25 + embeddings + RRF + reranker'),('W3.4','Cited answers','Numbered evidence and fixed fallback'),('W3.5','Retrieval set','32 answerable + 6 controls'),('W3.6','Faithfulness','Atomic claims + human calibration'),('W3.7','Two ablations','Dense / hybrid; reranker on / off'),('W3.8','Failure analysis','Retrieval versus generation')]
    deliv=data.get('deliverables',{})
    items=[]
    for i,(id_,name,default) in enumerate(labels):
        state=deliv.get(id_,{})
        note=state.get('note',default) if isinstance(state,dict) else default
        status=state.get('status','implementation / review pending') if isinstance(state,dict) else str(state)
        if id_ in {'W3.2','W3.3','W3.7'} and not state:status='implemented and measured'
        items.append(f'<section class="bk-panel w3-step-{min(i//3,2)}"><span class="w3-id">{id_}</span><span class="w3-deliv">{name}<span class="w3-status">{h(short(status+": "+note,105))}</span></span></section>')
    add('w3-roadmap','Eight deliverables, with evidence and open items','Week 3 / W3.1–W3.8',f'<div class="w3-content"><div class="w3-grid">{"".join(items)}</div></div>'+foot('Rewritten public guides need their own review. The completed historical judge check and customer interviews are preserved.'),15,'EFE · 15 s. Show all eight requirements. Distinguish current citizen-benchmark measurements from review of the rewritten guides. The team completed the historical human check and customer interviews.','reports/week-3.md','gorevli')
    body='<div class="w3-content w3-stack">'+card('Sources',f'<div class="w3-row"><div><span class="w3-hero-number">{n_docs}</span><p>documents · synthetic</p></div><div><span class="w3-hero-number">{n_chunks}</span><p>stable source chunks</p></div><div><span class="w3-metric">source / version / access</span><p>Public search filters staff evidence first.</p></div></div>',step=0)
    flow=[('BM25','word matching'),('Embeddings','semantic matching'),('RRF','combine ranks'),('Reranker','score query + passage')]
    body+='<div class="w3-flow w3-step-1">'+''.join(('<span class="bk-arrow"></span>' if i else '')+f'<section class="bk-panel"><strong>{a}</strong><small>{b}</small></section>' for i,(a,b) in enumerate(flow))+'</div>'
    body+='</div>'+foot('Section boundaries are preserved. Local retrieval models do not replace the Gemini answer model. No database or ticket-write tool.')
    add('w3-pipeline','Documents become evidence before the model answers','W3.1 / W3.2 / W3.3',body,20,'EFE · 20 s. The corpus has source, date/version and access metadata. It is divided by section. Lexical and semantic search feed RRF, then a cross-encoder reranker. Sources are evidence, never system instructions.','src/rag/ · config/retrieval.json','buyutec')
    q=demo.get('question_tr','Kiracıyım, su aboneliği için hangi belgeler gerekiyor?')
    ans=demo.get('answer','Generation result pending. This slide must be refreshed from the recorded answer run.')
    sl=demo.get('source_label','YV-D003#requirements · synthetic draft')
    excerpt=demo.get('source_excerpt','Recorded citizen-v2 source excerpt pending.')
    body='<div class="w3-content w3-stack">'+term(q,ans,sl,demo.get('run_label','recorded run / local evidence'))+f'<div class="w3-evidence w3-step-2"><span class="bk-label">Source excerpt · {h(sl)}</span><br>{h(short(excerpt,225))}</div></div>'
    add('w3-demo-answer','A service answer must point to its source','What we built / recorded demo',body,40,'EFE · 40 s. This is a recorded real run, not a live API call. Read the citizen question, show the answer and its numbered citation, then identify the source sentence that supports it. The municipality and requirements are synthetic.','eval/results/week3/','yaziyor')
    aq=demo.get('abstain_question','Yarın bizim sokaktaki boru için ekip saat kaçta gelecek?')
    aa=demo.get('abstain_answer','Generation result pending. The final recorded answer must use the fixed no-evidence response.')
    body='<div class="w3-content w3-stack">'+term(aq,aa,'No crew schedule or ticket database is available.','deterministic no-source check / no API call')+card('Boundary','<h3>A nearby passage is not an answer.</h3><p>The answer layer checks support. Retrieval scores are not probabilities that a question is answerable.</p>',step=2)+'</div>'
    add('w3-demo-abstain','Fixed fallback when no authorized source is supplied','W3.4 / software contract demonstration',body,35,'EFE · 35 s. This is a deterministic software check, not an LLM-generated reply. With an empty authorized-source list the answer module returns the exact fixed fallback without calling the model. The citizen-v2 model run records its unavailable-information controls and any service errors separately.','src/rag/answer.py · prompts/rag/','mahcup')
    # 2:00-4:00 — scoreboard, same 13 rows as Week 2.
    body='<div class="w3-content w3-stack"><div class="w3-row">'+card('Retrieval denominator',f'<span class="w3-hero-number">{n_answerable}</span><h3>answerable questions</h3><p>16 Turkish · 16 English</p>',step=0)+card('Separate controls',f'<span class="w3-hero-number">{n_controls}</span><h3>unavailable answers</h3><p>Excluded from hit@k and MRR.</p>',step=1)+'</div>'+card('Citizen questions and evidence',f'<p>{multi_facet_count} questions have multiple required facets; {cross_service_count} combine services. Registered alternative passages can support the same facet. Six development examples stay separate.</p><p class="w3-caption">The questions and evidence labels need independent review. Internal policy questions are outside this benchmark.</p>',step=2)+'</div>'
    add('w3-testset',f'{n_answerable} citizen questions + {n_controls} separate controls','Scoreboard / W3.5',body,20,f'EFE · 20 s. The citizen benchmark has {n_answerable} answerable questions in Turkish and English plus {n_controls} separate unavailable-information controls. {multi_facet_count} questions need multiple facets; {cross_service_count} cross service boundaries. Alternative evidence was registered before scoring. Internal policy questions belong in separate tests.','eval/testsets/week3_retrieval.jsonl','dusunen')
    metric_bars=[]
    hit5=base.get('hit_at_k',{}).get('5')
    hit5_count=round(hit5*n_answerable) if isinstance(hit5,(int,float)) else None
    all_facets=base.get('all_required_facets_hit_at_5',base.get('all_gold_hit_at_5'))
    all_facets_count=round(all_facets*n_answerable) if isinstance(all_facets,(int,float)) else None
    hit5_ratio=f'{hit5_count} / {n_answerable}' if hit5_count is not None else 'pending'
    facet_ratio=f'{all_facets_count} / {n_answerable}' if all_facets_count is not None else 'pending'
    for i,k in enumerate(['1','3','5','10']):
        v=base.get('hit_at_k',{}).get(k)
        metric_bars.append(f'<div class="w3-step-{min(i,2)}"><div class="w3-bar-label"><b>hit@{k}</b><span class="w3-metric">{fmt(v)}</span></div><div class="w3-bar-track"><div class="w3-bar-fill" style="width:{(v or 0)*100:.3f}%"></div></div></div>')
    body='<div class="w3-content w3-row">'+card('Hybrid + reranker','<div class="w3-bars">'+''.join(metric_bars)+'</div>',step=0)+card('Ranking and full coverage',f'<span class="w3-hero-number">{fmt(base.get("mrr_at_10"))}</span><h3>MRR@10</h3><p>All required facets @5:<br><strong>{facet_ratio}</strong></p><p class="w3-caption">Small synthetic citizen set · draft labels</p>',step=1)+'</div>'+foot('Hit@k locates relevant evidence. Full-facet coverage is separate; neither metric proves a complete, correct answer.')
    add('w3-retrieval-metrics',f'Evidence in the first five results: {hit5_ratio}','Scoreboard / W3.5',body,25,f'DORUK · 25 s. At least one registered facet appears in the first five results for {hit5_ratio} citizen questions. All required facets appear for {facet_ratio}. MRR at ten is {fmt(base.get("mrr_at_10"))}. These are retrieval measurements, not perfect-answer claims.','eval/results/week3/retrieval/summary.json','isaret')
    comparison_rows=[('hybrid_rerank','Hybrid + reranker'),('dense_rerank','Dense + reranker'),('hybrid_no_rerank','Hybrid, no reranker')]
    measured_mrr={key:summaries.get(key,{}).get('mrr_at_10') for key,_ in comparison_rows}
    measured_mrr={key:v for key,v in measured_mrr.items() if isinstance(v,(int,float))}
    best_mrr_key=max(measured_mrr,key=measured_mrr.get) if measured_mrr else None
    table='<table class="w3-table"><thead><tr><th>Configuration</th><th>hit@1</th><th>hit@5</th><th>MRR@10</th></tr></thead><tbody>'
    for key,label in comparison_rows:
        item=summaries.get(key,{})
        table+=f'<tr class="{"best" if key==best_mrr_key else ""}"><td>{label}</td><td>{fmt(item.get("hit_at_k",{}).get("1"))}</td><td>{fmt(item.get("hit_at_k",{}).get("5"))}</td><td>{fmt(item.get("mrr_at_10"))}</td></tr>'
    table+='</tbody></table>'
    hybrid_mrr=base.get('mrr_at_10');dense_mrr=summaries.get('dense_rerank',{}).get('mrr_at_10');no_rerank_mrr=summaries.get('hybrid_no_rerank',{}).get('mrr_at_10')
    if not all(isinstance(v,(int,float)) for v in (hybrid_mrr,dense_mrr)):
        hybrid_comparison='Hybrid / dense comparison pending.'
    elif abs(hybrid_mrr-dense_mrr)<1e-12:
        hybrid_comparison='Hybrid and dense have equal MRR here.'
    elif hybrid_mrr>dense_mrr:
        hybrid_comparison='Hybrid has higher MRR here.'
    else:
        hybrid_comparison='Dense has higher MRR here.'
    if not all(isinstance(v,(int,float)) for v in (hybrid_mrr,no_rerank_mrr)):
        rerank_comparison='Reranker comparison pending.'
    elif abs(hybrid_mrr-no_rerank_mrr)<1e-12:
        rerank_comparison=f'Reranker on/off MRR is equal: {fmt(hybrid_mrr)}.'
    else:
        rerank_comparison=f'MRR without reranker: {fmt(no_rerank_mrr)}; with: {fmt(hybrid_mrr)}.'
    body='<div class="w3-content w3-stack">'+card('One change per comparison',table,step=0)+card('Observed ranking quality',f'<h3>{h(hybrid_comparison)}</h3><p>{h(rerank_comparison)} Same corpus, questions and candidate budget.</p>',step=1)+'</div>'+foot('The highlight marks highest observed MRR. This small draft set does not establish universal superiority.')
    add('w3-ablations','Two ablations on the same citizen benchmark','Scoreboard / W3.7',body,25,f'DORUK · 25 s. Compare dense and hybrid with the same reranker. {hybrid_comparison} Hybrid MRR is {fmt(hybrid_mrr)} and dense MRR {fmt(dense_mrr)}. Then change only reranking: off {fmt(no_rerank_mrr)}, on {fmt(hybrid_mrr)}. The question and source version stay fixed.','eval/retrieval_week3.py','buyutec')
    sb=deepcopy(scoreboard)
    sb.setdefault('test_set_size',n_answerable+n_controls)
    sb.setdefault('hit_at_5',{'value':base.get('hit_at_k',{}).get('5')})
    sb.setdefault('mrr',{'value':base.get('mrr_at_10')})
    sb_rows=['test_set_size','e2e_accuracy','abstention_correct','unsupported_claims','hit_at_5','mrr','task_success','pass_k','injection_success','cost_per_task_usd','latency_p50_s','spend_week_usd','spend_total_usd']
    sbr=[]
    for key in sb_rows:
        current=value(sb.get(key));previous=value(old.get(key))
        now='null' if current is None else fmt(current,5 if key=='cost_per_task_usd' else 3)
        last='null' if previous is None else fmt(previous,5 if key=='cost_per_task_usd' else 3)
        klass='sb-val' if current is not None else 'sb-null'
        sbr.append(f'<div class="sb-row"><span class="sb-name">{key}</span><span class="{klass}">{h(now)}</span><span class="sb-last">{h(last)}</span><i class="sb-mk sb-mk--on" style="--k:3"></i></div>')
    measured=sum(value(sb.get(k)) is not None for k in sb_rows)
    body='<span id="sb-cap" class="bk-label">same rows · new evidence</span><section id="sb-table" class="bk-panel w3-step-0"><div class="sb-col sb-col--now" style="--k:3"></div><div class="sb-row sb-head"><span>metric</span><span>this week</span><span>last week</span>'+''.join(f'<span class="sb-wk">W{i}</span>' for i in range(1,7))+'</div>'+''.join(sbr)+'</section>'
    body+=f'<section id="sb-tally" class="bk-panel w3-step-1"><span class="bk-tab bk-tab--teal">measured</span><div class="sb-tally-n">{measured}<span class="sb-of">/ 13</span></div><span class="bk-label sb-tally-l">rows with a value</span></section><span id="sb-stamp" class="bk-stamp w3-step-2">null =<br>not measured</span>'
    body+='<p id="sb-foot" class="bk-note bk-note--plain bk-note--ink w3-step-2">W2 and W3 sets / capabilities differ: accuracy is not a like-for-like improvement claim.<br>MRR is truncated at 10. Latency excludes scheduling/backoff waits.<br>Model-judged values remain provisional with a limited human agreement check; unknown billing stays null.</p>'
    add('scoreboard','The same scoreboard; unmeasured values stay null','Scoreboard / W3',body,30,'DORUK · 30 s. Keep the thirteen-row scoreboard used in Week two. Read only measured values. Retrieval is newly measured; task success and repeated agent reliability remain for later weeks. Different test sets and system capabilities prevent a direct Week-two accuracy comparison.','eval/results/week3/scoreboard.json','dusunen')
    unsupported=generated.get('unsupported_claims',sb.get('unsupported_claims'))
    claims_total=generated.get('claims_total')
    cstatus=generated.get('summary','Claim-level answer evaluation results are pending the recorded run.')
    body='<div class="w3-content w3-stack">'+card('Claim-by-claim evaluation',f'<h3>{h(short(cstatus,120))}</h3><p>Split the answer into verifiable claims, then check each claim against its cited retrieved evidence.</p>',step=0)
    body+=card('Explicit denominator',f'<div class="w3-row"><div><span class="w3-metric">{fmt(unsupported)}</span><p>unsupported-claim rate</p></div><div><span class="w3-metric">{fmt(claims_total)}</span><p>claims evaluated</p></div></div><p class="w3-caption">Provisional model estimate. Missing claims, judge errors and abstentions are recorded separately.</p>',step=1)+'</div>'+foot('A cited number alone is not faithfulness. The source sentence must support the claim. Judge/human agreement is shown next.')
    add('w3-faithfulness','Claim-by-claim source support','Scoreboard / W3.6',body,20,'DORUK · 20 s. We evaluate claims against actual cited evidence. A citation existing does not mean it supports the claim. Unsupported claims have a clear denominator; missing extraction or judge errors cannot become successful answers.','eval/faithfulness_week3.py','gorevli')
    # 4:00-6:00 — failures and root causes.
    retrieval_case=data.get('retrieval_failure',{})
    case_label=retrieval_case.get('case_id','Current case pending')
    case_variant=retrieval_case.get('variant','hybrid_rerank')
    case_question=retrieval_case.get('question','No recorded citizen-v2 retrieval case has been supplied.')
    case_diagnosis=retrieval_case.get('diagnosis','Inspect the current result before assigning a retrieval-failure cause.')
    evidence_label=retrieval_case.get('evidence_label','Evidence review pending')
    case_note=retrieval_case.get('note','A lower-ranked or partial result is not automatically a complete retrieval miss.')
    body='<div class="w3-content w3-stack">'+card(f'{h(case_label)} · {h(case_variant)}',f'<p>“{h(short(case_question,210))}”</p>',step=0)
    body+=card('Recorded evidence coverage',f'<h3>{h(short(evidence_label,80))}</h3><p>{h(short(case_diagnosis,200))}</p><p class="w3-caption">{h(short(case_note,130))}</p>',cls='bk-panel--tomato',step=1)+'</div>'+foot('Relevant text can cover only part of a question. Keep the observed result and its frozen evidence labels.')
    add('w3-retrieval-failure','A closer look at retrieved evidence','Failure analysis / retrieval',body,25,f'DORUK · 25 s. Inspect {case_label} in {case_variant}. {case_diagnosis} {case_note} Finding one relevant passage does not establish that every requested facet is covered.','eval/results/week3/retrieval/failures.json','saskin')
    gf=data.get('failures',{}).get('generation',{})
    body='<div class="w3-content w3-stack">'+card('Recorded citizen-v2 run',f'<p>{h(short(gf.get("question","Recorded generation failure analysis is pending."),180))}</p><p class="w3-caption">{h(short(gf.get("answer","No fabricated failure example is substituted."),280))}</p>',step=0)+card('Root-cause split',f'<h3>{h(short(gf.get("diagnosis","Check whether the required evidence was retrieved."),150))}</h3><p>Evidence absent → retrieval. Evidence present but answer unsupported → generation. Judge disagreement → evaluation.</p>',step=1)+'</div>'
    add('w3-generation-failure','Service availability in the citizen run','Failure analysis / W3.8',body,15,'DORUK · 15 s. Read the citizen-v2 run’s own service record. Retired v1 source and question hashes describe a different benchmark. Separate provider errors, missing evidence and unsupported generated claims.','eval/results/week3/','mahcup')
    kappa=review.get('kappa')
    done=review.get('claim_labels_completed',0);target=review.get('claim_labels_target',20)
    body='<div class="w3-content w3-row">'+card('Historical human check',f'<span class="w3-hero-number">{h(fmt(kappa))}</span><h3>Cohen’s κ</h3><p>{done} human labels</p><p class="w3-caption">κ comparison n = {review.get("matched_human_judge_pairs",0)}<br>Observed agreement: {fmt(review.get("observed_agreement"))}</p>',step=0)+card('The historical judge check','<h3>Human labels use v1 evidence snapshots.</h3><p>The team completed the historical source-support check. Those claims and sources predate the citizen-corpus rewrite.</p><p class="w3-caption">This is not human accuracy measured on the new citizen-v2 answers.</p>',step=1)+'</div>'+foot('Only matched human–judge pairs enter κ. Historical calibration and current citizen-answer evaluation remain separate.')
    add('w3-judge-calibration','The historical judge check and its scope','Failure analysis / evaluation',body,30,'TARIK · 30 s. The team completed twenty human labels using the historical claims and their embedded v1 evidence. Read kappa with the actual matched sample. This checks the judge on that set; it does not establish human accuracy for the rewritten citizen-v2 questions.','eval/results/week3/calibration/','dusunen')
    ev=data.get('failures',{}).get('evaluation',{})
    body='<div class="w3-content w3-stack">'+card('Week 2 rule','<h3>Any phone, URL or e-mail was marked fabricated.</h3><p>That rule made sense only when no contact source was connected.</p>',step=0)+card('Week 3 rule',f'<h3>{h(ev.get("title","Ask whether the authorized source supports it."))}</h3><p>{h(short(ev.get("detail","A real source may contain a contact detail. The new judge checks evidence; it must still reject invented contacts, unperformed actions and instructions hidden in documents."),240))}</p>',cls='bk-panel--teal',step=1)+'</div>'
    add('w3-evaluation-boundaries','A separate judge for source-grounded answers','Failure analysis / evaluation',body,25,'TARIK · 25 s. We preserved Week-two evidence and introduced a separate source-aware evaluation. A contact detail is not automatically fabricated if it appears in an authorized source. A retrieved instruction still cannot override system rules or create a ticket.','prompts/judge/ · eval/faithfulness_week3.py','isaret')
    interviews=product.get('interviews_completed',0)
    body='<div class="w3-content w3-row">'+card('Citizen guide review',f'<span class="w3-hero-number">{public_reviews} / {n_public_docs}</span><h3>public guide approvals</h3><p>Earlier approvals do not carry across rewritten text.</p>',step=0)+card('Product track',f'<span class="w3-hero-number">{interviews} / 2</span><h3>customer conversations</h3><p>{h(short(product.get("summary","Real notes are still required: current workflow, willingness to pay and AI concerns."),190))}</p>',step=1)+'</div>'+foot('The team’s completed interview records remain preserved. Review of rewritten public guides is a separate task.')
    add('w3-review-status','Human reviews and customer interviews','Failure analysis / remaining gaps',body,25,f'TARIK · 25 s. The team has {interviews} completed customer interviews. Those records remain preserved. The citizen-v2 public guides have {public_reviews} of {n_public_docs} explicit approvals; rewriting the text requires a fresh source review.','reports/week-3.md · review records','gorevli')
    # 6:00-7:00 — next week's top three priorities, then questions.
    body='<div class="w3-content w3-stack">'+card('1 · Citizen evidence',f'<h3>Review the rewritten guides and evidence labels.</h3><p>Public approvals: {public_reviews} / {n_public_docs}. Check service facts and the gold evidence before claiming independent validation.</p>',step=0)+card('2 · Controlled tools','<h3>Add read-only structured lookup, then sandbox writes.</h3><p>Ticket status needs data access. Creation needs confirmation and a verified result. Move tool-result checks from unmeasured to measured.</p>',step=1)+card('3 · Measured tasks','<h3>Move task_success from null to measured.</h3><p>Record multi-step traces, limits, failures and actual cost per task.</p>',step=2)+'</div>'
    add('w3-next','Next week: reliable calls and controlled tools','Next week / 3 priorities',body,40,'TARIK · 40 s. Our priorities are to review the rewritten citizen guides and evidence labels, measure controlled tool results, and measure multi-step task success. Each priority moves a named metric; retrieval does not itself create or update tickets.','reports/week-3.md · Week 4 plan','yaziyor')
    tests=data.get('tests_passed')
    body='<div class="w3-content w3-stack">'+card('Reproduce', '<p class="bk-mono" style="font-size:28px">python -m eval.retrieval_week3<br>python -m eval.answer_week3<br>python -m pytest -q</p>',step=0)+card('Evidence ledger',f'<h3>{h(str(tests)+" tests passed" if tests is not None else "Final test count pending")}</h3><p>Corpus, model, prompt, question and code hashes travel with results. The reviewed implementation is on its working branch. Release tagging is a separate step.</p>',step=1)+'</div>'+foot('Source files and recorded outputs are preserved on week3. No release tag or deployment is claimed.')
    add('w3-reproduce','Every number should trace back to a command and files','Next week / reproducibility',body,15,'TARIK · 15 s. Commands, source versions and hashes accompany recorded outputs. The final test count comes from the actual test run. The Week-three implementation is shared on its review branch; a release tag and deployment are separate steps.','README.md · eval/results/week3/','isaret')
    body='<div class="w3-content"><div class="w3-question-grid">'+''.join(f'<section class="bk-panel w3-step-{i}"><h3>{q}</h3><div><span class="w3-qnum">0{i+1}</span><p class="bk-label">open answer →</p></div></section>' for i,q in enumerate(['What did we measure?','What failed, and why?','Why these priorities?']))+'</div></div>'
    add('w3-questions','Three questions we expect','Questions and feedback',body,5,'TARIK · 5 s. Thank you. We are ready for your questions.','Week 3 / Q&A','selam')
    assert len(slides)==18 and sum(s['seconds'] for s in slides)==420
    qa=[
      ('w3-q-measurement','What did you measure, and how sure are you?',f'<strong>Citizen retrieval:</strong> {n_answerable} answerable questions; hit@5 {hit5_ratio}, all required facets @5 {facet_ratio}, and MRR@10 {fmt(base.get("mrr_at_10"))}. The {n_controls} controls have a separate denominator.','<strong>Limits:</strong> small synthetic data and draft labels. Archived v1 results use different questions and sources. Historical judge agreement does not prove current-answer accuracy.'),
      ('w3-q-failure','What failed, and do you know why?',f'<strong>Recorded retrieval case:</strong> {h(case_label)} ({h(case_variant)}). {h(short(case_diagnosis,230))}',f'<strong>Interpretation:</strong> {h(short(case_note,170))} Provider errors and unsupported answers are separate stages; source labels stay frozen.'),
      ('w3-q-priority','Is next week’s plan the change that matters most?',f'<strong>Citizen evidence:</strong> the rewritten public guides have {public_reviews}/{n_public_docs} explicit approvals. Review source facts and gold evidence before extending the system.','<strong>Then controlled tools:</strong> actual ticket status needs a read tool; ticket creation needs confirmation, sandbox action results and measurable task traces. A document cannot replace a database.'),
      ('w3-q-corpus',f'Why {n_docs} documents and {fmt(n_chunks)} chunks?',f'<strong>Documents:</strong> {n_public_docs} public service guides and one staff-only fixture, with source/version/access metadata. Public prose addresses residents; internal policy tests stay outside this benchmark.','<strong>Chunks:</strong> sections stay separate. A 140-word cap and 20-word overlap apply only to long sections; actual chunking is recorded in the current manifest. Access filtering runs before ranking.')]
    metadata={'slides':[],'slideSequences':[]}
    scene_bodies=[];scene_ids=[];offset=0
    for index,s in enumerate(slides,1):
        sid=s['id'];scene_ids.append(sid)
        fragments=[round(offset+1.4,3),round(offset+2.5,3),round(offset+3.6,3)]
        if sid=='cover':fragments=[round(offset+1.4,3)]
        note=f'{s["notes"]}\nPlanned speaking time: {s["seconds"]} s. Starts {sum(x["seconds"] for x in slides[:index-1])//60}:{sum(x["seconds"] for x in slides[:index-1])%60:02d}.'
        meta={'sceneId':sid,'notes':note,'fragments':fragments}
        if sid=='w3-questions':
            meta['hotspots']=[{'id':f'w3-h{i}','label':q[1],'target':q[0], 'region':{'x':5+i*24.2,'y':72,'w':22.1,'h':15}} for i,q in enumerate(qa[:3])]
        metadata['slides'].append(meta)
        if sid=='cover':stage=s['body']
        else:
            stage=f'<div class="bk-stage"><div class="bk-sheet"></div><header class="bk-band"><span class="bk-folio">AIC390 / WEEK 03</span><span class="bk-section">{h(s["label"])}</span><span class="bk-no">{index:02d} / 18</span></header><div class="bk-rule"></div><h2 class="bk-title">{s["title"]}</h2>{s["body"]}<div class="bk-repo"><span class="bk-repo-k">repo</span>{h(s["repo"])}</div>{mascot(s["pose"]) if s["pose"] else ""}</div>'
        scene_bodies.append(f'<div data-composition-file="scenes/{sid}.html" id="{sid}" data-composition-id="{sid}" data-label="{index:02d} / 18 {h(s["title"])}" data-start="{offset}" data-duration="8" data-track-index="{index-1}" data-track-kind="graphics" data-width="1920" data-height="1080"><div style="width:1920px;height:1080px" data-hf-inner-root="true" data-hf-authored-id="root" data-hold="" data-width="1920" data-height="1080" data-window="8" data-fragments="1.4,2.5,3.6">{stage}</div></div>')
        offset+=8
    for i,(sid,title,p1,p2) in enumerate(qa):
        scene_ids.append(sid)
        metadata['slideSequences'].append({'id':sid,'label':title,'slides':[{'sceneId':sid,'notes':re.sub('<[^>]+>','',p1+'\n'+p2),'fragments':[offset+1.4,offset+2.5,offset+3.6]}]})
        stage=f'<div class="bk-stage"><div class="bk-sheet"></div><header class="bk-band"><span class="bk-folio">BELDESK / Q&A</span><span class="bk-section">Week 3</span><span class="bk-no">Q{i+1}</span></header><div class="bk-rule"></div><h2 class="bk-title">{h(title)}</h2><div class="w3-qa"><section class="bk-panel w3-step-0">{p1}</section><section class="bk-panel w3-step-1">{p2}</section><p class="w3-caption w3-step-2">Return to the main deck with Back / Escape.</p></div>{mascot("dusunen")}</div>'
        scene_bodies.append(f'<div data-composition-file="scenes/{sid}.html" id="{sid}" data-composition-id="{sid}" data-label="Q{i+1} {h(title)}" data-start="{offset}" data-duration="8" data-track-index="{18+i}" data-track-kind="graphics" data-width="1920" data-height="1080"><div style="width:1920px;height:1080px" data-hf-inner-root="true" data-hf-authored-id="root" data-hold="" data-width="1920" data-height="1080" data-window="8" data-fragments="1.4,2.5,3.6">{stage}</div></div>')
        offset+=8
    # Keep the original shared runtime, design CSS, embedded fonts, texture and GSAP kit.
    head=comp[:comp.index('</head>')].replace('<title>Beldesk Week 2</title>','<title>Beldesk Week 3</title>')
    head+='<style>'+CSS+'</style></head>'
    config=json.dumps(metadata,ensure_ascii=False,indent=2).replace('</','<\\/')
    anim='''window.__timelines=window.__timelines||{};const ids=IDS;for(const id of ids){BK.scene(id,(tl,root,kit)=>{kit.frame(tl,root,0);for(const e of root.querySelectorAll('.w3-step-0'))tl.fromTo(e,{opacity:0,y:20},{opacity:1,y:0,duration:.45,ease:'power3.out'},.3);for(const e of root.querySelectorAll('.w3-step-1'))tl.fromTo(e,{opacity:0,y:20},{opacity:1,y:0,duration:.45,ease:'power3.out'},1.45);for(const e of root.querySelectorAll('.w3-step-2'))tl.fromTo(e,{opacity:0,y:20},{opacity:1,y:0,duration:.45,ease:'power3.out'},2.55);const m=root.querySelector('.w3-mascot');if(m)kit.mascotIn(tl,m,.25);if(id==='cover'){kit.rise(tl,root.querySelectorAll('.cover-hero,.cover-sub,.cover-team,.cover-repo,.cover-foot,.cover-eyebrow'),.15);kit.mascotIn(tl,root.querySelector('#cover-mascot'),.2);kit.stamp(tl,root.querySelector('#cover-stamp'),.65);} });}'''.replace('IDS',json.dumps(scene_ids))
    composition=head+'<body><script type="application/hyperframes-slideshow+json">'+config+'</script>'+f'<div id="main" data-composition-id="main" data-start="0" data-duration="{offset}" data-width="1920" data-height="1080">'+''.join(scene_bodies)+'</div><script type="text/hf-after-fonts">'+anim+'</script></body></html>'
    output=reference.replace('<title>Beldesk Week 2</title>','<title>Beldesk Week 3</title>').replace('notes-storage-key="beldesk-week2"','notes-storage-key="beldesk-week3"')
    output=re.sub(r'(<script type="application/hyperframes-slideshow\+json">).*?(</script>)',lambda m:m[1]+config+m[2],output,count=1,flags=re.S)
    payload=base64.b64encode(composition.encode()).decode()
    output=re.sub(r'atob\("[A-Za-z0-9+/=]+"\)',lambda _:f'atob("{payload}")',output,count=1)
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(output,encoding='utf-8')
    # This compact authoring record makes presenter splits and timing auditable.
    source={'title':'Beldesk Week 3','total_speaking_seconds':420,'speakers':{'Efe':'1–6','Doruk':'7–12','Tarık':'13–18'},
            'slides':[{k:s[k] for k in ['id','title','label','seconds','notes','repo']} for s in slides],
            'source_data':str(DATA.relative_to(ROOT)), 'reference':'docs/index.html',
            'note':'Self-contained HTML. Rebuild from recorded evidence after data changes.'}
    (ROOT/'docs/week3/deck_manifest.json').write_text(json.dumps(source,ensure_ascii=False,indent=2)+'\n')
    print(f'Created {OUT}: {len(slides)} main slides + {len(qa)} Q&A branches; 420 spoken seconds; {len(output):,} bytes')


if __name__=='__main__':build()
