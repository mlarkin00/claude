#!/bin/bash
# verify_connection.sh - Automates the check for 2nd Gen Cloud Build connections

PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [[ -z "$PROJECT_ID" ]]; then
    echo "Error: PROJECT_ID not set. Set with 'gcloud config set project [PROJECT_ID]'"
    exit 1
fi

REPO_NAME=$1
if [[ -z "$REPO_NAME" ]]; then
    echo "Usage: $0 [REPO_NAME]"
    exit 1
fi

echo "Searching for repository connection for '$REPO_NAME' in project '$PROJECT_ID'..."

# List connections in common regions
REGIONS=("us-central1" "us-east1" "europe-west1" "asia-east1")

for REGION in "${REGIONS[@]}"; do
    echo "Checking region: $REGION..."
    RESULT=$(gcloud builds connections list --region="$REGION" --format="json" | grep -i "$REPO_NAME")
    if [[ -n "$RESULT" ]]; then
        echo "Found connection in region $REGION:"
        gcloud builds connections list --region="$REGION" --filter="repositories:$REPO_NAME"
        exit 0
    fi
done

echo "Error: Connection for '$REPO_NAME' not found in common regions. Try checking all regions with 'gcloud builds connections list --region=-'"
exit 1
