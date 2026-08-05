"""Synthetic-only tests for the Phase 9C-I4 (Amendment 2) annotation/audit pipeline.

No Run-2 ledger content, model service, network call, or FinVerify output is
used anywhere in this file, per Implementation Spec Section 14.
"""
from __future__ import annotations

import hashlib

import pytest

from verification.eligibility.aggregation import aggregate_votes
from verification.eligibility.amendment2_freeze import (
    ArtifactHashes, ProductionGateDenied, authorize_annotation_run, authorize_audit_release,
    build_freeze_record, build_kappa_report, build_weighted_statistics, verify_gate_ordering,
)
from verification.eligibility.annotation_config import (
    AnnotationConfig, AnnotatorSpec, DecodingSettings, FailureHandling, build_prompt, validate_disjointness,
)
from verification.eligibility.annotation_models import AnnotationRecord, AnnotatorVote
from verification.eligibility.annotation_runner import run_annotation, stratum_of, stratum_populations
from verification.eligibility.audit_sampling import (
    audit_seed_hex, build_manifest, candidate_rank_hex, hamilton_allocate,
    inclusion_probabilities, manifest_csv_bytes, rank_order, selected_candidates,
)
from verification.eligibility.double_coding import DOUBLE_CODE_COUNT, select_double_coded
from verification.eligibility.family_guard import (
    FamilyDisjointnessViolation, check_new_evaluation_family, freeze_rosters,
)
from verification.eligibility.human_audit import (
    AdjudicationRecord, PendingSecondReview, cohens_kappa, resolve_audit_outcome,
)
from verification.eligibility.review_package import (
    ReviewerResponse, assert_no_leaked_fields, export_blinded_audit, import_responses,
)

SHA_A = hashlib.sha256(b"raw-ledger-fixture").hexdigest()
SHA_B = hashlib.sha256(b"annotation-config-fixture").hexdigest()


def _prompt(role="annotator"):
    return build_prompt(role)


def _annotators(n=3, families=("family-a", "family-b", "family-c", "family-d", "family-e")):
    return tuple(
        AnnotatorSpec("a%d" % i, families[i], "v1", _prompt("role-%d" % i))
        for i in range(n)
    )


def _config(n=3, eval_families=("eval-x",)):
    return AnnotationConfig(
        annotators=_annotators(n),
        decoding=DecodingSettings(0.0, 1.0, 512),
        failure_handling=FailureHandling(60, 2),
        evaluation_model_families=eval_families,
        implementation_commit="a" * 40,
    )


# ---------------------------------------------------------------------------
# annotation_config + family_guard
# ---------------------------------------------------------------------------

def test_prompt_reproduces_rubric_verbatim():
    prompt = _prompt()
    from verification.eligibility.annotation_config import RUBRIC_QUESTION, RUBRIC_CHECKLIST
    assert RUBRIC_QUESTION in prompt
    for item in RUBRIC_CHECKLIST:
        assert item in prompt


def test_annotator_spec_rejects_paraphrased_prompt():
    with pytest.raises(ValueError, match="verbatim"):
        AnnotatorSpec("a1", "family-a", "v1", "Is this a financial fact?")


def test_config_requires_at_least_three_annotators():
    with pytest.raises(ValueError, match="k >= 3"):
        AnnotationConfig(
            annotators=_annotators(2), decoding=DecodingSettings(0.0, 1.0, 512),
            failure_handling=FailureHandling(60, 2), evaluation_model_families=("eval-x",),
        )


def test_config_requires_disjoint_annotator_model_families():
    with pytest.raises(ValueError, match="pairwise distinct"):
        AnnotationConfig(
            annotators=(
                AnnotatorSpec("a1", "family-a", "v1", _prompt()),
                AnnotatorSpec("a2", "family-a", "v2", _prompt()),
                AnnotatorSpec("a3", "family-b", "v1", _prompt()),
            ),
            decoding=DecodingSettings(0.0, 1.0, 512), failure_handling=FailureHandling(60, 2),
            evaluation_model_families=("eval-x",),
        )


