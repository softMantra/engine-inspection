#!/usr/bin/env bash

# exit on error
set -o errexit

# Install required dependencies
pip install -r requirements.txt

# Create models directory if it doesn't exist
mkdir -p models

# Replace this with your actual Google Drive File ID
# For example, if your link is https://drive.google.com/file/d/1XyZ_abc123.../view
# The ID is 1XyZ_abc123...
GDRIVE_FILE_ID="YOUR_GOOGLE_DRIVE_FILE_ID_HERE"

# Check if model already exists (optional, saves time on rebuilds)
if [ ! -f "models/best.pth" ]; then
    echo "Downloading best.pth from Google Drive..."
    # Download the model from Google Drive
    gdown --id $GDRIVE_FILE_ID -O models/best.pth
else
    echo "Model already exists. Skipping download."
fi
