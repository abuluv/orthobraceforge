"""
Unit tests for compliance_rag.py — ComplianceKnowledgeBase and ComplianceRAG.
"""
import sys
from pathlib import Path

import pytest

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from compliance_rag import ComplianceKnowledgeBase, ComplianceRAG, RAGDocument, RAGResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def knowledge_base():
    """Shared ComplianceKnowledgeBase instance (auto-generates default JSON)."""
    return ComplianceKnowledgeBase()


@pytest.fixture(scope="module")
def rag():
    """Shared ComplianceRAG instance."""
    return ComplianceRAG()


def _valid_params(**overrides):
    """Return a set of design parameters that should pass all checks."""
    params = {
        "thickness_mm": 3.5,
        "ankle_dorsiflexion_target_deg": 5.0,
        "age_years": 6,
        "material": "petg",
        "safety_factor": 3.5,
    }
    params.update(overrides)
    return params


# ---------------------------------------------------------------------------
# 1. ComplianceKnowledgeBase loads default entries
# ---------------------------------------------------------------------------
class TestComplianceKnowledgeBase:
    def test_documents_non_empty(self, knowledge_base):
        assert len(knowledge_base.documents) > 0

    # 2. All 5 source types have entries
    @pytest.mark.parametrize("source", ["fda", "iso13485", "iso10993", "clinical", "material"])
    def test_all_source_types_present(self, knowledge_base, source):
        sources = {doc.source for doc in knowledge_base.documents}
        assert source in sources, f"Source '{source}' missing from knowledge base"

    def test_documents_are_ragdocument_instances(self, knowledge_base):
        for doc in knowledge_base.documents:
            assert isinstance(doc, RAGDocument)

    def test_keyword_index_built(self, knowledge_base):
        assert hasattr(knowledge_base, "_keyword_index")
        assert len(knowledge_base._keyword_index) > 0


