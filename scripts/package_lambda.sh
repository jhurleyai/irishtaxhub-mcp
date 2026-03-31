#!/usr/bin/env bash
set -euo pipefail

# Lambda packaging script that uses Docker to ensure Linux compatibility

APP_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="$APP_ROOT/build"
DIST_DIR="$APP_ROOT/dist"
ZIP_NAME="irishtaxhub-mcp.zip"

rm -rf "$BUILD_DIR" "$DIST_DIR"
mkdir -p "$BUILD_DIR" "$DIST_DIR"

# Use Docker to build Lambda-compatible package for x86_64 architecture
echo "> Using Docker to build Lambda-compatible package (x86_64)"
docker run --rm --entrypoint="" --platform linux/amd64 \
    -v "$APP_ROOT:/var/task" \
    -v "$BUILD_DIR:/var/build" \
    public.ecr.aws/lambda/python:3.11 \
    /bin/bash -c "pip install -r /var/task/requirements.txt -t /var/build"

# Copy application code
echo "> Copying application code"
cp -R "$APP_ROOT/src/irishtaxhub_mcp" "$BUILD_DIR/"
cp "$APP_ROOT/lambda_handler.py" "$BUILD_DIR/"

# Create zip
echo "> Creating zip at $DIST_DIR/$ZIP_NAME"
(cd "$BUILD_DIR" && zip -rq "$DIST_DIR/$ZIP_NAME" .)

echo "> Package ready: $DIST_DIR/$ZIP_NAME"
