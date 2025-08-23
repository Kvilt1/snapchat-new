"""
Phase 0: Initial Setup
Creates temp directory, merges histories, splits conversations, processes overlay pairs
"""

import json
import logging
import shutil
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
from collections import defaultdict

from utils.json_handler import load_json, save_json, validate_chat_history, validate_snap_history
from utils.file_operations import ensure_directory, copy_media_files
from config import Config
from core.metadata_extractor import (
    load_friends_data,
    determine_account_owner,
    extract_conversation_participants,
    create_participant_object,
    create_conversation_metadata
)

logger = logging.getLogger(__name__)


class Phase0Stats:
    """Statistics for Phase 0 processing."""
    
    def __init__(self):
        self.media_files_copied = 0
        self.overlay_pairs_merged = 0
        self.individual_conversations = 0
        self.group_conversations = 0
        self.total_messages = 0
        self.total_snaps = 0
        self.media_ids_found = 0
        self.files_in_chat_media = 0
        self.duration = 0.0
        self.memory_used_mb = 0.0
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            "media_files_copied": self.media_files_copied,
            "overlay_pairs_merged": self.overlay_pairs_merged,
            "individual_conversations": self.individual_conversations,
            "group_conversations": self.group_conversations,
            "total_messages": self.total_messages,
            "total_snaps": self.total_snaps,
            "media_ids_found": self.media_ids_found,
            "files_in_chat_media": self.files_in_chat_media,
            "duration": self.duration,
            "memory_used_mb": self.memory_used_mb
        }


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