def test_config_rejects_overlap_with_evaluation_roster():
    with pytest.raises(ValueError, match="not disjoint"):
        AnnotationConfig(
            annotators=_annotators(3), decoding=DecodingSettings(0.0, 1.0, 512),
            failure_handling=FailureHandling(60, 2), evaluation_model_families=("family-a",),
        )


def test_failure_fallback_must_never_be_a_substantive_label():
    with pytest.raises(ValueError, match="never a substantive label"):
        FailureHandling(60, 2, fallback_status="ELIGIBLE")


def test_lock_bytes_are_deterministic_and_hash_stable():
    config = _config()
    b1 = config.lock_bytes()
    b2 = config.lock_bytes()
    assert b1 == b2
    assert config.lock_sha256() == hashlib.sha256(b1).hexdigest()


def test_validate_disjointness_helper():
    validate_disjointness(["family-a", "family-b"], ["family-c"])
    with pytest.raises(ValueError):
        validate_disjointness(["family-a"], ["family-a"])


def test_family_guard_freeze_rejects_overlap():
    with pytest.raises(FamilyDisjointnessViolation):
        freeze_rosters(["family-a", "family-b"], ["family-b"])


def test_family_guard_never_adjusts_annotation_roster_for_new_eval_family():
    rosters = freeze_rosters(["family-a", "family-b"], ["family-c"])
    with pytest.raises(FamilyDisjointnessViolation):
        check_new_evaluation_family(rosters, "family-a")
    # A genuinely new family is fine.
    check_new_evaluation_family(rosters, "family-d")


# ---------------------------------------------------------------------------
# aggregation
# ---------------------------------------------------------------------------

def _vote(cid="c1", aid="a1", verdict="ELIGIBLE", primary=None, secondary=(), failure=None):
    return AnnotatorVote(cid, aid, verdict, primary, list(secondary), failure)


def test_unanimous_eligible():
    votes = [_vote(aid="a%d" % i) for i in range(3)]
    label, tier, primary, secondary = aggregate_votes(votes)
    assert (label, tier, primary, secondary) == ("ELIGIBLE", "unanimous", None, [])


def test_majority_eligible_kminus1_of_k():
    votes = [_vote(aid="a1"), _vote(aid="a2"), _vote(aid="a3", verdict="EXCLUDED", primary="EXC_NON_FINANCIAL")]
    label, tier, primary, secondary = aggregate_votes(votes)
    assert (label, tier) == ("ELIGIBLE", "majority")


def test_unanimous_excluded_uses_agreeing_codes_and_precedence():
    votes = [
        _vote(aid="a1", verdict="EXCLUDED", primary="EXC_NON_FINANCIAL", secondary=["EXC_PARSE_FAILURE"]),
        _vote(aid="a2", verdict="EXCLUDED", primary="EXC_NON_FINANCIAL", secondary=["EXC_TABLE_CONTEXT_LOST"]),
        _vote(aid="a3", verdict="EXCLUDED", primary="EXC_NON_FINANCIAL"),
    ]
    label, tier, primary, secondary = aggregate_votes(votes)
    assert label == "EXCLUDED" and tier == "unanimous" and primary == "EXC_NON_FINANCIAL"
    assert secondary == ["EXC_TABLE_CONTEXT_LOST", "EXC_PARSE_FAILURE"]  # frozen precedence order


def test_genuine_split_routes_to_adjudication_required():
    votes = [_vote(aid="a1"), _vote(aid="a2", verdict="EXCLUDED", primary="EXC_NON_FINANCIAL"), _vote(aid="a3", verdict="CANNOT_RESOLVE")]
    label, tier, primary, secondary = aggregate_votes(votes)
    assert (label, tier, primary, secondary) == ("ADJUDICATION_REQUIRED", "split", None, [])


