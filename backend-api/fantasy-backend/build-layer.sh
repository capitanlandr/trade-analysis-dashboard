#!/bin/bash
# Build Lambda Layer: pandas + numpy (arm64, Python 3.11)
# Task 1.6 -- Enrichment Lambda dependency layer
# Usage:  ./build-layer.sh
# Output: layers/pandas-numpy-layer.zip

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAYER_DIR="${SCRIPT_DIR}/layers/pandas-numpy"
PYTHON_DIR="${LAYER_DIR}/python/lib/python3.11/site-packages"
OUTPUT_ZIP="${SCRIPT_DIR}/layers/pandas-numpy-layer.zip"

echo "============================================================"
echo "Building pandas/numpy Lambda Layer"
echo "Target: Python 3.11, arm64 (manylinux2014_aarch64)"
echo "============================================================"

# Clean previous build
rm -rf "${LAYER_DIR}"
rm -f "${OUTPUT_ZIP}"
mkdir -p "${PYTHON_DIR}"

# Install for Lambda arm64 architecture
echo ""
echo "Installing pandas + numpy..."
pip install \
    --platform manylinux2014_aarch64 \
    --target "${PYTHON_DIR}" \
    --implementation cp \
    --python-version 3.11 \
    --only-binary=:all: \
    --no-deps \
    pandas numpy pytz python-dateutil six

echo ""

# Check unzipped size (Lambda limit: 250MB)
UNZIPPED_SIZE=$(du -sm "${LAYER_DIR}" | cut -f1)
echo "Unzipped size: ${UNZIPPED_SIZE}MB (Lambda limit: 250MB)"

if [ "${UNZIPPED_SIZE}" -gt 250 ]; then
    echo ""
    echo "FAIL: Layer exceeds 250MB! Fall back to container image."
    rm -rf "${LAYER_DIR}"
    exit 1
fi

# Package into ZIP
echo ""
echo "Creating ZIP archive..."
cd "${LAYER_DIR}"
zip -r -q "${OUTPUT_ZIP}" python/
cd "${SCRIPT_DIR}"

ZIP_SIZE=$(du -sm "${OUTPUT_ZIP}" | cut -f1)

echo ""
echo "============================================================"
echo "Lambda Layer built successfully!"
echo "  Output:   ${OUTPUT_ZIP}"
echo "  Zipped:   ${ZIP_SIZE}MB"
echo "  Unzipped: ${UNZIPPED_SIZE}MB"
echo ""
echo "Next: sam build && sam deploy"
echo "============================================================"

# Cleanup build directory
rm -rf "${LAYER_DIR}"
