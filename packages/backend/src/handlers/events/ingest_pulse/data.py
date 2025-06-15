import random
from functools import cache
from pydantic import BaseModel, Field
from typing import Any, Dict, Tuple


@cache
def _current_dir() -> str:
    """Get the current directory of this file."""
    import os

    return os.path.dirname(os.path.abspath(__file__))


@cache
def _load_json_in_data_dir(file_name: str) -> Any:
    """Get the full path to a file in the data directory."""
    import json
    import os

    json_file_path = os.path.join(_current_dir(), "data", file_name)
    with open(json_file_path, "r") as file:
        return json.load(file)


@cache
def intensity_levels_data() -> Dict[str, Dict[str, int | str | list[str]]]:
    """Load intensity levels from a JSON file."""
    return _load_json_in_data_dir("intensity_levels.json")


class IntensityLevel(BaseModel):
    """Model for a single intensity level with an optional field."""

    name: str = Field(default="", description="Name of the intensity level")
    min_duration: int = Field(description="Minimum duration in seconds")
    max_duration: int = Field(description="Maximum duration in seconds")
    prefix: list[str] = Field(
        default_factory=list, description="List of prefixes for the intensity level"
    )

    @classmethod
    def from_name(cls, name: str) -> "IntensityLevel":
        """Create an IntensityLevel instance from a dictionary."""
        data = intensity_levels_data().get(name, {})
        if not data:
            raise ValueError(f"Invalid data for intensity level: {name}")
        if isinstance(data["min_duration"], list):
            raise ValueError(f"Invalid min_duration format for intensity level: {name}")
        if isinstance(data["max_duration"], list):
            raise ValueError(f"Invalid min_duration format for intensity level: {name}")
        try:
            data["min_duration"] = int(data["min_duration"])
            data["max_duration"] = int(data["max_duration"])
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"Invalid duration values for intensity level: {name}"
            ) from e
        if not isinstance(data["prefix"], list):
            raise ValueError(f"Invalid prefix format for intensity level: {name}")
        if data["min_duration"] < 0 or data["max_duration"] < 0:
            raise ValueError(
                f"Duration values cannot be negative for intensity level: {name}"
            )
        if data["min_duration"] >= data["max_duration"]:
            raise ValueError(
                f"Minimum duration must be less than maximum duration for intensity level: {name}"
            )

        return cls(
            name=str(name),
            min_duration=data["min_duration"],
            max_duration=int(data["max_duration"]),
            prefix=list(data["prefix"]),
        )


class IntensityLevels(BaseModel):
    """Model for intensity levels with optional fields."""

    @cache
    @staticmethod
    def intensity_levels() -> Dict[str, IntensityLevel]:
        """Return a dictionary of intensity levels."""
        return {
            name: IntensityLevel.from_name(name)
            for name in intensity_levels_data().keys()
        }

    @staticmethod
    def get_duration_level(
        duration_seconds: float,
    ) -> IntensityLevel:
        """Return the intensity level matching the duration."""
        levels = IntensityLevels.intensity_levels().values()
        for level in levels:
            if level.min_duration <= duration_seconds < level.max_duration:
                return level
        # Fallback to first level if none matched
        return next(iter(levels))

    @staticmethod
    def get_random_prefix_from_duration(duration_seconds: float) -> str:
        """Return a random prefix for the intensity level matching the duration."""
        return random.choice(
            IntensityLevels.get_duration_level(duration_seconds).prefix
        )


@cache
def intent_nouns() -> Dict[str, list[str]]:
    """Load intent_nouns from a JSON file."""
    return _load_json_in_data_dir("intent_nouns.json")


class IntentNoun(BaseModel):
    """Model for a single intent noun with an optional field."""

    name: str = Field(description="Name of the intent noun")
    nouns: list[str] = Field(
        description="List of nouns associated with the intent noun",
    )

    @classmethod
    def from_name(cls, name: str) -> "IntentNoun":
        """Create an IntentNoun instance from a dictionary."""
        data = intent_nouns().get(name, [])
        if not data:
            raise ValueError(f"Intent noun cannot be empty: {name}")
        return cls(name=name, nouns=data)


@cache
def synonyms() -> Dict[str, str]:
    """Load synonyms from a JSON file."""
    return _load_json_in_data_dir("synonyms.json")