def test_excluded_majority_code_disagreement_routes_to_adjudication():
    votes = [
        _vote(aid="a1", verdict="EXCLUDED", primary="EXC_NON_FINANCIAL"),
        _vote(aid="a2", verdict="EXCLUDED", primary="EXC_DERIVED_ONLY"),
        _vote(aid="a3"),
    ]
    label, tier, primary, secondary = aggregate_votes(votes)
    assert label == "ADJUDICATION_REQUIRED" and tier == "split"


def test_failure_vote_never_defaults_and_forces_split():
    votes = [_vote(aid="a1"), _vote(aid="a2"), _vote(aid="a3", verdict=None, failure="timeout")]
    label, tier, primary, secondary = aggregate_votes(votes)
    assert label == "ADJUDICATION_REQUIRED" and tier == "split"


def test_aggregate_votes_rejects_mixed_candidate_ids():
    with pytest.raises(ValueError):
        aggregate_votes([_vote(cid="c1"), _vote(cid="c2")])


def test_aggregate_votes_rejects_empty():
    with pytest.raises(ValueError):
        aggregate_votes([])


def test_annotator_vote_schema_validation():
    with pytest.raises(ValueError):
        AnnotatorVote("c1", "a1", "EXCLUDED", None, [], None)  # EXCLUDED needs a primary code
    with pytest.raises(ValueError):
        AnnotatorVote("c1", "a1", "ELIGIBLE", "EXC_NON_FINANCIAL", [], None)  # ELIGIBLE can't carry a code
    with pytest.raises(ValueError):
        AnnotatorVote("c1", "a1", "ELIGIBLE", None, [], "timeout")  # failure + verdict is invalid


# ---------------------------------------------------------------------------
# annotation_runner
# ---------------------------------------------------------------------------

def test_run_annotation_is_deterministic_and_provider_independent():
    ids = ["c1", "c2", "c3"]
    votes = {
        "c1": [_vote("c1", "a%d" % i) for i in range(3)],
        "c2": [_vote("c2", "a1", verdict="EXCLUDED", primary="EXC_NON_FINANCIAL"),
               _vote("c2", "a2", verdict="EXCLUDED", primary="EXC_NON_FINANCIAL"),
               _vote("c2", "a3", verdict="EXCLUDED", primary="EXC_NON_FINANCIAL")],
        "c3": [_vote("c3", "a1"), _vote("c3", "a2", verdict="EXCLUDED", primary="EXC_NON_FINANCIAL"),
               _vote("c3", "a3", verdict="CANNOT_RESOLVE")],
    }
    r1 = run_annotation(ids, votes)
    r2 = run_annotation(ids, votes)
    assert [ (r.candidate_id, r.llm_annotation, r.agreement_tier) for r in r1] == [(r.candidate_id, r.llm_annotation, r.agreement_tier) for r in r2]
    assert stratum_of(r1[0]) == "A" and stratum_of(r1[1]) == "B" and stratum_of(r1[2]) == "C"
    assert stratum_populations(r1) == {"A": 1, "B": 1, "C": 1}


def test_run_annotation_requires_complete_votes():
    with pytest.raises(ValueError, match="missing votes"):
        run_annotation(["c1", "c2"], {"c1": [_vote("c1")]})


def test_run_annotation_retries_failures_before_falling_back():
    calls = []

    def provider(cid, aid):
        calls.append((cid, aid))
        return _vote(cid, aid, verdict="ELIGIBLE")

    votes = {"c1": [_vote("c1", "a1"), _vote("c1", "a2"), _vote("c1", "a3", verdict=None, failure="timeout")]}
    records = run_annotation(["c1"], votes, retry_count=1, retry_provider=provider)
    assert records[0].llm_annotation == "ELIGIBLE"
    assert records[0].agreement_tier == "unanimous"
    assert calls == [("c1", "a3")]


