"""
Phase 2 Orphaned File Handling - T2.4
Handles identification and processing of unmapped/orphaned files.
"""

import logging
import json
import shutil
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from .stats import Phase2Stats

logger = logging.getLogger(__name__)


def identify_unmapped_files(
    temp_media_dir: Path,
    mapping_data: Dict[str, Any]
) -> List[Path]:
    """
    Identify files that were not mapped in Phase 1.
    
    T2.4.1: Identify unmapped files
    
    Args:
        temp_media_dir: Directory containing all media files
        mapping_data: Phase 1 mapping data
        
    Returns:
        List of unmapped file paths
    """
    unmapped_files = []
    
    if not temp_media_dir.exists():
        logger.warning(f"Temp media directory not found: {temp_media_dir}")
        return unmapped_files
    
    # Get mapped files from Phase 1
    media_index = mapping_data.get('media_index', {})
    mapped_filenames = set(media_index.values())
    
    # Check each file in temp_media
    for file_path in temp_media_dir.iterdir():
        if file_path.is_file():
            if file_path.name not in mapped_filenames:
                unmapped_files.append(file_path)
                logger.debug(f"Unmapped file: {file_path.name}")
    
    logger.info(f"Found {len(unmapped_files)} unmapped files")
    return unmapped_files


def move_orphaned_files(
    unmapped_files: List[Path],
    orphaned_dir: Path,
    stats: Phase2Stats
) -> List[str]:
    """
    Move unmapped files to orphaned directory.
    
    T2.4.2: Move files to single orphaned directory
    
    Args:
        unmapped_files: List of unmapped file paths
        orphaned_dir: Target orphaned directory
        stats: Statistics object to update
        
    Returns:
        List of moved filenames
    """
    moved_files = []
    
    for source_file in unmapped_files:
        target_file = orphaned_dir / source_file.name
        
        try:
            # Use shutil.move to move the file
            shutil.move(str(source_file), str(target_file))
            moved_files.append(source_file.name)
            stats.files_orphaned += 1
            logger.debug(f"Moved orphaned file: {source_file.name}")
            
        except Exception as e:
            logger.error(f"Failed to move orphaned file {source_file.name}: {e}")
            stats.errors.append(f"Failed to move orphaned file: {source_file.name}")
    
    return moved_files


def generate_orphaned_report(
    orphaned_dir: Path,
    moved_files: List[str],
    stats: Phase2Stats
) -> bool:
    """
    Generate a report of orphaned files.
    
    T2.4.3: Generate orphaned report
    
    Args:
        orphaned_dir: Orphaned files directory
        moved_files: List of moved filenames
        stats: Statistics object to update
        
    Returns:
        True if report generated successfully
    """
    report_file = orphaned_dir / "orphaned_files_report.json"
    
    try:
        # Create report data
        report_data = {
            "generated_at": datetime.now().isoformat(),
            "total_files": len(moved_files),
            "files": []
        }
        
        # Add file information
        for filename in sorted(moved_files):
            file_path = orphaned_dir / filename
            file_info = {
                "filename": filename,
                "size_bytes": file_path.stat().st_size if file_path.exists() else 0
            }
            
            # Try to extract date from filename
            if len(filename) >= 10 and filename[4] == '-' and filename[7] == '-':
                try:
                    date_str = filename[:10]
                    file_info["extracted_date"] = date_str
                except:
                    pass
            
            report_data["files"].append(file_info)
        
        # Save report
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Generated orphaned files report: {report_file}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to generate orphaned report: {e}")
        stats.errors.append("Failed to generate orphaned files report")
        return False


def identify_uncopied_files(
    temp_media_dir: Path,
    output_dir: Path
) -> List[Path]:
    """
    Identify files that were not copied to any conversation or group.
    
    Args:
        temp_media_dir: Directory containing all media files
        output_dir: Base output directory
        
    Returns:
        List of uncopied file paths
    """
    uncopied_files = []
    
    if not temp_media_dir.exists():
        logger.warning(f"Temp media directory not found: {temp_media_dir}")
        return uncopied_files
    
    # Get list of all files still in temp_media
    # These are files that weren't moved to conversations/groups
    for file_path in temp_media_dir.iterdir():
        if file_path.is_file():
            uncopied_files.append(file_path)
            logger.debug(f"Uncopied file: {file_path.name}")
    
    logger.info(f"Found {len(uncopied_files)} uncopied files")
    return uncopied_files


def process_orphaned_files(
    output_dir: Path,
    mapping_data: Dict[str, Any],
    stats: Phase2Stats
) -> None:
    """
    Process all orphaned (uncopied) files.
    
    Args:
        output_dir: Base output directory
        mapping_data: Phase 1 mapping data  
        stats: Statistics object to update
    """
    logger.info("\n--- T2.4: Orphaned File Handling ---")
    
    temp_media_dir = output_dir / "temp_media"
    orphaned_dir = output_dir / "orphaned"
    
    # Ensure orphaned directory exists
    if not orphaned_dir.exists():
        logger.error("Orphaned directory not found - run T2.1 first")
        stats.errors.append("Orphaned directory not found")
        return
    
    # T2.4.1: Identify files not copied to conversations
    # These are the truly orphaned files (mapped but not referenced in any conversation)
    uncopied_files = identify_uncopied_files(temp_media_dir, output_dir)
    
    if not uncopied_files:
        logger.info("No orphaned files to process")
        return
    
    # T2.4.2: Move files to orphaned directory
    moved_files = move_orphaned_files(uncopied_files, orphaned_dir, stats)
    
    # T2.4.3: Generate orphaned report
    if moved_files:
        generate_orphaned_report(orphaned_dir, moved_files, stats)
    
    logger.info(f"Moved {len(moved_files)} orphaned files to flat directory")