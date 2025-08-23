"""
Phase 2: Media Organization
Organizes media files into conversation folders and updates references
"""

import logging
import json
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


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
        self.errors = []
        
    def to_dict(self) -> Dict[str, Any]:
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


# ====================
# T2.1: Directory Structure
# ====================

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


# ====================
# T2.2: Media File Copying
# ====================

def load_phase1_mapping(output_dir: Path) -> Optional[Dict[str, Any]]:
    """
    Load the Phase 1 mapping data from JSON file.
    
    Args:
        output_dir: Base output directory
        
    Returns:
        Mapping data dictionary or None if not found
    """
    mapping_file = output_dir / "phase1_mapping.json"
    
    if not mapping_file.exists():
        logger.error(f"Phase 1 mapping file not found: {mapping_file}")
        return None
    
    try:
        with open(mapping_file, 'r', encoding='utf-8') as f:
            mapping_data = json.load(f)
        logger.info(f"Loaded Phase 1 mapping with {len(mapping_data.get('media_index', {}))} Media IDs")
        return mapping_data
    except Exception as e:
        logger.error(f"Failed to load Phase 1 mapping: {e}")
        return None


def get_media_files_for_conversation(
    conversation_file: Path,
    mapping_data: Dict[str, Any]
) -> Tuple[List[Tuple[str, str]], Dict[int, List[Dict[str, Any]]]]:
    """
    Get list of media files that belong to a conversation.
    
    Args:
        conversation_file: Path to conversation.json
        mapping_data: Phase 1 mapping data
        
    Returns:
        Tuple of:
        - List of tuples (match_type, filename)
        - Dict of mp4_matches by message index
    """
    media_files = []
    conv_mp4_matches = {}
    
    try:
        with open(conversation_file, 'r', encoding='utf-8') as f:
            conv_data = json.load(f)
        
        # Get conversation ID
        conv_id = conv_data.get('conversation_metadata', {}).get('conversation_id')
        messages = conv_data.get('messages', [])
        media_index = mapping_data.get('media_index', {})
        
        # Track unique files
        seen_files = set()
        
        # 1. Process Media ID matches
        for message in messages:
            media_ids_str = message.get('Media IDs', '')
            if media_ids_str:
                # Split pipe-separated IDs
                media_ids = [mid.strip() for mid in media_ids_str.split(' | ') if mid.strip()]
                
                for media_id in media_ids:
                    if media_id in media_index:
                        filename = media_index[media_id]
                        if filename not in seen_files:
                            seen_files.add(filename)
                            media_files.append(('media_id', filename))
        
        # 2. Process MP4 timestamp matches
        mp4_matches = mapping_data.get('mp4_matches', {})
        for filename, match_info in mp4_matches.items():
            if match_info['conv_id'] == conv_id:
                msg_idx = match_info['msg_idx']
                if msg_idx not in conv_mp4_matches:
                    conv_mp4_matches[msg_idx] = []
                conv_mp4_matches[msg_idx].append({
                    'filename': filename,
                    'diff_ms': match_info['diff_ms']
                })
                
                # Add to media files if not already added
                if filename not in seen_files:
                    seen_files.add(filename)
                    media_files.append(('timestamp_match', filename))
        
        logger.debug(f"Found {len(media_files)} unique media files for {conversation_file.parent.name} "
                    f"({len([f for t, f in media_files if t == 'media_id'])} by ID, "
                    f"{len([f for t, f in media_files if t == 'timestamp_match'])} by timestamp)")
        
    except Exception as e:
        logger.error(f"Error reading conversation file {conversation_file}: {e}")
    
    return media_files, conv_mp4_matches