def test_run_annotation_exhausted_retries_still_falls_back_to_adjudication():
    def always_fails(cid, aid):
        return _vote(cid, aid, verdict=None, failure="timeout")

    votes = {"c1": [_vote("c1", "a1"), _vote("c1", "a2"), _vote("c1", "a3", verdict=None, failure="timeout")]}
    records = run_annotation(["c1"], votes, retry_count=2, retry_provider=always_fails)
    assert records[0].llm_annotation == "ADJUDICATION_REQUIRED"


def test_annotation_record_eligibility_status_mirrors_llm_only():
    with pytest.raises(ValueError, match="mirror"):
        AnnotationRecord("c1", "ELIGIBLE", "unanimous", None, [], "EXCLUDED")


# ---------------------------------------------------------------------------
# audit_sampling
# ---------------------------------------------------------------------------

def test_audit_seed_hex_matches_frozen_construction():
    seed = audit_seed_hex(SHA_A, SHA_B)
    expected = hashlib.sha256(("finverify-phase9c-audit-v1\n" + SHA_A + "\n" + SHA_B).encode("utf-8")).hexdigest()
    assert seed == expected


def test_audit_seed_hex_rejects_non_lower_hex():
    with pytest.raises(ValueError):
        audit_seed_hex(SHA_A.upper(), SHA_B)


def test_candidate_rank_hex_matches_frozen_construction():
    seed = audit_seed_hex(SHA_A, SHA_B)
    rank = candidate_rank_hex(seed, "cand-1")
    expected = hashlib.sha256(("finverify-phase9c-audit-rank-v1\n" + seed + "\ncand-1").encode("utf-8")).hexdigest()
    assert rank == expected


def test_rank_order_is_deterministic_and_repeatable():
    seed = audit_seed_hex(SHA_A, SHA_B)
    ids = ["c%d" % i for i in range(50)]
    o1 = rank_order(ids, seed)
    o2 = rank_order(ids, seed)
    assert o1 == o2
    assert sorted(o1) == sorted(ids)


def test_hamilton_allocate_basic_proportional_floor_and_remainder():
    # N_A=1000, N_B=1000, N_C=118 (sums to 2118), n=100 -> proportional split.
    populations = {"A": 1000, "B": 1000, "C": 118}
    allocation = hamilton_allocate(100, populations)
    assert sum(allocation.values()) == 100
    for s in ("A", "B", "C"):
        assert allocation[s] <= populations[s]


def test_hamilton_allocate_never_exceeds_stratum_population():
    # A tiny stratum's proportional share (q_h = n*N_h/N) can never exceed
    # its own population when n <= N, so this must stay within N_A=3.
    populations = {"A": 3, "B": 1000, "C": 1000}
    allocation = hamilton_allocate(100, populations)
    assert allocation["A"] <= 3
    assert sum(allocation.values()) == 100
    assert allocation["B"] <= 1000 and allocation["C"] <= 1000


def test_hamilton_allocate_rejects_n_exceeding_total_population():
    with pytest.raises(ValueError, match="exceeds total available population"):
        hamilton_allocate(2119, {"A": 1000, "B": 1000, "C": 118})


def test_hamilton_allocate_full_census_of_tiny_stratum_exhausts_and_redistributes():
    # n == N: every stratum's full population is exactly its due share,
    # exercising the exhaustion path (remaining_capacity hits 0) for each
    # stratum in turn without ever exceeding any N_h.
    populations = {"A": 2, "B": 2, "C": 96}
    allocation = hamilton_allocate(100, populations)
    assert allocation == {"A": 2, "B": 2, "C": 96}


def test_hamilton_allocate_reused_for_incremental_topup_still_respects_capacity():
    # A later volunteer-driven top-up reuses the same populations with a
    # larger n; a stratum whose earlier allocation used its full capacity
    # must not be pushed over its population on the new call.
    populations = {"A": 2, "B": 1000, "C": 1000}
    first = hamilton_allocate(5, populations)
    assert first["A"] <= 2
    topped_up = hamilton_allocate(50, populations)
    assert topped_up["A"] <= 2
    assert sum(topped_up.values()) == 50


