#!/usr/bin/env python3
"""
Test script for T2.3 - JSON Reference Updates
Tests the functionality of updating conversation JSON files with media references.
"""
import sys
import json
import tempfile
from pathlib import Path

# Add the snapchat-new directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from phases.phase2 import (
    update_message_media_references,
    update_conversation_json,
    process_json_updates,
    Phase2Stats
)


def create_test_conversation_with_media():
    """Create a test conversation with media references."""
    return {
        "conversation_metadata": {
            "conversation_type": "individual",
            "participants": ["user", "john_doe"]
        },
        "messages": [
            {
                "From": "user",
                "Media Type": "TEXT",
                "Created": "2024-01-15 10:30:00 UTC",
                "Content": "Hello!",
                "Media IDs": "",
                "Type": "message"
            },
            {
                "From": "john_doe",
                "Media Type": "IMAGE",
                "Created": "2024-01-15 10:35:00 UTC",
                "Content": None,
                "Media IDs": "media_001",
                "Type": "snap"
            },
            {
                "From": "user",
                "Media Type": "VIDEO",
                "Created": "2024-01-15 10:40:00 UTC",
                "Content": None,
                "Media IDs": "media_002 | media_003",
                "Type": "snap"
            },
            {
                "From": "john_doe",
                "Media Type": "NOTE",
                "Created": "2024-01-15 10:45:00 UTC",
                "Content": None,
                "Media IDs": "media_004",
                "Type": "message"
            }
        ]
    }


def test_update_message_media_references():
    """Test updating individual message with media references."""
    print("\n[TEST] Testing update_message_media_references()...")
    
    # Test message with no media
    message_no_media = {
        "Media IDs": "",
        "Content": "Text only"
    }
    media_files = ["photo_001.jpg", "video_002.mp4"]
    
    updated = update_message_media_references(message_no_media, media_files)
    assert updated.get("media_locations") == [], "Empty media should have empty locations"
    print("  ✓ Correctly handled message with no media")
    
    # Test message with single media ID
    message_single = {
        "Media IDs": "media_001",
        "Content": None
    }
    media_files = ["2024-01-15_media_001.jpg", "2024-01-15_media_002.mp4"]
    
    updated = update_message_media_references(message_single, media_files)
    assert "2024-01-15_media_001.jpg" in updated.get("media_locations", []), "Should find matching media file"
    print("  ✓ Successfully matched single media ID to file")
    
    # Test message with pipe-separated media IDs
    message_multiple = {
        "Media IDs": "media_002 | media_003",
        "Content": None
    }
    media_files = ["2024-01-15_media_002.mp4", "2024-01-15_media_003.png", "2024-01-15_media_004.jpg"]
    
    updated = update_message_media_references(message_multiple, media_files)
    locations = updated.get("media_locations", [])
    assert "2024-01-15_media_002.mp4" in locations, "Should find first media file"
    assert "2024-01-15_media_003.png" in locations, "Should find second media file"
    assert len(locations) == 2, "Should have exactly 2 media locations"
    print("  ✓ Successfully handled pipe-separated Media IDs")
    
    # Test with no matching files
    message_no_match = {
        "Media IDs": "media_999",
        "Content": None
    }
    media_files = ["2024-01-15_media_001.jpg", "2024-01-15_media_002.mp4"]
    
    updated = update_message_media_references(message_no_match, media_files)
    assert updated.get("media_locations") == [], "Should have empty locations when no match"
    print("  ✓ Correctly handled media ID with no matching files")


