import random
from typing import List

from data import IntensityLevels, IntentData, SentimentAdjectives
from shared.models.pulse import StopPulse
import logging

logger = logging.getLogger(__name__)


class PulseTitleGenerator:
    """Generate engaging, gamified titles for pulse data."""

    @staticmethod
    def generate_title(pulse_data: StopPulse) -> str:
        """Generate a gamified title for the pulse."""
        # Extract data
        duration = pulse_data.duration_seconds or 0
        intent = pulse_data.intent
        reflection = pulse_data.reflection

        try:
            # Analyze components
            intensity_prefix = IntensityLevels.get_random_prefix_from_duration(duration)
            intent_category = IntentData.extract_intent_category(intent)
            # Get components
            sentiment_adjective = SentimentAdjectives.get_random_sentiment_adjective(
                reflection
            )
            action_noun = IntentData.get_action_noun(intent_category)
            emoji = IntentData.get_emoji(intent_category)

            # Create title variations
            title_templates = [
                f"{intensity_prefix} {sentiment_adjective} {action_noun}! {emoji}",
                f"{sentiment_adjective} {intensity_prefix} {action_noun} {emoji}",
                f"{emoji} {intensity_prefix} & {sentiment_adjective} {action_noun}",
                f"{action_noun}: {intensity_prefix} and {sentiment_adjective}! {emoji}",
            ]

            title = random.choice(title_templates)

            # Add duration context for very short or very long sessions
            if duration < 60:
                title += f" (Quick {int(duration)}s burst!)"
            elif duration > 7200:  # 2 hours
                hours = duration / 3600
                title += f" ({hours:.1f}h marathon!)"

            return title

        except Exception as e:
            # Fallback title
            print(f"Error generating title: {e}")
            return f"Session Complete! ✨\n\nKeep up the great work! 🌟"

    @staticmethod
    def generate_multiple_options(pulse_data: StopPulse, count: int = 3) -> List[str]:
        """Generate multiple title options for variety."""
        return list(
            [PulseTitleGenerator.generate_title(pulse_data) for _ in range(count)]
        )

    @staticmethod
    def get_achievement_badge(pulse_data: StopPulse) -> str:
        """Generate achievement badge based on pulse characteristics."""
        duration = pulse_data.duration_seconds
        duration = duration if duration is not None else 0
        intent_category = IntentData.extract_intent_category(pulse_data.intent)

        badges = {
            ("workout", "epic"): "🏆 Fitness Warrior",
            ("workout", "major"): "💪 Strong Performer",
            ("meditation", "major"): "🧘‍♀️ Zen Master",
            ("meditation", "epic"): "☮️ Inner Peace Champion",
            ("study", "epic"): "🎓 Knowledge Seeker",
            ("study", "major"): "📚 Learning Champion",
            ("work", "epic"): "🚀 Productivity Hero",
            ("work", "major"): "⚡ Task Crusher",
            ("coding", "epic"): "💻 Code Ninja",
            ("coding", "major"): "🛠️ Bug Slayer",
        }

        duration_level = IntensityLevels.get_duration_level(duration).name.lower()
        badge_key = (intent_category, duration_level)

        if badge_key in badges:
            return badges[badge_key]
        elif duration_level == "epic":
            return "🏆 Legendary Achiever"
        elif duration_level == "major":
            return "⭐ Great Performer"
        else:
            return "✨ Progress Maker"
