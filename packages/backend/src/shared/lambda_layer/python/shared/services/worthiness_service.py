"""
Enhanced AI Worthiness Calculation Service

Calculates pulse worthiness based on user investment and content quality.
Focuses on length, duration, reflection depth, and user engagement.
"""

import re
from typing import Dict, Any
from aws_lambda_powertools import Logger

logger = Logger()

# Investment-focused weights
WORTHINESS_WEIGHTS = {
    "content_length": 0.4,  # Length of intent + reflection (user effort)
    "duration": 0.3,  # Session duration (dedication)
    "reflection_depth": 0.2,  # Reflection quality and depth
    "frequency_bonus": 0.1,  # Daily engagement bonus
}

# Quality thresholds
EXCEPTIONAL_THRESHOLD = 0.8  # Always enhance if budget allows
GOOD_THRESHOLD = 0.4  # Probabilistic enhancement

# Strong words that indicate breakthrough/innovation
BREAKTHROUGH_WORDS = [
    "breakthrough",
    "innovation",
    "revolutionary",
    "novel",
    "pioneering",
    "discovery",
    "groundbreaking",
    "cutting-edge",
    "advanced",
    "sophisticated",
    "exceptional",
    "remarkable",
    "extraordinary",
    "unprecedented",
    "milestone",
    "achievement",
    "success",
    "triumph",
    "victory",
    "accomplishment",
]

# Technical domain indicators
TECHNICAL_DOMAINS = {
    "ai_ml": [
        "ai",
        "artificial intelligence",
        "machine learning",
        "ml",
        "neural",
        "deep learning",
        "transformer",
        "algorithm",
        "model",
        "training",
        "inference",
        "data science",
    ],
    "research": [
        "research",
        "study",
        "analysis",
        "investigation",
        "experiment",
        "hypothesis",
        "methodology",
        "findings",
        "results",
        "conclusion",
        "publication",
    ],
    "engineering": [
        "engineering",
        "development",
        "coding",
        "programming",
        "software",
        "system",
        "architecture",
        "design",
        "implementation",
        "optimization",
        "performance",
    ],
    "creative": [
        "creative",
        "design",
        "art",
        "writing",
        "content",
        "visual",
        "aesthetic",
        "inspiration",
        "imagination",
        "artistic",
        "innovative design",
    ],
    "business": [
        "strategy",
        "planning",
        "meeting",
        "presentation",
        "analysis",
        "decision",
        "leadership",
        "management",
        "collaboration",
        "teamwork",
    ],
}

# Emotion progression indicators
POSITIVE_EMOTIONS = [
    "accomplished",
    "fulfilled",
    "energized",
    "breakthrough",
    "innovative",
    "creative",
    "excited",
    "motivated",
    "inspired",
    "confident",
    "proud",
    "satisfied",
    "successful",
    "triumphant",
    "exhilarated",
]

NEGATIVE_EMOTIONS = [
    "frustrated",
    "tired",
    "stuck",
    "confused",
    "overwhelmed",
    "disappointed",
    "discouraged",
    "stressed",
    "anxious",
    "blocked",
]


