"""
Phase 2 Directory Structure Management - T2.1
Handles creation and verification of directory structures.
"""

import logging
from pathlib import Path
from typing import Tuple

from .stats import Phase2Stats

logger = logging.getLogger(__name__)


def create_orphaned_directory(output_dir: Path) -> bool:
    """
    Create single orphaned directory with flat structure.
    
    T2.1.2: Create single orphaned directory (flat structure)
    
    Args:
        output_dir: Base output directory
        
    Returns:
        True if created successfully, False otherwise
    """
    orphaned_dir = output_dir / "orphaned"
    
    try:
        orphaned_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created orphaned directory: {orphaned_dir}")
        return True
    except Exception as e:
        logger.error(f"Failed to create orphaned directory: {e}")
        return False


def verify_conversation_directories(output_dir: Path) -> Tuple[int, int]:
    """
    Verify and count existing conversation and group directories.
    
    T2.1.1: Verify media subdirectories in conversation folders
    
    Args:
        output_dir: Base output directory
        
    Returns:
        Tuple of (conversation_count, group_count)
    """
    conversations_dir = output_dir / "conversations"
    groups_dir = output_dir / "groups"
    
    conv_count = 0
    group_count = 0
    
    # Count individual conversation directories
    if conversations_dir.exists():
        conv_count = len([d for d in conversations_dir.iterdir() if d.is_dir()])
        logger.info(f"Found {conv_count} individual conversation directories")
    else:
        logger.warning(f"Conversations directory not found: {conversations_dir}")
    
    # Count group directories
    if groups_dir.exists():
        group_count = len([d for d in groups_dir.iterdir() if d.is_dir()])
        logger.info(f"Found {group_count} group directories")
    else:
        logger.warning(f"Groups directory not found: {groups_dir}")
    
    return conv_count, group_count


def verify_directory_permissions(path: Path) -> bool:
    """
    Verify that directory has proper read/write permissions.
    
    T2.1.3: Verify permissions
    
    Args:
        path: Directory path to verify
        
    Returns:
        True if permissions are adequate, False otherwise
    """
    try:
        # Test if we can read the directory
        if not path.exists():
            logger.error(f"Directory does not exist: {path}")
            return False
            
        if not path.is_dir():
            logger.error(f"Path is not a directory: {path}")
            return False
            
        # Test read permission by listing contents
        list(path.iterdir())
        
        # Test write permission by creating a temp file
        test_file = path / ".permission_test"
        test_file.touch()
        test_file.unlink()
        
        logger.debug(f"Directory permissions verified: {path}")
        return True
        
    except PermissionError as e:
        logger.error(f"Permission error for {path}: {e}")
        return False
    except Exception as e:
        logger.error(f"Error verifying permissions for {path}: {e}")
        return False


def setup_directory_structure(output_dir: Path, stats: Phase2Stats) -> bool:
    """
    Set up the complete directory structure for Phase 2.
    
    Implements T2.1: Directory Structure
    
    Args:
        output_dir: Base output directory
        stats: Phase 2 statistics object to update
        
    Returns:
        True if all directories are set up successfully, False otherwise
    """
    logger.info("Setting up directory structure for Phase 2")
    
    success = True
    
    # T2.1.1: Verify conversation and group directories
    conv_count, group_count = verify_conversation_directories(output_dir)
    stats.directories_created = conv_count + group_count
    
    if conv_count == 0 and group_count == 0:
        logger.error("No conversation or group directories found from Phase 0")
        stats.errors.append("No conversation directories found")
        success = False
    
    # T2.1.2: Create single orphaned directory
    if create_orphaned_directory(output_dir):
        stats.orphaned_dir_created = True
    else:
        stats.errors.append("Failed to create orphaned directory")
        success = False
    
    # T2.1.3: Verify permissions for all directories
    dirs_to_verify = [
        output_dir,
        output_dir / "conversations",
        output_dir / "groups",
        output_dir / "orphaned",
        output_dir / "temp_media"
    ]
    
    for dir_path in dirs_to_verify:
        if dir_path.exists():
            if not verify_directory_permissions(dir_path):
                stats.errors.append(f"Permission error: {dir_path}")
                success = False
    
    if success:
        logger.info("✅ Directory structure setup complete")
    else:
        logger.warning("⚠️ Directory structure setup completed with errors")
    
    return success