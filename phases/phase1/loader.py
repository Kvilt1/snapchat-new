"""
Phase 1 Data Loading Module.
Handles loading conversation data from JSON files.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def load_conversations(conversations_dir: Path, groups_dir: Path) -> Dict[str, List]:
    """Load all conversation and group data from JSON files.
    
    Args:
        conversations_dir: Directory containing individual conversation folders
        groups_dir: Directory containing group conversation folders
        
    Returns:
        Dictionary with 'conversations' and 'groups' lists
    """
    data = {
        'conversations': [],
        'groups': []
    }
    
    # Load individual conversations
    if conversations_dir.exists():
        for conv_folder in conversations_dir.iterdir():
            if conv_folder.is_dir():
                conv_file = conv_folder / "conversation.json"
                if conv_file.exists():
                    try:
                        with open(conv_file, 'r', encoding='utf-8') as f:
                            data['conversations'].append(json.load(f))
                    except Exception as e:
                        logger.error(f"Error loading {conv_file}: {e}")
    
    # Load group conversations
    if groups_dir.exists():
        for group_folder in groups_dir.iterdir():
            if group_folder.is_dir():
                group_file = group_folder / "conversation.json"
                if group_file.exists():
                    try:
                        with open(group_file, 'r', encoding='utf-8') as f:
                            data['groups'].append(json.load(f))
                    except Exception as e:
                        logger.error(f"Error loading {group_file}: {e}")
    
    return data