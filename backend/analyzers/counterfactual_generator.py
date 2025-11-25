"""
Counterfactual Generator for TrustChain.

Generates modified versions of input data by swapping protected attributes
to test for bias. If changing "Jamal" to "Brad" flips a decision, that's
measurable discrimination.

Usage:
    generator = CounterfactualGenerator()
    counterfactuals = generator.generate_all(input_data)

Built with care by Kareem & Claude
"""

import copy
import random
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


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
        name_cf = generator.generate_name_counterfactuals(input_data)
        gender_cf = generator.generate_gender_counterfactuals(input_data)
    """

    # Name databases for swapping
    # Based on research showing hiring discrimination by name
    NAMES_BY_PERCEIVED_RACE = {
        "likely_white": {
            "male": ["Brad", "Connor", "Jake", "Todd", "Garrett", "Brett", "Hunter", "Cody"],
            "female": ["Emily", "Claire", "Allison", "Megan", "Katie", "Lauren", "Hannah", "Molly"],
            "neutral": ["Jordan", "Taylor", "Morgan", "Casey", "Riley", "Avery", "Quinn", "Skyler"]
        },
        "likely_black": {
            "male": ["Jamal", "DeShawn", "Tyrone", "Malik", "Kareem", "Darius", "Terrell", "Andre"],
            "female": ["Lakisha", "Tanisha", "Ebony", "Aisha", "Imani", "Jasmine", "Keisha", "Shanice"],
            "neutral": ["Jordan", "Taylor", "Morgan", "Casey", "Riley", "Avery", "Quinn", "Skyler"]
        },
        "likely_hispanic": {
            "male": ["Carlos", "Jose", "Luis", "Miguel", "Jorge", "Diego", "Roberto", "Fernando"],
            "female": ["Maria", "Carmen", "Rosa", "Ana", "Isabel", "Sofia", "Guadalupe", "Elena"],
            "neutral": ["Jordan", "Taylor", "Morgan", "Casey", "Riley", "Avery", "Quinn", "Skyler"]
        },
        "likely_asian": {
            "male": ["Wei", "Raj", "Akira", "Jin", "Arjun", "Hiroshi", "Pranav", "Kai"],
            "female": ["Mei", "Priya", "Yuki", "Li", "Anjali", "Sakura", "Deepa", "Aiko"],
            "neutral": ["Jordan", "Taylor", "Morgan", "Casey", "Riley", "Avery", "Quinn", "Skyler"]
        }
    }

    LAST_NAMES_BY_PERCEIVED_RACE = {
        "likely_white": ["Smith", "Johnson", "Williams", "Miller", "Thompson", "Anderson", "Davis", "Wilson"],
        "likely_black": ["Washington", "Jefferson", "Jackson", "Brown", "Harris", "Robinson", "Freeman", "Banks"],
        "likely_hispanic": ["Garcia", "Rodriguez", "Martinez", "Lopez", "Hernandez", "Gonzalez", "Perez", "Sanchez"],
        "likely_asian": ["Li", "Wang", "Chen", "Patel", "Kumar", "Nguyen", "Kim", "Park"]
    }

    GENDER_PRONOUNS = {
        "male": ["he", "him", "his", "himself"],
        "female": ["she", "her", "hers", "herself"],
        "neutral": ["they", "them", "their", "themselves"]
    }

    GENDER_TITLES = {
        "male": ["Mr.", "Mr"],
        "female": ["Ms.", "Ms", "Mrs.", "Mrs", "Miss"],
        "neutral": ["Mx.", "Mx"]
    }

    # Locations by socioeconomic proxy
    LOCATIONS_BY_PROXY = {
        "high_ses": [
            "Palo Alto, CA", "Greenwich, CT", "Atherton, CA", "Beverly Hills, CA",
            "Scarsdale, NY", "McLean, VA", "Winnetka, IL", "Paradise Valley, AZ"
        ],
        "middle_ses": [
            "Austin, TX", "Denver, CO", "Portland, OR", "Atlanta, GA",
            "Nashville, TN", "Raleigh, NC", "Salt Lake City, UT", "Columbus, OH"
        ],
        "low_ses": [
            "Detroit, MI", "Flint, MI", "Camden, NJ", "Gary, IN",
            "Youngstown, OH", "East St. Louis, IL", "Stockton, CA", "Cleveland, OH"
        ]
    }

    # University prestige tiers
    UNIVERSITIES_BY_PRESTIGE = {
        "elite": [
            "Harvard University", "Stanford University", "MIT",
            "Yale University", "Princeton University", "Columbia University"
        ],
        "high": [
            "UC Berkeley", "University of Michigan", "UCLA",
            "UT Austin", "University of Virginia", "NYU"
        ],
        "mid": [
            "Penn State", "Ohio State University", "Rutgers University",
            "Indiana University", "Arizona State University", "University of Florida"
        ],
        "low": [
            "Wayne State University", "Cleveland State University",
            "University of Toledo", "Youngstown State University"
        ]
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._random_seed = config.get("random_seed") if config else None
        if self._random_seed:
            random.seed(self._random_seed)

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
        if "location" in input_data or "address" in input_data or "city" in input_data:
            cf = self.generate_location_counterfactual(input_data)
            if cf:
                counterfactuals.append(cf)

        # University prestige
        if "university" in input_data or "education" in input_data or "school" in input_data:
            cf = self.generate_university_counterfactual(input_data)
            if cf:
                counterfactuals.append(cf)

        logger.info(f"Generated {len(counterfactuals)} counterfactuals")
        return counterfactuals

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
                        description=f"Changed name from {original_name} to {new_name} (perceived {current_race} -> {race_category})",
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
        - Pronouns (he/she -> they, she/he)
        - Gendered titles (Mr./Ms.)
        - First names if gendered
        """
        current_gender = self._infer_gender_from_text(input_data)

        counterfactuals = []

        # Generate opposite gender and neutral versions
        target_genders = ["male", "female", "neutral"]
        if current_gender in target_genders:
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
        original_location = input_data.get("location") or input_data.get("city") or input_data.get("address", "")
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

        modified = copy.deepcopy(input_data)

        # Update location field
        for field_name in ["location", "city", "address"]:
            if field_name in modified:
                modified[field_name] = new_location

        # Also update in text fields if present
        for key, value in modified.items():
            if isinstance(value, str) and original_location in value:
                modified[key] = value.replace(original_location, new_location)

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
        university = input_data.get("university") or input_data.get("school", "")
        if not university:
            # Try to extract from education field
            education = input_data.get("education", [])
            if education and isinstance(education, list):
                if isinstance(education[0], dict):
                    university = education[0].get("school", "")
                elif isinstance(education[0], str):
                    university = education[0]

        if not university:
            return None

        current_tier = self._infer_university_prestige(university)

        # Swap to opposite tier
        if current_tier == "elite":
            target_tier = "low"
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

    # Helper methods

    def _has_name_in_text(self, data: Dict[str, Any]) -> bool:
        """Check if name field exists or name pattern in text."""
        return "name" in data

    def _has_gender_indicators(self, data: Dict[str, Any]) -> bool:
        """Check if gender pronouns appear in text."""
        text = str(data).lower()
        indicators = [" he ", " she ", " his ", " her ", " him ", "mr.", "ms.", "mrs."]
        return any(indicator in text for indicator in indicators)

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

        # Check last names too
        if " " in name_lower:
            last_name = name_lower.split()[-1]
            for race, last_names in self.LAST_NAMES_BY_PERCEIVED_RACE.items():
                if last_name in [n.lower() for n in last_names]:
                    return race

        # Default to likely_white if unknown
        return "likely_white"

    def _infer_gender(self, name: str, data: Dict[str, Any]) -> str:
        """Infer gender from name or pronouns in text."""
        # Check pronouns in text first
        text = str(data).lower()
        if any(p in text for p in [" he ", " his ", " him "]):
            return "male"
        if any(p in text for p in [" she ", " her ", " hers "]):
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
            for loc in locations:
                if loc.lower() in location_lower or location_lower in loc.lower():
                    return ses

        return "middle_ses"  # Default

    def _infer_university_prestige(self, university: str) -> str:
        """Infer university prestige tier."""
        university_lower = university.lower()

        for tier, universities in self.UNIVERSITIES_BY_PRESTIGE.items():
            for uni in universities:
                if uni.lower() in university_lower or university_lower in uni.lower():
                    return tier

        return "mid"  # Default

    def _deep_copy_and_replace_name(
        self,
        data: Dict[str, Any],
        old_name: str,
        new_name: str
    ) -> Dict[str, Any]:
        """Deep copy data and replace all instances of name."""
        modified = copy.deepcopy(data)

        # Replace in top-level fields
        if "name" in modified:
            modified["name"] = new_name

        if "email" in modified:
            # Update email to match new name
            new_email = self._generate_email_from_name(new_name)
            modified["email"] = new_email

        # Get name parts for replacement
        old_parts = old_name.split()
        new_parts = new_name.split()
        old_first = old_parts[0] if old_parts else ""
        new_first = new_parts[0] if new_parts else ""

        # Replace in text fields
        for key, value in modified.items():
            if isinstance(value, str):
                # Replace full name
                modified[key] = value.replace(old_name, new_name)

                # Replace first name only (common in resumes/cover letters)
                if old_first and new_first:
                    modified[key] = modified[key].replace(old_first, new_first)

        return modified

    def _generate_email_from_name(self, name: str) -> str:
        """Generate email from name."""
        parts = name.lower().split()
        if len(parts) >= 2:
            return f"{parts[0]}.{parts[1][0]}@email.com"
        return f"{parts[0]}@email.com"

    def _swap_gender_indicators(
        self,
        data: Dict[str, Any],
        from_gender: str,
        to_gender: str
    ) -> Dict[str, Any]:
        """Swap all gender indicators in data."""
        modified = copy.deepcopy(data)

        # Get pronoun mappings
        from_pronouns = self.GENDER_PRONOUNS.get(from_gender, [])
        to_pronouns = self.GENDER_PRONOUNS.get(to_gender, [])

        # Replace in all text fields
        for key, value in modified.items():
            if isinstance(value, str):
                text = value

                # Replace pronouns
                for i, from_p in enumerate(from_pronouns):
                    if i < len(to_pronouns):
                        to_p = to_pronouns[i]
                        # Add spaces to avoid partial matches
                        text = text.replace(f" {from_p} ", f" {to_p} ")
                        text = text.replace(f" {from_p.capitalize()} ", f" {to_p.capitalize()} ")
                        # Handle sentence start
                        if text.startswith(f"{from_p.capitalize()} "):
                            text = f"{to_p.capitalize()} " + text[len(from_p) + 1:]

                # Replace titles
                from_titles = self.GENDER_TITLES.get(from_gender, [])
                to_titles = self.GENDER_TITLES.get(to_gender, [])
                if from_titles and to_titles:
                    for title in from_titles:
                        text = text.replace(title, to_titles[0])

                modified[key] = text

        return modified

    def _deep_copy_and_replace_university(
        self,
        data: Dict[str, Any],
        old_uni: str,
        new_uni: str
    ) -> Dict[str, Any]:
        """Deep copy and replace university mentions."""
        modified = copy.deepcopy(data)

        if "university" in modified:
            modified["university"] = new_uni

        if "school" in modified:
            modified["school"] = new_uni

        if "education" in modified and isinstance(modified["education"], list):
            for edu in modified["education"]:
                if isinstance(edu, dict) and edu.get("school") == old_uni:
                    edu["school"] = new_uni

        # Replace in text fields
        for key, value in modified.items():
            if isinstance(value, str):
                modified[key] = value.replace(old_uni, new_uni)

        return modified
