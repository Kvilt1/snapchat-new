"""
Phase 2 Orchestrator
Main entry point for Phase 2: Media Organization
"""

import logging
from pathlib import Path

from .stats import Phase2Stats
from .directory import setup_directory_structure
from .media_copier import load_phase1_mapping, process_all_conversations
from .json_updater import process_json_updates
from .orphan_handler import process_orphaned_files
from .validator import run_phase2_validation
from .cleanup import cleanup_temp_media

logger = logging.getLogger(__name__)


def run_phase2(
    output_dir: Path,
    max_workers: int = 4
) -> Phase2Stats:
    """
    Run Phase 2: Media Organization.
    
    Args:
        output_dir: Output directory
        max_workers: Number of parallel workers
        
    Returns:
        Phase 2 statistics
    """
    stats = Phase2Stats()
    logger.info("Starting Phase 2: Media Organization")
    
    # T2.1: Set up directory structure
    if not setup_directory_structure(output_dir, stats):
        logger.error("Failed to set up directory structure")
        return stats
    
    # T2.2: Media File Copying
    logger.info("\n--- T2.2: Media File Copying ---")
    
    # Load Phase 1 mapping data
    mapping_data = load_phase1_mapping(output_dir)
    if not mapping_data:
        logger.error("Cannot proceed without Phase 1 mapping data")
        stats.errors.append("Phase 1 mapping data not found")
        return stats
    
    # Copy media files to conversation folders
    process_all_conversations(output_dir, mapping_data, stats, max_workers)
    
    logger.info(f"Moved {stats.files_copied_to_conversations} files to conversations")
    logger.info(f"Updated {stats.conversations_updated} individual conversations")
    logger.info(f"Updated {stats.groups_updated} group conversations")
    
    # T2.3: JSON Reference Updates
    process_json_updates(output_dir, mapping_data, stats)
    
    # T2.4: Orphaned File Handling
    process_orphaned_files(output_dir, mapping_data, stats)
    
    # T2.5: Phase 2 Validation
    validation_passed = run_phase2_validation(output_dir, stats)
    
    # T2.6: Cleanup temp_media directory
    cleanup_temp_media(output_dir, stats)
    
    logger.info(f"\nPhase 2 Complete!")
    logger.info(f"  Directories created: {stats.directories_created}")
    logger.info(f"  Files copied to conversations: {stats.files_copied_to_conversations}")
    logger.info(f"  Files orphaned: {stats.files_orphaned}")
    logger.info(f"  Conversations updated: {stats.conversations_updated}")
    logger.info(f"  Groups updated: {stats.groups_updated}")
    logger.info(f"  JSON references updated: {stats.json_references_updated}")
    
    if validation_passed and not stats.errors:
        logger.info("✅ Phase 2 completed successfully!")
    elif validation_passed:
        logger.warning("⚠️ Phase 2 completed with warnings")
    else:
        logger.error("❌ Phase 2 validation failed")
    
    if stats.errors:
        logger.warning(f"  Total errors: {len(stats.errors)}")
        for error in stats.errors[:5]:  # Show first 5 errors
            logger.warning(f"    - {error}")
    
    return stats