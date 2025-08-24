"""
Phase 2: Media Organization
Refactored module structure for better maintainability.
"""

# Main entry point
from .orchestrator import run_phase2

# Statistics
from .stats import Phase2Stats

# Directory management (T2.1)
from .directory import (
    create_orphaned_directory,
    verify_conversation_directories,
    verify_directory_permissions,
    setup_directory_structure
)

# Media copying (T2.2)
from .media_copier import (
    load_phase1_mapping,
    get_media_files_for_conversation,
    copy_media_file,
    copy_media_to_conversation,
    process_all_conversations
)

# JSON updates (T2.3)
from .json_updater import (
    update_message_media_references,
    update_conversation_json,
    process_json_updates
)

# Orphan handling (T2.4)
from .orphan_handler import (
    identify_unmapped_files,
    move_orphaned_files,
    generate_orphaned_report,
    identify_uncopied_files,
    process_orphaned_files
)

# Validation (T2.5)
from .validator import (
    verify_file_counts,
    check_media_references,
    validate_directory_structure,
    generate_phase2_statistics,
    run_phase2_validation
)

# Cleanup (T2.6)
from .cleanup import cleanup_temp_media

__all__ = [
    # Main function
    'run_phase2',
    'Phase2Stats',
    
    # Directory management
    'create_orphaned_directory',
    'verify_conversation_directories',
    'verify_directory_permissions',
    'setup_directory_structure',
    
    # Media copying
    'load_phase1_mapping',
    'get_media_files_for_conversation',
    'copy_media_file',
    'copy_media_to_conversation',
    'process_all_conversations',
    
    # JSON updates
    'update_message_media_references',
    'update_conversation_json',
    'process_json_updates',
    
    # Orphan handling
    'identify_unmapped_files',
    'move_orphaned_files',
    'generate_orphaned_report',
    'identify_uncopied_files',
    'process_orphaned_files',
    
    # Validation
    'verify_file_counts',
    'check_media_references',
    'validate_directory_structure',
    'generate_phase2_statistics',
    'run_phase2_validation',
    
    # Cleanup
    'cleanup_temp_media'
]