"""
TrustChain Phase 5: Counterfactual Fairness Testing

Tests for the counterfactual generator and fairness analyzer.

Built with care by Kareem & Claude
"""

import pytest
from analyzers.counterfactual_generator import (
    CounterfactualGenerator,
    Counterfactual,
    CounterfactualModification,
    ProtectedAttribute,
)
from analyzers.counterfactual_fairness import (
    CounterfactualFairnessAnalyzer,
    BiasStrength,
)


# ============================================================================
# CounterfactualGenerator Tests
# ============================================================================

class TestCounterfactualGenerator:
    """Test CounterfactualGenerator functionality."""

    def test_init_default(self):
        """Test default initialization."""
        generator = CounterfactualGenerator()
        assert generator.config == {}

    def test_init_with_seed(self):
        """Test initialization with random seed for reproducibility."""
        generator = CounterfactualGenerator(config={"random_seed": 42})
        assert generator._random_seed == 42


class TestNameCounterfactuals:
    """Test name-based counterfactual generation."""

    def test_generate_name_counterfactuals(self):
        """Test that name counterfactuals are generated correctly."""
        generator = CounterfactualGenerator(config={"random_seed": 42})

        input_data = {
            "name": "Jamal Washington",
            "email": "jamal.w@email.com",
            "location": "Detroit, MI",
            "resume_text": "Jamal has 8 years of experience..."
        }

        counterfactuals = generator.generate_name_counterfactuals(input_data)

        # Should generate 3 counterfactuals (one for each other race category)
        assert len(counterfactuals) == 3

        # Each should have name modification
        for cf in counterfactuals:
            assert cf.modification_method == "name_swap"
            assert len(cf.modifications) == 1
            assert cf.modifications[0].attribute == ProtectedAttribute.NAME
            assert cf.modified_input["name"] != "Jamal Washington"

    def test_name_counterfactual_replaces_in_text(self):
        """Test that name is replaced in text fields too."""
        generator = CounterfactualGenerator(config={"random_seed": 42})

        input_data = {
            "name": "Jamal Washington",
            "resume_text": "Jamal has led multiple teams. Jamal's skills include..."
        }

        counterfactuals = generator.generate_name_counterfactuals(input_data)
        assert len(counterfactuals) > 0

        cf = counterfactuals[0]
        new_first_name = cf.modified_input["name"].split()[0]

        # Check that old name is NOT in the text
        assert "Jamal" not in cf.modified_input["resume_text"]
        # Check that new name IS in the text
        assert new_first_name in cf.modified_input["resume_text"]

    def test_name_counterfactual_updates_email(self):
        """Test that email is updated to match new name."""
        generator = CounterfactualGenerator(config={"random_seed": 42})

        input_data = {
            "name": "Jamal Washington",
            "email": "jamal.w@email.com",
        }

        counterfactuals = generator.generate_name_counterfactuals(input_data)

        for cf in counterfactuals:
            # Email should be updated (not contain "jamal")
            assert "jamal" not in cf.modified_input["email"].lower()

    def test_no_name_no_counterfactuals(self):
        """Test that no counterfactuals are generated without a name."""
        generator = CounterfactualGenerator()

        input_data = {
            "location": "Detroit, MI",
            "experience": "8 years"
        }

        counterfactuals = generator.generate_name_counterfactuals(input_data)
        assert len(counterfactuals) == 0


class TestGenderCounterfactuals:
    """Test gender-based counterfactual generation."""

    def test_generate_gender_counterfactuals_male(self):
        """Test gender pronoun swapping from male."""
        generator = CounterfactualGenerator()

        input_data = {
            "name": "John Smith",
            "resume_text": "He has excellent leadership skills. His team delivered on time."
        }

        counterfactuals = generator.generate_gender_counterfactuals(input_data)

        # Should generate 2 counterfactuals (female and neutral)
        assert len(counterfactuals) == 2

        # Find female version
        female_cf = next(
            (cf for cf in counterfactuals if "female" in cf.counterfactual_id),
            None
        )
        assert female_cf is not None
        # Check for "she" and "her/hers" (case insensitive, may be at start of sentence)
        text_lower = female_cf.modified_input["resume_text"].lower()
        assert "she " in text_lower or " she " in text_lower
        # "her" or "hers" should be present (hers is used as possessive replacement for "his")
        assert "her" in text_lower

    def test_generate_gender_counterfactuals_female(self):
        """Test gender pronoun swapping from female."""
        generator = CounterfactualGenerator()

        input_data = {
            "name": "Jane Smith",
            "resume_text": "She has excellent leadership skills. Her team delivered."
        }

        counterfactuals = generator.generate_gender_counterfactuals(input_data)

        # Should generate 2 counterfactuals (male and neutral)
        assert len(counterfactuals) == 2

        # Find male version
        male_cf = next(
            (cf for cf in counterfactuals if "male" in cf.counterfactual_id),
            None
        )
        assert male_cf is not None

    def test_no_gender_indicators_no_counterfactuals(self):
        """Test that neutral text generates no gender counterfactuals."""
        generator = CounterfactualGenerator()

        input_data = {
            "name": "Alex Smith",
            "skills": ["Python", "JavaScript"]
        }

        # This should not have gender indicators
        assert not generator._has_gender_indicators(input_data)


