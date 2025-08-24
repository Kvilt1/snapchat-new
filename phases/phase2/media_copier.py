"""
Phase 2 Media File Copying - T2.2
Handles copying media files to conversation directories.
"""

import logging
import json
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from .stats import Phase2Stats

logger = logging.getLogger(__name__)


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
        max_workers: Number of parallel workers (not used in current implementation)
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