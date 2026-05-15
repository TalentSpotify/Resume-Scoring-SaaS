"""Tests for pipeline logic: filtering, ranking, weighted score computation."""

import pytest
from app.pipeline import _apply_filter, _compute_weighted_score
from app.schemas import FilterDecision


class TestFilterDecision:
    def test_reject_below_60(self):
        assert _apply_filter(59.9) == FilterDecision.reject

    def test_shortlist_at_60(self):
        assert _apply_filter(60.0) == FilterDecision.shortlist

    def test_shortlist_at_79(self):
        assert _apply_filter(79.9) == FilterDecision.shortlist

    def test_strong_match_at_80(self):
        assert _apply_filter(80.0) == FilterDecision.strong_match

    def test_strong_match_above_80(self):
        assert _apply_filter(95.0) == FilterDecision.strong_match

    def test_reject_at_zero(self):
        assert _apply_filter(0) == FilterDecision.reject


class TestWeightedScore:
    def test_all_perfect_scores(self):
        score = _compute_weighted_score(100, 100, 100, 100, 100)
        assert score == 100.0

    def test_all_zero_scores(self):
        score = _compute_weighted_score(0, 0, 0, 0, 0)
        assert score == 0.0

    def test_llm_dominates(self):
        # LLM=100, everything else=0 → should be ~65
        score = _compute_weighted_score(100, 0, 0, 0, 0)
        assert 60 <= score <= 70

    def test_non_llm_without_llm(self):
        # LLM=0, everything else=100 → should be ~35
        score = _compute_weighted_score(0, 100, 100, 100, 100)
        assert 30 <= score <= 40

    def test_weights_sum_to_1(self):
        from app.config import config
        w = config.weights
        total = w.llm + w.ats_keyword + w.skill_fit + w.experience_fit + w.domain_fit
        assert abs(total - 1.0) < 0.01
