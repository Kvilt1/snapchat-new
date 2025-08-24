#!/usr/bin/env python3
"""
Test script for T1.2 - Build file mapping index.
"""

import sys
import json
from pathlib import Path
from pprint import pprint

# Add the snapchat-new directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from phases.phase1 import create_media_index, extract_media_ids_from_messages


def test_create_media_index():
    """Test the media index creation function."""
    print("Testing create_media_index()...")
    print("=" * 60)
    
    # Test with the temp_media directory from Phase 0
    media_dir = Path('/Users/rokur/Projects/snap-cursor/test_output/temp_media')
    
    if not media_dir.exists():
        print(f"Media directory not found: {media_dir}")
        print("Run Phase 0 first to create test data")
        return
    
    # Create the media index
    print(f"Building media index for: {media_dir}")
    media_index = create_media_index(media_dir, use_parallel=False)
    
    # Display results
    print(f"\nTotal Media IDs mapped: {len(media_index)}")
    
    # Show statistics by ID type
    id_stats = {
        'b~': 0,
        'media~': 0,
        'overlay~': 0,
        'media~zip-': 0
    }
    
    for media_id in media_index.keys():
        if media_id.startswith('b~'):
            id_stats['b~'] += 1
        elif media_id.startswith('media~zip-'):
            id_stats['media~zip-'] += 1
        elif media_id.startswith('media~'):
            id_stats['media~'] += 1
        elif media_id.startswith('overlay~'):
            id_stats['overlay~'] += 1
    
    print("\nMedia ID breakdown:")
    for pattern, count in id_stats.items():
        print(f"  {pattern}: {count}")
    
    # Show some example mappings
    print("\nExample mappings (first 5):")
    for i, (media_id, filename) in enumerate(list(media_index.items())[:5]):
        print(f"  {i+1}. ID: {media_id[:30]}...")
        print(f"     File: {filename}")
    
    print("\n✅ Media index creation test completed!")
    return media_index


def test_bidirectional_mapping(media_index):
    """Test that mappings work both ways."""
    print("\n" + "=" * 60)
    print("Testing bidirectional mapping...")
    
    # Create reverse mapping (filename -> ID)
    reverse_map = {filename: media_id for media_id, filename in media_index.items()}
    
    print(f"Forward mappings (ID -> filename): {len(media_index)}")
    print(f"Reverse mappings (filename -> ID): {len(reverse_map)}")
    
    # Check for any duplicates
    if len(media_index) != len(reverse_map):
        print("⚠️ Warning: Some filenames map to multiple IDs!")
        # Find duplicates
        filename_counts = {}
        for filename in media_index.values():
            filename_counts[filename] = filename_counts.get(filename, 0) + 1
        
        duplicates = [f for f, count in filename_counts.items() if count > 1]
        if duplicates:
            print(f"Duplicate filenames: {duplicates[:5]}")
    else:
        print("✅ All mappings are unique (no duplicates)")
    
    print("\n✅ Bidirectional mapping test completed!")


def test_with_messages():
    """Test mapping IDs from actual messages to files."""
    print("\n" + "=" * 60)
    print("Testing Media ID to file mapping with actual messages...")
    
    # Load sample messages
    chat_history_path = Path('/Users/rokur/Projects/snap-cursor/mydat/json/chat_history.json')
    
    if not chat_history_path.exists():
        print(f"Sample data not found at {chat_history_path}")
        return
    
    with open(chat_history_path, 'r', encoding='utf-8') as f:
        chat_data = json.load(f)
    
    # Extract Media IDs from messages
    all_media_ids, stats = extract_media_ids_from_messages(chat_data)
    print(f"Found {len(all_media_ids)} unique Media IDs in messages")
    
    # Build media index
    media_dir = Path('/Users/rokur/Projects/snap-cursor/test_output/temp_media')
    if not media_dir.exists():
        print(f"Media directory not found: {media_dir}")
        return
        
    media_index = create_media_index(media_dir)
    print(f"Built index with {len(media_index)} Media IDs from files")
    
    # Find matches
    matched_ids = all_media_ids.intersection(set(media_index.keys()))
    unmatched_ids = all_media_ids - set(media_index.keys())
    orphaned_files = set(media_index.keys()) - all_media_ids
    
    print(f"\nMatching results:")
    print(f"  Matched IDs: {len(matched_ids)} ({len(matched_ids)*100/len(all_media_ids):.1f}%)")
    print(f"  Unmatched IDs (no file): {len(unmatched_ids)}")
    print(f"  Orphaned files (no message): {len(orphaned_files)}")
    
    # Show some examples
    if matched_ids:
        print(f"\nExample matches (first 3):")
        for i, media_id in enumerate(list(matched_ids)[:3]):
            print(f"  {i+1}. ID: {media_id[:30]}...")
            print(f"     File: {media_index[media_id]}")
    
    if unmatched_ids:
        print(f"\nExample unmatched IDs (first 3):")
        for i, media_id in enumerate(list(unmatched_ids)[:3]):
            print(f"  {i+1}. {media_id[:50]}...")
    
    print("\n✅ Message to file mapping test completed!")


def main():
    print("=" * 60)
    print("T1.2 File Mapping Index Tests")
    print("=" * 60)
    print()
    
    # Run tests
    media_index = test_create_media_index()
    
    if media_index:
        test_bidirectional_mapping(media_index)
        test_with_messages()
    
    print("\n" + "=" * 60)
    print("All T1.2 tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()