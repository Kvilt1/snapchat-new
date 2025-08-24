"""
Phase 0 Statistics Tracking Module.
Manages all statistics for the initial setup phase.
"""

from typing import Dict, Any


class Phase0Stats:
    """Statistics tracker for Phase 0 initial setup operations."""
    
    def __init__(self):
        """Initialize Phase 0 statistics."""
        self.media_files_copied = 0
        self.overlay_pairs_merged = 0
        self.individual_conversations = 0
        self.group_conversations = 0
        self.total_messages = 0
        self.total_snaps = 0
        self.media_ids_found = 0
        self.files_in_chat_media = 0
        self.duration = 0.0
        self.memory_used_mb = 0.0
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            "media_files_copied": self.media_files_copied,
            "overlay_pairs_merged": self.overlay_pairs_merged,
            "individual_conversations": self.individual_conversations,
            "group_conversations": self.group_conversations,
            "total_messages": self.total_messages,
            "total_snaps": self.total_snaps,
            "media_ids_found": self.media_ids_found,
            "files_in_chat_media": self.files_in_chat_media,
            "duration": self.duration,
            "memory_used_mb": self.memory_used_mb
        }