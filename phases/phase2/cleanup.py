"""
Phase 2 Cleanup Operations - T2.6
Handles cleanup of temporary directories after processing.
"""

import logging
from pathlib import Path

from .stats import Phase2Stats

logger = logging.getLogger(__name__)


def cleanup_temp_media(output_dir: Path, stats: Phase2Stats) -> bool:
    """
    Remove empty temp_media directory after all files are moved.
    
    T2.6: Cleanup temporary directory
    
    Args:
        output_dir: Base output directory
        stats: Statistics object to update
        
    Returns:
        True if cleanup successful, False otherwise
    """
    temp_media_dir = output_dir / "temp_media"
    
    if temp_media_dir.exists():
        try:
            # Check if directory is empty
            remaining_files = list(temp_media_dir.iterdir())
            if not remaining_files:
                temp_media_dir.rmdir()
                logger.info("✅ Removed empty temp_media directory")
                return True
            else:
                # Count remaining files and directories
                file_count = sum(1 for f in remaining_files if f.is_file())
                dir_count = sum(1 for d in remaining_files if d.is_dir())
                
                if file_count > 0:
                    logger.warning(f"⚠️ Cannot remove temp_media - {file_count} files remain")
                    stats.errors.append(f"temp_media not empty: {file_count} files remain")
                if dir_count > 0:
                    logger.warning(f"⚠️ Cannot remove temp_media - {dir_count} directories remain")
                    
                return False
        except Exception as e:
            logger.error(f"Failed to remove temp_media: {e}")
            stats.errors.append(f"Failed to remove temp_media: {e}")
            return False
    else:
        logger.info("temp_media directory already removed or doesn't exist")
        return True