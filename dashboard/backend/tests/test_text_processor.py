import pytest
from unittest.mock import patch, MagicMock
from app.etl.processors.text_processor import (
    load_stopwords, fullwidth_to_halfwidth, normalize_text,
    apply_replace_words, extract_unicode_emojis, extract_youtube_emotes,
    remove_emojis, remove_youtube_emotes, tokenize_text, process_message,
    clear_stopwords_cache
)

@pytest.fixture(autouse=True)
def cleanup_stopwords_cache():
    clear_stopwords_cache()
    yield
    clear_stopwords_cache()

def test_load_stopwords(tmp_path):
    """Test loading stopwords from file."""
    # Create temporary stopwords file
    stopwords_file = tmp_path / "stopwords.txt"
    stopwords_file.write_text("the\nis\nat", encoding="utf-8")
    
    # Test loading
    stopwords = load_stopwords(stopwords_file)
    assert "the" in stopwords
    assert "is" in stopwords
    assert "at" in stopwords
    assert len(stopwords) == 3
    
    # Test caching (should return same set object)
    stopwords2 = load_stopwords(stopwords_file)
    assert stopwords2 is stopwords


def test_fullwidth_to_halfwidth():
    """Test fullwidth to halfwidth conversion."""
    text = "Ｈｅｌｌｏ，　Ｗｏｒｌｄ！１２３"
    expected = "Hello, World!123"
    assert fullwidth_to_halfwidth(text) == expected


def test_normalize_text():
    """Test text normalization."""
    text = "  Ｈｅｌｌｏ   Ｗｏｒｌｄ  "
    # Fullwidth -> Halfwidth: "  Hello   World  "
    # Regex replace space: " Hello World "
    # Strip: "Hello World"
    # Wait, implementation:
    # 1. Fullwidth to halfwidth
    # 2. re.sub(r'\s+', ' ', text)
    # 3. text.strip()
    
    assert normalize_text(text) == "Hello World"
    assert normalize_text(None) == ""


def test_apply_replace_words():
    """Test replacing words."""
    replace_dict = {
        "kusa": "草",
        "lol": "笑"
    }
    text = "This is kusa lol"
    assert apply_replace_words(text, replace_dict) == "This is 草 笑"
    
    # Test overlapping replacements (longest match first)
    replace_dict = {
        "apple pie": "Food",
        "apple": "Fruit"
    }
    text = "I like apple pie"
    # Should replace "apple pie" not "apple"
    assert apply_replace_words(text, replace_dict) == "I like Food"


def test_extract_unicode_emojis():
    """Test extracting unicode emojis."""
    text = "Hello 😀 world 🌍"
    emojis = extract_unicode_emojis(text)
    assert "😀" in emojis
    assert "🌍" in emojis
    assert len(emojis) == 2


def test_extract_youtube_emotes():
    """Test extracting YouTube emotes."""
    emotes_json = [
        {
            "name": ":test_emote:",
            "id": "123",
            "images": [{"url": "http://example.com/emote.png"}]
        }
    ]
    emotes = extract_youtube_emotes(emotes_json)
    assert len(emotes) == 1
    assert emotes[0]["name"] == ":test_emote:"
    assert emotes[0]["url"] == "http://example.com/emote.png"
    
    assert extract_youtube_emotes(None) == []


def test_remove_emojis():
    """Test removing emojis."""
    text = "Hello 😀 world 🌍"
    assert remove_emojis(text) == "Hello  world "


def test_remove_youtube_emotes():
    """Test removing YouTube emotes."""
    text = "Hello :test_emote: world"
    emotes_json = [{"name": ":test_emote:"}]
    assert remove_youtube_emotes(text, emotes_json) == "Hello  world"
    assert remove_youtube_emotes(text, None) == text


def test_tokenize_text():
    """Test tokenization using jieba."""
    text = "我愛hololive"
    special_words = ["hololive"]
    stopwords = {"我"}
    
    tokens = tokenize_text(text, special_words, stopwords)
    assert "hololive" in tokens
    assert "愛" in tokens
    assert "我" not in tokens


@patch('app.etl.processors.text_processor.load_stopwords')
def test_process_message(mock_load_stopwords):
    """Test full message processing flow."""
    mock_load_stopwords.return_value = {"is", "the"}
    
    message = "  This is :kusa: 😀  "
    emotes_json = [{"name": ":kusa:", "images": [{"url": "url"}]}]
    replace_dict = {"This": "That"}
    special_words = ["That"]
    
    processed, tokens, unicode_emojis, youtube_emotes = process_message(
        message, emotes_json, replace_dict, special_words
    )
    
    # 1. Extract emojis: 😀
    assert "😀" in unicode_emojis
    
    # 2. Extract emotes: :kusa:
    assert youtube_emotes[0]["name"] == ":kusa:"
    
    # 3. Replace: "  That is :kusa: 😀  "
    
    # 4. Remove emojis/emotes: "  That is    "
    
    # 5. Normalize: "That is"
    assert processed == "That is"
    
    # 6. Tokenize: "That" (is is stopword)
    assert "That" in tokens
    assert "is" not in tokens
