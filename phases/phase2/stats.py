"""
Phase 2 Statistics tracking.
"""

from typing import Dict, Any, List


class Phase2Stats:
    """Statistics for Phase 2 processing."""
    
    def __init__(self):
        self.files_copied_to_conversations = 0
        self.files_orphaned = 0
        self.conversations_updated = 0
        self.groups_updated = 0
        self.json_references_updated = 0
        self.directories_created = 0
        self.orphaned_dir_created = False
        self.errors: List[str] = []
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert statistics to dictionary for reporting."""
        return {
            "files_copied_to_conversations": self.files_copied_to_conversations,
            "files_orphaned": self.files_orphaned,
            "conversations_updated": self.conversations_updated,
            "groups_updated": self.groups_updated,
            "json_references_updated": self.json_references_updated,
            "directories_created": self.directories_created,
            "orphaned_dir_created": self.orphaned_dir_created,
            "errors": self.errors
        }