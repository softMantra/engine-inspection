#!/usr/bin/env bash
set -o errexit

# Install required dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create models directory if it doesn't exist
mkdir -p models

# ── Download MobileNetV4 classification model (saddle_best.pth) ──
GDRIVE_SADDLE="https://drive.google.com/file/d/1NGPQ8HbtE9Ioc5_S6fPDaKjJ0nGklGx-/view?usp=sharing"

if [ ! -f "models/saddle_best.pth" ]; then
    echo "Downloading saddle_best.pth from Google Drive..."
    gdown "$GDRIVE_SADDLE" -O models/saddle_best.pth --fuzzy
else
    echo "saddle_best.pth already exists. Skipping download."
fi

# ── Download YOLO detection model (engine_best (2).pt) ──
GDRIVE_YOLO="https://drive.google.com/file/d/17-wA5NKT9ifI-SFvnw0XNX0y14MyK3Xr/view?usp=sharing"

if [ ! -f "models/engine_best (2).pt" ]; then
    echo "Downloading engine_best (2).pt from Google Drive..."
    gdown "$GDRIVE_YOLO" -O "models/engine_best (2).pt" --fuzzy
else
    echo "engine_best (2).pt already exists. Skipping download."
fi
