"""
Phase 0 Conversation Splitter Module.
Splits merged conversations into individual and group conversation folders.
"""

import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime

from utils.file_operations import ensure_directory
from utils.json_handler import save_json
from core.metadata_extractor import (
    extract_conversation_participants,
    create_participant_object,
    create_conversation_metadata
)

logger = logging.getLogger(__name__)


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