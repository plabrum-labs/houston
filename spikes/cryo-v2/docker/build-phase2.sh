#!/usr/bin/env bash
# Builds and pushes control-plane, echo-backend, and envoy images for spike 3.
set -euo pipefail

cd "$(dirname "$0")/.."

REGION="us-east-1"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

for name in control-plane echo-backend envoy; do
  REPO_URL="$(terraform -chdir=terraform/foundation output -json ecr_repository_urls | python3 -c "import json,sys; print(json.load(sys.stdin)['$name'])")"
  docker build --platform linux/arm64 -f "docker/${name}.Dockerfile" -t "${REPO_URL}:latest" .
  docker push "${REPO_URL}:latest"
  echo "pushed ${REPO_URL}:latest"
done
