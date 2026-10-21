import sys
import pytest
from scripts.data_audit import audit


def test_legacy_exact_and_template_leakage_is_detected(tmp_path, monkeypatch):
    # Recreate the seeded synthetic fixture in isolation; private/local datasets
    # are intentionally absent from a fresh clone and must never be uploaded.
    from scripts.prepare_data import main as prepare_synthetic
    monkeypatch.setattr(sys, 'argv', ['prepare_data.py', '--output', str(tmp_path)])
    prepare_synthetic()
    report=audit(tmp_path,tokenize=False)
    assert report['status']=='FAIL' and report['generalization_split']=='FAIL'
    assert report['overlap']['train_test']['exact_prompts']==9
    assert report['overlap']['train_test']['normalized_template_families']==3
    assert sum(s['count'] for s in report['splits'].values())==360


def test_real_tokenizer_counts_tokens_not_batch_encoding_keys():
    pytest.importorskip('transformers')
    from recase.model import resolve_model
    from huggingface_hub.errors import LocalEntryNotFoundError
    from transformers import AutoTokenizer
    try:
        model_path = resolve_model()
    except LocalEntryNotFoundError:
        pytest.skip('Optional tokenizer integration requires the existing local Qwen cache; no download')
    tokenizer=AutoTokenizer.from_pretrained(str(model_path),local_files_only=True)
    message=[{'role':'user','content':'공개 증거 E1과 E2의 관계를 확인하세요.'}]
    tokens=tokenizer.apply_chat_template(message,return_dict=False)
    assert isinstance(tokens,list) and len(tokens)>10 and all(isinstance(t,int) for t in tokens)
