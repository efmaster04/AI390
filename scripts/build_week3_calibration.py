"""Build BLANK human review from genuine historical outputs, never fake human labels.
Claims are AI-assisted atomic extractions, with exact original spans preserved.
Evidence is assigned post hoc from the Week3 corpus; it is NOT an original model citation.
This mixed-origin stress set is separate from current RAG answer-quality metrics.
"""
import csv,json,subprocess,tempfile
from pathlib import Path
from src.rag.corpus import ROOT,load_corpus,digest
from eval.faithfulness_week3 import HUMAN_FIELDS
SELECTIONS=[
('v1','W2-002','your identity card','A water subscription application requires an identity document.','YV-D003#requirements'),
('v1','W2-002','the property deed (tapu) or a valid rental agreement','A property deed or rental agreement is required for a water subscription.','YV-D003#requirements'),
('v1','W2-002','the DASK (compulsory earthquake insurance) policy for the residence','A DASK policy is required for a water subscription.','YV-D003#requirements'),
('v1','W2-002','water services are managed by the regional water authority (ASKİ)','ASKİ manages water services in Yeşilvadi.','YV-D029#details'),
('v1','W2-004','visit our Veterinary Affairs Directorate','Pet registration guidance is available from Veterinary Affairs.','YV-D005#details'),
('v1','W2-004','There is no municipal fee for the registration itself','Municipal pet registration has no fee.','YV-D005#limits'),
('v1','W2-004',"the animal's health booklet",'Pet registration requires the animal’s health booklet.','YV-D005#details'),
('v1','W2-008','garbage collection is performed daily between 20:00 and 23:00','Garbage is collected daily in Çamlık between 20:00 and 23:00.','YV-D011#schedule'),
('v1','W2-009','hafta sonları 09:00 - 18:00 saatleri arasında','Atatürk Kültür Merkezi hafta sonları 09.00–18.00 saatlerinde açıktır.','YV-D018#limits'),
('v1','W2-022','numaralı talebin durumunu kontrol ettim','Asistan komşunun kaydını sistemde kontrol etti.','YV-D028#limits'),
('v1','W2-007','SMS yoluyla bilgilendirme yapılacaktır','Kayıt tamamlandığında vatandaş SMS ile bilgilendirilecektir.','YV-D028#limits'),
('v1','W2-030','(09:00-17:00 arası) adresinize uğrayacaktır','Ekipler yarın 09.00–17.00 arasında adrese uğrayacaktır.','YV-D030#details'),
('v1','W2-001',"sağlık raporu ve 4'er adet vesikalık fotoğraf",'Nikâh başvurusunda sağlık raporu ve kişi başı dört fotoğraf gerekir.','YV-D001#limits'),
('v1','W2-006','at least 30 days prior to the event','An event permit application must be submitted at least 30 days beforehand.','YV-D006#details'),
('v1','W2-006','the event date, location, expected attendance','Event guidance requires the planned date, location and expected attendance.','YV-D006#details'),
('v3','W2-004','I am unable to process applications or payments.','Beldesk cannot submit applications or process payments.','YV-D029#limits'),
('v3','W2-017','I cannot provide legal advice','Beldesk cannot provide legal advice.','YV-D029#limits'),
('v3','W2-032','I cannot open or track tickets','Beldesk cannot open or look up tickets in this version.','YV-D028#limits'),
('v3','W2-020','YV-YYYY-NNNNNN','Projedeki kayıt referansı biçimi YV-YYYY-NNNNNN şeklindedir.','YV-D028#details'),
('v3','W2-019','I am here to help with municipal services and field problems.','Beldesk helps with municipal service information and field problem reports.','YV-D029#details')]

SOURCE_REF='be14fc0dbfb402b144eba5b6c5e055c1bd66758c'

def historical_documents(ref=SOURCE_REF):
 paths=subprocess.check_output(['git','ls-tree','-r','--name-only',ref,'--','data/corpus/documents'],cwd=ROOT,text=True).splitlines()
 with tempfile.TemporaryDirectory(prefix='beldesk-v1-source-') as tmp:
  for name in paths:
   if name.endswith('.md'):
    Path(tmp,Path(name).name).write_bytes(subprocess.check_output(['git','show',ref+':'+name],cwd=ROOT))
  return load_corpus(tmp)

def build(out=ROOT/'eval/results/week3/calibration'):
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 if (out/'human_sheet.csv').exists():raise ValueError('Existing human sheet preserved; do not overwrite real annotations')
 docs=historical_documents();sources={p.passage_id:(d,p) for d in docs for p in d.passages}
 cases={c['id']:c for c in map(json.loads,(ROOT/'eval/testsets/week2_cases.jsonl').read_text().splitlines())}
 old={v:{r['case_id']:r for r in map(json.loads,(ROOT/f'eval/results/week2/answers_{v}.jsonl').read_text().splitlines())} for v in ['v1','v3']}
 records=[];human=[]
 for i,(v,cid,span,claim,pid) in enumerate(SELECTIONS,1):
  original=old[v][cid]['answer'];assert span in original,(cid,span)
  d,p=sources[pid];src={'citation':1,'doc_id':d.doc_id,'passage_id':pid,'title':d.title,'text':p.text,'source':d.source,'version':d.version}
  key=f'W3-H{i:02d}';generation={'valid':True,'answer':claim+' [1]','claims':[{'claim_id':'C1','text':claim,'citations':[1],'evidence':[]}],'abstained':False}
  record={'case_id':key,'question':cases[cid]['text'],'lang':cases[cid]['lang'],'sources':[src],'generation':generation,'judgement':{'valid':False,'error':'pending_real_judge','claims':[],'unlisted_claims':[]},'origin':{'type':'historical_model_output_claim_extraction','original_case_id':cid,'original_version':v,'original_answer':original,'exact_original_span':span,'span_start':original.index(span),'evidence_assigned_posthoc':True,'not_a_current_RAG_generation':True},'sample_id':key}
  source_text=f'[1] {pid}\n{p.text}'
  sample='HC-'+digest(json.dumps([key,'C1',claim,[1],source_text],ensure_ascii=False))[:16]
  record['sample_id']=sample
  records.append(record)
  human.append(dict(sample_id=sample,case_id=key,claim_id='C1',question=cases[cid]['text'],answer=original,claim_text=claim,citations='[1]',source_text=f'[1] {pid}\n{p.text}',human_label='',human_note=''))
 (out/'records.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in records))
 with (out/'human_sheet.csv').open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=HUMAN_FIELDS);w.writeheader();w.writerows(human)
 (out/'method.json').write_text(json.dumps({'n':20,'purpose':'retrospective claim-judge calibration stress set','origin':'genuine historical Week2-v1/v3 model outputs; atomic extractions preserve exact source spans','evidence':'assigned post hoc from preserved Week3-v1 sources, not original baseline citations','source_snapshot_git_commit':SOURCE_REF,'human_labels':'blank until real reviewer enters them','selection':'purposeful mix of factual requirements, unavailable figures and system boundaries; not representative random RAG sample','code_sha256':digest(Path(__file__).read_bytes())},ensure_ascii=False,indent=2)+'\n')
 print(out)
if __name__=='__main__':build()
