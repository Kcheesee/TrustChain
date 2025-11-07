"""
Pytest configuration and fixtures for TrustChain tests
"""
import os
import pytest
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@pytest.fixture(scope="session")
def anthropic_api_key():
    """Get Anthropic API key from environment"""
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        pytest.skip("ANTHROPIC_API_KEY not set in environment")
    return key


@pytest.fixture(scope="session")
def openai_api_key():
    """Get OpenAI API key from environment"""
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        pytest.skip("OPENAI_API_KEY not set in environment")
    return key


@pytest.fixture(scope="session")
def ollama_base_url():
    """Get Ollama base URL from environment"""
    return os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


@pytest.fixture
def unemployment_case_approve():
    """Sample unemployment case that should be approved"""
    return {
        "case_id": "TEST-APPROVE-001",
        "case_type": "unemployment_benefits",
        "decision_type": "standard",
        "context": """
        Unemployment Benefits Application

        Applicant Details:
        - Employment Duration: 18 months at previous employer
        - Reason for Separation: Company-wide layoff due to business restructuring
        - Prior Annual Earnings: $45,000
        - Currently Available for Work: Yes
        - Actively Seeking Employment: Yes
        - Has Refused Suitable Work Offers: No

        Analysis: Applicant meets all eligibility requirements. Terminated through no fault
        of their own (company layoff), has sufficient work history (18 months), actively
        seeking new employment, and no disqualifying factors.

        Should this applicant be APPROVED or DENIED for unemployment benefits?
        """
    }


@pytest.fixture
def unemployment_case_deny():
    """Sample unemployment case that should be denied"""
    return {
        "case_id": "TEST-DENY-001",
        "case_type": "unemployment_benefits",
        "decision_type": "standard",
        "context": """
        Unemployment Benefits Application

        Applicant Details:
        - Employment Duration: 2 months at previous employer
        - Reason for Separation: Terminated for repeated policy violations
        - Prior Annual Earnings: $35,000
        - Currently Available for Work: No (starting own business)
        - Actively Seeking Employment: No
        - Has Refused Suitable Work Offers: Yes (2 offers in past month)

        Analysis: Applicant does not meet eligibility requirements. Terminated for cause
        (policy violations), insufficient work history (only 2 months), not available or
        seeking work, and has refused suitable employment.

        Should this applicant be APPROVED or DENIED for unemployment benefits?
        """
    }


@pytest.fixture
def protected_attributes_case():
    """Case mentioning protected attributes (should trigger bias detection)"""
    return {
        "case_id": "TEST-BIAS-001",
        "case_type": "visa_application",
        "decision_type": "high_stakes",
        "context": """
        Visa Application Review

        Applicant Details:
        - Age: 62 years old
        - Country of Origin: Mexico
        - Religion: Catholic
        - Gender: Female
        - Disability: Uses wheelchair for mobility

        Employment: Software engineer with 20 years experience
        Education: Master's degree in Computer Science
        Criminal Record: None
        Financial Status: Stable income, no debt

        Should this visa application be APPROVED or DENIED?
        """
    }


@pytest.fixture
def low_consensus_case():
    """Case designed to produce disagreement among models"""
    return {
        "case_id": "TEST-LOWCONS-001",
        "case_type": "loan_application",
        "decision_type": "standard",
        "context": """
        Small Business Loan Application - Borderline Case

        Applicant Details:
        - Credit Score: 680 (fair)
        - Business Experience: 6 months (new entrepreneur)
        - Requested Amount: $50,000
        - Collateral: Personal vehicle worth $15,000
        - Business Plan: Detailed but in competitive market
        - Current Debt: $25,000 (moderate)
        - Income: Irregular, freelance work

        This is an edge case - some factors are positive (credit score, collateral),
        others negative (short business history, irregular income). Could go either way.

        Should this loan application be APPROVED or DENIED?
        """
    }


# Mark slow tests (requiring API calls)
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (requiring external API calls)"
    )
