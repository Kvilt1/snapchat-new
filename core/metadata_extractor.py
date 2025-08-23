"""
Metadata extraction module for Snapchat Merger V2.

Provides functionality to extract participant metadata from friends data
and build comprehensive conversation metadata objects.

Adapted from: snapchat_merger/metadata_extractor.py
"""

from datetime import datetime
from typing import Dict, List, Any, Optional, Set
import logging

logger = logging.getLogger(__name__)


def load_friends_data(friends_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Load and organize friends data from all sections.
    
    Adapted from: snapchat_merger/metadata_extractor.py:13-54
    
    Args:
        friends_data: Raw friends data loaded from friends.json
        
    Returns:
        Mapping of username to friend data with status information
    """
    friends_map = {}
    
    # Process active friends
    for friend in friends_data.get('Friends', []):
        username = friend.get('Username')
        if username:
            friends_map[username] = {
                'display_name': friend.get('Display Name', friend.get('Name', username)),
                'creation_timestamp': friend.get('Creation Timestamp', 'N/A'),
                'last_modified_timestamp': friend.get('Last Modified Timestamp', 'N/A'),
                'source': friend.get('Source', 'unknown'),
                'friend_status': 'active',
                'friend_list_section': 'Friends'
            }
    
    # Process deleted friends
    for friend in friends_data.get('Deleted Friends', []):
        username = friend.get('Username')
        if username:
            friends_map[username] = {
                'display_name': friend.get('Display Name', friend.get('Name', username)),
                'creation_timestamp': friend.get('Creation Timestamp', 'N/A'),
                'last_modified_timestamp': friend.get('Last Modified Timestamp', 'N/A'),
                'source': friend.get('Source', 'unknown'),
                'friend_status': 'deleted',
                'friend_list_section': 'Deleted Friends'
            }
    
    logger.info(f"Loaded friend data for {len(friends_map)} users")
    return friends_map


def determine_account_owner(merged_data: Dict[str, List[Dict[str, Any]]]) -> str:
    """
    Determine the account owner from message data.
    
    Adapted from: snapchat_merger/metadata_extractor.py:210-231
    
    Args:
        merged_data: The merged conversation data
        
    Returns:
        Username of the account owner
    """
    # Find messages where IsSender is True
    for messages in merged_data.values():
        if isinstance(messages, list):
            for msg in messages:
                if msg.get('IsSender') and msg.get('From'):
                    owner = msg['From']
                    logger.info(f"Determined account owner: {owner}")
                    return owner
    
    logger.warning("Could not determine account owner from messages")
    return 'unknown'


def extract_conversation_participants(
    conversation_id: str,
    messages: List[Dict[str, Any]],
    account_owner: str
) -> Set[str]:
    """
    Extract unique participants from a conversation.
    
    Adapted from: snapchat_merger/metadata_extractor.py:56-94
    
    Args:
        conversation_id: The conversation ID (username or UUID)
        messages: List of messages in the conversation
        account_owner: Username of the account owner
        
    Returns:
        Set of unique participant usernames (excluding account owner)
    """
    participants = set()
    
    # For individual conversations, the conversation ID is the other participant
    is_group = any(msg.get('Conversation Title') for msg in messages)
    
    if not is_group:
        # Individual conversation - conversation ID is the other participant
        participants.add(conversation_id)
    else:
        # Group conversation - extract from message senders and recipients
        for msg in messages:
            sender = msg.get('From')
            recipient = msg.get('To')
            
            if sender and sender != account_owner:
                participants.add(sender)
            if recipient and recipient != account_owner:
                participants.add(recipient)
    
    return participants


def create_participant_object(
    username: str,
    friends_map: Dict[str, Dict[str, Any]],
    account_owner: str
) -> Dict[str, Any]:
    """
    Create a participant object for a user.
    
    Adapted from: snapchat_merger/metadata_extractor.py:97-149
    
    Args:
        username: The participant's username
        friends_map: Mapping of username to friend data
        account_owner: Username of the account owner
        
    Returns:
        Participant object with all required fields
    """
    # Check if this is the account owner
    is_owner = username == account_owner
    
    # Get friend data if available
    friend_data = friends_map.get(username, {})
    
    if friend_data:
        return {
            'username': username,
            'display_name': friend_data.get('display_name', username),
            'creation_timestamp': friend_data.get('creation_timestamp', 'N/A'),
            'last_modified_timestamp': friend_data.get('last_modified_timestamp', 'N/A'),
            'source': friend_data.get('source', 'unknown'),
            'friend_status': friend_data.get('friend_status', 'not_found'),
            'friend_list_section': friend_data.get('friend_list_section', 'Not Found'),
            'is_owner': is_owner
        }
    else:
        # User not in friends list
        return {
            'username': username,
            'display_name': username,
            'creation_timestamp': 'N/A',
            'last_modified_timestamp': 'N/A',
            'source': 'not_in_friends_list',
            'friend_status': 'not_found',
            'friend_list_section': 'Not Found',
            'is_owner': is_owner,
            'note': 'User not found in any friends list'
        }


def create_conversation_metadata(
    conversation_id: str,
    messages: List[Dict[str, Any]],
    participants: List[Dict[str, Any]],
    is_group: bool,
    account_owner: str
) -> Dict[str, Any]:
    """
    Create comprehensive conversation metadata.
    
    Enhanced from: snapchat_merger/metadata_extractor.py:152-207
    
    Args:
        conversation_id: The conversation ID
        messages: List of messages in the conversation
        participants: List of participant objects
        is_group: Whether this is a group conversation
        account_owner: Username of the account owner
        
    Returns:
        Conversation metadata object
    """
    # Calculate date range
    date_range = {
        'first_message': 'N/A',
        'last_message': 'N/A'
    }
    
    if messages:
        # Get first and last message timestamps
        first_msg = messages[0]
        last_msg = messages[-1]
        
        # Use Created field for timestamps
        if first_msg.get('Created'):
            date_range['first_message'] = first_msg['Created']
        if last_msg.get('Created'):
            date_range['last_message'] = last_msg['Created']
    
    # Count message types
    message_count = len(messages)
    snap_count = sum(1 for msg in messages if msg.get('Type') == 'snap')
    chat_count = sum(1 for msg in messages if msg.get('Type') == 'message')
    
    metadata = {
        'conversation_type': 'group' if is_group else 'individual',
        'conversation_id': conversation_id,
        'total_messages': message_count,
        'snap_count': snap_count,
        'chat_count': chat_count,
        'participants': participants,
        'participant_count': len(participants),
        'account_owner': account_owner,
        'date_range': date_range,
        'index_created': datetime.utcnow().isoformat() + 'Z'
    }
    
    # Add group-specific metadata
    if is_group and messages:
        # Get conversation title from any message
        for msg in messages:
            if msg.get('Conversation Title'):
                metadata['group_name'] = msg['Conversation Title']
                break
    
    return metadata