"""
File operations utilities for Snapchat Merger V2
Simplified from snapchat_merger/file_operations.py
"""

import shutil
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
import hashlib

logger = logging.getLogger(__name__)


def ensure_directory(path: Path) -> None:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        path: Directory path to ensure exists
    """
    try:
        path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Ensured directory exists: {path}")
    except Exception as e:
        logger.error(f"Failed to create directory {path}: {e}")
        raise


def copy_media_files(
    source_dir: Path,
    dest_dir: Path,
    exclude_pattern: str = "thumbnail~",
    preserve_metadata: bool = True
) -> Dict[str, Any]:
    """
    Copy media files from source to destination, excluding thumbnails.
    
    Args:
        source_dir: Source directory containing media files
        dest_dir: Destination directory
        exclude_pattern: Pattern to exclude (default: "thumbnail~")
        preserve_metadata: Whether to preserve file metadata
        
    Returns:
        Dictionary with statistics about the copy operation
    """
    ensure_directory(dest_dir)
    
    stats = {
        "total_files": 0,
        "copied": 0,
        "excluded": 0,
        "failed": 0,
        "total_size": 0
    }
    
    try:
        for file_path in source_dir.iterdir():
            if not file_path.is_file():
                continue
                
            stats["total_files"] += 1
            
            # Check if file should be excluded
            if exclude_pattern and exclude_pattern in file_path.name:
                stats["excluded"] += 1
                logger.debug(f"Excluded: {file_path.name}")
                continue
            
            # Copy file
            dest_path = dest_dir / file_path.name
            try:
                if preserve_metadata:
                    shutil.copy2(file_path, dest_path)
                else:
                    shutil.copy(file_path, dest_path)
                    
                stats["copied"] += 1
                stats["total_size"] += file_path.stat().st_size
                
                if stats["copied"] % 100 == 0:
                    logger.info(f"Copied {stats['copied']} files...")
                    
            except Exception as e:
                stats["failed"] += 1
                logger.error(f"Failed to copy {file_path.name}: {e}")
    
    except Exception as e:
        logger.error(f"Error during file copy operation: {e}")
        raise
    
    logger.info(f"Copy complete: {stats['copied']} copied, "
                f"{stats['excluded']} excluded, {stats['failed']} failed")
    
    return stats


def move_file(source: Path, dest: Path) -> bool:
    """
    Move a file from source to destination.
    
    Args:
        source: Source file path
        dest: Destination file path
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure destination directory exists
        ensure_directory(dest.parent)
        
        # Move the file
        shutil.move(str(source), str(dest))
        logger.debug(f"Moved {source} to {dest}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to move {source} to {dest}: {e}")
        return False


def get_file_hash(file_path: Path, algorithm: str = "md5") -> Optional[str]:
    """
    Calculate hash of a file.
    
    Args:
        file_path: Path to file
        algorithm: Hash algorithm to use (default: "md5")
        
    Returns:
        Hash string or None if error
    """
    try:
        hash_func = hashlib.new(algorithm)
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hash_func.update(chunk)
        return hash_func.hexdigest()
    except Exception as e:
        logger.error(f"Failed to hash {file_path}: {e}")
        return None


def count_files(directory: Path, pattern: Optional[str] = None) -> int:
    """
    Count files in a directory.
    
    Args:
        directory: Directory to count files in
        pattern: Optional pattern to match
        
    Returns:
        Number of files
    """
    if not directory.exists():
        return 0
    
    if pattern:
        return len(list(directory.glob(pattern)))
    else:
        return len([f for f in directory.iterdir() if f.is_file()])