def copy_media_file(
    source_file: Path,
    target_file: Path,
    preserve_metadata: bool = True
) -> bool:
    """
    Move a single media file (not copy, to avoid duplication).
    
    T2.2.2: Maintain file metadata
    
    Args:
        source_file: Source file path
        target_file: Target file path
        preserve_metadata: Whether to preserve file metadata (always True for move)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if not source_file.exists():
            logger.warning(f"Source file not found: {source_file}")
            return False
        
        # Ensure target directory exists
        target_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Move file (preserves metadata by default)
        shutil.move(str(source_file), str(target_file))
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to move {source_file.name}: {e}")
        return False


def copy_media_to_conversation(
    media_files: List[Tuple[str, str]],
    source_dir: Path,
    target_dir: Path,
    stats: Phase2Stats
) -> List[str]:
    """
    Move media files to a conversation's media subdirectory.
    
    T2.2.1: Move mapped files to conversations/media
    
    Args:
        media_files: List of (match_type, filename) tuples
        source_dir: Source directory (temp_media)
        target_dir: Target conversation directory
        stats: Statistics object to update
        
    Returns:
        List of successfully moved filenames
    """
    moved_files = []
    
    # Only create media subdirectory if there are files to move
    if media_files:
        media_dir = target_dir / "media"
        try:
            media_dir.mkdir(exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create media directory {media_dir}: {e}")
            stats.errors.append(f"Failed to create media directory: {e}")
            return moved_files
        
        for match_type, filename in media_files:
            source_file = source_dir / filename
            # Move to media subdirectory instead of root
            target_file = media_dir / filename
            
            if copy_media_file(source_file, target_file):
                moved_files.append(filename)
                stats.files_copied_to_conversations += 1
            else:
                stats.errors.append(f"Failed to move {filename}")
    
    return moved_files


def process_all_conversations(
    output_dir: Path,
    mapping_data: Dict[str, Any],
    stats: Phase2Stats,
    max_workers: int = 4
) -> None:
    """
    Process all conversations and copy their media files.
    
    Args:
        output_dir: Base output directory
        mapping_data: Phase 1 mapping data
        stats: Statistics object to update
        max_workers: Number of parallel workers
    """
    temp_media_dir = output_dir / "temp_media"
    
    if not temp_media_dir.exists():
        logger.error(f"Temp media directory not found: {temp_media_dir}")
        return
    
    # Process individual conversations
    conversations_dir = output_dir / "conversations"
    if conversations_dir.exists():
        for conv_folder in conversations_dir.iterdir():
            if conv_folder.is_dir():
                conv_file = conv_folder / "conversation.json"
                if conv_file.exists():
                    # Get media files for this conversation
                    media_files, mp4_matches = get_media_files_for_conversation(conv_file, mapping_data)
                    
                    if media_files:
                        logger.info(f"Moving {len(media_files)} files to {conv_folder.name}")
                        moved = copy_media_to_conversation(
                            media_files,
                            temp_media_dir,
                            conv_folder,
                            stats
                        )
                        
                        if moved:
                            stats.conversations_updated += 1
    
    # Process group conversations
    groups_dir = output_dir / "groups"
    if groups_dir.exists():
        for group_folder in groups_dir.iterdir():
            if group_folder.is_dir():
                group_file = group_folder / "conversation.json"
                if group_file.exists():
                    # Get media files for this group
                    media_files, mp4_matches = get_media_files_for_conversation(group_file, mapping_data)
                    
                    if media_files:
                        logger.info(f"Moving {len(media_files)} files to {group_folder.name}")
                        moved = copy_media_to_conversation(
                            media_files,
                            temp_media_dir,
                            group_folder,
                            stats
                        )
                        
                        if moved:
                            stats.groups_updated += 1


# ====================
# T2.3: JSON Reference Updates
# ====================

def update_message_media_references(
    message: Dict[str, Any],
    msg_idx: int,
    media_files: List[str],
    media_index: Dict[str, str],
    mp4_matches_for_msg: Dict[int, List[Dict[str, Any]]]
) -> Dict[str, Any]:
    """
    Update a message with media location references.
    
    T2.3.1: Update media paths in messages
    
    Args:
        message: Message dictionary to update
        msg_idx: Message index in conversation
        media_files: List of media filenames in conversation folder
        media_index: Media ID to filename mapping
        mp4_matches_for_msg: MP4 matches for this conversation by message index
        
    Returns:
        Updated message dictionary
    """
    matched_media_files = []
    media_locations = []
    
    # 1. Process Media ID matches
    media_ids_str = message.get('Media IDs', '')
    if media_ids_str:
        # Split pipe-separated IDs
        media_ids = [mid.strip() for mid in media_ids_str.split(' | ') if mid.strip()]
        
        for media_id in media_ids:
            if media_id in media_index:
                filename = media_index[media_id]
                # Check if file is in this conversation folder
                if filename in media_files:
                    matched_media_files.append(filename)
                    # Add media/ prefix for the location
                    media_locations.append(f"media/{filename}")
    
    # 2. Process MP4 timestamp matches for this message
    if msg_idx in mp4_matches_for_msg:
        for match in mp4_matches_for_msg[msg_idx]:
            filename = match['filename']
            # Check if file is in this conversation folder
            if filename in media_files:
                matched_media_files.append(filename)
                # Add media/ prefix for the location
                media_locations.append(f"media/{filename}")
                # Add time_diff_seconds ONLY for timestamp matches
                message['time_diff_seconds'] = abs(match['diff_ms']) / 1000.0
    
    # Update message fields
    if matched_media_files:
        message['matched_media_files'] = matched_media_files
    if media_locations:
        message['media_locations'] = media_locations
    elif 'media_locations' not in message:
        # Set empty array if no media found
        message['media_locations'] = []
    
    return message


def update_conversation_json(
    conversation_file: Path,
    media_files: List[str],
    mapping_data: Dict[str, Any],
    stats: Phase2Stats
) -> bool:
    """
    Update conversation JSON with media references.
    
    T2.3.3: Save updated JSON
    
    Args:
        conversation_file: Path to conversation.json
        media_files: List of media files in the conversation folder
        mapping_data: Phase 1 mapping data
        stats: Statistics object to update
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Load existing JSON
        with open(conversation_file, 'r', encoding='utf-8') as f:
            conv_data = json.load(f)
        
        # Get conversation ID
        conv_id = conv_data.get('conversation_metadata', {}).get('conversation_id')
        
        # Get MP4 matches for this conversation
        mp4_matches = mapping_data.get('mp4_matches', {})
        conv_mp4_matches = {}
        for filename, match_info in mp4_matches.items():
            if match_info['conv_id'] == conv_id:
                msg_idx = match_info['msg_idx']
                if msg_idx not in conv_mp4_matches:
                    conv_mp4_matches[msg_idx] = []
                conv_mp4_matches[msg_idx].append({
                    'filename': filename,
                    'diff_ms': match_info['diff_ms']
                })
        
        # Get media index
        media_index = mapping_data.get('media_index', {})
        
        # Update each message
        messages = conv_data.get('messages', [])
        updated_count = 0
        
        for msg_idx, message in enumerate(messages):
            original_locations = message.get('media_locations', [])
            original_matched = message.get('matched_media_files', [])
            
            update_message_media_references(
                message,
                msg_idx,
                media_files,
                media_index,
                conv_mp4_matches
            )
            
            # Check if we added new references
            new_locations = message.get('media_locations', [])
            new_matched = message.get('matched_media_files', [])
            if (new_locations and not original_locations) or (new_matched and not original_matched):
                updated_count += 1
        
        # Save updated JSON
        with open(conversation_file, 'w', encoding='utf-8') as f:
            json.dump(conv_data, f, indent=2, ensure_ascii=False)
        
        if updated_count > 0:
            logger.info(f"Updated {updated_count} messages with media references in {conversation_file.parent.name}")
            stats.json_references_updated += 1
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to update JSON references in {conversation_file}: {e}")
        stats.errors.append(f"JSON update failed: {conversation_file.name}")
        return False


