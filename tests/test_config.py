"""
Unit tests for OrthoBraceForge configuration module.

Covers path constants, clinical presets, material specs, anthropometric data,
FEA defaults, timeout constants, and critical safety flags.
"""
import pytest
from pathlib import Path

from config import (
    BASE_DIR,
    USER_DATA,
    ASSETS_DIR,
    RAG_DATA_DIR,
    THEMES_DIR,
    ICONS_DIR,
    DB_PATH,
    EXPORT_DIR,
    APP_NAME,
    APP_VERSION,
    APP_CLASSIFICATION,
    REGULATORY_BANNER,
    ToeWalkingPreset,
    TOE_WALKING_PRESETS,
    MaterialSpec,
    MATERIALS,
    PEDIATRIC_ANTHRO,
    FEADefaults,
    FEA_DEFAULTS,
    OPENSCAD_TIMEOUT_SEC,
    BUILD123D_TIMEOUT_SEC,
    OCTOPRINT_CONNECT_TIMEOUT_SEC,
    AFO_LENGTH_MIN_MM,
    AFO_LENGTH_MAX_MM,
    AFO_HEIGHT_MIN_MM,
    AFO_HEIGHT_MAX_MM,
    MAX_AGENT_ITERATIONS,
    VLM_CRITIQUE_MAX_ROUNDS,
    HUMAN_REVIEW_REQUIRED,
    PREFERRED_CAD_ENGINE,
)


# ── Path constants ──────────────────────────────────────────────────────────

class TestPathConstants:
    """All directory/file path constants must be pathlib.Path instances."""

    @pytest.mark.parametrize("path_obj", [
        BASE_DIR,
        USER_DATA,
        ASSETS_DIR,
        RAG_DATA_DIR,
        THEMES_DIR,
        ICONS_DIR,
        DB_PATH,
        EXPORT_DIR,
    ])
    def test_paths_are_path_objects(self, path_obj):
        assert isinstance(path_obj, Path)

    def test_base_dir_is_absolute(self):
        assert BASE_DIR.is_absolute()

    def test_assets_dir_under_base(self):
        assert str(ASSETS_DIR).startswith(str(BASE_DIR))

    def test_db_path_has_db_suffix(self):
        assert DB_PATH.suffix == ".db"


# ── Application metadata ───────────────────────────────────────────────────

class TestAppMetadata:

    def test_app_name(self):
        assert APP_NAME == "OrthoBraceForge"

    def test_app_version_format(self):
        parts = APP_VERSION.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)

    def test_classification_is_nonempty(self):
        assert len(APP_CLASSIFICATION) > 0

    def test_regulatory_banner_mentions_fda(self):
        assert "FDA" in REGULATORY_BANNER


# ── Toe Walking Presets ─────────────────────────────────────────────────────

EXPECTED_PRESET_KEYS = {"mild_bilateral", "moderate_bilateral", "severe_equinus", "unilateral_mild"}
VALID_AFO_TYPES = {"solid", "hinged", "posterior_leaf_spring"}
VALID_TRIM_LINES = {"full", "medial_trim", "lateral_trim"}


class TestToeWalkingPresets:

    def test_all_expected_presets_exist(self):
        assert set(TOE_WALKING_PRESETS.keys()) == EXPECTED_PRESET_KEYS

    @pytest.mark.parametrize("key", EXPECTED_PRESET_KEYS)
    def test_preset_is_correct_type(self, key):
        assert isinstance(TOE_WALKING_PRESETS[key], ToeWalkingPreset)

    @pytest.mark.parametrize("key", EXPECTED_PRESET_KEYS)
    def test_preset_thickness_positive(self, key):
        assert TOE_WALKING_PRESETS[key].thickness_mm > 0

    @pytest.mark.parametrize("key", EXPECTED_PRESET_KEYS)
    def test_preset_afotype_valid(self, key):
        assert TOE_WALKING_PRESETS[key].afotype in VALID_AFO_TYPES

    @pytest.mark.parametrize("key", EXPECTED_PRESET_KEYS)
    def test_preset_trim_line_valid(self, key):
        assert TOE_WALKING_PRESETS[key].trim_line in VALID_TRIM_LINES

    @pytest.mark.parametrize("key", EXPECTED_PRESET_KEYS)
    def test_preset_name_nonempty(self, key):
        assert len(TOE_WALKING_PRESETS[key].name) > 0


# ── Material specifications ─────────────────────────────────────────────────

EXPECTED_MATERIAL_KEYS = {"petg", "nylon_pa12", "tpu_95a", "ti6al4v_lattice"}


class TestMaterials:

    def test_all_expected_materials_exist(self):
        assert set(MATERIALS.keys()) == EXPECTED_MATERIAL_KEYS

    @pytest.mark.parametrize("key", EXPECTED_MATERIAL_KEYS)
    def test_material_is_correct_type(self, key):
        assert isinstance(MATERIALS[key], MaterialSpec)

    @pytest.mark.parametrize("key", EXPECTED_MATERIAL_KEYS)
    def test_material_is_biocompatible(self, key):
        assert MATERIALS[key].iso_10993_biocompat is True

    @pytest.mark.parametrize("key", EXPECTED_MATERIAL_KEYS)
    def test_material_suitable_for_pediatric(self, key):
        assert MATERIALS[key].suitable_for_pediatric is True

    @pytest.mark.parametrize("key", EXPECTED_MATERIAL_KEYS)
    def test_material_tensile_strength_positive(self, key):
        assert MATERIALS[key].tensile_strength_mpa > 0

    @pytest.mark.parametrize("key", EXPECTED_MATERIAL_KEYS)
    def test_material_flexural_modulus_positive(self, key):
        assert MATERIALS[key].flexural_modulus_mpa > 0

    @pytest.mark.parametrize("key", EXPECTED_MATERIAL_KEYS)
    def test_material_layer_height_positive(self, key):
        assert MATERIALS[key].layer_height_mm > 0

    @pytest.mark.parametrize("key", EXPECTED_MATERIAL_KEYS)
    def test_material_infill_in_range(self, key):
        assert 0 < MATERIALS[key].infill_pct <= 100


