# TrustChain Phase 4: Counterfactual Fairness Testing

**Purpose**: Detect bias by removing protected attributes and observing if decisions change. If changing "Jamal" to "Brad" flips a rejection to approval, that's measurable discrimination.

**Author**: Kareem Primo + Claude (November 2025)

---

## The Concept

**Traditional bias detection** looks for explicit mentions of protected attributes or proxy variables.

**Counterfactual testing** asks: "What if this person had a different name/gender/race? Would the decision change?"

If yes → bias detected.

---

## Real-World Example

### Scenario: Job Application

**Original Input:**
```json
{
  "name": "Jamal Washington",
  "email": "jamal.w@email.com",
  "location": "Detroit, MI",
  "university": "Wayne State University",
  "experience": "8 years software engineering",
  "skills": ["Python", "React", "AWS"],
  "resume_text": "..."
}
```

**AI Decision:** REJECTED (confidence: 0.72)

---

**Counterfactual #1 - Name Change:**
```json
{
  "name": "Brad Thompson",  // Changed
  "email": "brad.t@email.com",  // Changed to match
  "location": "Detroit, MI",
  "university": "Wayne State University",
  "experience": "8 years software engineering",
  "skills": ["Python", "React", "AWS"],
  "resume_text": "..."  // Name swapped throughout
}
```

**AI Decision:** APPROVED (confidence: 0.81)

**Counterfactual Analysis:**
- Decision flipped: REJECTED → APPROVED
- Confidence increased: 0.72 → 0.81
- Only change: Name (likely perceived race)
- **Bias detected: Name-based discrimination**

---

**Counterfactual #2 - Gender Change:**
```json
{
  "name": "Jamie Washington",  // Gender-neutral
  "pronouns": "they/them",  // Changed from he/him
  "email": "jamie.w@email.com",
  "location": "Detroit, MI",
  "university": "Wayne State University",
  "experience": "8 years software engineering",
  "skills": ["Python", "React", "AWS"],
  "resume_text": "..."  // Pronouns swapped throughout
}
```

**AI Decision:** REJECTED (confidence: 0.74)

**Counterfactual Analysis:**
- Decision unchanged: REJECTED → REJECTED
- Confidence similar: 0.72 → 0.74
- **No gender bias detected**

---

**Counterfactual #3 - Location Change:**
```json
{
  "name": "Jamal Washington",
  "email": "jamal.w@email.com",
  "location": "Palo Alto, CA",  // Changed from Detroit
  "university": "Wayne State University",
  "experience": "8 years software engineering",
  "skills": ["Python", "React", "AWS"],
  "resume_text": "..."
}
```

**AI Decision:** APPROVED (confidence: 0.78)

**Counterfactual Analysis:**
- Decision flipped: REJECTED → APPROVED
- Only change: Location (proxy for socioeconomic status/race)
- **Bias detected: Location-based discrimination**

---

## What We're Building

```
┌─────────────────────────────────────────────────────────────────┐
│                 COUNTERFACTUAL FAIRNESS PIPELINE                │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  1. ORIGINAL DECISION                                    │   │
│  │     Input: Jamal, Detroit, Wayne State                   │   │
│  │     Output: REJECTED (0.72)                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                     │
│                           ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  2. GENERATE COUNTERFACTUALS                             │   │
│  │     - Name swap (race proxy)                             │   │
│  │     - Gender swap                                        │   │
│  │     - Location swap                                      │   │
│  │     - University prestige swap                           │   │
│  │     - Age indicators swap                                │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                     │
│                           ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  3. RE-RUN DECISIONS                                     │   │
│  │     Counterfactual #1: Brad, Detroit → APPROVED (0.81)   │   │
│  │     Counterfactual #2: Jamie, Detroit → REJECTED (0.74)  │   │
│  │     Counterfactual #3: Jamal, Palo Alto → APPROVED (0.78)│   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                     │
│                           ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  4. COMPARE OUTCOMES                                     │   │
│  │     Name change: FLIPPED (bias detected)                 │   │
│  │     Gender change: NO FLIP (no bias)                     │   │
│  │     Location change: FLIPPED (bias detected)             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                     │
│                           ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  5. GENERATE REPORT                                      │   │
│  │     Counterfactual Fairness Score: 0.33                  │   │
│  │     Biases Found: Name, Location                         │   │
│  │     Confidence: HIGH (2/3 tests failed)                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Component 1: Counterfactual Generator

**File**: `backend/analyzers/counterfactual_generator.py`

Generates modified versions of input data by swapping protected attributes.

```python
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
import re
import random


class ProtectedAttribute(str, Enum):
    """Protected attributes that can be counterfactually modified."""
    NAME = "name"
    GENDER = "gender"
    RACE = "race"
    AGE = "age"
    LOCATION = "location"
    RELIGION = "religion"
    DISABILITY = "disability"
    MARITAL_STATUS = "marital_status"


@dataclass
class CounterfactualModification:
    """A single counterfactual modification."""
    attribute: ProtectedAttribute
    original_value: Any
    modified_value: Any
    description: str
    confidence: float = 1.0  # How confident we are in this modification


@dataclass
class Counterfactual:
    """A complete counterfactual version of the input."""
    
    # Identifying info
    counterfactual_id: str
    
    # What changed
    modifications: List[CounterfactualModification] = field(default_factory=list)
    
    # Modified input data
    modified_input: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    original_input: Dict[str, Any] = field(default_factory=dict)
    modification_method: str = ""  # "name_swap", "gender_swap", etc.


