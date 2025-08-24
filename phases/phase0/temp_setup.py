"""
Phase 0 Temporary Directory Setup Module.
Handles creation and management of temporary directories.
"""

import logging
from pathlib import Path
from utils.file_operations import ensure_directory

logger = logging.getLogger(__name__)


def create_temp_directory(output_dir: Path) -> Path:
    """
    Create temporary directory for media files.
    
    Args:
        output_dir: Base output directory
        
    Returns:
        Path to temp directory
    """
    temp_dir = output_dir / "temp_media"
    ensure_directory(temp_dir)
    logger.info(f"Created temp directory: {temp_dir}")
    return temp_dir