"""Actual cached model integration. Skip downloads in a clean unit-test environment."""
from pathlib import Path
import pytest
from agent.settings import Settings
from agent.retrieval import RunbookIndex


def test_real_multilingual_retrieval_and_index_invalidation(tmp_path):
    settings=Settings()
    if not (settings.data_dir/'.embedding_cache').exists():
        pytest.skip('먼저 python -m evaluation.run으로 모델을 준비하세요.')
    index=RunbookIndex(settings.data_dir,tmp_path/'vectors.db',settings.embedding_model)
    docs=index.search('메모리가 계속 차오르고 사용한 공간이 반환되지 않습니다')
    assert docs and docs[0]['id']=='R:memory-leak'
    assert all(d['uri'].startswith('runbook://incident-response/') for d in docs)
    count=index.conn.execute('SELECT count(*) FROM vectors').fetchone()[0]
    index.prepare()
    assert len(index.documents)==count==6
    index.close()
