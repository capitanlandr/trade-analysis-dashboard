#!/bin/bash
# Start local development server
# Reads from static JSON files (same as production)

cd "$(dirname "$0")/dashboard"
npm run dev
