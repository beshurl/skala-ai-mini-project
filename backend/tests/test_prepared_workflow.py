import hashlib
import json

import pytest

from scripts import prepared_workflow as workflow


def test_packet_escape_is_rejected(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setattr(workflow, "PROJECT", project)
    with pytest.raises(ValueError, match="outputs/runs"):
        workflow.validate_packet(tmp_path)


def test_edited_code_rejected_before_execution(tmp_path, monkeypatch):
    monkeypatch.setattr(workflow, "PROJECT", tmp_path)
    packet = tmp_path / "outputs/runs/test-packet"
    packet.mkdir(parents=True)
    source = packet / "review_control.py"
    source.write_text("raise AssertionError('must not execute')")
    seal = {source.name: hashlib.sha256(source.read_bytes()).hexdigest()}
    (packet / "tool_manifest.json").write_text(json.dumps(seal))
    assert workflow.validate_packet(packet) == packet
    source.write_text("changed")
    with pytest.raises(ValueError, match="changed"):
        workflow.validate_packet(packet)
