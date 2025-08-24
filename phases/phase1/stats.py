"""
Phase 1 Statistics Tracking Module.
Manages all statistics for the media mapping phase.
"""

from typing import List, Dict, Any


class Phase1Stats:
    """Statistics tracker for Phase 1 media mapping operations."""
    
    def __init__(self):
        """Initialize Phase 1 statistics."""
        # Media ID statistics
        self.total_media_ids = 0
        self.ids_mapped = 0
        self.ids_unmapped = 0
        self.unique_ids = 0
        self.pipe_separated_count = 0
        
        # MP4 processing statistics
        self.mp4s_processed = 0
        self.mp4s_matched = 0
        
        # File statistics
        self.total_media_files = 0
        self.orphaned_files = 0
        
        # Processing statistics
        self.conversations_processed = 0
        self.groups_processed = 0
        
        # Error tracking
        self.errors: List[str] = []
        
        # Timing and resource information
        self.duration = 0.0
        self.memory_used_mb = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert statistics to dictionary format."""
        return {
            "total_media_ids": self.total_media_ids,
            "ids_mapped": self.ids_mapped,
            "ids_unmapped": self.ids_unmapped,
            "unique_ids": self.unique_ids,
            "pipe_separated_count": self.pipe_separated_count,
            "mp4s_processed": self.mp4s_processed,
            "mp4s_matched": self.mp4s_matched,
            "total_media_files": self.total_media_files,
            "orphaned_files": self.orphaned_files,
            "conversations_processed": self.conversations_processed,
            "groups_processed": self.groups_processed,
            "duration": self.duration,
            "memory_used_mb": self.memory_used_mb,
            "errors": self.errors
        }