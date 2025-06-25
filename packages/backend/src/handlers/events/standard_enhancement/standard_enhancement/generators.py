import random
from typing import List

from standard_enhancement.data import IntensityLevels, IntentData, SentimentAdjectives
from shared.models.pulse import StopPulse
import logging

logger = logging.getLogger(__name__)


class PulseTitleGenerator:
    """Generate engaging, gamified titles for pulse data."""

    @staticmethod
    def generate_title(pulse_data: StopPulse) -> str:
        """Generate a gamified title for the pulse."""
        # Extract data
        duration = pulse_data.actual_duration_seconds
        intent = pulse_data.intent
        reflection = pulse_data.reflection
        intent_emotion = getattr(pulse_data, "intent_emotion", "") or ""
        reflection_emotion = getattr(pulse_data, "reflection_emotion", "") or ""

        try:
            # Analyze components
            intensity_prefix = IntensityLevels.get_random_prefix_from_duration(duration)
            intent_category = IntentData.extract_intent_category(intent)
            # Get components with emotion enhancement
            sentiment_adjective = SentimentAdjectives.get_random_sentiment_adjective(
                reflection, reflection_emotion
            )
            action_noun = IntentData.get_action_noun(intent_category)
            emoji = IntentData.get_emoji(
                intent_category, intent_emotion, reflection_emotion
            )

            # Create emotion-aware title variations
            base_templates = [
                f"{intensity_prefix} {sentiment_adjective} {action_noun}! {emoji}",
                f"{sentiment_adjective} {intensity_prefix} {action_noun} {emoji}",
                f"{emoji} {intensity_prefix} & {sentiment_adjective} {action_noun}",
                f"{action_noun}: {intensity_prefix} and {sentiment_adjective}! {emoji}",
            ]

            # Add emotion journey templates if emotions differ
            if (
                intent_emotion
                and reflection_emotion
                and intent_emotion.lower() != reflection_emotion.lower()
            ):
                emotion_journey_templates = [
                    f"{emoji} {intent_emotion.title()} → {reflection_emotion.title()} {action_noun}",
                    f"{intensity_prefix} {intent_emotion} to {reflection_emotion} Journey! {emoji}",
                    f"{action_noun}: {intent_emotion} → {reflection_emotion} Growth {emoji}",
                ]
                title_templates = base_templates + emotion_journey_templates
            else:
                title_templates = base_templates

            title = random.choice(title_templates)

            # Add duration context for different session lengths
            if duration < 60:
                title += f" (Quick {int(duration)}s burst!)"
            elif 60 <= duration < 1200:
                minutes = duration / 60
                title += f" ({minutes:.0f} min session!)"
            elif 1200 <= duration < 3600:
                minutes = duration / 60
                title += f" (Focused {minutes:.0f} min streak!)"
            elif 3600 <= duration < 7200:
                hours = duration / 3600
                title += f" (Power {hours:.1f}h session!)"
            elif duration >= 7200:
                hours = duration / 3600
                title += f" ({hours:.1f}h marathon!)"

            return title

        except Exception as e:
            # Fallback title
            print(f"Error generating title: {e}")
            return "Session Complete! ✨\n\nKeep up the great work! 🌟"

    @staticmethod
    def generate_multiple_options(pulse_data: StopPulse, count: int = 3) -> List[str]:
        """Generate multiple title options for variety."""
        return list(
            [PulseTitleGenerator.generate_title(pulse_data) for _ in range(count)]
        )

    @staticmethod
    def get_achievement_badge(pulse_data: StopPulse) -> str:
        """Generate achievement badge based on pulse characteristics and emotions."""
        duration = pulse_data.duration_seconds
        duration = duration if duration is not None else 0
        intent_category = IntentData.extract_intent_category(pulse_data.intent)
        print(f"Found intent_category: {intent_category}")
        intent_emotion = getattr(pulse_data, "intent_emotion", "") or ""
        reflection_emotion = getattr(pulse_data, "reflection_emotion", "") or ""

        # Standard badges
        badges = {
            # Workout
            ("workout", "epic"): "🏆 Fitness Warrior",
            ("workout", "grand"): "🥇 Grand Fitness Champion",
            ("workout", "major"): "💪 Strong Performer",
            ("workout", "minor"): "🏃 Active Starter",
            ("workout", "micro"): "🔸 Quick Mover",
            # Meditation
            ("meditation", "epic"): "☮️ Inner Peace Champion",
            ("meditation", "grand"): "🌌 Grand Zen Sage",
            ("meditation", "major"): "🧘‍♀️ Zen Master",
            ("meditation", "minor"): "🌱 Calm Initiate",
            ("meditation", "micro"): "🫧 Mindful Moment",
            # Study
            ("study", "epic"): "🎓 Knowledge Seeker",
            ("study", "grand"): "🏅 Grand Scholar",
            ("study", "major"): "📚 Learning Champion",
            ("study", "minor"): "✏️ Study Starter",
            ("study", "micro"): "🔖 Quick Learner",
            # Work
            ("work", "epic"): "🚀 Productivity Hero",
            ("work", "grand"): "🏆 Grand Productivity Master",
            ("work", "major"): "⚡ Task Crusher",
            ("work", "minor"): "📝 Task Initiator",
            ("work", "micro"): "⏳ Quick Contributor",
            # Reading
            ("reading", "epic"): "📖 Reading Legend",
            ("reading", "grand"): "🏅 Grand Bookworm",
            ("reading", "major"): "📚 Page Turner",
            ("reading", "minor"): "🔖 Reading Starter",
            ("reading", "micro"): "📄 Quick Reader",
            # Creative
            ("creative", "epic"): "🎨 Creative Virtuoso",
            ("creative", "grand"): "🏅 Grand Creator",
            ("creative", "major"): "🖌️ Artful Achiever",
            ("creative", "minor"): "✏️ Creative Starter",
            ("creative", "micro"): "🪄 Quick Creator",
            # Coding
            ("coding", "epic"): "💻 Code Ninja",
            ("coding", "grand"): "🏅 Grand Code Architect",
            ("coding", "major"): "🛠️ Bug Slayer",
            ("coding", "minor"): "👨‍💻 Code Starter",
            ("coding", "micro"): "⌨️ Quick Coder",
            # Music
            ("music", "epic"): "🎶 Maestro Supreme",
            ("music", "grand"): "🏅 Grand Virtuoso",
            ("music", "major"): "🎸 Music Maker",
            ("music", "minor"): "🎵 Music Starter",
            ("music", "micro"): "🔔 Quick Tune",
            # Cooking
            ("cooking", "epic"): "👨‍🍳 Culinary Legend",
            ("cooking", "grand"): "🏅 Grand Chef",
            ("cooking", "major"): "🍲 Kitchen Pro",
            ("cooking", "minor"): "🥄 Cooking Starter",
            ("cooking", "micro"): "🍪 Quick Cook",
            # Gaming
            ("gaming", "epic"): "🎮 Gaming Champion",
            ("gaming", "grand"): "🏅 Grand Gamer",
            ("gaming", "major"): "🕹️ Game Master",
            ("gaming", "minor"): "🎲 Game Starter",
            ("gaming", "micro"): "🃏 Quick Player",
            # Social
            ("social", "epic"): "🤝 Social Star",
            ("social", "grand"): "🏅 Grand Connector",
            ("social", "major"): "💬 Social Achiever",
            ("social", "minor"): "👋 Social Starter",
            ("social", "micro"): "📱 Quick Chat",
            # Travel
            ("travel", "epic"): "🌍 World Explorer",
            ("travel", "grand"): "🏅 Grand Traveler",
            ("travel", "major"): "🧳 Journey Maker",
            ("travel", "minor"): "🚗 Travel Starter",
            ("travel", "micro"): "🗺️ Quick Trip",
            # Default (fallback)
            ("default", "epic"): "🏆 Legendary Achiever",
            ("default", "grand"): "⭐ Grand Performer",
            ("default", "major"): "✨ Progress Maker",
            ("default", "minor"): "🔹 Starter",
            ("default", "micro"): "🔸 Quick Session",
        }

        duration_level = IntensityLevels.get_duration_level(duration).name.lower()
        badge_key = (intent_category, duration_level)

        # Check for emotion-based special badges first
        if intent_emotion and reflection_emotion:
            # Emotion journey badges (when emotions change significantly)
            if intent_emotion.lower() != reflection_emotion.lower():
                emotion_journey_badges = {
                    ("focus", "accomplished"): "🎯➡️🏆 Focus Champion",
                    ("creation", "fulfilled"): "💡➡️✨ Creative Master",
                    ("study", "energized"): "📚➡️⚡ Learning Dynamo",
                    ("work", "accomplished"): "💼➡️🎉 Task Conqueror",
                    ("frustrated", "peaceful"): "😤➡️🕯️ Transformation Hero",
                    ("tired", "energized"): "😴➡️⚡ Energy Transformer",
                }

                journey_key = (intent_emotion.lower(), reflection_emotion.lower())
                if journey_key in emotion_journey_badges:
                    return emotion_journey_badges[journey_key]

            # High-energy completion badges
            high_energy_emotions = [
                "accomplished",
                "fulfilled",
                "energized",
                "excited",
                "peaceful",
            ]
            if duration_level in ["epic", "grand"]:
                best_emotion_match = IntentData.find_best_match_fuzzy(
                    reflection_emotion.lower(), high_energy_emotions
                )
                if best_emotion_match:
                    return f"🌟 {reflection_emotion.title()} Master"

        # Fallback to standard badges
        if badge_key in badges:
            return badges[badge_key]
        elif duration_level == "epic":
            return "🏆 Legendary Achiever"
        elif duration_level == "major":
            return "⭐ Great Performer"
        else:
            return "✨ Progress Maker"
