#!/usr/bin/env python3
"""
Test script for T2.2 - Media File Copying
Tests the functionality of copying media files to conversation directories.
"""
import sys
import json
import shutil
import tempfile
from pathlib import Path
from datetime import datetime

# Add the snapchat-new directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from phases.phase2 import (
    load_phase1_mapping,
    get_media_files_for_conversation,
    copy_media_file,
    copy_media_to_conversation,
    process_all_conversations,
    Phase2Stats
)


def create_test_mapping_data():
    """Create test Phase 1 mapping data."""
    return {
        "media_index": {
            "media_001": "photo_001.jpg",
            "media_002": "video_002.mp4",
            "media_003": "photo_003.png",
            "media_004": "audio_004.mp3",
            "media_005": "photo_005.jpg"
        },
        "statistics": {
            "total_media_files": 5,
            "mapped_files": 5,
            "unmapped_files": 0
        }
    }


def create_test_conversation():
    """Create a test conversation with media references."""
    return {
        "conversation_id": "john_doe",
        "participants": ["user", "john_doe"],
        "messages": [
            {
                "sender": "user",
                "text": "Check out this photo",
                "Media IDs": "media_001",
                "timestamp": "2024-01-15 10:30:00"
            },
            {
                "sender": "john_doe",
                "text": "Nice! Here's a video",
                "Media IDs": "media_002 | media_003",
                "timestamp": "2024-01-15 10:35:00"
            },
            {
                "sender": "user",
                "text": "Audio message",
                "Media IDs": "media_004",
                "timestamp": "2024-01-15 10:40:00"
            }
        ]
    }