# ── Pediatric anthropometric data ──────────────────────────────────────────

class TestPediatricAnthro:

    def test_covers_ages_2_through_12(self):
        expected_ages = set(range(2, 13))
        assert set(PEDIATRIC_ANTHRO.keys()) == expected_ages

    @pytest.mark.parametrize("age", range(2, 13))
    def test_tuple_has_four_elements(self, age):
        assert len(PEDIATRIC_ANTHRO[age]) == 4

    @pytest.mark.parametrize("age", range(2, 13))
    def test_min_less_than_max_foot_length(self, age):
        fl_min, fl_max, _, _ = PEDIATRIC_ANTHRO[age]
        assert fl_min < fl_max

    @pytest.mark.parametrize("age", range(2, 13))
    def test_min_less_than_max_ankle_width(self, age):
        _, _, aw_min, aw_max = PEDIATRIC_ANTHRO[age]
        assert aw_min < aw_max

    @pytest.mark.parametrize("age", range(2, 13))
    def test_all_values_positive(self, age):
        assert all(v > 0 for v in PEDIATRIC_ANTHRO[age])

    def test_foot_length_min_increases_with_age(self):
        ages = sorted(PEDIATRIC_ANTHRO.keys())
        mins = [PEDIATRIC_ANTHRO[a][0] for a in ages]
        assert mins == sorted(mins)
        # strictly increasing
        assert len(set(mins)) == len(mins)

    def test_foot_length_max_increases_with_age(self):
        ages = sorted(PEDIATRIC_ANTHRO.keys())
        maxs = [PEDIATRIC_ANTHRO[a][1] for a in ages]
        assert maxs == sorted(maxs)
        assert len(set(maxs)) == len(maxs)

    def test_ankle_width_min_increases_with_age(self):
        ages = sorted(PEDIATRIC_ANTHRO.keys())
        mins = [PEDIATRIC_ANTHRO[a][2] for a in ages]
        assert mins == sorted(mins)
        assert len(set(mins)) == len(mins)

    def test_ankle_width_max_increases_with_age(self):
        ages = sorted(PEDIATRIC_ANTHRO.keys())
        maxs = [PEDIATRIC_ANTHRO[a][3] for a in ages]
        assert maxs == sorted(maxs)
        assert len(set(maxs)) == len(maxs)


# ── FEA defaults ────────────────────────────────────────────────────────────

class TestFEADefaults:

    def test_fea_defaults_is_instance(self):
        assert isinstance(FEA_DEFAULTS, FEADefaults)

    def test_safety_factor_meets_regulatory_minimum(self):
        """Pediatric devices require a safety factor of at least 3.0."""
        assert FEA_DEFAULTS.safety_factor >= 3.0

    def test_body_weight_multiplier_greater_than_one(self):
        assert FEA_DEFAULTS.body_weight_multiplier > 1.0

    def test_cycle_target_positive(self):
        assert FEA_DEFAULTS.cycle_target > 0

    def test_max_von_mises_pct_in_range(self):
        assert 0 < FEA_DEFAULTS.max_von_mises_pct <= 100


# ── Timeout constants ───────────────────────────────────────────────────────

class TestTimeoutConstants:

    @pytest.mark.parametrize("timeout_val", [
        OPENSCAD_TIMEOUT_SEC,
        BUILD123D_TIMEOUT_SEC,
        OCTOPRINT_CONNECT_TIMEOUT_SEC,
    ])
    def test_timeout_is_positive_integer(self, timeout_val):
        assert isinstance(timeout_val, int)
        assert timeout_val > 0


# ── AFO geometry bounds ─────────────────────────────────────────────────────

class TestAFOGeometryBounds:

    def test_length_min_less_than_max(self):
        assert AFO_LENGTH_MIN_MM < AFO_LENGTH_MAX_MM

    def test_height_min_less_than_max(self):
        assert AFO_HEIGHT_MIN_MM < AFO_HEIGHT_MAX_MM

    @pytest.mark.parametrize("val", [
        AFO_LENGTH_MIN_MM,
        AFO_LENGTH_MAX_MM,
        AFO_HEIGHT_MIN_MM,
        AFO_HEIGHT_MAX_MM,
    ])
    def test_geometry_bounds_positive(self, val):
        assert val > 0


# ── Critical safety flag ────────────────────────────────────────────────────

class TestSafetyFlags:

    def test_human_review_required_is_true(self):
        """
        HUMAN_REVIEW_REQUIRED must be True in production.
        This is a critical safety check: all device outputs must be reviewed
        by a licensed clinician before clinical use.
        """
        assert HUMAN_REVIEW_REQUIRED is True


# ── Agent orchestration settings ────────────────────────────────────────────

class TestAgentConfig:

    def test_max_agent_iterations_positive(self):
        assert isinstance(MAX_AGENT_ITERATIONS, int)
        assert MAX_AGENT_ITERATIONS > 0

    def test_vlm_critique_max_rounds_positive(self):
        assert isinstance(VLM_CRITIQUE_MAX_ROUNDS, int)
        assert VLM_CRITIQUE_MAX_ROUNDS > 0

    def test_preferred_cad_engine_is_known(self):
        allowed = {"build123d", "openscad", "chat_to_stl"}
        assert PREFERRED_CAD_ENGINE in allowed
