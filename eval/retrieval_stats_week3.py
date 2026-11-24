"""Paired hit tests and Wilson intervals from the saved retrieval records; no model calls."""
import json
from pathlib import Path
from src.rag.corpus import ROOT
from eval.stats import mcnemar,wilson_ci

def run():
 p=ROOT/'eval/results/week3/retrieval'; variants={}
 for name in ['hybrid_rerank','dense_rerank','hybrid_no_rerank']:
  rows=[json.loads(x) for x in (p/f'{name}.jsonl').read_text().splitlines()]
  variants[name]={r['case_id']:r for r in rows if r['answerable']}
 ids=sorted(variants['hybrid_rerank']);assert all(sorted(v)==ids for v in variants.values())
 tests={}
 for other in ['dense_rerank','hybrid_no_rerank']:
  for k in ['1','5']:
   tests[f'hybrid_rerank_vs_{other}_hit{k}']=mcnemar([variants['hybrid_rerank'][i]['metrics']['hit'][k] for i in ids],[variants[other][i]['metrics']['hit'][k] for i in ids])
 intervals={name:{k:wilson_ci(sum(row['metrics']['hit'][k] for row in rows.values()),len(rows)) for k in ['1','3','5','10']} for name,rows in variants.items()}
 result={'n':len(ids),'paired_tests':tests,'wilson_95':intervals,'note':'Exploratory paired tests on one small AI-authored draft set; not independent evidence of real-world performance.'}
 (p/'paired_statistics.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return result
if __name__=='__main__':run()