def test_hamilton_allocate_full_census_when_n_equals_total_population():
    populations = {"A": 5, "B": 7, "C": 3}
    allocation = hamilton_allocate(15, populations)
    assert allocation == {"A": 5, "B": 7, "C": 3}


def test_hamilton_allocate_tie_break_is_lexical_A_lt_B_lt_C():
    # Symmetric populations producing equal fractional remainders.
    populations = {"A": 10, "B": 10, "C": 10}
    allocation = hamilton_allocate(1, populations)
    assert allocation == {"A": 1, "B": 0, "C": 0}


def test_inclusion_probabilities_zero_for_unallocated_stratum():
    pi = inclusion_probabilities({"A": 10, "B": 0}, {"A": 100, "B": 50, "C": 0})
    assert pi["A"] == pytest.approx(0.1)
    assert pi["B"] == 0.0
    assert pi["C"] == 0.0


def test_build_manifest_every_occurrence_has_a_row_and_selection_matches_allocation():
    seed = audit_seed_hex(SHA_A, SHA_B)
    candidates_by_stratum = {
        "A": ["a%d" % i for i in range(10)],
        "B": ["b%d" % i for i in range(10)],
        "C": ["c%d" % i for i in range(10)],
    }
    populations = {s: len(v) for s, v in candidates_by_stratum.items()}
    rows = build_manifest(candidates_by_stratum, populations, n=9, audit_seed_hex_value=seed)
    assert len(rows) == 30
    selected = [r for r in rows if r.selected]
    assert len(selected) == 9
    picked = selected_candidates(rows)
    assert sum(len(v) for v in picked.values()) == 9


def test_build_manifest_is_deterministic_across_calls():
    seed = audit_seed_hex(SHA_A, SHA_B)
    candidates_by_stratum = {"A": ["a%d" % i for i in range(20)], "B": [], "C": []}
    populations = {"A": 20, "B": 0, "C": 0}
    r1 = build_manifest(candidates_by_stratum, populations, n=5, audit_seed_hex_value=seed)
    r2 = build_manifest(candidates_by_stratum, populations, n=5, audit_seed_hex_value=seed)
    assert [(r.candidate_id, r.selected) for r in r1] == [(r.candidate_id, r.selected) for r in r2]


def test_manifest_csv_bytes_is_byte_identical_on_repeat_serialization():
    seed = audit_seed_hex(SHA_A, SHA_B)
    candidates_by_stratum = {"A": ["a1", "a2"], "B": ["b1"], "C": []}
    populations = {"A": 2, "B": 1, "C": 0}
    rows = build_manifest(candidates_by_stratum, populations, n=2, audit_seed_hex_value=seed)
    b1 = manifest_csv_bytes(rows, generation_timestamp="2026-08-05T00:00:00Z",
                             raw_ledger_sha256_lower=SHA_A, annotation_config_sha256_lower=SHA_B,
                             audit_seed_hex_value=seed)
    b2 = manifest_csv_bytes(rows, generation_timestamp="2026-08-05T00:00:00Z",
                             raw_ledger_sha256_lower=SHA_A, annotation_config_sha256_lower=SHA_B,
                             audit_seed_hex_value=seed)
    assert b1 == b2
    assert b1.startswith(b"# raw_ledger_sha256=")


def test_build_manifest_rejects_population_mismatch():
    with pytest.raises(ValueError):
        build_manifest({"A": ["a1"]}, {"A": 2}, n=1, audit_seed_hex_value="0" * 64)


# ---------------------------------------------------------------------------
# double_coding
# ---------------------------------------------------------------------------

