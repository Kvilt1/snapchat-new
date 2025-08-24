"""
Phase 0 Orchestrator Module.
Main entry point that coordinates all Phase 0 operations.
"""

import logging
from pathlib import Path
from typing import Dict

from .stats import Phase0Stats
from .temp_setup import create_temp_directory
from .user_mapper import build_user_display_map
from .conversation_merger import merge_conversations
from .conversation_splitter import split_conversations
from .overlay_processor import merge_overlay_pairs

from utils.json_handler import load_json, validate_chat_history, validate_snap_history
from utils.file_operations import copy_media_files
from core.metadata_extractor import (
    load_friends_data,
    determine_account_owner
)

logger = logging.getLogger(__name__)


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