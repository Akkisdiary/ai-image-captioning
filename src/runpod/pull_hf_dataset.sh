#!/bin/bash

set -e

USAGE='bash <(curl -fsSL https://raw.githubusercontent.com/Akkisdiary/ai-tools/refs/heads/main/src/runpod/pull_hf_dataset.sh) <repo_id> <dataset_path> <dataset_name> [output_dir]'

REPO_ID=$1
DATASET_PATH=$2
DATASET_NAME=$3
OUTPUT_DIR=$4
DEFAULT_TARGET_DIR="/app/ai-toolkit/datasets/${DATASET_NAME}"
TARGET_DIR="${OUTPUT_DIR:-$DEFAULT_TARGET_DIR}"

if [[ -z "$REPO_ID" || -z "$DATASET_PATH" ]]; then
    echo "Error: Missing arguments."
    echo "Usage:"
    echo ""
    echo "  $USAGE"
    exit 1
fi

if ! hf auth whoami &>/dev/null; then
    echo "Warning: Not logged into Hugging Face CLI. Attempting to log in..."
    hf auth login
    
    if ! hf auth whoami; then
        echo "Please run 'hf auth login' and provide your token before running this script."
        exit 1
    fi
else
    echo "Successfully authenticated with Hugging Face."
fi

echo "Downloading dataset from $REPO_ID/$DATASET_PATH to $TARGET_DIR"

mkdir -p "$TARGET_DIR"
TEMP_DOWNLOAD_DIR="/tmp/pull_hf_dataset"

hf download $REPO_ID \
    --local-dir "$TEMP_DOWNLOAD_DIR" \
    --include "$DATASET_PATH/*" \
    --repo-type dataset

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Error: Failed to download the dataset."
    rm -rf "$TEMP_DOWNLOAD_DIR"
    exit 1
fi

find "$TEMP_DOWNLOAD_DIR" -mindepth 1 -maxdepth 1 -exec sh -c 'cp -r "{}"/* "$TARGET_DIR"' \;

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Success: Dataset contents downloaded and flattened to '$TARGET_DIR'."
else
    echo ""
    echo "❌ Error: Failed during the file flattening/copy process."
fi

rm -rf "$TEMP_DOWNLOAD_DIR"