def test_select_double_coded_picks_exactly_twenty_when_available():
    seed = audit_seed_hex(SHA_A, SHA_B)
    selected = {
        "A": ["a%d" % i for i in range(40)],
        "B": ["b%d" % i for i in range(40)],
        "C": ["c%d" % i for i in range(20)],
    }
    double_coded = select_double_coded(selected, audit_seed_hex_value=seed)
    total = sum(len(v) for v in double_coded.values())
    assert total == DOUBLE_CODE_COUNT == 20
    for s in ("A", "B", "C"):
        assert set(double_coded[s]).issubset(set(selected[s]))


def test_select_double_coded_is_deterministic():
    seed = audit_seed_hex(SHA_A, SHA_B)
    selected = {"A": ["a%d" % i for i in range(50)], "B": ["b%d" % i for i in range(30)], "C": ["c%d" % i for i in range(20)]}
    d1 = select_double_coded(selected, audit_seed_hex_value=seed)
    d2 = select_double_coded(selected, audit_seed_hex_value=seed)
    assert d1 == d2


def test_select_double_coded_rejects_more_than_selected():
    with pytest.raises(ValueError):
        select_double_coded({"A": ["a1"], "B": [], "C": []}, audit_seed_hex_value="0" * 64, count=20)


# ---------------------------------------------------------------------------
# review_package (blinding)
# ---------------------------------------------------------------------------

def test_export_blinded_audit_strips_llm_and_finverify_fields():
    candidates = [
        {
            "candidate_id": "c1", "evidence_type": "prose", "evidence_text": "Revenue was $1.",
            "target_raw_text": "$1", "source_locator": "block/0", "applicable_heading": "Results",
            "issuer": "Example Corp", "reporting_event": "Q1-2025", "dependency_log": [],
            # Deliberately included to prove the exporter strips them:
            "llm_annotation": "ELIGIBLE", "agreement_tier": "unanimous", "model_family": "family-a",
            "finverify_output": "should never appear",
        }
    ]
    rows, mapping = export_blinded_audit(candidates, shuffle_seed_hex="s" * 64)
    assert_no_leaked_fields(rows)
    assert len(rows) == 1 and len(mapping) == 1
    assert mapping[rows[0].row_id] == "c1"
    assert "candidate_id" not in rows[0].evidence


def test_export_blinded_audit_order_independent_of_stratum_input_order():
    candidates = [{"candidate_id": "c%d" % i, "evidence_text": "x"} for i in range(10)]
    rows_a, _ = export_blinded_audit(candidates, shuffle_seed_hex="seed-1" + "0" * 58)
    rows_b, _ = export_blinded_audit(list(reversed(candidates)), shuffle_seed_hex="seed-1" + "0" * 58)
    assert [r.row_id for r in rows_a] == [r.row_id for r in rows_b]


def test_import_responses_restores_identity_and_rejects_unknown_row():
    candidates = [{"candidate_id": "c1", "evidence_text": "x"}]
    rows, mapping = export_blinded_audit(candidates, shuffle_seed_hex="a" * 64)
    response = ReviewerResponse(rows[0].row_id, "R1", "ELIGIBLE")
    restored = import_responses([response], mapping)
    assert restored["c1"].verdict == "ELIGIBLE"
    with pytest.raises(ValueError, match="unknown row_id"):
        import_responses([ReviewerResponse("bogus", "R1", "ELIGIBLE")], mapping)


def test_import_responses_rejects_duplicate_submission():
    candidates = [{"candidate_id": "c1", "evidence_text": "x"}]
    rows, mapping = export_blinded_audit(candidates, shuffle_seed_hex="a" * 64)
    dup = [ReviewerResponse(rows[0].row_id, "R1", "ELIGIBLE"), ReviewerResponse(rows[0].row_id, "R1", "EXCLUDED", "EXC_NON_FINANCIAL")]
    with pytest.raises(ValueError, match="duplicate response"):
        import_responses(dup, mapping)


# ---------------------------------------------------------------------------
# human_audit: consensus / adjudication
# ---------------------------------------------------------------------------

