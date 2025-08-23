"""
JSON handling utilities with UTF-8 support and error handling
Adapted from snapchat_merger/utils.py
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def load_json(path: Path) -> Dict[str, Any]:
    """
    Load JSON file with UTF-8 encoding and comprehensive error handling.
    
    Args:
        path: Path to JSON file
        
    Returns:
        Dictionary containing parsed JSON data
        
    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If JSON is invalid
        Exception: For other errors
    """
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logger.debug(f"Successfully loaded JSON from {path}")
            return data
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {path}: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to load {path}: {e}")
        raise


def save_json(
    data: Dict[str, Any],
    path: Path,
    indent: int = 2,
    ensure_ascii: bool = False
) -> None:
    """
    Save data to JSON file with proper Unicode support.
    
    Args:
        data: Dictionary to save
        path: Output file path
        indent: JSON indentation (default: 2)
        ensure_ascii: Whether to escape non-ASCII characters (default: False)
    """
    try:
        # Create parent directory if it doesn't exist
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
            logger.debug(f"Successfully saved JSON to {path}")
    except Exception as e:
        logger.error(f"Failed to save JSON to {path}: {e}")
        raise


def validate_chat_history(data: Dict[str, Any]) -> bool:
    """
    Validate chat history JSON structure.
    
    Args:
        data: Chat history data
        
    Returns:
        True if valid, False otherwise
    """
    if not isinstance(data, dict):
        logger.error("Chat history must be a dictionary")
        return False
    
    # Check that all values are lists of messages
    for conv_id, messages in data.items():
        if not isinstance(messages, list):
            logger.error(f"Conversation {conv_id} messages must be a list")
            return False
        
        # Validate first message structure if present
        if messages and len(messages) > 0:
            msg = messages[0]
            required_fields = ["From", "Media Type", "Created", "IsSender"]
            for field in required_fields:
                if field not in msg:
                    logger.error(f"Message missing required field: {field}")
                    return False
    
    return True


def validate_snap_history(data: Dict[str, Any]) -> bool:
    """
    Validate snap history JSON structure.
    
    Args:
        data: Snap history data
        
    Returns:
        True if valid, False otherwise
    """
    if not isinstance(data, dict):
        logger.error("Snap history must be a dictionary")
        return False
    
    # Similar structure to chat history but simpler
    for user_id, snaps in data.items():
        if not isinstance(snaps, list):
            logger.error(f"User {user_id} snaps must be a list")
            return False
        
        # Validate first snap if present
        if snaps and len(snaps) > 0:
            snap = snaps[0]
            required_fields = ["From", "Media Type", "Created", "IsSender"]
            for field in required_fields:
                if field not in snap:
                    logger.error(f"Snap missing required field: {field}")
                    return False
    
    return True


def validate_friends_data(data: Dict[str, Any]) -> bool:
    """
    Validate friends.json structure.
    
    Args:
        data: Friends data
        
    Returns:
        True if valid, False otherwise
    """
    if not isinstance(data, dict):
        logger.error("Friends data must be a dictionary")
        return False
    
    # Check for Friends section at minimum
    if "Friends" not in data:
        logger.warning("Friends data missing 'Friends' section")
    
    return True