class WorthinessCalculator:
    def __init__(self, budget_service=None):
        self.budget_service = budget_service

    def calculate_worthiness(self, pulse_data: Dict[str, Any], user_id: str) -> float:
        """Calculate AI worthiness score (0-1) based on investment and quality"""

        # Extract key data
        intent = pulse_data.get("intent", "")
        reflection = pulse_data.get("reflection", "")
        duration_seconds = pulse_data.get("duration_seconds", 0)
        intent_emotion = pulse_data.get("intent_emotion", "")
        reflection_emotion = pulse_data.get("reflection_emotion", "")

        # Calculate component scores
        length_score = self._calculate_length_score(intent, reflection)
        duration_score = self._calculate_duration_score(duration_seconds)
        depth_score = self._calculate_reflection_depth(
            intent, reflection, intent_emotion, reflection_emotion
        )
        frequency_score = self._calculate_frequency_bonus(user_id)

        # Calculate weighted worthiness
        worthiness = (
            length_score * WORTHINESS_WEIGHTS["content_length"]
            + duration_score * WORTHINESS_WEIGHTS["duration"]
            + depth_score * WORTHINESS_WEIGHTS["reflection_depth"]
            + frequency_score * WORTHINESS_WEIGHTS["frequency_bonus"]
        )

        logger.info(
            f"Worthiness calculation for user {user_id}: "
            f"length={length_score:.3f}, duration={duration_score:.3f}, "
            f"depth={depth_score:.3f}, frequency={frequency_score:.3f}, "
            f"total={worthiness:.3f}"
        )

        return min(1.0, worthiness)  # Cap at 1.0

    def _calculate_length_score(self, intent: str, reflection: str) -> float:
        """Calculate score based on content length (indicates user effort)"""
        total_chars = len(intent) + len(reflection)

        # Progressive scoring
        if total_chars >= 500:  # 500+ chars = max score (significant effort)
            return 1.0
        elif total_chars >= 300:  # 300-499 chars = high score
            return 0.8 + (total_chars - 300) / 200 * 0.2
        elif total_chars >= 150:  # 150-299 chars = medium score
            return 0.5 + (total_chars - 150) / 150 * 0.3
        elif total_chars >= 50:  # 50-149 chars = low score
            return 0.2 + (total_chars - 50) / 100 * 0.3
        else:  # <50 chars = minimal score
            return total_chars / 50 * 0.2

    def _calculate_duration_score(self, duration_seconds: int) -> float:
        """Calculate score based on session duration (indicates dedication)"""
        duration_hours = float(duration_seconds) / 3600

        # Progressive scoring
        if duration_hours >= 2.0:  # 2+ hours = max score (deep work)
            return 1.0
        elif duration_hours >= 1.0:  # 1-2 hours = high score
            return 0.7 + (duration_hours - 1.0) * 0.3
        elif duration_hours >= 0.5:  # 30min-1hr = medium score
            return 0.4 + (duration_hours - 0.5) * 0.6
        elif duration_hours >= 0.25:  # 15-30min = low score
            return 0.2 + (duration_hours - 0.25) * 0.8
        else:  # <15min = minimal score
            return duration_hours / 0.25 * 0.2

    def _calculate_reflection_depth(
        self, intent: str, reflection: str, intent_emotion: str, reflection_emotion: str
    ) -> float:
        """Calculate reflection depth based on content quality and emotional journey"""

        score = 0.0
        content = (intent + " " + reflection).lower()

        # 1. Breakthrough/innovation words (0-0.3)
        breakthrough_count = sum(1 for word in BREAKTHROUGH_WORDS if word in content)
        breakthrough_score = min(0.3, breakthrough_count * 0.1)
        score += breakthrough_score

        # 2. Technical domain detection (0-0.2)
        domain_score = 0.0
        for domain, keywords in TECHNICAL_DOMAINS.items():
            domain_matches = sum(1 for keyword in keywords if keyword in content)
            if domain_matches > 0:
                domain_score = min(0.2, domain_matches * 0.05)
                break
        score += domain_score

        # 3. Emotional progression (0-0.3)
        emotion_score = self._calculate_emotion_score(
            intent_emotion, reflection_emotion
        )
        score += emotion_score

        # 4. Specificity and detail (0-0.2)
        specificity_score = self._calculate_specificity_score(content)
        score += specificity_score

        return min(1.0, score)

    def _calculate_emotion_score(self, start_emotion: str, end_emotion: str) -> float:
        """Score emotional journey and final state"""
        score = 0.0

        # Positive end emotion
        if end_emotion.lower() in [e.lower() for e in POSITIVE_EMOTIONS]:
            score += 0.15

        # Emotional progression (negative to positive)
        if start_emotion.lower() in [
            e.lower() for e in NEGATIVE_EMOTIONS
        ] and end_emotion.lower() in [e.lower() for e in POSITIVE_EMOTIONS]:
            score += 0.15  # Bonus for overcoming challenges

        # Special high-value emotions
        if end_emotion.lower() in [
            "breakthrough",
            "innovative",
            "accomplished",
            "exhilarated",
        ]:
            score += 0.1  # Extra bonus for exceptional emotional outcomes

        return score

    def _calculate_specificity_score(self, content: str) -> float:
        """Score content specificity and detail"""
        score = 0.0

        # Numbers and metrics (indicates concrete results)
        number_pattern = (
            r"\d+(?:\.\d+)?(?:%|percent|hours?|minutes?|seconds?|mb|gb|tb|kb)"
        )
        if re.search(number_pattern, content):
            score += 0.05

        # Technical terms and jargon
        technical_patterns = [
            r"\b\w+(?:API|SDK|ML|AI|DB|SQL|HTTP|JSON|XML|CSS|HTML|JS)\b",
            r"\b(?:algorithm|architecture|framework|methodology|implementation)\b",
            r"\b(?:performance|optimization|efficiency|scalability|reliability)\b",
        ]
        for pattern in technical_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                score += 0.03

        # Detailed descriptions (longer sentences)
        sentences = content.split(".")
        long_sentences = [s for s in sentences if len(s.strip()) > 80]
        if len(long_sentences) >= 2:
            score += 0.05

        # Action verbs (indicates active work)
        action_verbs = [
            "implemented",
            "developed",
            "created",
            "built",
            "designed",
            "achieved",
            "completed",
            "solved",
            "optimized",
            "improved",
        ]
        action_count = sum(1 for verb in action_verbs if verb in content.lower())
        score += min(0.05, action_count * 0.02)

        return score

    def _calculate_frequency_bonus(self, user_id: str) -> float:
        """Calculate bonus based on user's daily engagement"""
        if not self.budget_service:
            return 0.5  # Default moderate bonus

        try:
            daily_count = self.budget_service.get_daily_pulse_count(user_id)

            # Progressive bonus for engagement
            if daily_count >= 5:  # 5+ pulses = max bonus (very engaged)
                return 1.0
            elif daily_count >= 3:  # 3-4 pulses = high bonus
                return 0.7 + (daily_count - 3) * 0.15
            elif daily_count >= 2:  # 2 pulses = medium bonus
                return 0.5 + (daily_count - 2) * 0.2
            else:  # 1 pulse = low bonus
                return 0.3

        except Exception as e:
            logger.warning(f"Error calculating frequency bonus for user {user_id}: {e}")
            return 0.5  # Default on error

    def get_worthiness_explanation(
        self, pulse_data: Dict[str, Any], user_id: str
    ) -> Dict[str, Any]:
        """Get detailed explanation of worthiness calculation"""
        intent = pulse_data.get("intent", "")
        reflection = pulse_data.get("reflection", "")
        duration_seconds = pulse_data.get("duration_seconds", 0)

        length_score = self._calculate_length_score(intent, reflection)
        duration_score = self._calculate_duration_score(duration_seconds)
        depth_score = self._calculate_reflection_depth(
            intent,
            reflection,
            pulse_data.get("intent_emotion", ""),
            pulse_data.get("reflection_emotion", ""),
        )
        frequency_score = self._calculate_frequency_bonus(user_id)

        total_worthiness = (
            length_score * WORTHINESS_WEIGHTS["content_length"]
            + duration_score * WORTHINESS_WEIGHTS["duration"]
            + depth_score * WORTHINESS_WEIGHTS["reflection_depth"]
            + frequency_score * WORTHINESS_WEIGHTS["frequency_bonus"]
        )

        return {
            "total_worthiness": min(1.0, total_worthiness),
            "components": {
                "content_length": {
                    "score": length_score,
                    "weight": WORTHINESS_WEIGHTS["content_length"],
                    "contribution": length_score * WORTHINESS_WEIGHTS["content_length"],
                    "description": f"{len(intent + reflection)} characters",
                },
                "duration": {
                    "score": duration_score,
                    "weight": WORTHINESS_WEIGHTS["duration"],
                    "contribution": duration_score * WORTHINESS_WEIGHTS["duration"],
                    "description": f"{duration_seconds/3600:.1f} hours",
                },
                "reflection_depth": {
                    "score": depth_score,
                    "weight": WORTHINESS_WEIGHTS["reflection_depth"],
                    "contribution": depth_score
                    * WORTHINESS_WEIGHTS["reflection_depth"],
                    "description": "Content quality and emotional journey",
                },
                "frequency_bonus": {
                    "score": frequency_score,
                    "weight": WORTHINESS_WEIGHTS["frequency_bonus"],
                    "contribution": frequency_score
                    * WORTHINESS_WEIGHTS["frequency_bonus"],
                    "description": "Daily engagement level",
                },
            },
            "thresholds": {
                "exceptional": EXCEPTIONAL_THRESHOLD,
                "good": GOOD_THRESHOLD,
            },
            "recommendation": (
                "guaranteed"
                if total_worthiness >= EXCEPTIONAL_THRESHOLD
                else "probable" if total_worthiness >= GOOD_THRESHOLD else "unlikely"
            ),
        }
