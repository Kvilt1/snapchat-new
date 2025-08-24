"""
Phase 0 Conversation Merger Module.
Merges chat and snap histories into unified conversations.
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


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