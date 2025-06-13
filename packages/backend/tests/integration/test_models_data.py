from src.shared.models.data import (IntensityLevels, IntentData,
                                    MotivationalSuffixes, SentimentAdjectives)


def test_intensity_levels():
    duration = 300
    intensity_prefix = IntensityLevels.get_random_prefix_from_duration(duration)
    assert intensity_prefix is not None


def test_intent_nouns():
    intent_category = "meditation"
    action_noun = IntentData.get_action_noun(intent_category)
    assert action_noun is not None

    emoji = IntentData.get_emoji(intent_category)
    assert emoji is not None


def test_synonyms():
    intent_category = "exercise"
    synonym = IntentData.get_synonym_for_noun(intent_category)
    assert synonym is not None
    assert synonym != "default"  # Ensure we get a valid synonym


def test_extract_intent_category():
    intent = "I want to meditate"
    intent_category = IntentData.extract_intent_category(intent)
    assert intent_category is not None
    assert intent_category == "meditation"  # Assuming "meditation" is a valid category


def test_intent_data():
    intent_nouns = IntentData.intent_nouns()
    assert isinstance(intent_nouns, dict)
    assert len(intent_nouns) > 0  # Ensure we have some intent nouns

    intent_emojis = IntentData.intent_emojis()
    assert isinstance(intent_emojis, dict)
    assert len(intent_emojis) > 0  # Ensure we have some intent emojis


def test_intent_data_cache():
    # Test caching functionality
    intent_nouns_1 = IntentData.intent_nouns()
    intent_nouns_2 = IntentData.intent_nouns()
    assert intent_nouns_1 is intent_nouns_2  # Should return the same cached object

    intent_emojis_1 = IntentData.intent_emojis()
    intent_emojis_2 = IntentData.intent_emojis()
    assert intent_emojis_1 is intent_emojis_2  # Should return the same cached object


def test_intent_data_synonyms():
    # Test synonyms functionality
    synonym = IntentData.get_synonym_for_noun("exercise")
    assert synonym is not None
    assert synonym != "default"  # Ensure we get a valid synonym

    # Test with a noun that has no synonym
    no_synonym = IntentData.get_synonym_for_noun("nonexistentnoun")
    assert no_synonym == "default"  # Should return default if no synonym exists


def test_intent_data_extract_intent_category():
    # Test extracting intent category
    intent = "I want to exercise"
    intent_category = IntentData.extract_intent_category(intent)
    assert intent_category is not None
    assert intent_category == "exercise"  # Assuming "exercise" is a valid category

    # Test with an unknown intent
    unknown_intent = "I want to do something"
    unknown_category = IntentData.extract_intent_category(unknown_intent)
    assert unknown_category == "default"  # Should return default if no category matches


def test_sentiment_adjectives():
    # Test sentiment adjectives functionality
    reflection = "I feel great after my workout!"
    sentiment_adjective = SentimentAdjectives.get_random_sentiment_adjective(reflection)
    assert sentiment_adjective is not None
    assert isinstance(sentiment_adjective, str)  # Should return a string adjective


def test_motivational_suffixes():
    # Test motivational suffixes functionality
    motivational_suffix = MotivationalSuffixes.get_random_suffix()
    assert motivational_suffix is not None
    assert isinstance(motivational_suffix, str)  # Should return a string suffix
    assert len(motivational_suffix) > 0  # Ensure the suffix is not empty
