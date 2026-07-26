#!/bin/bash

set -e

REPO_ID=$1
LORA_NAME=$2
LORA_VERSION=$3
MODEL_NAME=$4

if [[ -z "$REPO_ID" || -z "$LORA_NAME" || -z $LORA_VERSION || -z $MODEL_NAME ]]; then
    echo "Error: Missing arguments."
    echo "Usage:"
    echo ""
    echo "  bash <(curl -fsSL https://raw.githubusercontent.com/Akkisdiary/ai-tools/refs/heads/main/src/runpod/cron_push_lora.sh) <repo_id> <lora_name> <lora_version> <model_name>"
    exit 1
fi

nohup bash -c '
	REPO_ID=${REPO_ID}
	LORA_NAME=${LORA_NAME}
	LORA_VERSION=${LORA_VERSION}
	MODEL_NAME=${MODEL_NAME}

	while true; do
		echo "===== START $(date "+%Y-%m-%d %H:%M:%S") ====="
	
		if hf upload ${REPO_ID} /app/ai-toolkit/output/${LORA_NAME}/ ${LORA_NAME}/${MODEL_NAME}/${LORA_VERSION} --repo-type model; then
			echo "STATUS: SUCCESS"
		else 
			echo "STATUS: FAILED (exit code $?)"
		fi 

		echo "===== END $(date "+%Y-%m-%d %H:%M:%S") ====="
        echo
        sleep 300
	done
' >> /cron_push_lora.log 2>&1 &