class TestLocationCounterfactuals:
    """Test location-based counterfactual generation."""

    def test_generate_location_counterfactual_low_to_high(self):
        """Test swapping from low SES location to high SES."""
        generator = CounterfactualGenerator(config={"random_seed": 42})

        input_data = {
            "location": "Detroit, MI"
        }

        cf = generator.generate_location_counterfactual(input_data)

        assert cf is not None
        assert cf.modification_method == "location_swap"
        assert cf.modified_input["location"] != "Detroit, MI"
        # Should swap to high SES location
        high_ses = generator.LOCATIONS_BY_PROXY["high_ses"]
        assert cf.modified_input["location"] in high_ses

    def test_generate_location_counterfactual_high_to_low(self):
        """Test swapping from high SES location to low SES."""
        generator = CounterfactualGenerator(config={"random_seed": 42})

        input_data = {
            "location": "Palo Alto, CA"
        }

        cf = generator.generate_location_counterfactual(input_data)

        assert cf is not None
        # Should swap to low SES location
        low_ses = generator.LOCATIONS_BY_PROXY["low_ses"]
        assert cf.modified_input["location"] in low_ses

    def test_no_location_no_counterfactual(self):
        """Test that no counterfactual is generated without location."""
        generator = CounterfactualGenerator()

        input_data = {
            "name": "John Smith"
        }

        cf = generator.generate_location_counterfactual(input_data)
        assert cf is None


class TestUniversityCounterfactuals:
    """Test university prestige counterfactual generation."""

    def test_generate_university_counterfactual_low_to_elite(self):
        """Test swapping from low prestige to elite university."""
        generator = CounterfactualGenerator(config={"random_seed": 42})

        input_data = {
            "university": "Wayne State University"
        }

        cf = generator.generate_university_counterfactual(input_data)

        assert cf is not None
        assert cf.modification_method == "university_swap"
        assert cf.modified_input["university"] != "Wayne State University"
        # Should swap to elite
        elite = generator.UNIVERSITIES_BY_PRESTIGE["elite"]
        assert cf.modified_input["university"] in elite

    def test_generate_university_counterfactual_elite_to_low(self):
        """Test swapping from elite to low prestige university."""
        generator = CounterfactualGenerator(config={"random_seed": 42})

        input_data = {
            "university": "Harvard University"
        }

        cf = generator.generate_university_counterfactual(input_data)

        assert cf is not None
        # Should swap to low
        low = generator.UNIVERSITIES_BY_PRESTIGE["low"]
        assert cf.modified_input["university"] in low

    def test_university_from_education_field(self):
        """Test extracting university from education field."""
        generator = CounterfactualGenerator(config={"random_seed": 42})

        input_data = {
            "education": [
                {"school": "Wayne State University", "degree": "BS Computer Science"}
            ]
        }

        cf = generator.generate_university_counterfactual(input_data)
        assert cf is not None


class TestGenerateAll:
    """Test generate_all method."""

    def test_generate_all_with_full_input(self):
        """Test generating all counterfactuals for comprehensive input."""
        generator = CounterfactualGenerator(config={"random_seed": 42})

        input_data = {
            "name": "Jamal Washington",
            "email": "jamal.w@email.com",
            "location": "Detroit, MI",
            "university": "Wayne State University",
            "resume_text": "He has 8 years of experience. His expertise includes..."
        }

        counterfactuals = generator.generate_all(input_data)

        # Should have name (3) + gender (2) + location (1) + university (1) = 7
        assert len(counterfactuals) >= 5  # At least these many

        # Check we have each type
        methods = [cf.modification_method for cf in counterfactuals]
        assert "name_swap" in methods
        assert "gender_swap" in methods
        assert "location_swap" in methods
        assert "university_swap" in methods

    def test_generate_all_minimal_input(self):
        """Test with minimal input that has few protected attributes."""
        generator = CounterfactualGenerator()

        input_data = {
            "experience": "8 years",
            "skills": ["Python", "AWS"]
        }

        counterfactuals = generator.generate_all(input_data)
        # Should be empty or minimal
        assert len(counterfactuals) == 0


# ============================================================================
# Inference Helper Tests
# ============================================================================