def test_single_review_agreeing_with_llm_is_llm_audited_agree():
    outcome = resolve_audit_outcome(candidate_id="c1", llm_annotation="ELIGIBLE", human_audit_label="ELIGIBLE")
    assert outcome.label_source == "llm_audited_agree"
    assert outcome.eligibility_status == "ELIGIBLE"
    assert outcome.agrees_with_llm is True


def test_divergent_single_review_requires_second_review():
    with pytest.raises(PendingSecondReview):
        resolve_audit_outcome(candidate_id="c1", llm_annotation="ELIGIBLE", human_audit_label="EXCLUDED")


def test_double_coded_case_always_requires_second_review_even_if_agrees_with_llm():
    with pytest.raises(PendingSecondReview):
        resolve_audit_outcome(candidate_id="c1", llm_annotation="ELIGIBLE", human_audit_label="ELIGIBLE", is_double_coded=True)


def test_unanimous_blind_human_consensus_overrides_llm_and_is_binding():
    outcome = resolve_audit_outcome(
        candidate_id="c1", llm_annotation="ELIGIBLE",
        human_audit_label="EXCLUDED", human_audit_label_2="EXCLUDED",
    )
    assert outcome.label_source == "llm_human_consensus"
    assert outcome.eligibility_status == "EXCLUDED"
    assert outcome.agrees_with_llm is False


def test_human_human_disagreement_requires_adjudication():
    with pytest.raises(PendingSecondReview, match="adjudication"):
        resolve_audit_outcome(
            candidate_id="c1", llm_annotation="ELIGIBLE",
            human_audit_label="EXCLUDED", human_audit_label_2="ELIGIBLE",
        )


def test_adjudication_resolves_human_human_disagreement():
    adjudication = AdjudicationRecord(
        candidate_id="c1", adjudicated_label="EXCLUDED", justification="Source text lacks required period context.",
        timestamp="2026-08-05T00:00:00Z", adjudicator_id="ADJ-1",
    )
    outcome = resolve_audit_outcome(
        candidate_id="c1", llm_annotation="ELIGIBLE",
        human_audit_label="EXCLUDED", human_audit_label_2="ELIGIBLE", adjudication=adjudication,
    )
    assert outcome.label_source == "llm_human_adjudicated"
    assert outcome.eligibility_status == "EXCLUDED"
    assert outcome.audit_status == "ADJUDICATED"


def test_adjudication_requires_nonempty_justification_and_valid_label():
    with pytest.raises(ValueError, match="justification"):
        AdjudicationRecord("c1", "EXCLUDED", "   ", "2026-08-05T00:00:00Z", "ADJ-1")
    with pytest.raises(ValueError):
        AdjudicationRecord("c1", "MAYBE", "reason", "2026-08-05T00:00:00Z", "ADJ-1")


def test_cohens_kappa_perfect_agreement_and_chance_agreement():
    assert cohens_kappa([("ELIGIBLE", "ELIGIBLE"), ("EXCLUDED", "EXCLUDED")]) == 1.0
    assert cohens_kappa([]) is None
    # Some real disagreement present -> kappa strictly less than 1.
    kappa = cohens_kappa([("ELIGIBLE", "ELIGIBLE"), ("ELIGIBLE", "EXCLUDED"), ("EXCLUDED", "EXCLUDED"), ("EXCLUDED", "ELIGIBLE")])
    assert kappa is not None and kappa < 1.0


# ---------------------------------------------------------------------------
# amendment2_freeze: default-deny gates, ordering, final record
# ---------------------------------------------------------------------------

def test_gate1_default_deny():
    with pytest.raises(ProductionGateDenied):
        authorize_annotation_run(allow_annotation_production=False, implementation_commit="a" * 40)


