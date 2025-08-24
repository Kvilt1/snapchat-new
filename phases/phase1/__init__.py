"""
Phase 1: Media Mapping
Refactored module structure for better maintainability.
"""

# Main entry point
from .orchestrator import run_phase1, load_all_conversations

# Statistics
from .stats import Phase1Stats

# Media ID extraction (T1.1)
from .media_id_extractor import (
    split_pipe_separated_ids,
    extract_media_ids_from_messages,
    extract_media_id_from_filename
)

# File mapping (T1.2)
from .file_mapper import create_media_index

# MP4 processing (T1.3)
from .mp4_processor import (
    parse_mp4_timestamp_binary,
    parse_mp4_timestamp_ffprobe,
    extract_mp4_timestamp
)

# Timestamp matching (T1.4)
from .timestamp_matcher import (
    build_millisecond_index,
    find_closest_message_binary,
    match_mp4_timestamps
)

__all__ = [
    # Main function
    'run_phase1',
    'Phase1Stats',
    
    # Data loading
    'load_all_conversations',
    
    # Media ID extraction
    'split_pipe_separated_ids',
    'extract_media_ids_from_messages',
    'extract_media_id_from_filename',
    
    # File mapping
    'create_media_index',
    
    # MP4 processing
    'parse_mp4_timestamp_binary',
    'parse_mp4_timestamp_ffprobe',
    'extract_mp4_timestamp',
    
    # Timestamp matching
    'build_millisecond_index',
    'find_closest_message_binary',
    'match_mp4_timestamps'
]