#!/usr/bin/env python3
"""
Test script for T1.1 - Media ID parsing functionality.
"""

import sys
import json
from pathlib import Path

# Add the snapchat-new directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from phases.phase1_mapping import split_pipe_separated_ids, extract_media_ids_from_messages


def test_split_pipe_separated_ids():
    """Test the pipe-separated ID splitting function."""
    print("Testing split_pipe_separated_ids()...")
    
    # Test case 1: Single ID
    result = split_pipe_separated_ids("b~EiASFU8zdmJFSGUxRDR6MzV1VUJBelNRQTIBCEgCUARgAQ")
    assert result == ["b~EiASFU8zdmJFSGUxRDR6MzV1VUJBelNRQTIBCEgCUARgAQ"], f"Single ID failed: {result}"
    print("✅ Single ID test passed")
    
    # Test case 2: Multiple IDs with pipe separator
    result = split_pipe_separated_ids("id1 | id2 | id3")
    assert result == ["id1", "id2", "id3"], f"Multiple IDs failed: {result}"
    print("✅ Multiple IDs test passed")
    
    # Test case 3: Empty string
    result = split_pipe_separated_ids("")
    assert result == [], f"Empty string failed: {result}"
    print("✅ Empty string test passed")
    
    # Test case 4: None
    result = split_pipe_separated_ids(None)
    assert result == [], f"None failed: {result}"
    print("✅ None test passed")
    
    # Test case 5: IDs with extra spaces
    result = split_pipe_separated_ids("  id1  |  id2  |  id3  ")
    assert result == ["id1", "id2", "id3"], f"Extra spaces failed: {result}"
    print("✅ Extra spaces test passed")
    
    print("All split_pipe_separated_ids tests passed!\n")


def test_with_sample_data():
    """Test with actual sample data from mydat."""
    print("Testing with sample data...")
    
    # Load a sample conversation
    chat_history_path = Path('/Users/rokur/Projects/snap-cursor/mydat/json/chat_history.json')
    
    if not chat_history_path.exists():
        print(f"Sample data not found at {chat_history_path}")
        return
    
    with open(chat_history_path, 'r', encoding='utf-8') as f:
        chat_data = json.load(f)
    
    # Extract media IDs
    all_media_ids, stats = extract_media_ids_from_messages(chat_data)
    
    print(f"Total messages: {stats['total_messages']}")
    print(f"Messages with media: {stats['messages_with_media']}")
    print(f"Total Media IDs: {stats['total_ids']}")
    print(f"Unique Media IDs: {len(all_media_ids)}")
    print(f"Messages with pipe-separated IDs: {stats.get('pipe_separated', 0)}")
    
    # Check for pipe-separated IDs
    pipe_separated_examples = []
    for conv_id, messages in chat_data.items():
        for msg in messages:
            media_ids = msg.get('Media IDs', '')
            if ' | ' in media_ids:
                pipe_separated_examples.append(media_ids)
                if len(pipe_separated_examples) >= 3:
                    break
        if len(pipe_separated_examples) >= 3:
            break
    
    if pipe_separated_examples:
        print(f"\nExamples of pipe-separated IDs found:")
        for example in pipe_separated_examples[:3]:
            ids = split_pipe_separated_ids(example)
            print(f"  Original: {example[:50]}...")
            print(f"  Split into {len(ids)} IDs")
    
    # Show some example IDs
    print(f"\nFirst 5 unique Media IDs:")
    for i, media_id in enumerate(list(all_media_ids)[:5]):
        print(f"  {i+1}. {media_id[:50]}..." if len(media_id) > 50 else f"  {i+1}. {media_id}")
    
    print("\n✅ Sample data test completed!")


def main():
    print("=" * 60)
    print("T1.1 Media ID Parsing Tests")
    print("=" * 60)
    print()
    
    # Run tests
    test_split_pipe_separated_ids()
    test_with_sample_data()
    
    print("\n" + "=" * 60)
    print("All tests completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()