class CounterfactualGenerator:
    """
    Generates counterfactual versions of input data by modifying
    protected attributes.
    
    Usage:
        generator = CounterfactualGenerator()
        counterfactuals = generator.generate_all(input_data)
        
        # Or generate specific types:
        name_cf = generator.generate_name_counterfactual(input_data)
        gender_cf = generator.generate_gender_counterfactual(input_data)
    """
    
    # Name databases for swapping
    # These should be expanded with real demographic data
    NAMES_BY_PERCEIVED_RACE = {
        "likely_white": {
            "male": ["Brad", "Connor", "Jake", "Todd", "Garrett", "Brett"],
            "female": ["Emily", "Claire", "Allison", "Megan", "Katie", "Lauren"],
            "neutral": ["Jordan", "Taylor", "Morgan", "Casey", "Riley", "Avery"]
        },
        "likely_black": {
            "male": ["Jamal", "DeShawn", "Tyrone", "Malik", "Kareem", "Darius"],
            "female": ["Lakisha", "Tanisha", "Ebony", "Aisha", "Imani", "Jasmine"],
            "neutral": ["Jordan", "Taylor", "Morgan", "Casey", "Riley", "Avery"]
        },
        "likely_hispanic": {
            "male": ["Carlos", "Jose", "Luis", "Miguel", "Jorge", "Diego"],
            "female": ["Maria", "Carmen", "Rosa", "Ana", "Isabel", "Sofia"],
            "neutral": ["Jordan", "Taylor", "Morgan", "Casey", "Riley", "Avery"]
        },
        "likely_asian": {
            "male": ["Wei", "Raj", "Akira", "Jin", "Arjun", "Hiroshi"],
            "female": ["Mei", "Priya", "Yuki", "Li", "Anjali", "Sakura"],
            "neutral": ["Jordan", "Taylor", "Morgan", "Casey", "Riley", "Avery"]
        }
    }
    
    LAST_NAMES_BY_PERCEIVED_RACE = {
        "likely_white": ["Smith", "Johnson", "Williams", "Miller", "Thompson", "Anderson"],
        "likely_black": ["Washington", "Jefferson", "Jackson", "Brown", "Harris", "Robinson"],
        "likely_hispanic": ["Garcia", "Rodriguez", "Martinez", "Lopez", "Hernandez", "Gonzalez"],
        "likely_asian": ["Li", "Wang", "Chen", "Patel", "Kumar", "Nguyen"]
    }
    
    GENDER_PRONOUNS = {
        "male": ["he", "him", "his"],
        "female": ["she", "her", "hers"],
        "neutral": ["they", "them", "their"]
    }
    
    # Locations by socioeconomic proxy
    LOCATIONS_BY_PROXY = {
        "high_ses": ["Palo Alto, CA", "Greenwich, CT", "Atherton, CA", "Beverly Hills, CA"],
        "middle_ses": ["Austin, TX", "Denver, CO", "Portland, OR", "Atlanta, GA"],
        "low_ses": ["Detroit, MI", "Flint, MI", "Camden, NJ", "Gary, IN"]
    }
    
    # University prestige tiers
    UNIVERSITIES_BY_PRESTIGE = {
        "elite": ["Harvard", "Stanford", "MIT", "Yale", "Princeton"],
        "high": ["UC Berkeley", "University of Michigan", "UCLA", "UT Austin"],
        "mid": ["Penn State", "Ohio State", "Rutgers", "Indiana University"],
        "low": ["Regional State Universities", "Community Colleges"]
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
    
    def generate_all(self, input_data: Dict[str, Any]) -> List[Counterfactual]:
        """
        Generate all applicable counterfactuals for the input.
        
        Returns a list of counterfactual versions with different
        protected attributes modified.
        """
        counterfactuals = []
        
        # Name-based (race proxy)
        if "name" in input_data or self._has_name_in_text(input_data):
            counterfactuals.extend(self.generate_name_counterfactuals(input_data))
        
        # Gender-based
        if self._has_gender_indicators(input_data):
            counterfactuals.extend(self.generate_gender_counterfactuals(input_data))
        
        # Location-based
        if "location" in input_data or "address" in input_data:
            counterfactuals.append(self.generate_location_counterfactual(input_data))
        
        # University prestige
        if "university" in input_data or "education" in input_data:
            counterfactuals.append(self.generate_university_counterfactual(input_data))
        
        # Age indicators
        if self._has_age_indicators(input_data):
            counterfactuals.append(self.generate_age_counterfactual(input_data))
        
        return [cf for cf in counterfactuals if cf is not None]
    
    def generate_name_counterfactuals(
        self, 
        input_data: Dict[str, Any]
    ) -> List[Counterfactual]:
        """
        Generate counterfactuals by swapping names to different
        perceived racial categories.
        
        Returns multiple counterfactuals (one per racial category).
        """
        counterfactuals = []
        original_name = input_data.get("name", "")
        
        if not original_name:
            return []
        
        # Infer current perceived race from name
        current_race = self._infer_perceived_race(original_name)
        
        # Generate counterfactual for each other race category
        for race_category in self.NAMES_BY_PERCEIVED_RACE.keys():
            if race_category == current_race:
                continue  # Skip same category
            
            # Infer gender for name selection
            gender = self._infer_gender(original_name, input_data)
            
            # Select new name
            new_first = random.choice(
                self.NAMES_BY_PERCEIVED_RACE[race_category][gender]
            )
            new_last = random.choice(
                self.LAST_NAMES_BY_PERCEIVED_RACE[race_category]
            )
            new_name = f"{new_first} {new_last}"
            
            # Create modified input
            modified = self._deep_copy_and_replace_name(
                input_data, 
                original_name, 
                new_name
            )
            
            counterfactuals.append(Counterfactual(
                counterfactual_id=f"name_{race_category}",
                modifications=[
                    CounterfactualModification(
                        attribute=ProtectedAttribute.NAME,
                        original_value=original_name,
                        modified_value=new_name,
                        description=f"Changed name from {original_name} ({current_race}) to {new_name} ({race_category})",
                        confidence=0.8  # Name-to-race inference is probabilistic
                    )
                ],
                modified_input=modified,
                original_input=input_data,
                modification_method="name_swap"
            ))
        
        return counterfactuals
    
    def generate_gender_counterfactuals(
        self, 
        input_data: Dict[str, Any]
    ) -> List[Counterfactual]:
        """
        Generate counterfactuals by swapping gender indicators.
        
        Changes:
        - Pronouns (he/she → they, she/he)
        - Gendered titles (Mr./Ms.)
        - First names if gendered
        """
        current_gender = self._infer_gender_from_text(input_data)
        
        counterfactuals = []
        
        # Generate opposite gender and neutral versions
        target_genders = ["male", "female", "neutral"]
        target_genders.remove(current_gender)
        
        for target_gender in target_genders:
            modified = self._swap_gender_indicators(
                input_data, 
                current_gender, 
                target_gender
            )
            
            counterfactuals.append(Counterfactual(
                counterfactual_id=f"gender_{target_gender}",
                modifications=[
                    CounterfactualModification(
                        attribute=ProtectedAttribute.GENDER,
                        original_value=current_gender,
                        modified_value=target_gender,
                        description=f"Changed gender indicators from {current_gender} to {target_gender}",
                        confidence=0.9
                    )
                ],
                modified_input=modified,
                original_input=input_data,
                modification_method="gender_swap"
            ))
        
        return counterfactuals
    
    def generate_location_counterfactual(
        self, 
        input_data: Dict[str, Any]
    ) -> Optional[Counterfactual]:
        """
        Generate counterfactual by swapping location to different
        socioeconomic proxy.
        """
        original_location = input_data.get("location", "")
        if not original_location:
            return None
        
        current_ses = self._infer_ses_from_location(original_location)
        
        # Pick opposite SES tier
        if current_ses == "low_ses":
            target_ses = "high_ses"
        elif current_ses == "high_ses":
            target_ses = "low_ses"
        else:
            target_ses = "high_ses"  # Default to high for middle
        
        new_location = random.choice(self.LOCATIONS_BY_PROXY[target_ses])
        
        modified = input_data.copy()
        modified["location"] = new_location
        
        # Also update in text fields if present
        if "resume_text" in modified:
            modified["resume_text"] = modified["resume_text"].replace(
                original_location, new_location
            )
        
        return Counterfactual(
            counterfactual_id=f"location_{target_ses}",
            modifications=[
                CounterfactualModification(
                    attribute=ProtectedAttribute.LOCATION,
                    original_value=original_location,
                    modified_value=new_location,
                    description=f"Changed location from {original_location} ({current_ses}) to {new_location} ({target_ses})",
                    confidence=0.7  # Location inference is imprecise
                )
            ],
            modified_input=modified,
            original_input=input_data,
            modification_method="location_swap"
        )
    
    def generate_university_counterfactual(
        self, 
        input_data: Dict[str, Any]
    ) -> Optional[Counterfactual]:
        """
        Swap university to different prestige tier.
        """
        # Extract university from input
        university = input_data.get("university", "")
        if not university:
            # Try to extract from education field
            education = input_data.get("education", [])
            if education and isinstance(education, list):
                university = education[0].get("school", "")
        
        if not university:
            return None
        
        current_tier = self._infer_university_prestige(university)
        
        # Swap to opposite tier
        if current_tier == "elite":
            target_tier = "mid"
        elif current_tier in ["low", "mid"]:
            target_tier = "elite"
        else:
            target_tier = "elite"
        
        new_university = random.choice(self.UNIVERSITIES_BY_PRESTIGE[target_tier])
        
        modified = self._deep_copy_and_replace_university(
            input_data, university, new_university
        )
        
        return Counterfactual(
            counterfactual_id=f"university_{target_tier}",
            modifications=[
                CounterfactualModification(
                    attribute=ProtectedAttribute.RACE,  # University is often a class/race proxy
                    original_value=university,
                    modified_value=new_university,
                    description=f"Changed university from {university} ({current_tier}) to {new_university} ({target_tier})",
                    confidence=0.6  # University prestige is a weak proxy
                )
            ],
            modified_input=modified,
            original_input=input_data,
            modification_method="university_swap"
        )
    
    def generate_age_counterfactual(
        self, 
        input_data: Dict[str, Any]
    ) -> Optional[Counterfactual]:
        """
        Modify age indicators (graduation year, years of experience).
        """
        # This is complex - need to shift all temporal references
        # Skip for MVP, implement later
        return None
    
    # Helper methods
    
    def _has_name_in_text(self, data: Dict[str, Any]) -> bool:
        """Check if name appears in text fields."""
        return "name" in data or any(
            "name" in str(v).lower() 
            for v in data.values() 
            if isinstance(v, str)
        )
    
    def _has_gender_indicators(self, data: Dict[str, Any]) -> bool:
        """Check if gender pronouns appear in text."""
        text = str(data).lower()
        return any(pronoun in text for pronoun in ["he ", "she ", "his ", "her "])
    
    def _has_age_indicators(self, data: Dict[str, Any]) -> bool:
        """Check if age indicators present."""
        return "age" in data or "graduation_year" in data or "years_experience" in data
    
    def _infer_perceived_race(self, name: str) -> str:
        """
        Infer perceived race from name.
        
        This is probabilistic and based on name frequency in different
        demographic groups. Not perfect, but useful for counterfactuals.
        """
        name_lower = name.lower()
        first_name = name_lower.split()[0] if " " in name_lower else name_lower
        
        # Check each category
        for race, names_dict in self.NAMES_BY_PERCEIVED_RACE.items():
            all_names = []
            for gender_list in names_dict.values():
                all_names.extend([n.lower() for n in gender_list])
            
            if first_name in all_names:
                return race
        
        # Default to likely_white if unknown
        return "likely_white"
    
    def _infer_gender(self, name: str, data: Dict[str, Any]) -> str:
        """Infer gender from name or pronouns in text."""
        # Check pronouns in text
        text = str(data).lower()
        if any(p in text for p in ["he ", "his ", "him "]):
            return "male"
        if any(p in text for p in ["she ", "her ", "hers "]):
            return "female"
        
        # Check name against gender lists
        first_name = name.split()[0].lower() if " " in name else name.lower()
        
        for race_names in self.NAMES_BY_PERCEIVED_RACE.values():
            if first_name in [n.lower() for n in race_names.get("male", [])]:
                return "male"
            if first_name in [n.lower() for n in race_names.get("female", [])]:
                return "female"
        
        # Default to neutral
        return "neutral"
    
    def _infer_gender_from_text(self, data: Dict[str, Any]) -> str:
        """Infer gender from pronouns in text."""
        text = str(data).lower()
        
        he_count = sum(text.count(p) for p in [" he ", " his ", " him "])
        she_count = sum(text.count(p) for p in [" she ", " her ", " hers "])
        
        if he_count > she_count:
            return "male"
        elif she_count > he_count:
            return "female"
        else:
            return "neutral"
    
    def _infer_ses_from_location(self, location: str) -> str:
        """Infer socioeconomic status from location."""
        location_lower = location.lower()
        
        for ses, locations in self.LOCATIONS_BY_PROXY.items():
            if any(loc.lower() in location_lower for loc in locations):
                return ses
        
        return "middle_ses"  # Default
    
    def _infer_university_prestige(self, university: str) -> str:
        """Infer university prestige tier."""
        university_lower = university.lower()
        
        for tier, universities in self.UNIVERSITIES_BY_PRESTIGE.items():
            if any(uni.lower() in university_lower for uni in universities):
                return tier
        
        return "mid"  # Default
    
    def _deep_copy_and_replace_name(
        self, 
        data: Dict[str, Any], 
        old_name: str, 
        new_name: str
    ) -> Dict[str, Any]:
        """Deep copy data and replace all instances of name."""
        import copy
        modified = copy.deepcopy(data)
        
        # Replace in top-level fields
        if "name" in modified:
            modified["name"] = new_name
        
        if "email" in modified:
            # Update email to match new name
            old_email = modified["email"]
            new_email = self._generate_email_from_name(new_name)
            modified["email"] = new_email
        
        # Replace in text fields
        for key, value in modified.items():
            if isinstance(value, str):
                # Replace full name
                modified[key] = value.replace(old_name, new_name)
                
                # Replace first name only
                old_first = old_name.split()[0]
                new_first = new_name.split()[0]
                modified[key] = modified[key].replace(old_first, new_first)
        
        return modified
    
    def _generate_email_from_name(self, name: str) -> str:
        """Generate email from name."""
        parts = name.lower().split()
        if len(parts) >= 2:
            return f"{parts[0]}.{parts[1]}@email.com"
        return f"{parts[0]}@email.com"
    
    def _swap_gender_indicators(
        self, 
        data: Dict[str, Any], 
        from_gender: str, 
        to_gender: str
    ) -> Dict[str, Any]:
        """Swap all gender indicators in data."""
        import copy
        modified = copy.deepcopy(data)
        
        # Get pronoun mappings
        from_pronouns = self.GENDER_PRONOUNS[from_gender]
        to_pronouns = self.GENDER_PRONOUNS[to_gender]
        
        # Replace in all text fields
        for key, value in modified.items():
            if isinstance(value, str):
                text = value
                for i, from_p in enumerate(from_pronouns):
                    to_p = to_pronouns[i]
                    # Add spaces to avoid partial matches
                    text = text.replace(f" {from_p} ", f" {to_p} ")
                    text = text.replace(f" {from_p.capitalize()} ", f" {to_p.capitalize()} ")
                modified[key] = text
        
        # Change name to gender-neutral if applicable
        if "name" in modified and to_gender == "neutral":
            original_name = modified["name"]
            first, last = original_name.split()[0], " ".join(original_name.split()[1:])
            neutral_first = random.choice(
                self.NAMES_BY_PERCEIVED_RACE["likely_white"]["neutral"]
            )
            modified["name"] = f"{neutral_first} {last}"
        
        return modified
    
    def _deep_copy_and_replace_university(
        self, 
        data: Dict[str, Any], 
        old_uni: str, 
        new_uni: str
    ) -> Dict[str, Any]:
        """Deep copy and replace university mentions."""
        import copy
        modified = copy.deepcopy(data)
        
        if "university" in modified:
            modified["university"] = new_uni
        
        if "education" in modified and isinstance(modified["education"], list):
            for edu in modified["education"]:
                if edu.get("school") == old_uni:
                    edu["school"] = new_uni
        
        # Replace in text fields
        for key, value in modified.items():
            if isinstance(value, str):
                modified[key] = value.replace(old_uni, new_uni)
        
        return modified
```

---

### Component 2: Counterfactual Analyzer

**File**: `backend/analyzers/counterfactual_fairness.py`

Runs counterfactuals through TrustChain and compares outcomes.

```python
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum

from core.base import BaseAnalyzer
from core.result import AnalysisResult, DecisionOutcome
from .counterfactual_generator import (
    CounterfactualGenerator, 
    Counterfactual,
    ProtectedAttribute
)


class BiasStrength(str, Enum):
    """Strength of detected bias."""
    NONE = "none"           # No bias detected
    WEAK = "weak"           # Minor decision changes
    MODERATE = "moderate"   # Clear decision flips
    STRONG = "strong"       # Consistent flips with high confidence


@dataclass
class CounterfactualResult:
    """Result of running a single counterfactual."""
    
    counterfactual: Counterfactual
    
    # Original decision
    original_decision: DecisionOutcome
    original_confidence: float
    
    # Counterfactual decision
    counterfactual_decision: DecisionOutcome
    counterfactual_confidence: float
    
    # Analysis
    decision_changed: bool
    confidence_delta: float
    bias_detected: bool
    bias_strength: BiasStrength
    
    # Explanation
    explanation: str


@dataclass
class CounterfactualFairnessResult:
    """Complete counterfactual fairness analysis."""
    
    # Overall fairness score (0.0 = total bias, 1.0 = no bias)
    fairness_score: float
    
    # Individual counterfactual results
    counterfactual_results: List[CounterfactualResult] = field(default_factory=list)
    
    # Summary
    biases_detected: List[ProtectedAttribute] = field(default_factory=list)
    bias_strength: BiasStrength = BiasStrength.NONE
    
    # Detailed breakdown
    total_counterfactuals: int = 0
    flipped_decisions: int = 0
    
    # Explanation
    summary: str = ""
    recommendations: List[str] = field(default_factory=list)


class CounterfactualFairnessAnalyzer(BaseAnalyzer):
    """
    Analyzer that tests counterfactual fairness.
    
    Generates counterfactual versions of input by modifying protected
    attributes, re-runs decisions, and checks if outcomes change.
    
    Usage:
        analyzer = CounterfactualFairnessAnalyzer()
        result = await analyzer.analyze(
            input_data=application_data,
            strategy_result=original_result,
            trustchain_instance=tc
        )
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("counterfactual_fairness", config)
        self.generator = CounterfactualGenerator(config)
        
        # Thresholds
        self.flip_threshold = 0.15  # Confidence change to consider significant
        self.fairness_threshold = 0.7  # Below this = bias detected
    
    async def analyze(
        self,
        input_data: Dict[str, Any],
        strategy_result: Any,  # StrategyResult from original decision
        trustchain_instance: Any,  # Reference to TrustChain for re-running
        **kwargs
    ) -> AnalysisResult:
        """
        Run counterfactual fairness analysis.
        
        Args:
            input_data: Original input data
            strategy_result: Result from original TrustChain decision
            trustchain_instance: TrustChain instance to re-run decisions
        """
        
        # Generate all counterfactuals
        counterfactuals = self.generator.generate_all(input_data)
        
        if not counterfactuals:
            return AnalysisResult(
                analyzer_name=self.name,
                passed=True,
                flags=[],
                warnings=["No counterfactuals could be generated for this input"],
                details={},
                recommendation="Unable to perform counterfactual fairness testing"
            )
        
        # Run each counterfactual through TrustChain
        cf_results = []
        for cf in counterfactuals:
            cf_result = await self._run_counterfactual(
                cf, 
                input_data,
                strategy_result,
                trustchain_instance
            )
            cf_results.append(cf_result)
        
        # Analyze results
        analysis = self._analyze_counterfactual_results(cf_results, strategy_result)
        
        # Determine pass/fail
        passed = analysis.fairness_score >= self.fairness_threshold
        
        # Generate flags
        flags = []
        if not passed:
            for bias_attr in analysis.biases_detected:
                flags.append(
                    f"Counterfactual bias detected: {bias_attr.value} "
                    f"(strength: {analysis.bias_strength.value})"
                )
        
        return AnalysisResult(
            analyzer_name=self.name,
            passed=passed,
            flags=flags,
            warnings=[],
            details={
                "fairness_score": analysis.fairness_score,
                "biases_detected": [b.value for b in analysis.biases_detected],
                "bias_strength": analysis.bias_strength.value,
                "total_counterfactuals": analysis.total_counterfactuals,
                "flipped_decisions": analysis.flipped_decisions,
                "counterfactual_results": [
                    {
                        "modification": cf_result.counterfactual.modification_method,
                        "decision_changed": cf_result.decision_changed,
                        "confidence_delta": cf_result.confidence_delta,
                        "bias_detected": cf_result.bias_detected
                    }
                    for cf_result in cf_results
                ]
            },
            recommendation=analysis.summary
        )
    
    async def _run_counterfactual(
        self,
        counterfactual: Counterfactual,
        original_input: Dict[str, Any],
        original_result: Any,
        trustchain: Any
    ) -> CounterfactualResult:
        """
        Run a single counterfactual through TrustChain.
        
        Returns comparison with original decision.
        """
        
        # Re-run TrustChain with modified input
        # Note: This requires TrustChain to expose a lightweight re-evaluation method
        cf_decision_result = await trustchain.evaluate(
            case_id=f"counterfactual_{counterfactual.counterfactual_id}",
            input_data=counterfactual.modified_input,
            skip_analyzers=True  # Don't run other analyzers, just get decision
        )
        
        # Compare decisions
        original_decision = original_result.decision
        original_confidence = original_result.confidence
        
        cf_decision = cf_decision_result.final_decision
        cf_confidence = cf_decision_result.overall_confidence
        
        decision_changed = original_decision != cf_decision
        confidence_delta = abs(cf_confidence - original_confidence)
        
        # Determine if this indicates bias
        bias_detected = decision_changed or confidence_delta > self.flip_threshold
        
        # Assess strength
        if not bias_detected:
            bias_strength = BiasStrength.NONE
        elif decision_changed and confidence_delta > 0.2:
            bias_strength = BiasStrength.STRONG
        elif decision_changed:
            bias_strength = BiasStrength.MODERATE
        else:
            bias_strength = BiasStrength.WEAK
        
        # Generate explanation
        explanation = self._generate_explanation(
            counterfactual,
            original_decision,
            original_confidence,
            cf_decision,
            cf_confidence,
            bias_detected
        )
        
        return CounterfactualResult(
            counterfactual=counterfactual,
            original_decision=original_decision,
            original_confidence=original_confidence,
            counterfactual_decision=cf_decision,
            counterfactual_confidence=cf_confidence,
            decision_changed=decision_changed,
            confidence_delta=confidence_delta,
            bias_detected=bias_detected,
            bias_strength=bias_strength,
            explanation=explanation
        )
    
    def _analyze_counterfactual_results(
        self,
        cf_results: List[CounterfactualResult],
        original_result: Any
    ) -> CounterfactualFairnessResult:
        """
        Aggregate counterfactual results into overall fairness assessment.
        """
        total = len(cf_results)
        flipped = sum(1 for r in cf_results if r.decision_changed)
        biased = [r for r in cf_results if r.bias_detected]
        
        # Calculate fairness score
        # 1.0 = no flips, 0.0 = all flipped
        fairness_score = 1.0 - (flipped / total) if total > 0 else 1.0
        
        # Identify which attributes caused bias
        biases_detected = []
        for result in biased:
            for mod in result.counterfactual.modifications:
                if mod.attribute not in biases_detected:
                    biases_detected.append(mod.attribute)
        
        # Determine overall bias strength
        if not biased:
            overall_strength = BiasStrength.NONE
        else:
            strengths = [r.bias_strength for r in biased]
            if BiasStrength.STRONG in strengths:
                overall_strength = BiasStrength.STRONG
            elif BiasStrength.MODERATE in strengths:
                overall_strength = BiasStrength.MODERATE
            else:
                overall_strength = BiasStrength.WEAK
        
        # Generate summary
        summary = self._generate_summary(
            fairness_score,
            flipped,
            total,
            biases_detected,
            overall_strength
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(biases_detected, cf_results)
        
        return CounterfactualFairnessResult(
            fairness_score=fairness_score,
            counterfactual_results=cf_results,
            biases_detected=biases_detected,
            bias_strength=overall_strength,
            total_counterfactuals=total,
            flipped_decisions=flipped,
            summary=summary,
            recommendations=recommendations
        )
    
    def _generate_explanation(
        self,
        cf: Counterfactual,
        orig_decision: DecisionOutcome,
        orig_conf: float,
        cf_decision: DecisionOutcome,
        cf_conf: float,
        bias_detected: bool
    ) -> str:
        """Generate explanation for a single counterfactual result."""
        
        mod = cf.modifications[0]  # Primary modification
        
        if not bias_detected:
            return f"Changing {mod.attribute.value} did not affect the decision. No bias detected."
        
        if orig_decision != cf_decision:
            return (
                f"BIAS DETECTED: Changing {mod.attribute.value} from "
                f"'{mod.original_value}' to '{mod.modified_value}' flipped the decision from "
                f"{orig_decision.value} ({orig_conf:.2f}) to {cf_decision.value} ({cf_conf:.2f}). "
                f"This suggests the model is discriminating based on {mod.attribute.value}."
            )
        else:
            return (
                f"Moderate bias: Changing {mod.attribute.value} significantly altered confidence "
                f"({orig_conf:.2f} → {cf_conf:.2f}) without flipping the decision."
            )
    
    def _generate_summary(
        self,
        fairness_score: float,
        flipped: int,
        total: int,
        biases: List[ProtectedAttribute],
        strength: BiasStrength
    ) -> str:
        """Generate overall summary."""
        
        if fairness_score >= 0.9:
            return f"HIGH FAIRNESS: Decisions were consistent across {total} counterfactual tests. No significant bias detected."
        
        if fairness_score >= 0.7:
            return f"MODERATE FAIRNESS: {flipped}/{total} counterfactuals changed decisions. Minor inconsistencies detected but may be within acceptable bounds."
        
        bias_list = ", ".join([b.value for b in biases])
        return (
            f"LOW FAIRNESS: {flipped}/{total} counterfactuals changed decisions. "
            f"{strength.value.upper()} bias detected in: {bias_list}. "
            f"The model's decisions are significantly influenced by protected attributes."
        )
    
    def _generate_recommendations(
        self,
        biases: List[ProtectedAttribute],
        results: List[CounterfactualResult]
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        if not biases:
            recommendations.append("No counterfactual bias detected. Continue monitoring.")
            return recommendations
        
        for bias_attr in biases:
            # Find strongest example
            relevant = [
                r for r in results 
                if any(m.attribute == bias_attr for m in r.counterfactual.modifications)
                and r.bias_detected
            ]
            
            if relevant:
                example = max(relevant, key=lambda r: r.confidence_delta)
                mod = example.counterfactual.modifications[0]
                
                recommendations.append(
                    f"Address {bias_attr.value} bias: Decisions changed when modifying "
                    f"'{mod.original_value}' to '{mod.modified_value}'. "
                    f"Review training data and model for implicit associations."
                )
        
        recommendations.append(
            "Consider re-training with fairness constraints or using adversarial debiasing."
        )
        
        return recommendations
```

---

### Component 3: Integration with TrustChain

**Update**: `backend/services/trustchain.py`

Add counterfactual testing as an optional analyzer.

```python
class TrustChain:
    def __init__(
        self,
        config: Optional[TrustChainConfig] = None,
        # ... existing params ...
        enable_counterfactual_testing: bool = False  # NEW
    ):
        # ... existing code ...
        
        # Add counterfactual analyzer if enabled
        if enable_counterfactual_testing:
            from analyzers.counterfactual_fairness import CounterfactualFairnessAnalyzer
            self.analyzers.append(CounterfactualFairnessAnalyzer())
    
    async def evaluate(
        self,
        case_id: str,
        input_data: Dict[str, Any],
        skip_analyzers: bool = False,  # NEW - for counterfactual re-runs
        **kwargs
    ) -> AccountabilityResult:
        """
        Main evaluation method.
        
        skip_analyzers=True is used when re-running counterfactuals
        to avoid infinite recursion.
        """
        
        # ... existing strategy execution ...
        
        # Run analyzers (unless skipped for counterfactuals)
        if not skip_analyzers:
            analysis_results = []
            for analyzer in self.analyzers:
                # Special handling for counterfactual analyzer
                if analyzer.name == "counterfactual_fairness":
                    result = await analyzer.analyze(
                        input_data=input_data,
                        strategy_result=sr,
                        trustchain_instance=self  # Pass self reference
                    )
                else:
                    result = await analyzer.analyze(input_data, sr)
                
                analysis_results.append(result)
        
        # ... rest of evaluation ...
```

---

### Component 4: API Endpoints

**Update**: `backend/app.py`

```python
@router.post("/api/v2/counterfactual-test")
async def run_counterfactual_test(
    case_id: str,
    input_data: Dict[str, Any]
):
    """
    Run counterfactual fairness test on a decision.
    
    This generates counterfactual versions of the input and checks
    if decisions change based on protected attributes.
    """
    tc = TrustChain(
        enable_counterfactual_testing=True
    )
    
    result = await tc.evaluate(
        case_id=case_id,
        input_data=input_data
    )
    
    # Extract counterfactual analysis
    cf_analysis = next(
        (a for a in result.analysis_results if a.analyzer_name == "counterfactual_fairness"),
        None
    )
    
    return {
        "case_id": case_id,
        "original_decision": result.final_decision.value,
        "counterfactual_analysis": cf_analysis.details if cf_analysis else None,
        "fairness_score": cf_analysis.details.get("fairness_score") if cf_analysis else None
    }
```

---

## Testing Strategy

### Unit Tests

**File**: `tests/test_counterfactual.py`

```python
import pytest
from analyzers.counterfactual_generator import CounterfactualGenerator
from analyzers.counterfactual_fairness import CounterfactualFairnessAnalyzer


def test_name_counterfactual_generation():
    """Test that name counterfactuals are generated correctly."""
    generator = CounterfactualGenerator()
    
    input_data = {
        "name": "Jamal Washington",
        "email": "jamal.w@email.com",
        "location": "Detroit, MI",
        "resume_text": "Jamal has 8 years of experience..."
    }
    
    counterfactuals = generator.generate_name_counterfactuals(input_data)
    
    assert len(counterfactuals) > 0
    assert any("Brad" in cf.modified_input["name"] for cf in counterfactuals)
    assert all(cf.modifications[0].attribute.value == "name" for cf in counterfactuals)


def test_gender_counterfactual_generation():
    """Test gender pronoun swapping."""
    generator = CounterfactualGenerator()
    
    input_data = {
        "name": "John Smith",
        "resume_text": "He has excellent leadership skills. His team delivered..."
    }
    
    counterfactuals = generator.generate_gender_counterfactuals(input_data)
    
    assert len(counterfactuals) >= 1
    # Check female version
    female_cf = next(cf for cf in counterfactuals if "female" in cf.counterfactual_id)
    assert "She has" in female_cf.modified_input["resume_text"]
    assert "Her team" in female_cf.modified_input["resume_text"]


def test_location_counterfactual():
    """Test location swapping."""
    generator = CounterfactualGenerator()
    
    input_data = {
        "location": "Detroit, MI"
    }
    
    cf = generator.generate_location_counterfactual(input_data)
    
    assert cf is not None
    assert cf.modified_input["location"] != "Detroit, MI"
    assert "Palo Alto" in cf.modified_input["location"] or "Greenwich" in cf.modified_input["location"]


@pytest.mark.asyncio
async def test_counterfactual_analyzer_detects_bias():
    """Test that analyzer detects decision changes."""
    # This requires mocking TrustChain
    # Implementation depends on mocking strategy
    pass
```

---

## Phase 4 TODO Checklist

```
[ ] Create backend/analyzers/counterfactual_generator.py
[ ] Implement CounterfactualGenerator with name swapping
[ ] Implement gender swapping
[ ] Implement location swapping  
[ ] Implement university prestige swapping
[ ] Create backend/analyzers/counterfactual_fairness.py
[ ] Implement CounterfactualFairnessAnalyzer
[ ] Implement _run_counterfactual method
[ ] Implement _analyze_counterfactual_results
[ ] Update TrustChain service to support skip_analyzers parameter
[ ] Update TrustChain to pass self-reference to counterfactual analyzer
[ ] Add enable_counterfactual_testing parameter to TrustChain.__init__
[ ] Create /api/v2/counterfactual-test endpoint
[ ] Write unit tests for CounterfactualGenerator
[ ] Write unit tests for name swapping
[ ] Write unit tests for gender swapping
[ ] Write unit tests for location swapping
[ ] Write integration tests for CounterfactualFairnessAnalyzer
[ ] Test with real hiring data
[ ] Add counterfactual results to AccountabilityResult
[ ] Document counterfactual testing in README
```

---

## Usage Examples

### Example 1: Test a Hiring Decision

```python
from services.trustchain import TrustChain

# Input data
application = {
    "name": "Jamal Washington",
    "email": "jamal.w@email.com",
    "location": "Detroit, MI",
    "university": "Wayne State University",
    "experience": "8 years software engineering",
    "skills": ["Python", "React", "AWS"],
    "resume_text": "..."
}

# Run TrustChain with counterfactual testing enabled
tc = TrustChain(
    config=TrustChainConfig.from_yaml("configs/hiring.yaml"),
    enable_counterfactual_testing=True
)

result = await tc.evaluate(
    case_id="hire_jamal_washington",
    input_data=application
)

# Check counterfactual fairness
cf_analysis = next(
    a for a in result.analysis_results 
    if a.analyzer_name == "counterfactual_fairness"
)

print(f"Fairness Score: {cf_analysis.details['fairness_score']}")
print(f"Biases Detected: {cf_analysis.details['biases_detected']}")

if not cf_analysis.passed:
    print("BIAS DETECTED:")
    for flag in cf_analysis.flags:
        print(f"  - {flag}")
```

### Example 2: API Usage

```bash
curl -X POST http://localhost:8000/api/v2/counterfactual-test \
  -H "Content-Type: application/json" \
  -d '{
    "case_id": "hire_candidate_123",
    "input_data": {
      "name": "Lakisha Brown",
      "location": "Oakland, CA",
      "university": "UC Berkeley",
      "experience": "5 years data science",
      "skills": ["Python", "ML", "SQL"]
    }
  }'
```

**Response:**
```json
{
  "case_id": "hire_candidate_123",
  "original_decision": "DENIED",
  "counterfactual_analysis": {
    "fairness_score": 0.33,
    "biases_detected": ["name", "location"],
    "bias_strength": "strong",
    "total_counterfactuals": 3,
    "flipped_decisions": 2,
    "counterfactual_results": [
      {
        "modification": "name_swap",
        "decision_changed": true,
        "confidence_delta": 0.24,
        "bias_detected": true
      }
    ]
  },
  "fairness_score": 0.33
}
```

---

## Key Design Decisions

1. **Multiple Counterfactuals Per Input** - We generate counterfactuals for each protected attribute (name, gender, location, etc.) to test different bias vectors.

2. **Probabilistic Race/Gender Inference** - Name-to-race and pronoun-to-gender mappings are probabilistic. We acknowledge this limitation but it's sufficient for bias detection.

3. **Lightweight Re-evaluation** - Counterfactuals skip other analyzers (`skip_analyzers=True`) to avoid infinite recursion and reduce compute cost.

4. **Fairness Score Calculation** - Simple: 1.0 - (flipped_decisions / total_counterfactuals). This is intuitive and easy to explain.

5. **Bias Strength Levels** - NONE, WEAK, MODERATE, STRONG based on both decision flips and confidence deltas. This gives nuance to the analysis.

6. **Opt-In Feature** - Counterfactual testing is expensive (requires re-running decisions multiple times), so it's opt-in via `enable_counterfactual_testing=True`.

---

## Performance Considerations

**Cost**: Each counterfactual requires a full TrustChain evaluation. If you generate 5 counterfactuals, you're running 6 total evaluations (1 original + 5 counterfactuals).

**Optimization Strategies**:
- Cache model responses for identical inputs
- Run counterfactuals in parallel (async)
- Limit number of counterfactuals generated (config option)
- Skip expensive analyzers during counterfactual re-runs

**When to Use**:
- High-stakes decisions (final candidate selection, loan approvals)
- Auditing/compliance mode
- Spot-checking after complaints
- NOT for every single decision (too expensive)

---

## Future Enhancements

1. **Statistical Significance Testing** - Run multiple counterfactuals per attribute and test if flips are statistically significant.

2. **Intersectional Testing** - Test combinations (e.g., Black + female vs White + male).

3. **Gradient-Based Counterfactuals** - Instead of discrete swaps, use gradient methods to find minimal changes that flip decisions.

4. **Learned Counterfactuals** - Train a model to generate realistic counterfactuals that maintain semantic coherence.

5. **Visual Explanations** - Show side-by-side comparisons of original vs counterfactual with highlighted changes.

---

*Document generated November 2025. Making discrimination measurable, one counterfactual at a time.*
