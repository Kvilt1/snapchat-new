"""
Phase 2 Validation - T2.5
Handles validation of Phase 2 processing results.
"""

import logging
import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

from .stats import Phase2Stats

logger = logging.getLogger(__name__)


def verify_file_counts(
    output_dir: Path,
    stats: Phase2Stats
) -> Dict[str, int]:
    """
    Verify file counts across all directories.
    
    T2.5.1: Verify file counts
    
    Args:
        output_dir: Base output directory
        stats: Statistics object
        
    Returns:
        Dictionary with file counts
    """
    counts = {
        "temp_media": 0,
        "conversations": 0,
        "groups": 0,
        "orphaned": 0,
        "total_processed": 0
    }
    
    # Count files in temp_media (original source)
    temp_media_dir = output_dir / "temp_media"
    if temp_media_dir.exists():
        counts["temp_media"] = sum(1 for f in temp_media_dir.iterdir() if f.is_file())
    
    # Count files in conversations
    conversations_dir = output_dir / "conversations"
    if conversations_dir.exists():
        for conv_folder in conversations_dir.iterdir():
            if conv_folder.is_dir():
                # Count media files in media subdirectory
                media_dir = conv_folder / "media"
                if media_dir.exists():
                    media_count = sum(1 for f in media_dir.iterdir() if f.is_file())
                    counts["conversations"] += media_count
    
    # Count files in groups
    groups_dir = output_dir / "groups"
    if groups_dir.exists():
        for group_folder in groups_dir.iterdir():
            if group_folder.is_dir():
                # Count media files in media subdirectory
                media_dir = group_folder / "media"
                if media_dir.exists():
                    media_count = sum(1 for f in media_dir.iterdir() if f.is_file())
                    counts["groups"] += media_count
    
    # Count files in orphaned
    orphaned_dir = output_dir / "orphaned"
    if orphaned_dir.exists():
        # Count all files except the report
        counts["orphaned"] = sum(1 for f in orphaned_dir.iterdir() 
                               if f.is_file() and f.name != "orphaned_files_report.json")
    
    counts["total_processed"] = counts["conversations"] + counts["groups"] + counts["orphaned"]
    
    return counts


def check_media_references(
    output_dir: Path,
    stats: Phase2Stats
) -> bool:
    """
    Check that all media references in JSONs are valid.
    
    T2.5.2: Check media references
    
    Args:
        output_dir: Base output directory
        stats: Statistics object
        
    Returns:
        True if all references are valid
    """
    all_valid = True
    invalid_refs = []
    
    # Check conversations
    conversations_dir = output_dir / "conversations"
    if conversations_dir.exists():
        for conv_folder in conversations_dir.iterdir():
            if conv_folder.is_dir():
                conv_file = conv_folder / "conversation.json"
                if conv_file.exists():
                    with open(conv_file, 'r', encoding='utf-8') as f:
                        conv_data = json.load(f)
                    
                    for message in conv_data.get('messages', []):
                        for location in message.get('media_locations', []):
                            media_file = conv_folder / location
                            if not media_file.exists():
                                all_valid = False
                                invalid_refs.append(f"{conv_folder.name}/{location}")
    
    # Check groups
    groups_dir = output_dir / "groups"
    if groups_dir.exists():
        for group_folder in groups_dir.iterdir():
            if group_folder.is_dir():
                group_file = group_folder / "conversation.json"
                if group_file.exists():
                    with open(group_file, 'r', encoding='utf-8') as f:
                        group_data = json.load(f)
                    
                    for message in group_data.get('messages', []):
                        for location in message.get('media_locations', []):
                            media_file = group_folder / location
                            if not media_file.exists():
                                all_valid = False
                                invalid_refs.append(f"{group_folder.name}/{location}")
    
    if invalid_refs:
        logger.warning(f"Found {len(invalid_refs)} invalid media references")
        for ref in invalid_refs[:5]:  # Show first 5
            logger.warning(f"  - {ref}")
        stats.errors.append(f"Found {len(invalid_refs)} invalid media references")
    
    return all_valid


def validate_directory_structure(
    output_dir: Path,
    stats: Phase2Stats
) -> bool:
    """
    Validate the directory structure is correct.
    
    T2.5.3: Validate directory structure
    
    Args:
        output_dir: Base output directory
        stats: Statistics object
        
    Returns:
        True if structure is valid
    """
    required_dirs = [
        output_dir / "conversations",
        output_dir / "groups",
        output_dir / "orphaned"
    ]
    
    all_valid = True
    for dir_path in required_dirs:
        if not dir_path.exists():
            logger.error(f"Required directory missing: {dir_path}")
            stats.errors.append(f"Missing directory: {dir_path.name}")
            all_valid = False
        elif not dir_path.is_dir():
            logger.error(f"Path exists but is not a directory: {dir_path}")
            stats.errors.append(f"Not a directory: {dir_path.name}")
            all_valid = False
    
    return all_valid


def generate_phase2_statistics(
    output_dir: Path,
    stats: Phase2Stats,
    file_counts: Dict[str, int]
) -> None:
    """
    Generate Phase 2 statistics summary.
    
    T2.5.4: Generate Phase 2 statistics
    
    Args:
        output_dir: Base output directory
        stats: Statistics object
        file_counts: File count dictionary
    """
    summary = {
        "phase": "Phase 2: Media Organization",
        "status": "COMPLETE" if not stats.errors else "COMPLETE_WITH_ERRORS",
        "timestamp": datetime.now().isoformat(),
        "statistics": {
            "directories_created": stats.directories_created,
            "files_copied_to_conversations": stats.files_copied_to_conversations,
            "files_orphaned": stats.files_orphaned,
            "conversations_updated": stats.conversations_updated,
            "groups_updated": stats.groups_updated,
            "json_references_updated": stats.json_references_updated,
            "orphaned_dir_created": stats.orphaned_dir_created
        },
        "file_counts": file_counts,
        "errors": stats.errors
    }
    
    # Save statistics
    stats_file = output_dir / "phase2_statistics.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Generated Phase 2 statistics: {stats_file}")


def run_phase2_validation(
    output_dir: Path,
    stats: Phase2Stats
) -> bool:
    """
    Run Phase 2 validation checks.
    
    Args:
        output_dir: Base output directory
        stats: Statistics object
        
    Returns:
        True if all validations pass
    """
    logger.info("\n--- T2.5: Phase 2 Validation ---")
    
    # T2.5.1: Verify file counts
    file_counts = verify_file_counts(output_dir, stats)
    logger.info(f"File counts - Temp: {file_counts['temp_media']}, "
               f"Processed: {file_counts['total_processed']}")
    
    # T2.5.2: Check media references
    refs_valid = check_media_references(output_dir, stats)
    if refs_valid:
        logger.info("All media references are valid")
    
    # T2.5.3: Validate directory structure
    structure_valid = validate_directory_structure(output_dir, stats)
    if structure_valid:
        logger.info("Directory structure is valid")
    
    # T2.5.4: Generate Phase 2 statistics
    generate_phase2_statistics(output_dir, stats, file_counts)
    
    # Check if we processed all files
    if file_counts['temp_media'] > 0:
        if file_counts['total_processed'] == file_counts['temp_media']:
            logger.info("✅ All files accounted for")
        else:
            missing = file_counts['temp_media'] - file_counts['total_processed']
            logger.warning(f"⚠️ {missing} files unaccounted for")
            stats.errors.append(f"{missing} files unaccounted for")
    
    return refs_valid and structure_valid