def test_load_phase1_mapping():
    """Test loading Phase 1 mapping data from JSON."""
    print("\n[TEST] Testing load_phase1_mapping()...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test mapping file
        mapping_data = create_test_mapping_data()
        mapping_file = temp_path / "phase1_mapping.json"
        with open(mapping_file, 'w', encoding='utf-8') as f:
            json.dump(mapping_data, f, indent=2)
        
        # Test loading existing file
        loaded_data = load_phase1_mapping(temp_path)
        assert loaded_data is not None, "Failed to load mapping data"
        assert "media_index" in loaded_data, "Missing media_index in loaded data"
        assert len(loaded_data["media_index"]) == 5, "Incorrect number of media items"
        assert loaded_data["media_index"]["media_001"] == "photo_001.jpg", "Incorrect media mapping"
        print("  ✓ Successfully loaded Phase 1 mapping data")
        
        # Test loading non-existent file
        non_existent_path = temp_path / "non_existent"
        loaded_data = load_phase1_mapping(non_existent_path)
        assert loaded_data is None, "Should return None for non-existent file"
        print("  ✓ Correctly handled non-existent mapping file")


def test_get_media_files_for_conversation():
    """Test extracting media files from conversation data."""
    print("\n[TEST] Testing get_media_files_for_conversation()...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test conversation file
        conv_data = create_test_conversation()
        conv_dir = temp_path / "conversations" / "john_doe"
        conv_dir.mkdir(parents=True)
        conv_file = conv_dir / "conversation.json"
        with open(conv_file, 'w', encoding='utf-8') as f:
            json.dump(conv_data, f, indent=2)
        
        # Create mapping data
        mapping_data = create_test_mapping_data()
        
        # Test extracting media files
        media_files = get_media_files_for_conversation(conv_file, mapping_data)
        assert len(media_files) == 4, f"Expected 4 media files, got {len(media_files)}"
        
        # Check that we got the correct media IDs
        media_ids = [mid for mid, _ in media_files]
        assert "media_001" in media_ids, "Missing media_001"
        assert "media_002" in media_ids, "Missing media_002"
        assert "media_003" in media_ids, "Missing media_003"
        assert "media_004" in media_ids, "Missing media_004"
        print("  ✓ Successfully extracted media files from conversation")
        
        # Test handling pipe-separated IDs
        filenames = [fname for _, fname in media_files]
        assert "video_002.mp4" in filenames, "Failed to handle pipe-separated Media IDs"
        assert "photo_003.png" in filenames, "Failed to handle pipe-separated Media IDs"
        print("  ✓ Correctly handled pipe-separated Media IDs")


def test_copy_media_file():
    """Test copying individual media files with metadata preservation."""
    print("\n[TEST] Testing copy_media_file()...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create source file
        source_dir = temp_path / "source"
        source_dir.mkdir()
        source_file = source_dir / "test_photo.jpg"
        source_file.write_text("test image data")
        
        # Set specific modification time for metadata test
        import os
        import time
        mod_time = time.time() - 86400  # 1 day ago
        os.utime(source_file, (mod_time, mod_time))
        
        # Test successful copy with metadata
        target_dir = temp_path / "target"
        target_file = target_dir / "test_photo.jpg"
        
        result = copy_media_file(source_file, target_file, preserve_metadata=True)
        assert result is True, "Copy operation failed"
        assert target_file.exists(), "Target file was not created"
        assert target_file.read_text() == "test image data", "File content mismatch"
        
        # Check metadata preservation (approximate due to precision)
        source_stat = source_file.stat()
        target_stat = target_file.stat()
        assert abs(source_stat.st_mtime - target_stat.st_mtime) < 1, "Metadata not preserved"
        print("  ✓ Successfully copied file with metadata preservation")
        
        # Test copy without metadata preservation
        target_file2 = target_dir / "test_photo2.jpg"
        result = copy_media_file(source_file, target_file2, preserve_metadata=False)
        assert result is True, "Copy without metadata failed"
        assert target_file2.exists(), "Target file was not created"
        print("  ✓ Successfully copied file without metadata preservation")
        
        # Test copying non-existent file
        non_existent = source_dir / "non_existent.jpg"
        target_file3 = target_dir / "test_photo3.jpg"
        result = copy_media_file(non_existent, target_file3)
        assert result is False, "Should return False for non-existent source"
        assert not target_file3.exists(), "Target should not be created for failed copy"
        print("  ✓ Correctly handled non-existent source file")


def test_copy_media_to_conversation():
    """Test copying multiple media files to a conversation directory."""
    print("\n[TEST] Testing copy_media_to_conversation()...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create source media files
        source_dir = temp_path / "temp_media"
        source_dir.mkdir()
        
        media_files = [
            ("media_001", "photo_001.jpg"),
            ("media_002", "video_002.mp4"),
            ("media_003", "photo_003.png")
        ]
        
        for _, filename in media_files:
            source_file = source_dir / filename
            source_file.write_text(f"content of {filename}")
        
        # Create target conversation directory
        target_dir = temp_path / "conversations" / "john_doe"
        target_dir.mkdir(parents=True)
        
        # Create stats object
        stats = Phase2Stats()
        
        # Test copying media files
        copied_files = copy_media_to_conversation(
            media_files,
            source_dir,
            target_dir,
            stats
        )
        
        assert len(copied_files) == 3, f"Expected 3 copied files, got {len(copied_files)}"
        assert stats.files_copied_to_conversations == 3, "Incorrect stats count"
        
        # Verify files were copied
        for _, filename in media_files:
            target_file = target_dir / filename
            assert target_file.exists(), f"File {filename} was not copied"
            assert f"content of {filename}" in target_file.read_text(), f"Content mismatch for {filename}"
        
        print("  ✓ Successfully copied all media files to conversation")
        print(f"  ✓ Stats updated correctly: {stats.files_copied_to_conversations} files copied")
        
        # Test with some missing source files
        media_files_with_missing = media_files + [("media_999", "missing.jpg")]
        stats2 = Phase2Stats()
        
        copied_files2 = copy_media_to_conversation(
            media_files_with_missing,
            source_dir,
            target_dir / "test2",
            stats2
        )
        
        assert len(copied_files2) == 3, "Should copy only existing files"
        assert len(stats2.errors) == 1, "Should record error for missing file"
        print("  ✓ Correctly handled missing source files")


def test_process_all_conversations():
    """Test processing all conversations and groups."""
    print("\n[TEST] Testing process_all_conversations()...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create directory structure
        output_dir = temp_path / "output"
        temp_media_dir = output_dir / "temp_media"
        conversations_dir = output_dir / "conversations"
        groups_dir = output_dir / "groups"
        
        temp_media_dir.mkdir(parents=True)
        conversations_dir.mkdir(parents=True)
        groups_dir.mkdir(parents=True)
        
        # Create media files
        media_files = {
            "photo_001.jpg": "photo content 1",
            "video_002.mp4": "video content 2",
            "photo_003.png": "photo content 3",
            "audio_004.mp3": "audio content 4",
            "photo_005.jpg": "photo content 5"
        }
        
        for filename, content in media_files.items():
            (temp_media_dir / filename).write_text(content)
        
        # Create Phase 1 mapping
        mapping_data = create_test_mapping_data()
        
        # Create individual conversation
        conv1_dir = conversations_dir / "john_doe"
        conv1_dir.mkdir()
        conv1_data = create_test_conversation()
        with open(conv1_dir / "conversation.json", 'w') as f:
            json.dump(conv1_data, f)
        
        # Create group conversation
        group1_dir = groups_dir / "study_group"
        group1_dir.mkdir()
        group1_data = {
            "conversation_id": "study_group",
            "participants": ["user", "alice", "bob"],
            "messages": [
                {
                    "sender": "alice",
                    "text": "Here's the study material",
                    "Media IDs": "media_005",
                    "timestamp": "2024-01-16 14:00:00"
                }
            ]
        }
        with open(group1_dir / "conversation.json", 'w') as f:
            json.dump(group1_data, f)
        
        # Process all conversations
        stats = Phase2Stats()
        process_all_conversations(output_dir, mapping_data, stats)
        
        # Verify individual conversation files
        assert (conv1_dir / "photo_001.jpg").exists(), "Media file not copied to conversation"
        assert (conv1_dir / "video_002.mp4").exists(), "Media file not copied to conversation"
        assert (conv1_dir / "photo_003.png").exists(), "Media file not copied to conversation"
        assert (conv1_dir / "audio_004.mp3").exists(), "Media file not copied to conversation"
        
        # Verify group conversation files
        assert (group1_dir / "photo_005.jpg").exists(), "Media file not copied to group"
        
        # Check statistics
        assert stats.conversations_updated == 1, f"Expected 1 conversation updated, got {stats.conversations_updated}"
        assert stats.groups_updated == 1, f"Expected 1 group updated, got {stats.groups_updated}"
        assert stats.files_copied_to_conversations == 5, f"Expected 5 files copied, got {stats.files_copied_to_conversations}"
        
        print("  ✓ Successfully processed all conversations")
        print(f"  ✓ Conversations updated: {stats.conversations_updated}")
        print(f"  ✓ Groups updated: {stats.groups_updated}")
        print(f"  ✓ Total files copied: {stats.files_copied_to_conversations}")


def test_with_real_data():
    """Test with actual sample data from mydat if available."""
    print("\n[TEST] Testing with real data structure...")
    
    mydat_path = Path("/Users/rokur/Projects/snap-cursor/mydat")
    if not mydat_path.exists():
        print("  ⚠ Real data directory not found, skipping real data test")
        return
    
    # Check for actual media files
    memories_media = mydat_path / "memories_media"
    if memories_media.exists():
        media_files = list(memories_media.glob("*"))
        print(f"  ℹ Found {len(media_files)} media files in memories_media")
        
        # Sample some file types
        extensions = set()
        for f in media_files[:100]:  # Sample first 100
            extensions.add(f.suffix.lower())
        print(f"  ℹ File types found: {', '.join(sorted(extensions))}")
    
    print("  ✓ Real data structure validation complete")


def main():
    """Run all tests for T2.2."""
    print("=" * 60)
    print("T2.2: Media File Copying - Test Suite")
    print("=" * 60)
    
    try:
        test_load_phase1_mapping()
        test_get_media_files_for_conversation()
        test_copy_media_file()
        test_copy_media_to_conversation()
        test_process_all_conversations()
        test_with_real_data()
        
        print("\n" + "=" * 60)
        print("✅ ALL T2.2 TESTS PASSED!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()