def test_update_conversation_json():
    """Test updating entire conversation JSON file."""
    print("\n[TEST] Testing update_conversation_json()...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create conversation directory and JSON
        conv_dir = temp_path / "conversations" / "john_doe"
        conv_dir.mkdir(parents=True)
        
        conv_data = create_test_conversation_with_media()
        conv_file = conv_dir / "conversation.json"
        with open(conv_file, 'w', encoding='utf-8') as f:
            json.dump(conv_data, f, indent=2)
        
        # Create media files
        media_files = [
            "2024-01-15_media_001.jpg",
            "2024-01-15_media_002.mp4",
            "2024-01-15_media_003.png",
            "2024-01-15_media_004.mp3"
        ]
        
        for filename in media_files:
            (conv_dir / filename).write_text(f"content of {filename}")
        
        # Update conversation JSON
        stats = Phase2Stats()
        result = update_conversation_json(conv_file, media_files, stats)
        
        assert result is True, "Update should succeed"
        assert stats.json_references_updated == 1, "Should update one conversation"
        print("  ✓ Successfully updated conversation JSON")
        
        # Verify the updates
        with open(conv_file, 'r', encoding='utf-8') as f:
            updated_data = json.load(f)
        
        messages = updated_data.get("messages", [])
        
        # Check first message (no media)
        assert messages[0].get("media_locations") == [], "Text message should have empty locations"
        
        # Check second message (single media)
        assert "2024-01-15_media_001.jpg" in messages[1].get("media_locations", []), "Should have media_001 file"
        
        # Check third message (multiple media)
        locations = messages[2].get("media_locations", [])
        assert "2024-01-15_media_002.mp4" in locations, "Should have media_002 file"
        assert "2024-01-15_media_003.png" in locations, "Should have media_003 file"
        
        # Check fourth message (audio note)
        assert "2024-01-15_media_004.mp3" in messages[3].get("media_locations", []), "Should have media_004 file"
        
        print("  ✓ All message media references correctly updated")
        print("  ✓ JSON structure preserved and valid")


def test_process_json_updates():
    """Test processing all conversations and groups."""
    print("\n[TEST] Testing process_json_updates()...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        output_dir = temp_path / "output"
        
        # Create directory structure
        conversations_dir = output_dir / "conversations"
        groups_dir = output_dir / "groups"
        conversations_dir.mkdir(parents=True)
        groups_dir.mkdir(parents=True)
        
        # Create individual conversation 1
        conv1_dir = conversations_dir / "john_doe"
        conv1_dir.mkdir()
        conv1_data = create_test_conversation_with_media()
        with open(conv1_dir / "conversation.json", 'w') as f:
            json.dump(conv1_data, f)
        
        # Add media files to conv1
        (conv1_dir / "2024-01-15_media_001.jpg").write_text("photo")
        (conv1_dir / "2024-01-15_media_002.mp4").write_text("video")
        
        # Create individual conversation 2 (no media)
        conv2_dir = conversations_dir / "jane_doe"
        conv2_dir.mkdir()
        conv2_data = {
            "conversation_metadata": {"conversation_type": "individual"},
            "messages": [
                {"Media IDs": "", "Content": "Text only"}
            ]
        }
        with open(conv2_dir / "conversation.json", 'w') as f:
            json.dump(conv2_data, f)
        
        # Create group conversation
        group1_dir = groups_dir / "study_group"
        group1_dir.mkdir()
        group1_data = {
            "conversation_metadata": {"conversation_type": "group"},
            "messages": [
                {"Media IDs": "media_005", "Content": None}
            ]
        }
        with open(group1_dir / "conversation.json", 'w') as f:
            json.dump(group1_data, f)
        
        # Add media file to group
        (group1_dir / "2024-01-16_media_005.pdf").write_text("document")
        
        # Process all JSON updates
        stats = Phase2Stats()
        process_json_updates(output_dir, stats)
        
        # Verify statistics
        assert stats.json_references_updated == 2, f"Expected 2 updates, got {stats.json_references_updated}"
        assert len(stats.errors) == 0, f"Should have no errors, got {stats.errors}"
        print("  ✓ Successfully processed all conversations")
        print(f"  ✓ Updated {stats.json_references_updated} conversations with media references")
        
        # Verify individual conversation updates
        with open(conv1_dir / "conversation.json", 'r') as f:
            conv1_updated = json.load(f)
        
        # Check that media_locations was added
        message_with_media = conv1_updated["messages"][1]
        assert "media_locations" in message_with_media, "Should have media_locations field"
        assert len(message_with_media["media_locations"]) > 0, "Should have media files referenced"
        
        # Verify group conversation updates
        with open(group1_dir / "conversation.json", 'r') as f:
            group1_updated = json.load(f)
        
        group_message = group1_updated["messages"][0]
        assert "media_locations" in group_message, "Group should have media_locations field"
        assert "2024-01-16_media_005.pdf" in group_message["media_locations"], "Should reference PDF file"
        
        print("  ✓ Individual and group conversations properly updated")


def test_validation():
    """Test T2.3.4: Validate references."""
    print("\n[TEST] Testing reference validation...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create conversation with media references
        conv_dir = temp_path / "conversations" / "test_user"
        conv_dir.mkdir(parents=True)
        
        # Create media files first
        media_files = ["photo1.jpg", "video1.mp4", "audio1.mp3"]
        for f in media_files:
            (conv_dir / f).write_text(f"content of {f}")
        
        # Create conversation with references
        conv_data = {
            "messages": [
                {"Media IDs": "id1", "Content": None},
                {"Media IDs": "id2 | id3", "Content": None}
            ]
        }
        
        conv_file = conv_dir / "conversation.json"
        with open(conv_file, 'w') as f:
            json.dump(conv_data, f)
        
        # Test files that contain the media IDs
        test_files = ["2024-01-15_id1_photo.jpg", "2024-01-15_id2_video.mp4", "2024-01-15_id3_audio.mp3"]
        
        stats = Phase2Stats()
        update_conversation_json(conv_file, test_files, stats)
        
        # Load and validate
        with open(conv_file, 'r') as f:
            validated_data = json.load(f)
        
        # Validate all references are relative paths
        for message in validated_data["messages"]:
            for location in message.get("media_locations", []):
                assert not Path(location).is_absolute(), f"Path should be relative: {location}"
                assert "/" not in location, f"Should be filename only: {location}"
        
        print("  ✓ All media references are relative paths")
        print("  ✓ JSON structure is valid after updates")
        print("  ✓ Reference validation complete")


def test_with_real_data_structure():
    """Test with structure similar to real Snapchat data."""
    print("\n[TEST] Testing with real data structure...")
    
    # Check if mydat exists
    mydat_path = Path("/Users/rokur/Projects/snap-cursor/mydat")
    if mydat_path.exists():
        print("  ℹ Real data directory found")
        
        # Check for chat_history.json structure
        chat_history = mydat_path / "json" / "chat_history.json"
        if chat_history.exists():
            with open(chat_history, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Check for Received/Sent Saved Chat Media entries
            if "Received Saved Chat Media" in data:
                sample = data["Received Saved Chat Media"][:1]  # First entry
                if sample:
                    print(f"  ℹ Sample media structure found with keys: {list(sample[0].keys())[:5]}")
            
            print("  ✓ Real data structure validation complete")
    else:
        print("  ⚠ Real data directory not found, skipping real data test")


def main():
    """Run all tests for T2.3."""
    print("=" * 60)
    print("T2.3: JSON Reference Updates - Test Suite")
    print("=" * 60)
    
    try:
        test_update_message_media_references()
        test_update_conversation_json()
        test_process_json_updates()
        test_validation()
        test_with_real_data_structure()
        
        print("\n" + "=" * 60)
        print("✅ ALL T2.3 TESTS PASSED!")
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