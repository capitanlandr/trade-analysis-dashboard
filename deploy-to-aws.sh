#!/bin/bash

# Manual AWS Deployment Script
# Updates your AWS CloudFront site with latest data

echo "🚀 Starting manual AWS deployment..."
echo ""

# Step 1: Build production bundle
echo "📦 Building production bundle..."
cd dashboard/frontend
npm run build

if [ $? -ne 0 ]; then
  echo "❌ Build failed!"
  exit 1
fi

echo "✅ Build successful!"
echo ""

# Step 2: Upload to S3
echo "☁️ Uploading to S3..."

# Upload assets (JS, CSS) with long cache
aws s3 sync dist/ s3://dynasuiiii-website/ \
  --delete \
  --cache-control "public, max-age=31536000, immutable" \
  --exclude "*.html" \
  --exclude "*.json"

# Upload HTML and JSON with short cache
aws s3 sync dist/ s3://dynasuiiii-website/ \
  --exclude "*" \
  --include "*.html" \
  --include "*.json" \
  --cache-control "public, max-age=3600, must-revalidate"

if [ $? -ne 0 ]; then
  echo "❌ S3 upload failed!"
  exit 1
fi

echo "✅ Files uploaded to S3!"
echo ""

# Step 3: Invalidate CloudFront cache
echo "🔄 Invalidating CloudFront cache..."
aws cloudfront create-invalidation \
  --distribution-id EL6SCNZ7VJGN2 \
  --paths "/*"

if [ $? -ne 0 ]; then
  echo "❌ CloudFront invalidation failed!"
  exit 1
fi

echo "✅ CloudFront cache invalidated!"
echo ""
echo "🎉 Deployment complete!"
echo "🌐 Your site will update in 1-2 minutes:"
echo "   https://d137gsvp1einvh.cloudfront.net"
echo ""
