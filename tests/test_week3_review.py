import csv
import pytest
from tools.week3_review.server import ReviewStore

def make(tmp_path):
 p=tmp_path/'sheet.csv'
 with p.open('w',newline='') as h:
  w=csv.DictWriter(h,fieldnames=['sample_id','claim_text','human_label','human_note','judge_label']);w.writeheader();w.writerow({'sample_id':'A','claim_text':'Example','human_label':'','human_note':'','judge_label':'unsupported'})
 return ReviewStore(p)

def test_blind_payload_excludes_judge_and_does_not_prefill(tmp_path):
 s=make(tmp_path);d=s.public_data();assert 'judge_label' not in d['items'][0];assert d['items'][0]['human_label']==''

def test_revision_conflict_preserves_actual_human_label(tmp_path):
 s=make(tmp_path);d=s.public_data();payload={'csrf':s.token,'revision':d['revision'],'sample_id':'A','label':'supported','note':'Read source'}
 result=s.label(payload);assert result['items'][0]['human_label']=='supported'
 with pytest.raises(RuntimeError):s.label(dict(payload,label='unsupported'))
 assert s.public_data()['items'][0]['human_label']=='supported'

def test_invalid_token_and_label_do_not_write(tmp_path):
 s=make(tmp_path);d=s.public_data()
 with pytest.raises(PermissionError):s.label({'csrf':'bad','label':'supported'})
 with pytest.raises(ValueError):s.label({'csrf':s.token,'label':'invented'})
 assert s.public_data()['revision']==d['revision']

def test_supplementary_advice_is_readonly_and_not_mixed_with_human_labels(tmp_path):
 import json
 s=make(tmp_path);before=s.sheet.read_bytes()
 advice={'title':'Tamamlayıcı inceleme','author':'assistant','eligible_for_human_kappa':False,
         'human_completed':13,'assistant_completed':7,'assistant_audited':13,
         'human_sheet_sha256':s.public_data()['revision'],
         'items':[{'sample_id':'A','supplementary_label':'supported'}]}
 s.sheet.with_name('supplementary_review.json').write_text(json.dumps(advice))
 data=s.supplementary_data()
 assert data['author']=='assistant' and data['eligible_for_human_kappa'] is False
 assert data['human_sheet_unchanged_since_review'] is True
 assert s.sheet.read_bytes()==before
 human=s.public_data()
 assert human['supplementary_available'] is True
 assert human['items'][0]['human_label']==''
 assert 'supplementary_label' not in human['items'][0]
 assert s.supplementary_viewed is True

def test_supplementary_missing_or_false_provenance_is_rejected(tmp_path):
 import json
 s=make(tmp_path)
 with pytest.raises(FileNotFoundError):s.supplementary_data()
 s.sheet.with_name('supplementary_review.json').write_text(json.dumps({'author':'human','eligible_for_human_kappa':True}))
 with pytest.raises(ValueError):s.supplementary_data()
 assert s.public_data()['items'][0]['human_label']==''

def test_supplementary_page_has_no_label_submission_or_autoselection():
 from tools.week3_review.server import SUPPLEMENTARY_PAGE
 html=SUPPLEMENTARY_PAGE.read_text()
 assert '<h1>Tamamlayıcı inceleme</h1>' in html
 assert '/api/supplementary' in html
 assert '/api/label' not in html and 'method:\'POST\'' not in html
 assert 'data-label' not in html