def process_json_updates(
    output_dir: Path,
    mapping_data: Dict[str, Any],
    stats: Phase2Stats
) -> None:
    """
    Process all conversation JSONs to update media references.
    
    T2.3.4: Validate references
    
    Args:
        output_dir: Base output directory
        mapping_data: Phase 1 mapping data with media_index and mp4_matches
        stats: Statistics object to update
    """
    logger.info("\n--- T2.3: JSON Reference Updates ---")
    
    # Process individual conversations
    conversations_dir = output_dir / "conversations"
    if conversations_dir.exists():
        for conv_folder in conversations_dir.iterdir():
            if conv_folder.is_dir():
                conv_file = conv_folder / "conversation.json"
                if conv_file.exists():
                    # Get list of media files in the media subdirectory
                    media_dir = conv_folder / "media"
                    media_files = []
                    if media_dir.exists():
                        media_files = [f.name for f in media_dir.iterdir() 
                                     if f.is_file()]
                    
                    if media_files:
                        update_conversation_json(conv_file, media_files, mapping_data, stats)
    
    # Process group conversations
    groups_dir = output_dir / "groups"
    if groups_dir.exists():
        for group_folder in groups_dir.iterdir():
            if group_folder.is_dir():
                group_file = group_folder / "conversation.json"
                if group_file.exists():
                    # Get list of media files in the media subdirectory
                    media_dir = group_folder / "media"
                    media_files = []
                    if media_dir.exists():
                        media_files = [f.name for f in media_dir.iterdir() 
                                     if f.is_file()]
                    
                    if media_files:
                        update_conversation_json(group_file, media_files, mapping_data, stats)
    
    logger.info(f"Updated JSON references in {stats.json_references_updated} conversations")


# ====================
# T2.4: Orphaned File Handling
# ====================

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


# ====================
# T2.5: Phase 2 Validation
# ====================

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
                # Count media files (exclude conversation.json)
                media_count = sum(1 for f in conv_folder.iterdir() 
                                if f.is_file() and f.name != "conversation.json")
                counts["conversations"] += media_count
    
    # Count files in groups
    groups_dir = output_dir / "groups"
    if groups_dir.exists():
        for group_folder in groups_dir.iterdir():
            if group_folder.is_dir():
                # Count media files (exclude conversation.json)
                media_count = sum(1 for f in group_folder.iterdir() 
                                if f.is_file() and f.name != "conversation.json")
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
                # Count remaining files
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