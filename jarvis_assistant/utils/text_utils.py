import re

def clean_text_for_tts(text: str) -> str:
    """
    Remove emoji and validate text for TTS.
    Returns None if text is not readable (e.g. only punctuation/emoji).
    """
    if not text:
        return None
        
    # Remove emoji and special unicode characters
    # Keep Chinese, English, numbers, and basic punctuation
    # Fixed escape sequence warning with raw string or correct escaping
    cleaned = re.sub(r'[^\u4e00-\u9fff\u3000-\u303fa-zA-Z0-9，。！？、；：""''（）《》\-\s,\.!?;:\'\"()]', '', text)
    
    # Remove extra whitespace
    cleaned = ' '.join(cleaned.split())
    
    # Check if there's any readable content left
    # (at least one Chinese character, letter, or number)
    if not re.search(r'[\u4e00-\u9fffa-zA-Z0-9]', cleaned):
        return None
    
    return cleaned