def test_gate1_requires_valid_commit_even_when_allowed():
    with pytest.raises(ProductionGateDenied, match="implementation commit"):
        authorize_annotation_run(allow_annotation_production=True, implementation_commit="not-a-commit")
    authorize_annotation_run(allow_annotation_production=True, implementation_commit="a" * 40)  # ok


def test_gate2_default_deny_and_independent_of_gate1():
    with pytest.raises(ProductionGateDenied):
        authorize_audit_release(allow_audit_release=False, annotation_ledger_frozen=True, manifest_frozen=True)
    with pytest.raises(ProductionGateDenied, match="already be frozen"):
        authorize_audit_release(allow_audit_release=True, annotation_ledger_frozen=False, manifest_frozen=True)
    authorize_audit_release(allow_audit_release=True, annotation_ledger_frozen=True, manifest_frozen=True)  # ok


def test_gate_ordering_enforced():
    verify_gate_ordering(
        annotation_gate_ts="2026-08-01T00:00:00Z", manifest_ts="2026-08-02T00:00:00Z",
        audit_release_gate_ts="2026-08-03T00:00:00Z",
    )
    with pytest.raises(ValueError, match="preceding"):
        verify_gate_ordering(
            annotation_gate_ts="2026-08-03T00:00:00Z", manifest_ts="2026-08-02T00:00:00Z",
            audit_release_gate_ts="2026-08-01T00:00:00Z",
        )


def test_weighted_statistics_reuses_frozen_estimator():
    strata = {"A": (5000, 40, 39), "B": (5000, 40, 38), "C": (4118, 20, 15)}
    result = build_weighted_statistics(strata)
    assert result["status"] == "ESTIMATED"
    assert 0.0 <= result["point_estimate"] <= 1.0


def test_kappa_report_aggregates_per_stratum_and_double_coded():
    per_stratum = {
        "A": [("ELIGIBLE", "ELIGIBLE")] * 10,
        "B": [("EXCLUDED", "EXCLUDED")] * 8 + [("EXCLUDED", "ELIGIBLE")] * 2,
    }
    double_coded = [("ELIGIBLE", "ELIGIBLE")] * 18 + [("ELIGIBLE", "EXCLUDED")] * 2
    report = build_kappa_report(per_stratum, double_coded)
    assert report["double_coded_n"] == 20
    assert report["per_stratum_kappa"]["A"] == 1.0
    assert report["human_human_kappa_double_coded"] is not None


def test_build_freeze_record_requires_exactly_twenty_double_coded():
    kwargs = dict(
        phase="9C-I4",
        artifact_hashes=ArtifactHashes(*(["0" * 64] * 10)),
        audit_seed_hex_value="0" * 64, audit_size=100,
        weighted_statistics={}, kappa_report={}, model_family_disjointness_attestation=True,
        annotation_gate_ts="2026-08-01T00:00:00Z", manifest_ts="2026-08-02T00:00:00Z",
        audit_release_gate_ts="2026-08-03T00:00:00Z", implementation_commit="a" * 40,
    )
    with pytest.raises(ValueError, match="exactly 20"):
        build_freeze_record(double_coded_count=19, **kwargs)
    record = build_freeze_record(double_coded_count=20, **kwargs)
    assert record["double_coded_count"] == 20
    assert "not a fully human-reviewed corpus" in record["corpus_characterization"]


def test_build_freeze_record_requires_disjointness_attestation():
    kwargs = dict(
        phase="9C-I4", artifact_hashes=ArtifactHashes(*(["0" * 64] * 10)),
        audit_seed_hex_value="0" * 64, audit_size=100, double_coded_count=20,
        weighted_statistics={}, kappa_report={},
        annotation_gate_ts="2026-08-01T00:00:00Z", manifest_ts="2026-08-02T00:00:00Z",
        audit_release_gate_ts="2026-08-03T00:00:00Z", implementation_commit="a" * 40,
    )
    with pytest.raises(ValueError, match="disjointness attestation"):
        build_freeze_record(model_family_disjointness_attestation=False, **kwargs)
