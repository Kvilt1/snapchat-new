"""
Phase 1 T1.1: Media ID Extraction Module.
Extracts media IDs from messages and filenames.
"""

import re
import logging
from typing import Dict, List, Tuple, Optional, Set, Any

logger = logging.getLogger(__name__)


def split_pipe_separated_ids(media_ids_str: str) -> List[str]:
    """
    Parse a Media IDs string which may contain multiple IDs separated by pipe.
    Adapted from snapchat_merger/media_mapper.py:123-142
    
    Args:
        media_ids_str: The Media IDs string, potentially containing multiple IDs 
                      separated by " | " (pipe with spaces).
        
    Returns:
        A list of individual Media IDs.
        
    Examples:
        >>> split_pipe_separated_ids("id1 | id2 | id3")
        ['id1', 'id2', 'id3']
        >>> split_pipe_separated_ids("single_id")
        ['single_id']
        >>> split_pipe_separated_ids("")
        []
    """
    if not media_ids_str:
        return []
    
    # Split by pipe separator WITH SPACES (as per actual data format)
    # The data uses " | " not just "|"
    ids = [id.strip() for id in media_ids_str.split(' | ') if id.strip()]
    return ids


def extract_media_ids_from_messages(messages: Dict[str, List[Dict[str, Any]]]) -> Tuple[Set[str], Dict[str, Any]]:
    """
    Extract all unique Media IDs from messages.
    
    Args:
        messages: Dictionary of conversations with message lists
        
    Returns:
        Tuple of (unique_media_ids set, statistics dict)
    """
    all_media_ids = set()
    stats = {
        'total_messages': 0,
        'messages_with_media': 0,
        'pipe_separated': 0,  # Changed key name to match what run_phase1 expects
        'total_ids': 0
    }
    
    for conversation_id, message_list in messages.items():
        for message in message_list:
            stats['total_messages'] += 1
            
            media_ids_field = message.get('Media IDs', '')
            if media_ids_field:
                stats['messages_with_media'] += 1
                
                # Parse the IDs
                ids = split_pipe_separated_ids(media_ids_field)
                
                if len(ids) > 1:
                    stats['pipe_separated'] += 1
                
                stats['total_ids'] += len(ids)
                all_media_ids.update(ids)
    
    logger.info(f"Extracted {len(all_media_ids)} unique Media IDs from {stats['total_messages']} messages")
    logger.info(f"Found {stats['pipe_separated']} messages with pipe-separated IDs")
    
    return all_media_ids, stats


def extract_media_id_from_filename(filename: str) -> Optional[str]:
    """
    Extract the Media ID from a media filename.
    Adapted from snapchat_merger/media_mapper.py:18-65
    
    Media files can have patterns:
    - 2025-07-27_b~EiASFU8zdmJFSGUxRDR6MzV1VUJBelNRQTIBCEgCUARgAQ.jpeg
    - 2025-07-27_media~28E0FFB8-5182-4D9D-92E1-DD941C881FC5.mp4
    - 2025-07-27_overlay~7E80A0BA-875C-49B0-8F4A-865EB6F8EC21.webp
    - 2025-07-30_media~zip-C63E6B4D-4DF6-4C2C-A331-A49E4F1C0109.mp4
    
    Args:
        filename: The media filename.
        
    Returns:
        The extracted Media ID if found, None otherwise.
    """
    # Exclude all thumbnail files
    if 'thumbnail~' in filename:
        return None
    
    # Look for b~ pattern in filename
    if 'b~' in filename:
        # Split by b~ and get everything after it
        parts = filename.split('b~', 1)
        if len(parts) > 1:
            # Get the ID part before the file extension
            id_with_ext = parts[1]
            # Remove the extension
            id_part = id_with_ext.rsplit('.', 1)[0]
            return f'b~{id_part}'
    
    # Special handling for media~zip pattern
    if '_media~zip-' in filename:
        match = re.search(r'media~zip-([A-F0-9\-]+)', filename)
        if match:
            return f'media~zip-{match.group(1)}'
    
    # Look for media~ or overlay~ pattern
    match = re.search(r'(?:media|overlay)~([A-F0-9\-]+)', filename)
    if match:
        prefix = 'media' if 'media~' in filename else 'overlay'
        return f'{prefix}~{match.group(1)}'
    
    return None