class IntentData(BaseModel):
    """Model for intent nouns with optional fields."""

    @cache
    @staticmethod
    def intent_nouns() -> Dict[str, IntentNoun]:
        """Return a dictionary of intent nouns."""
        return {name: IntentNoun.from_name(name) for name in intent_nouns().keys()}

    @cache
    @staticmethod
    def intent_nouns_categories() -> list[str]:
        """Return a list of IntentNoun objects."""
        return list(IntentData.intent_nouns().keys())

    @cache
    @staticmethod
    def intent_emojis() -> Dict[str, list[str]]:
        """Return a dictionary of intent emojis."""
        return _load_json_in_data_dir("intent_emojis.json")

    @staticmethod
    def get_synonym_for_noun(noun: str) -> str:
        """Return a synonym for the given noun."""
        synonym = IntentData.find_best_match_fuzzy(noun, list(synonyms().keys()))
        if synonym:
            return synonym
        return "default"

    @staticmethod
    def find_best_match_fuzzy(
        input_word: str, choices: list[str], threshold: int = 50
    ) -> str | None:
        """Find best match using fuzzywuzzy (more accurate)."""
        from fuzzywuzzy import fuzz, process

        best_match: tuple[str, float] = process.extractOne(input_word, choices, scorer=fuzz.ratio)  # type: ignore
        if best_match and best_match[1] >= threshold:
            return best_match[0]  # type: ignore
        return None

    @staticmethod
    def extract_intent_category(intent: str) -> str:
        """Extract intent category from intent string."""
        intent_lower = intent.lower()

        # Check for common patterns

        category = IntentData.find_best_match_fuzzy(
            intent_lower, list(IntentData.intent_nouns_categories())
        )
        if category:
            return category

        # Fallback to synonyms
        return IntentData.get_synonym_for_noun(intent_lower)

    @staticmethod
    def get_emoji(intent_category: str) -> str:
        """Get appropriate emoji for intent."""
        emojis = IntentData.intent_emojis().get(
            intent_category, IntentData.intent_emojis()["default"]
        )
        return random.choice(emojis)

    @staticmethod
    def get_action_noun(intent_category: str) -> str:
        """Get a random action noun for the intent category."""
        nouns = (
            IntentData.intent_nouns()
            .get(intent_category, IntentNoun(name="default", nouns=["action"]))
            .nouns
        )
        return random.choice(nouns) if nouns else "action"


class MotivationalSuffixes(BaseModel):
    """Model for motivational suffixes with optional fields."""

    @cache
    @staticmethod
    def motivational_suffixes() -> list[str]:
        """Return a list of motivational suffixes."""
        return _load_json_in_data_dir("motivational_suffixes.json")

    @staticmethod
    def get_random_suffix() -> str:
        """Return a random motivational suffix."""
        return random.choice(MotivationalSuffixes.motivational_suffixes())


class SentimentAdjectives(BaseModel):
    """Model for sentiment adjectives with optional fields."""

    @cache
    @staticmethod
    def sentiment_adjectives() -> Dict[str, list[str]]:
        """Return a dictionary of sentiment adjectives."""
        return _load_json_in_data_dir("sentiment_adjectives.json")

    @staticmethod
    def get_random_adjective(sentiment_category: str) -> str:
        """Return a random adjective for the sentiment category."""
        adjectives = SentimentAdjectives.sentiment_adjectives().get(
            sentiment_category, []
        )
        return random.choice(adjectives) if adjectives else "neutral"

    @staticmethod
    def analyze_sentiment(text: str) -> Tuple[str, float]:
        """Analyze sentiment of reflection text."""
        from textblob import TextBlob  # type: ignore

        if not text:
            return "neutral", 0.0

        try:
            blob = TextBlob(text)
            polarity = float(blob.sentiment.polarity)  # type: ignore

            if polarity >= 0.7:
                return "very_positive", polarity
            elif polarity >= 0.3:
                return "positive", polarity
            elif polarity >= 0.1:
                return "neutral_positive", polarity
            elif polarity >= -0.1:
                return "neutral", polarity
            elif polarity >= -0.3:
                return "neutral_negative", polarity
            elif polarity >= -0.7:
                return "negative", polarity
            else:
                return "very_negative", polarity

        except Exception:
            return "neutral", 0.0

    @staticmethod
    def get_random_sentiment_adjective(text: str) -> str:
        """Get random sentiment category for the given text."""
        sentiment_category, _ = SentimentAdjectives.analyze_sentiment(text)
        sentiment_adjective = SentimentAdjectives.get_random_adjective(
            sentiment_category
        )
        if not sentiment_adjective:
            sentiment_adjective = "Neutral"
        return sentiment_adjective.capitalize()
