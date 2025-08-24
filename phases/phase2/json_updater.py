"""
Phase 2 JSON Reference Updates - T2.3
Handles updating JSON files with media location references.
"""

import logging
import json
from pathlib import Path
from typing import Dict, Any, List

from .stats import Phase2Stats

logger = logging.getLogger(__name__)


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