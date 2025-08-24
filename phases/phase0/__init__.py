"""
Phase 0: Initial Setup
Refactored module structure for better maintainability.
"""

# Main entry point
from .orchestrator import run_phase0

# Statistics
from .stats import Phase0Stats

# Temp setup
from .temp_setup import create_temp_directory

# User mapping
from .user_mapper import build_user_display_map

# Conversation merging
from .conversation_merger import (
    add_message_type,
    merge_conversations
)

# Conversation splitting
from .conversation_splitter import (
    is_group_conversation,
    get_latest_timestamp,
    generate_conversation_folder_name,
    write_conversation_file,
    split_conversations
)

# Overlay processing
from .overlay_processor import (
    detect_overlay_pairs,
    merge_overlay_pairs
)

__all__ = [
    # Main function
    'run_phase0',
    'Phase0Stats',
    
    # Temp setup
    'create_temp_directory',
    
    # User mapping
    'build_user_display_map',
    
    # Conversation merging
    'add_message_type',
    'merge_conversations',
    
    # Conversation splitting
    'is_group_conversation',
    'get_latest_timestamp',
    'generate_conversation_folder_name',
    'write_conversation_file',
    'split_conversations',
    
    # Overlay processing
    'detect_overlay_pairs',
    'merge_overlay_pairs'
]