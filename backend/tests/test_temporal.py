from datetime import datetime
import pytest
from recase.temporal import Observation, feasibility


def obs(place, at='2026-10-10T21:00:00+09:00', **kwargs):
    return Observation('A',place,datetime.fromisoformat(at),**kwargs)


def test_missing_travel_time_does_not_imply_contradiction():
    assert feasibility(obs('연구실'),obs('주차장','2026-10-10T21:05:00+09:00'),None)['label']=='INSUFFICIENT'


def test_confirmed_impossible_and_possible_with_known_minimum():
    a,b=obs('연구실'),obs('주차장','2026-10-10T21:05:00+09:00')
    assert feasibility(a,b,720)['label']=='IMPOSSIBLE'
    assert feasibility(a,b,180)['label']=='POSSIBLE'


def test_clock_uncertainty_changes_decision_to_insufficient():
    a=obs('연구실',tolerance_seconds=90)
    b=obs('주차장','2026-10-10T21:05:00+09:00',tolerance_seconds=90)
    assert feasibility(a,b,420)['label']=='INSUFFICIENT'


def test_date_boundary_and_timezone_offsets_are_preserved():
    a=obs('연구실','2026-10-10T23:58:00+09:00')
    b=obs('주차장','2026-10-11T00:04:00+09:00')
    assert feasibility(a,b,300)['label']=='POSSIBLE'
    same_instant=obs('주차장','2026-10-10T14:58:00+00:00')
    assert feasibility(a,same_instant,60)['label']=='IMPOSSIBLE'


def test_identity_and_continuous_stay_are_not_assumed():
    assert feasibility(obs('연구실'),obs('주차장',identity_verified=False),60)['label']=='INSUFFICIENT'
    result=feasibility(obs('연구실'),obs('연구실','2026-10-10T23:00:00+09:00'),None)
    assert result['label']=='POSSIBLE' and '연속 체류를 입증하지' in result['reason']


def test_naive_timestamps_and_invalid_bounds_are_rejected():
    with pytest.raises(ValueError): Observation('A','연구실',datetime(2026,10,10,21))
    with pytest.raises(ValueError): obs('연구실',tolerance_seconds=-1)
    with pytest.raises(ValueError): feasibility(obs('연구실'),obs('주차장'),-1)
