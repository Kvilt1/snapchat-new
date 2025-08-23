# Input Directory Instructions

## How to Use This Directory

Place your entire Snapchat data export folder in this directory.

### Required Structure:
```
input/
└── [your-export-folder]/     (can be named anything: mydat, my-snapchat-data, etc.)
    ├── json/
    │   ├── chat_history.json    (required)
    │   ├── snap_history.json    (required)
    │   └── friends.json         (optional but recommended)
    └── chat_media/
        └── (all media files)     (your photos, videos, etc.)
```

### Step-by-Step Instructions:

1. **Download your Snapchat data** from Snapchat's website (Settings → My Data)
2. **Extract the ZIP file** you received from Snapchat
3. **Copy the entire extracted folder** (not just its contents) into this `input` directory
4. **Run the merger** from the snapchat-new directory: `python main.py`

### Important Notes:
- ⚠️ Do NOT place the `json` and `chat_media` folders directly in `input/`
- ✅ Place the entire export folder (which contains these folders) in `input/`
- The export folder can have any name (mydat, snapchat-data, etc.)
- Only one export folder should be in the input directory at a time

### Example:
If your Snapchat export created a folder called `mydata_download`, your structure should be:
```
input/
└── mydata_download/
    ├── json/
    │   └── (JSON files)
    └── chat_media/
        └── (media files)
```

## Running the Merger

Once your data is in place, run from the snapchat-new directory:

```bash
python main.py
```

Or with custom options:

```bash
# Enable debug logging
python main.py --debug

# Use more workers for parallel processing
python main.py --workers 8

# Skip overlay merging
python main.py --no-overlay-merge

# Adjust timestamp matching threshold (in seconds)
python main.py --timestamp-threshold 15

# Use a custom output directory
python main.py --output /path/to/output
```

## Output

Processed data will be placed in the `output/` directory with the following structure:

```
output/
├── conversations/     # Individual conversations organized by date and username
├── groups/           # Group conversations organized by date and name
├── orphaned/         # Media files that couldn't be matched to messages
├── phase1_mapping.json
├── phase2_statistics.json
└── statistics.json   # Overall processing statistics
```

## Troubleshooting

### Common Issues:

1. **"No Snapchat data export folder found"**
   - Make sure you copied the entire export folder, not just its contents
   - The folder must contain both `json/` and `chat_media/` subdirectories

2. **"Multiple data export folders found"**
   - Remove any extra folders from the input directory
   - Keep only one Snapchat export folder at a time

3. **"Required file not found: chat_history.json"**
   - Ensure your export includes chat history
   - Check that the JSON files are in the `json/` subfolder of your export

4. **"Input directory not found"**
   - Make sure you're running the script from the `snapchat-new` directory
   - The `input` folder should exist in the same directory as `main.py`

## Privacy Note

Your data stays local and is never uploaded anywhere. All processing happens on your machine.