class TestInference:
    """Test inference helper methods."""

    def test_infer_perceived_race_black(self):
        """Test inferring race from typically Black names."""
        generator = CounterfactualGenerator()

        assert generator._infer_perceived_race("Jamal Washington") == "likely_black"
        assert generator._infer_perceived_race("Lakisha Brown") == "likely_black"

    def test_infer_perceived_race_white(self):
        """Test inferring race from typically white names."""
        generator = CounterfactualGenerator()

        assert generator._infer_perceived_race("Brad Thompson") == "likely_white"
        assert generator._infer_perceived_race("Emily Anderson") == "likely_white"

    def test_infer_perceived_race_hispanic(self):
        """Test inferring race from typically Hispanic names."""
        generator = CounterfactualGenerator()

        assert generator._infer_perceived_race("Carlos Garcia") == "likely_hispanic"
        assert generator._infer_perceived_race("Maria Rodriguez") == "likely_hispanic"

    def test_infer_perceived_race_asian(self):
        """Test inferring race from typically Asian names."""
        generator = CounterfactualGenerator()

        assert generator._infer_perceived_race("Wei Li") == "likely_asian"
        assert generator._infer_perceived_race("Raj Patel") == "likely_asian"

    def test_infer_gender_from_pronouns(self):
        """Test inferring gender from pronouns in text."""
        generator = CounterfactualGenerator()

        male_data = {"text": "He has great skills. His work is excellent."}
        assert generator._infer_gender_from_text(male_data) == "male"

        female_data = {"text": "She has great skills. Her work is excellent."}
        assert generator._infer_gender_from_text(female_data) == "female"

    def test_infer_ses_from_location(self):
        """Test inferring SES from location."""
        generator = CounterfactualGenerator()

        assert generator._infer_ses_from_location("Detroit, MI") == "low_ses"
        assert generator._infer_ses_from_location("Palo Alto, CA") == "high_ses"
        assert generator._infer_ses_from_location("Austin, TX") == "middle_ses"


# ============================================================================
# CounterfactualFairnessAnalyzer Tests
# ============================================================================

class TestCounterfactualFairnessAnalyzer:
    """Test CounterfactualFairnessAnalyzer."""

    def test_init_default(self):
        """Test default initialization."""
        analyzer = CounterfactualFairnessAnalyzer()

        assert analyzer.name == "counterfactual_fairness"
        assert analyzer.flip_threshold == 0.15
        assert analyzer.fairness_threshold == 0.7

    def test_init_custom_thresholds(self):
        """Test initialization with custom thresholds."""
        analyzer = CounterfactualFairnessAnalyzer(config={
            "flip_threshold": 0.1,
            "fairness_threshold": 0.8
        })

        assert analyzer.flip_threshold == 0.1
        assert analyzer.fairness_threshold == 0.8

    def test_validate_config_valid(self):
        """Test config validation with valid values."""
        analyzer = CounterfactualFairnessAnalyzer()

        assert analyzer.validate_config({"flip_threshold": 0.5}) is True
        assert analyzer.validate_config({"fairness_threshold": 0.9}) is True

    def test_validate_config_invalid(self):
        """Test config validation with invalid values."""
        analyzer = CounterfactualFairnessAnalyzer()

        with pytest.raises(ValueError):
            analyzer.validate_config({"flip_threshold": 1.5})

        with pytest.raises(ValueError):
            analyzer.validate_config({"fairness_threshold": -0.1})

    def test_sync_analyze_returns_warning(self):
        """Test that sync analyze returns async warning."""
        analyzer = CounterfactualFairnessAnalyzer()

        # Create minimal mock strategy result
        from core.result import StrategyResult, DecisionOutcome
        mock_result = StrategyResult(
            strategy_name="test",
            decision=DecisionOutcome.APPROVED,
            confidence=0.8,
            reasoning="Test reasoning"
        )

        result = analyzer.analyze(mock_result, {}, {})

        assert result.passed is True
        assert len(result.warnings) > 0
        assert "async" in result.warnings[0].lower()


class TestBiasStrength:
    """Test BiasStrength enum."""

    def test_bias_strength_values(self):
        """Test that all expected bias strength values exist."""
        assert BiasStrength.NONE.value == "none"
        assert BiasStrength.WEAK.value == "weak"
        assert BiasStrength.MODERATE.value == "moderate"
        assert BiasStrength.STRONG.value == "strong"


class TestProtectedAttribute:
    """Test ProtectedAttribute enum."""

    def test_protected_attribute_values(self):
        """Test that all expected protected attributes exist."""
        assert ProtectedAttribute.NAME.value == "name"
        assert ProtectedAttribute.GENDER.value == "gender"
        assert ProtectedAttribute.RACE.value == "race"
        assert ProtectedAttribute.AGE.value == "age"
        assert ProtectedAttribute.LOCATION.value == "location"


# ============================================================================
# Integration Tests (require mocking TrustChain)
# ============================================================================

class TestIntegration:
    """Integration tests - these test the full pipeline."""

    @pytest.mark.asyncio
    async def test_analyzer_without_trustchain(self):
        """Test analyzer handles missing TrustChain gracefully."""
        from core.result import StrategyResult, DecisionOutcome

        analyzer = CounterfactualFairnessAnalyzer()

        mock_result = StrategyResult(
            strategy_name="test",
            decision=DecisionOutcome.DENIED,
            confidence=0.72,
            reasoning="Test"
        )

        input_data = {
            "name": "Jamal Washington",
            "location": "Detroit, MI"
        }

        # Without trustchain_instance
        result = await analyzer.analyze_async(
            mock_result, input_data, {},
            trustchain_instance=None
        )

        assert result.passed is True
        assert len(result.warnings) > 0  # Should warn about no TrustChain
