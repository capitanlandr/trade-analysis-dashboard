#!/bin/bash
# Build Lambda Layer: pandas + numpy (arm64, Python 3.14)
# Task 1.6 -- Enrichment Lambda dependency layer
# Usage:  ./build-layer.sh
# Output: layers/pandas-numpy-layer.zip

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAYER_DIR="${SCRIPT_DIR}/layers/pandas-numpy"
PYTHON_DIR="${LAYER_DIR}/python/lib/python3.14/site-packages"
OUTPUT_ZIP="${SCRIPT_DIR}/layers/pandas-numpy-layer.zip"

echo "============================================================"
echo "Building pandas/numpy Lambda Layer"
echo "Target: Python 3.14, arm64 (manylinux_2_28_aarch64)"
echo "============================================================"

# Clean previous build
rm -rf "${LAYER_DIR}"
rm -f "${OUTPUT_ZIP}"
mkdir -p "${PYTHON_DIR}"

# Install for Lambda arm64 architecture.
# Versions are pinned because the CPython 3.14 (cp314) wheel is the
# constraint: pandas gained cp314 wheels at 2.3.3 and numpy at 2.3.3,
# so the previous 2.3.2/2.2.6 pair cannot build for this runtime.
# manylinux_2_28 is required -- the cp314 wheels are published as
# manylinux_2_28_aarch64, and the old manylinux2014 tag alone resolves
# to nothing. Amazon Linux 2023 provides glibc 2.34, so 2.28 is safe.
echo ""
echo "Installing pandas + numpy..."
pip install \
    --platform manylinux_2_28_aarch64 \
    --platform manylinux2014_aarch64 \
    --target "${PYTHON_DIR}" \
    --implementation cp \
    --python-version 3.14 \
    --only-binary=:all: \
    --no-deps \
    "pandas==2.3.3" \
    "numpy==2.3.3" \
    "pytz==2025.2" \
    "python-dateutil==2.9.0.post0" \
    "six==1.17.0"

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
