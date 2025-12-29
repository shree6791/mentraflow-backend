"""Application constants.

This file centralizes all application constants that don't need to be in .env.
Constants that are configuration (like API keys, URLs) should remain in .env.
Constants that are business logic defaults should be here.
"""

# ============================================================================
# Flashcard Constants
# ============================================================================

# Valid flashcard generation modes
FLASHCARD_MODES = {"key_terms", "qa", "cloze"}

# Default flashcard mode
DEFAULT_FLASHCARD_MODE = "qa"

# Mapping from flashcard mode to card type
FLASHCARD_MODE_TO_CARD_TYPE = {
    "key_terms": "basic",
    "qa": "qa",
    "cloze": "cloze",
}

# Valid card types
CARD_TYPES = {"basic", "qa", "cloze"}

# ============================================================================
# User Preference Defaults
# ============================================================================

# Default user preference values
DEFAULT_AUTO_INGEST_ON_UPLOAD = True
DEFAULT_AUTO_SUMMARY_AFTER_INGEST = True
DEFAULT_AUTO_FLASHCARDS_AFTER_INGEST = True
# Note: DEFAULT_FLASHCARD_MODE is used for both flashcard mode and preference default

# ============================================================================
# Summary Constants
# ============================================================================

# Default summary max bullets
DEFAULT_SUMMARY_MAX_BULLETS = 7

# Summary max bullets range
SUMMARY_MAX_BULLETS_MIN = 1
SUMMARY_MAX_BULLETS_MAX = 20

# ============================================================================
# Retrieval Constants
# ============================================================================

# Default top_k for semantic search
DEFAULT_TOP_K = 8

# Default top_k range
TOP_K_MIN = 1
TOP_K_MAX = 50

# ============================================================================
# Chunking Constants
# ============================================================================

# Default chunk size and overlap
DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 120

