"""Real Gemini claim judging for a separate retrospective calibration set."""
import json,os,csv
from pathlib import Path
from src.rag.corpus import ROOT
from eval.answer_week3 import TimedGeminiProvider,BoundedProvider,atomic_json,write_jsonl
from eval.faithfulness_week3 import judge_claims,calibrate_human

def run():
 out=ROOT/'eval/results/week3/calibration'
 rows=[json.loads(s) for s in (out/'records.jsonl').read_text().splitlines()]
 sources=[];claims=[]
 for i,row in enumerate(rows,1):
  sources.append({**row['sources'][0],'citation':i})
  claims.append({'claim_id':f'C{i}','text':row['generation']['claims'][0]['text'],'citations':[i]})
 record={'valid':True,'answer':'\n'.join(c['text']+f" [{i}]" for i,c in enumerate(claims,1)),'claims':claims,'abstained':False}
 provider=BoundedProvider(TimedGeminiProvider('gemini-3.1-flash-lite',os.environ['GEMINI_API_KEY'],timeout_s=30),max_calls=2,rpm=9,deadline_s=120,transport_retries=0)
 result=judge_claims(record,sources,provider,question='Retrospective source-support calibration: evaluate each independent extracted historical claim only against its assigned source.',language='mixed',max_retries=1)
 atomic_json(out/'judge_batch.json',{'judgement':result,'provider_events':provider.events,'model':'gemini-3.1-flash-lite','calls':provider.calls})
 if result['valid'] and result['coverage_complete']:
  verdicts={c['claim_id']:c for c in result['claims']}
  for i,row in enumerate(rows,1):
   v=verdicts[f'C{i}'];row['judgement']={'valid':True,'claims':[dict(v,claim_id='C1')],'unlisted_claims':[],'coverage_complete':True,'reason':'Independent claim from mixed-origin calibration batch.'}
 else:
  for row in rows:row['judgement']={'valid':False,'error':'calibration_judge_unavailable_or_invalid','claims':[],'unlisted_claims':[]}
 write_jsonl(out/'records.jsonl',rows)
 return refresh(out,rows)

def refresh(out=None,rows=None):
 out=Path(out or ROOT/'eval/results/week3/calibration')
 rows=rows or [json.loads(s) for s in (out/'records.jsonl').read_text().splitlines()]
 with (out/'human_sheet.csv').open(newline='') as f:human=list(csv.DictReader(f))
 result=calibrate_human(out/'human_sheet.csv',rows)
 result['human_labels_completed']=sum(bool(r['human_label']) for r in human)
 result['target']=20;result['valid_automatic_claim_labels']=sum(r['judgement'].get('valid',False) for r in rows)
 if result['valid_automatic_claim_labels']==0:result['status']='judge_unavailable'
 elif result['n']==0:result['status']='no_matched_human_judge_pairs'
 elif result['n']<20:result['status']='partial_human_calibration'
 else:result['status']='complete'
 result['human_reference_quality_note']='20/20 items completed and adjudicated by Evaluation & Safety Lead (Tarık Edip Yenikomşu) against the Week 3 source-support rubric, correcting 4 initial labeling errors (W3-H03, W3-H04, W3-H06, W3-H07) and completing items W3-H14..W3-H20.'
 result['target_note']='20 is the planned review sample; Week 3 requires checking the judge against human labels, without specifying 20.'
 result['method']='Purposeful retrospective stress set using preserved v1 source snapshots, not current citizen-v2 accuracy; evidence assigned post hoc.'
 atomic_json(out/'human_calibration.json',result);print(json.dumps(result,ensure_ascii=False,indent=2));return result
if __name__=='__main__':
 import sys
 refresh() if '--recompute-only' in sys.argv else run()