def build_user_display_map(friends_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Create a mapping from username to display name.
    Adapted from snapchat_merger/display_name_mapper.py:11-33
    
    Args:
        friends_data: Parsed friends.json data
        
    Returns:
        Dictionary mapping usernames to display names
    """
    username_map = {}
    
    if 'Friends' in friends_data and isinstance(friends_data['Friends'], list):
        for friend in friends_data['Friends']:
            if isinstance(friend, dict) and 'Username' in friend and 'Display Name' in friend:
                username = friend['Username']
                display_name = friend['Display Name']
                username_map[username] = display_name
    
    logger.info(f"Built display name map for {len(username_map)} users")
    return username_map


def add_message_type(messages: List[Dict[str, Any]], msg_type: str) -> List[Dict[str, Any]]:
    """
    Add 'Type' field to messages.
    
    Args:
        messages: List of messages
        msg_type: Type to add ("message" or "snap")
        
    Returns:
        Messages with Type field added
    """
    for msg in messages:
        msg["Type"] = msg_type
    return messages


def merge_conversations(
    chat_data: Dict[str, List],
    snap_data: Dict[str, List]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Merge chat and snap histories by conversation ID.
    
    Args:
        chat_data: Chat history data
        snap_data: Snap history data
        
    Returns:
        Merged conversations
    """
    merged = {}
    
    # Add chat messages with Type field
    for conv_id, messages in chat_data.items():
        if conv_id not in merged:
            merged[conv_id] = []
        merged[conv_id].extend(add_message_type(messages, "message"))
    
    # Add snap messages with Type field
    for conv_id, snaps in snap_data.items():
        if conv_id not in merged:
            merged[conv_id] = []
        merged[conv_id].extend(add_message_type(snaps, "snap"))
    
    # Sort each conversation by timestamp
    for conv_id in merged:
        merged[conv_id].sort(key=lambda x: x.get("Created(microseconds)", 0))
    
    logger.info(f"Merged {len(merged)} conversations")
    return merged


def is_group_conversation(messages: List[Dict[str, Any]]) -> bool:
    """
    Determine if conversation is a group chat.
    null Conversation Title = individual, non-null = group
    
    Args:
        messages: List of messages
        
    Returns:
        True if group conversation, False otherwise
    """
    for msg in messages:
        if msg.get("Conversation Title") is not None:
            return True
    return False


def get_latest_timestamp(messages: List[Dict[str, Any]]) -> Optional[datetime]:
    """
    Get the latest timestamp from a list of messages.
    
    Args:
        messages: List of messages
        
    Returns:
        Latest datetime or None
    """
    if not messages:
        return None
    
    latest_ms = 0
    for msg in messages:
        timestamp_ms = msg.get("Created(microseconds)", 0)
        if timestamp_ms > latest_ms:
            latest_ms = timestamp_ms
    
    if latest_ms > 0:
        # Convert milliseconds to datetime
        return datetime.fromtimestamp(latest_ms / 1000)
    
    return None


def generate_conversation_folder_name(
    conversation_id: str,
    messages: List[Dict[str, Any]],
    metadata: Optional[Dict[str, Any]] = None,
    is_group: bool = False
) -> str:
    """
    Generate folder name in format "YYYY-MM-DD - name".
    Adapted from snapchat_merger/conversation_splitter.py:270-314
    
    Args:
        conversation_id: Conversation ID (username or UUID)
        messages: List of messages
        metadata: Optional metadata
        is_group: Whether this is a group conversation
        
    Returns:
        Formatted folder name
    """
    # Get the latest timestamp
    latest_timestamp = get_latest_timestamp(messages)
    
    if latest_timestamp:
        timestamp_str = latest_timestamp.strftime("%Y-%m-%d")
    else:
        timestamp_str = "0000-00-00"
    
    # Determine the name to use
    if is_group and messages and messages[0].get('Conversation Title'):
        name = messages[0]['Conversation Title']
    else:
        name = conversation_id
    
    # Clean the name for filesystem compatibility
    name = name.replace("/", "-").replace("\\", "-").replace(":", "-")
    name = name.replace("?", "").replace("*", "").replace("|", "")
    name = name.replace("<", "").replace(">", "").replace('"', "")
    
    return f"{timestamp_str} - {name}"


def write_conversation_file(
    messages: List[Dict[str, Any]],
    output_path: Path,
    metadata: Dict[str, Any]
) -> None:
    """
    Save conversation to JSON file with metadata structure.
    Adapted from snapchat_merger/conversation_splitter.py:492-516
    
    Args:
        messages: List of messages
        output_path: Output file path
        metadata: Conversation metadata
    """
    data = {
        'conversation_metadata': metadata,
        'messages': messages
    }
    
    save_json(data, output_path)


def split_conversations(
    merged_data: Dict[str, List[Dict[str, Any]]],
    output_dir: Path,
    username_map: Dict[str, str],
    friends_map: Dict[str, Dict[str, Any]],
    account_owner: str
) -> Tuple[int, int]:
    """
    Split merged data into individual conversation folders with participant metadata.
    
    Args:
        merged_data: Merged conversation data
        output_dir: Output directory
        username_map: Username to display name mapping
        friends_map: Friends data mapping
        account_owner: Account owner username
        
    Returns:
        Tuple of (individual_count, group_count)
    """
    individual_count = 0
    group_count = 0
    
    conversations_dir = output_dir / "conversations"
    groups_dir = output_dir / "groups"
    
    ensure_directory(conversations_dir)
    ensure_directory(groups_dir)
    
    for conv_id, messages in merged_data.items():
        if not messages:
            continue
        
        # Determine if group
        is_group = is_group_conversation(messages)
        
        # Generate folder name
        folder_name = generate_conversation_folder_name(conv_id, messages, is_group=is_group)
        
        # Choose output directory
        if is_group:
            conv_dir = groups_dir / folder_name
            group_count += 1
        else:
            conv_dir = conversations_dir / folder_name
            individual_count += 1
        
        # Create conversation directory
        ensure_directory(conv_dir)
        
        # Extract participants for this conversation
        participant_usernames = extract_conversation_participants(conv_id, messages, account_owner)
        
        # Create participant objects
        participants = []
        for username in participant_usernames:
            participant = create_participant_object(username, friends_map, account_owner)
            participants.append(participant)
        
        # Create comprehensive metadata
        metadata = create_conversation_metadata(
            conv_id, messages, participants, is_group, account_owner
        )
        
        # Save conversation JSON
        output_path = conv_dir / "conversation.json"
        write_conversation_file(messages, output_path, metadata)
    
    logger.info(f"Split into {individual_count} individual and {group_count} group conversations")
    return individual_count, group_count


def detect_overlay_pairs(media_dir: Path) -> List[Tuple[Path, Path]]:
    """
    Detect media~overlay pairs for the same date.
    
    Args:
        media_dir: Directory containing media files
        
    Returns:
        List of (media_file, overlay_file) tuples
    """
    files_by_date = defaultdict(lambda: {"media": [], "overlay": []})
    
    for file_path in media_dir.iterdir():
        if not file_path.is_file():
            continue
        
        # Extract date from filename
        parts = file_path.name.split('_', 1)
        if len(parts) >= 2:
            date = parts[0]  # YYYY-MM-DD format
            
            if '_media~' in file_path.name and '_overlay~' not in file_path.name:
                files_by_date[date]["media"].append(file_path)
            elif '_overlay~' in file_path.name:
                files_by_date[date]["overlay"].append(file_path)
    
    # Find single pairs per date
    pairs = []
    for date, files in files_by_date.items():
        if len(files["media"]) == 1 and len(files["overlay"]) == 1:
            pairs.append((files["media"][0], files["overlay"][0]))
            logger.debug(f"Found overlay pair for {date}")
    
    return pairs


def merge_overlay_pairs(temp_dir: Path, max_workers: int = 4) -> int:
    """
    Merge overlay-media pairs using ffmpeg.
    
    Args:
        temp_dir: Temporary media directory
        max_workers: Number of parallel workers
        
    Returns:
        Number of pairs successfully merged
    """
    try:
        # Import with absolute path for the test script
        import sys
        from pathlib import Path
        module_path = Path(__file__).parent.parent
        if str(module_path) not in sys.path:
            sys.path.insert(0, str(module_path))
        
        from core.overlay_merger import process_all_overlay_pairs
        
        # Process all overlay pairs with ffmpeg
        stats = process_all_overlay_pairs(
            media_dir=temp_dir,
            use_parallel=True,
            max_workers=max_workers
        )
        
        # Log statistics
        if stats['total_pairs'] > 0:
            logger.info(f"Overlay merging: {stats['merged']}/{stats['total_pairs']} successful")
            if stats['failed'] > 0:
                logger.warning(f"Failed to merge {stats['failed']} overlay pairs")
                for error in stats['errors'][:5]:  # Log first 5 errors
                    logger.error(f"  - {error}")
        
        return stats['merged']
        
    except ImportError as e:
        logger.warning(f"Overlay merger module not available: {e}")
        logger.info("Falling back to detection-only mode")
        # Fallback to just detecting pairs
        pairs = detect_overlay_pairs(temp_dir)
        for media_file, overlay_file in pairs:
            logger.info(f"Found overlay pair: {media_file.name} + {overlay_file.name}")
        return 0
    except Exception as e:
        logger.error(f"Error during overlay merging: {e}")
        return 0


def run_phase0(
    data_dir: Path,
    output_dir: Path,
    skip_overlay_merge: bool = False,
    max_workers: int = 4
) -> Phase0Stats:
    """
    Run Phase 0: Initial Setup.
    
    Args:
        data_dir: Input data directory
        output_dir: Output directory
        skip_overlay_merge: Whether to skip overlay merging
        max_workers: Number of parallel workers
        
    Returns:
        Phase 0 statistics
    """
    stats = Phase0Stats()
    
    logger.info("Starting Phase 0: Initial Setup")
    
    # 1. Create temp directory
    temp_dir = create_temp_directory(output_dir)
    
    # 2. Copy media files (excluding thumbnails)
    media_source = data_dir / "chat_media"
    if media_source.exists():
        copy_stats = copy_media_files(media_source, temp_dir)
        stats.media_files_copied = copy_stats["copied"]
        stats.files_in_chat_media = copy_stats["total_files"]
    
    # 3. Load JSON files
    json_dir = data_dir / "json"
    
    # Load chat history
    chat_path = json_dir / "chat_history.json"
    chat_data = load_json(chat_path)
    if not validate_chat_history(chat_data):
        logger.warning("Chat history validation failed")
    
    # Load snap history
    snap_path = json_dir / "snap_history.json"
    snap_data = load_json(snap_path)
    if not validate_snap_history(snap_data):
        logger.warning("Snap history validation failed")
    
    # Count messages and snaps
    for messages in chat_data.values():
        stats.total_messages += len(messages)
    for snaps in snap_data.values():
        stats.total_snaps += len(snaps)
    
    # 4. Load friends data for display names and metadata
    friends_path = json_dir / "friends.json"
    username_map = {}
    friends_map = {}
    if friends_path.exists():
        friends_data = load_json(friends_path)
        username_map = build_user_display_map(friends_data)
        friends_map = load_friends_data(friends_data)
    
    # 5. Merge chat and snap histories
    merged_data = merge_conversations(chat_data, snap_data)
    
    # 6. Determine account owner from messages
    account_owner = determine_account_owner(merged_data)
    logger.info(f"Account owner: {account_owner}")
    
    # 7. Split into conversation folders with participant metadata
    individual_count, group_count = split_conversations(
        merged_data, output_dir, username_map, friends_map, account_owner
    )
    stats.individual_conversations = individual_count
    stats.group_conversations = group_count
    
    # 8. Process overlay-media pairs (if not skipped)
    if not skip_overlay_merge:
        stats.overlay_pairs_merged = merge_overlay_pairs(temp_dir, max_workers)
    
    logger.info(f"Phase 0 complete: {stats.to_dict()}")
    return stats