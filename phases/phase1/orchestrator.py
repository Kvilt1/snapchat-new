"""
Phase 1 Orchestrator Module.
Main entry point that coordinates all Phase 1 operations.
"""

import json
import logging
from pathlib import Path
from typing import Tuple, Dict, Any

from .stats import Phase1Stats
from .loader import load_conversations
from .media_id_extractor import extract_media_ids_from_messages, extract_media_id_from_filename
from .file_mapper import create_media_index
from .timestamp_matcher import match_mp4_timestamps

logger = logging.getLogger(__name__)


def load_all_conversations(conversations_dir: Path, groups_dir: Path) -> Dict[str, list]:
    """Load all conversation files from Phase 0 output directories.
    
    Args:
        conversations_dir: Path to output/conversations/ directory
        groups_dir: Path to output/groups/ directory
        
    Returns:
        Dictionary mapping conversation IDs to message lists
    """
    logger.info(f"Loading conversations from {conversations_dir} and {groups_dir}")
    all_messages = {}
    
    # Process individual conversations
    if conversations_dir.exists():
        for conv_folder in conversations_dir.iterdir():
            if conv_folder.is_dir():
                conv_file = conv_folder / 'conversation.json'
                if conv_file.exists():
                    with open(conv_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    # Extract conversation ID from metadata
                    conv_id = data['conversation_metadata']['conversation_id']
                    all_messages[conv_id] = data.get('messages', [])
                    logger.debug(f"Loaded {len(data.get('messages', []))} messages from {conv_id}")
    
    # Process group conversations  
    if groups_dir.exists():
        for group_folder in groups_dir.iterdir():
            if group_folder.is_dir():
                group_file = group_folder / 'conversation.json'
                if group_file.exists():
                    with open(group_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    # Extract group ID from metadata
                    group_id = data['conversation_metadata']['conversation_id']
                    all_messages[group_id] = data.get('messages', [])
                    logger.debug(f"Loaded {len(data.get('messages', []))} messages from group {group_id}")
    
    logger.info(f"Loaded {len(all_messages)} total conversations")
    return all_messages


def run_phase1(
    conversations_dir: Path,
    groups_dir: Path,
    media_dir: Path,
    output_dir: Path,
    timestamp_threshold: int = 10,
    max_workers: int = 4,
    use_parallel: bool = False
) -> Tuple[Phase1Stats, Dict[str, Any]]:
    """
    Run Phase 1: Media Mapping.
    
    This function orchestrates all Phase 1 operations:
    1. Extract media IDs from messages (T1.1)
    2. Build file mapping index (T1.2)
    3. Match MP4s using timestamp analysis (T1.3-T1.4)
    
    Args:
        conversations_dir: Path to output/conversations/ directory
        groups_dir: Path to output/groups/ directory
        media_dir: Directory containing media files
        output_dir: Output directory for results
        timestamp_threshold: Threshold for timestamp matching (seconds)
        max_workers: Number of parallel workers
        use_parallel: Whether to use parallel processing
        
    Returns:
        Tuple of (Phase1Stats, mapping_data)
    """
    stats = Phase1Stats()
    logger.info("=" * 60)
    logger.info("Starting Phase 1: Media Mapping")
    logger.info("=" * 60)
    
    # Load all conversations from individual files
    logger.info("Loading individual conversation files...")
    messages = load_all_conversations(conversations_dir, groups_dir)
    
    if not messages:
        logger.warning("No conversations found in output directories")
        return Phase1Stats(), {}
    
    logger.info(f"Loaded {len(messages)} conversations with {sum(len(msgs) for msgs in messages.values())} total messages")
    
    # ====================
    # T1.1: Extract Media IDs from messages
    # ====================
    logger.info("\n--- T1.1: Extracting Media IDs from messages ---")
    all_media_ids, extraction_stats = extract_media_ids_from_messages(messages)
    
    stats.total_media_ids = extraction_stats['total_ids']
    stats.unique_ids = len(all_media_ids)
    stats.pipe_separated_count = extraction_stats['pipe_separated']
    
    logger.info(f"Extracted {stats.unique_ids} unique Media IDs from {extraction_stats['messages_with_media']} messages")
    
    # ====================
    # T1.2: Build file mapping index
    # ====================
    logger.info("\n--- T1.2: Building file mapping index ---")
    media_index = create_media_index(media_dir, use_parallel=use_parallel, max_workers=max_workers)
    
    logger.info(f"Created index with {len(media_index)} Media IDs from files")
    
    # Count total media files
    all_media_files = list(media_dir.glob('*'))
    stats.total_media_files = len([f for f in all_media_files if f.is_file()])
    
    # Calculate mapping statistics
    matched_ids = all_media_ids.intersection(set(media_index.keys()))
    unmatched_ids = all_media_ids - set(media_index.keys())
    orphaned_files = set(media_index.keys()) - all_media_ids
    
    stats.ids_mapped = len(matched_ids)
    stats.ids_unmapped = len(unmatched_ids)
    stats.orphaned_files = len(orphaned_files)
    
    logger.info(f"Matched {stats.ids_mapped}/{stats.unique_ids} Media IDs ({stats.ids_mapped*100/stats.unique_ids:.1f}%)")
    logger.info(f"Unmatched IDs: {stats.ids_unmapped}")
    logger.info(f"Orphaned files: {len(orphaned_files)}")
    
    # ====================
    # T1.3-T1.4: MP4 Timestamp Matching
    # ====================
    logger.info("\n--- T1.3-T1.4: MP4 Timestamp Matching ---")
    
    # Find MP4 files that don't have Media IDs
    all_mp4s = list(media_dir.glob('*.mp4'))
    mp4s_without_ids = []
    
    for mp4_file in all_mp4s:
        # Check if this MP4 has a Media ID
        media_id = extract_media_id_from_filename(mp4_file.name)
        if not media_id or media_id not in matched_ids:
            mp4s_without_ids.append(mp4_file)
    
    logger.info(f"Found {len(mp4s_without_ids)} MP4 files without matched Media IDs")
    
    # Match MP4s using timestamps
    mp4_matches = {}
    if mp4s_without_ids:
        mp4_matches = match_mp4_timestamps(
            mp4s_without_ids,
            messages,
            threshold_seconds=timestamp_threshold,
            use_parallel=use_parallel,
            max_workers=max_workers
        )
        
        stats.mp4s_processed = len(mp4s_without_ids)
        stats.mp4s_matched = len(mp4_matches)
        
        logger.info(f"Matched {stats.mp4s_matched}/{stats.mp4s_processed} MP4 files using timestamps")
    
    # ====================
    # Compile final mapping data
    # ====================
    mapping_data = {
        'media_index': media_index,           # Media ID -> filename mapping
        'matched_ids': list(matched_ids),     # IDs found in both messages and files
        'unmatched_ids': list(unmatched_ids), # IDs in messages but not files
        'orphaned_files': list(orphaned_files), # Files without corresponding messages
        'mp4_matches': mp4_matches,           # MP4 filename -> (conv_id, msg_idx, diff_ms)
        'statistics': stats.to_dict()
    }
    
    # Save mapping data to output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    mapping_file = output_dir / 'phase1_mapping.json'
    
    # Create a serializable version of mapping_data
    serializable_data = {
        'media_index': mapping_data['media_index'],
        'matched_ids': mapping_data['matched_ids'],
        'unmatched_ids': mapping_data['unmatched_ids'],
        'orphaned_files': mapping_data['orphaned_files'],
        'mp4_matches': {k: {'conv_id': v[0], 'msg_idx': v[1], 'diff_ms': v[2]} 
                       for k, v in mapping_data['mp4_matches'].items()},
        'statistics': mapping_data['statistics']
    }
    
    with open(mapping_file, 'w', encoding='utf-8') as f:
        json.dump(serializable_data, f, indent=2)
    
    logger.info(f"\nSaved mapping data to {mapping_file}")
    
    # ====================
    # Phase 1 Summary
    # ====================
    logger.info("\n" + "=" * 60)
    logger.info("Phase 1 Complete - Summary:")
    logger.info("=" * 60)
    logger.info(f"Total Media IDs extracted: {stats.total_media_ids}")
    logger.info(f"Unique Media IDs: {stats.unique_ids}")
    logger.info(f"IDs mapped to files: {stats.ids_mapped} ({stats.ids_mapped*100/stats.unique_ids:.1f}%)")
    logger.info(f"IDs not found in files: {stats.ids_unmapped}")
    logger.info(f"MP4s processed for timestamp matching: {stats.mp4s_processed}")
    logger.info(f"MP4s matched: {stats.mp4s_matched}")
    
    mapping_rate = (stats.ids_mapped / stats.unique_ids * 100) if stats.unique_ids > 0 else 0
    if mapping_rate >= 90:
        logger.info(f"✅ Mapping rate {mapping_rate:.1f}% - Excellent!")
    elif mapping_rate >= 70:
        logger.info(f"⚠️ Mapping rate {mapping_rate:.1f}% - Good but some files missing")
    else:
        logger.info(f"❌ Mapping rate {mapping_rate:.1f}% - Many files missing")
    
    return stats, mapping_data