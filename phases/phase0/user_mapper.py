"""
Phase 0 User Display Name Mapping Module.
Creates mappings between usernames and display names.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


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