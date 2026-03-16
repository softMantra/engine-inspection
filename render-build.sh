#!/usr/bin/env bash
set -o errexit

# Install required dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create models directory if it doesn't exist
mkdir -p models

# Extracted ID from the link provided by user
GDRIVE_FILE_ID="1NGPQ8HbtE9Ioc5_S6fPDaKjJ0nGklGx-"

# Check if model already exists
if [ ! -f "models/best.pth" ]; then
    echo "Downloading best.pth from Google Drive..."
    # Download the model from Google Drive
    gdown --id $GDRIVE_FILE_ID -O models/best.pth
else
    echo "Model already exists. Skipping download."
fi
