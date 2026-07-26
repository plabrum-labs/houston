#!/usr/bin/env bash
# Builds the runner image and pushes it to the ECR repo the foundation stack
# created. Single arm64 image serves both task types, since Fargate tasks are
# also pinned to ARM64/Graviton to match the EC2 capacity provider's t4g
# instances.
set -euo pipefail

cd "$(dirname "$0")/.."

REGION="us-east-1"
REPO_URL="$(terraform -chdir=terraform/foundation output -json ecr_repository_urls | python3 -c 'import json,sys; print(json.load(sys.stdin)["runner"])')"
ACCOUNT_ID="$(echo "$REPO_URL" | cut -d. -f1)"

aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

docker build --platform linux/arm64 -f docker/runner.Dockerfile -t "${REPO_URL}:latest" .
docker push "${REPO_URL}:latest"

echo "pushed ${REPO_URL}:latest"