# ---------------------------------------------------------------------------
# 3-5. ComplianceRAG.query()
# ---------------------------------------------------------------------------
class TestQuery:
    # 3. query returns results for relevant keywords
    def test_query_returns_results_for_pediatric_afo(self, rag):
        results = rag.query("pediatric afo")
        assert len(results) > 0
        assert all(isinstance(r, RAGResult) for r in results)

    def test_query_returns_results_for_biocompatibility(self, rag):
        results = rag.query("biocompatibility skin contact")
        assert len(results) > 0

    # 4. query with source_filter returns only docs from that source
    @pytest.mark.parametrize("source", ["fda", "iso13485", "iso10993", "clinical", "material"])
    def test_query_source_filter(self, rag, source):
        # Use a broad query that should match something in every source
        results = rag.query("device design safety pediatric material", source_filter=source)
        for r in results:
            assert r.document.source == source

    def test_query_source_filter_fda_only(self, rag):
        results = rag.query("510k clearance class", source_filter="fda")
        assert len(results) > 0
        assert all(r.document.source == "fda" for r in results)

    # 5. Results sorted by relevance score descending
    def test_query_results_sorted_descending(self, rag):
        results = rag.query("pediatric afo design safety")
        scores = [r.relevance_score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_query_top_k_limits_results(self, rag):
        results = rag.query("pediatric afo", top_k=2)
        assert len(results) <= 2

    def test_query_no_match_returns_empty(self, rag):
        results = rag.query("xyznonexistentkeyword")
        assert results == []

    def test_severity_weighting_critical_scores_higher(self, rag):
        """Critical documents should score higher than informational ones
        for equivalent keyword overlap."""
        results = rag.query("pediatric afo")
        if len(results) >= 2:
            critical_results = [r for r in results if r.document.severity == "critical"]
            info_results = [r for r in results if r.document.severity == "informational"]
            if critical_results and info_results:
                assert critical_results[0].relevance_score >= info_results[0].relevance_score


# ---------------------------------------------------------------------------
# 6-11. ComplianceRAG.check_design_compliance()
# ---------------------------------------------------------------------------
class TestCheckDesignCompliance:
    # 6. Valid params => passed=True
    def test_valid_params_pass(self, rag):
        result = rag.check_design_compliance(_valid_params())
        assert result["passed"] is True
        assert len(result["blocking_issues"]) == 0

    # 7. thickness <2.5mm => blocking
    def test_thickness_below_min_blocks(self, rag):
        result = rag.check_design_compliance(_valid_params(thickness_mm=2.0))
        assert result["passed"] is False
        assert any("thickness" in b.lower() for b in result["blocking_issues"])
        assert "THICKNESS_BELOW_MIN" in result["flags"]

    def test_thickness_marginal_warns(self, rag):
        result = rag.check_design_compliance(_valid_params(thickness_mm=2.8))
        assert result["passed"] is True
        assert any("thickness" in w.lower() for w in result["warnings"])

    # 8. age <2 => blocking
    def test_age_below_2_blocks(self, rag):
        result = rag.check_design_compliance(_valid_params(age_years=1))
        assert result["passed"] is False
        assert any("age" in b.lower() for b in result["blocking_issues"])
        assert "AGE_CONTRAINDICATED" in result["flags"]

    def test_age_above_12_warns(self, rag):
        result = rag.check_design_compliance(_valid_params(age_years=14))
        assert result["passed"] is True
        assert any("age" in w.lower() for w in result["warnings"])

    # 9. Invalid material => blocking
    def test_invalid_material_blocks(self, rag):
        result = rag.check_design_compliance(_valid_params(material="abs_generic"))
        assert result["passed"] is False
        assert any("material" in b.lower() for b in result["blocking_issues"])
        assert "MATERIAL_NOT_VALIDATED" in result["flags"]

    def test_valid_materials_pass(self, rag):
        for mat in ("petg", "nylon_pa12", "tpu_95a", "ti6al4v_lattice"):
            result = rag.check_design_compliance(_valid_params(material=mat))
            assert "MATERIAL_NOT_VALIDATED" not in result["flags"]

    # 10. safety_factor <3.0 => blocking
    def test_safety_factor_below_min_blocks(self, rag):
        result = rag.check_design_compliance(_valid_params(safety_factor=2.5))
        assert result["passed"] is False
        assert any("safety factor" in b.lower() for b in result["blocking_issues"])
        assert "SAFETY_FACTOR_LOW" in result["flags"]

    # 11. HUMAN_REVIEW_MANDATORY always present
    def test_human_review_mandatory_always_present(self, rag):
        result = rag.check_design_compliance(_valid_params())
        assert "HUMAN_REVIEW_MANDATORY" in result["flags"]

    def test_human_review_mandatory_even_when_blocking(self, rag):
        result = rag.check_design_compliance(_valid_params(thickness_mm=1.0))
        assert "HUMAN_REVIEW_MANDATORY" in result["flags"]

    def test_ankle_angle_out_of_range_blocks(self, rag):
        result = rag.check_design_compliance(
            _valid_params(ankle_dorsiflexion_target_deg=-20)
        )
        assert result["passed"] is False
        assert "ANGLE_OUT_OF_RANGE" in result["flags"]

    def test_multiple_blocking_issues_all_reported(self, rag):
        result = rag.check_design_compliance(_valid_params(
            thickness_mm=1.0,
            age_years=1,
            material="unknown_plastic",
            safety_factor=1.0,
        ))
        assert result["passed"] is False
        assert len(result["blocking_issues"]) >= 4
        expected_flags = {
            "THICKNESS_BELOW_MIN",
            "AGE_CONTRAINDICATED",
            "MATERIAL_NOT_VALIDATED",
            "SAFETY_FACTOR_LOW",
        }
        assert expected_flags.issubset(set(result["flags"]))

    def test_result_contains_classification(self, rag):
        result = rag.check_design_compliance(_valid_params())
        assert "classification" in result

    def test_result_contains_recommendations(self, rag):
        result = rag.check_design_compliance(_valid_params())
        assert len(result["recommendations"]) > 0


# ---------------------------------------------------------------------------
# 12-13. ComplianceRAG.get_design_constraints()
# ---------------------------------------------------------------------------
class TestGetDesignConstraints:
    # 12. Valid preset returns valid constraints dict
    @pytest.mark.parametrize("preset_key", [
        "mild_bilateral",
        "moderate_bilateral",
        "severe_equinus",
        "unilateral_mild",
    ])
    def test_valid_preset_returns_constraints(self, rag, preset_key):
        result = rag.get_design_constraints(preset_key, age=6, weight_kg=20.0)
        assert "error" not in result
        assert "preset" in result
        assert "afo_type" in result
        assert "ankle_target_deg" in result
        assert "wall_thickness_mm" in result
        assert "dynamic_load_n" in result
        assert "safety_factor" in result
        assert result["safety_factor"] >= 3.0

    def test_constraints_dynamic_load_calculated(self, rag):
        result = rag.get_design_constraints("mild_bilateral", age=6, weight_kg=25.0)
        # dynamic_load_n = weight_kg * 9.81 * 1.5
        expected = round(25.0 * 9.81 * 1.5, 1)
        assert result["dynamic_load_n"] == expected

    def test_constraints_growth_accommodation_young(self, rag):
        result = rag.get_design_constraints("mild_bilateral", age=5, weight_kg=18.0)
        assert result["growth_accommodation_mm"] == 5.0
        assert result["replacement_interval_months"] == 6

    def test_constraints_growth_accommodation_older(self, rag):
        result = rag.get_design_constraints("mild_bilateral", age=10, weight_kg=35.0)
        assert result["growth_accommodation_mm"] == 3.0
        assert result["replacement_interval_months"] == 12

    def test_constraints_material_recommendation_light(self, rag):
        result = rag.get_design_constraints("mild_bilateral", age=5, weight_kg=18.0)
        assert result["material_recommendation"] == "petg"

    def test_constraints_material_recommendation_heavy(self, rag):
        result = rag.get_design_constraints("mild_bilateral", age=10, weight_kg=35.0)
        assert result["material_recommendation"] == "nylon_pa12"

    # 13. Invalid preset returns error
    def test_invalid_preset_returns_error(self, rag):
        result = rag.get_design_constraints("nonexistent_preset", age=6, weight_kg=20.0)
        assert "error" in result
        assert "nonexistent_preset" in result["error"]
