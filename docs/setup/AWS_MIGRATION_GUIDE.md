# AWS Migration Guide: Vercel → AWS

> **Target Audience:** Technical Product Managers and developers new to AWS deployments
> 
> **Goal:** Migrate your static React dashboard from Vercel to AWS using S3 + CloudFront
> 
> **Estimated Time:** 2-3 hours for first-time setup

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Step 1: Verify AWS CLI Setup](#step-1-verify-aws-cli-setup)
4. [Step 2: Build Production Bundle](#step-2-build-production-bundle)
5. [Step 3: Create S3 Bucket](#step-3-create-s3-bucket)
6. [Step 4: Upload Website to S3](#step-4-upload-website-to-s3)
7. [Step 5: Create CloudFront Distribution](#step-5-create-cloudfront-distribution)
8. [Step 6: Test Your Website](#step-6-test-your-website)
9. [Step 7: Set Up CI/CD with GitHub Actions](#step-7-set-up-cicd-with-github-actions)
10. [Step 8: (Optional) Custom Domain](#step-8-optional-custom-domain)
11. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

### Current State (Vercel)
```
GitHub Push → Vercel Build → Vercel CDN → Users
```

### Target State (AWS)
```
GitHub Push → GitHub Actions → S3 Bucket → CloudFront CDN → Users
```

### AWS Services We'll Use

**Amazon S3 (Simple Storage Service)**
- **What it does:** Stores your website files (HTML, CSS, JS, JSON)
- **Why we need it:** It's like a file server in the cloud that can host static websites
- **Cost:** Very cheap (~$0.023 per GB/month, plus minimal request costs)

**Amazon CloudFront**
- **What it does:** Content Delivery Network (CDN) that caches your website globally
- **Why we need it:** Makes your site fast worldwide + provides HTTPS
- **Cost:** Free tier covers first 1TB of data transfer

**GitHub Actions**
- **What it does:** Runs automated deployment scripts when you push code
- **Why we need it:** Replaces Vercel's automatic deployment
- **Cost:** Free for public repos (2,000 minutes/month for private repos)

---

## Prerequisites

### What You Need
- ✅ AWS Account (personal or work)
- ✅ GitHub repository with your dashboard code
- ✅ Terminal/command line access
- ✅ Node.js and npm installed

### AWS Account Setup
If you don't have a personal AWS account yet:

1. Go to https://aws.amazon.com
2. Click "Create an AWS Account"
3. Follow the signup process (requires credit card, but we'll stay in free tier)
4. Enable MFA (multi-factor authentication) for security

**Note:** Since you work at Amazon, you can use internal resources, but this guide assumes a personal AWS account for separation of concerns.

---

## Step 1: Verify AWS CLI Setup

The AWS CLI (Command Line Interface) lets you control AWS services from your terminal.

### Check if AWS CLI is Installed

```bash
aws --version
```

**Expected output:** `aws-cli/2.x.x Python/3.x.x Darwin/xx.x.x`

### If Not Installed

**For macOS:**
```bash
# Using Homebrew (recommended)
brew install awscli

# Or download installer from:
# https://awscli.amazonaws.com/AWSCLIV2.pkg
```

### Configure AWS CLI

You need to tell the AWS CLI which account to use.

#### Option A: Using Personal AWS Account

1. **Get your AWS credentials:**
   - Log into AWS Console (https://console.aws.amazon.com)
   - Click your username (top right) → Security Credentials
   - Scroll to "Access keys" → Create access key
   - **Important:** Download and save the Access Key ID and Secret Access Key (you can't see the secret again!)

2. **Configure the CLI:**
   ```bash
   aws configure
   ```

   You'll be prompted for:
   ```
   AWS Access Key ID: [paste your key]
   AWS Secret Access Key: [paste your secret]
   Default region name: us-east-1
   Default output format: json
   ```

   **Region explanation:** `us-east-1` (N. Virginia) is the default and cheapest region. For CloudFront, it doesn't matter much since it's global.

#### Option B: Using Amazon Internal Tools (if applicable)

If you have Amazon internal credentials:
```bash
# Check if you have Isengard/Midway access
mwinit
```

### Verify Configuration

```bash
# Test that AWS CLI works
aws sts get-caller-identity
```

**Expected output:**
```json
{
    "UserId": "AIDXXXXXXXXXXXXXXXXXX",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/your-username"
}
```

✅ **Checkpoint:** You should see your AWS account number. If you see an error, double-check your credentials.

---

## Step 2: Build Production Bundle

Before deploying, we need to create optimized production files.

### Navigate to Frontend Directory

```bash
cd dashboard/frontend
```

### Install Dependencies (if needed)

```bash
npm install
```

### Build for Production

```bash
npm run build
```

**What this does:**
- Compiles TypeScript to JavaScript
- Minifies and optimizes code
- Bundles CSS
- Creates a `dist/` folder with production-ready files

### Verify Build Output

```bash
ls -lh dist/
```

**You should see:**
```
index.html          # Main HTML file
assets/             # JS, CSS, and other assets
api-trades.json     # Your data files
api-*.json          # Other data files
```

**Important:** The `dist/` folder contains everything needed for your website.

✅ **Checkpoint:** You should have a `dist/` folder with `index.html` and an `assets/` folder.

---

## Step 3: Create S3 Bucket

S3 buckets are like folders in the cloud that store files.

### Understanding Bucket Names
- Must be globally unique (across ALL AWS accounts)
- Can only contain lowercase letters, numbers, and hyphens
- Should be descriptive, e.g., `fantasy-trade-dashboard-2026` or `your-name-trade-dashboard`

### Create Bucket via AWS CLI

```bash
# Replace with your desired bucket name
export BUCKET_NAME="fantasy-trade-dashboard-2026"

# Create the bucket
aws s3 mb s3://$BUCKET_NAME --region us-east-1
```

**Expected output:** `make_bucket: fantasy-trade-dashboard-2026`

### Alternative: Create via AWS Console

If you prefer a visual interface:

1. Go to https://s3.console.aws.amazon.com
2. Click "Create bucket"
3. **Bucket name:** `fantasy-trade-dashboard-2026`
4. **Region:** `us-east-1`
5. **Block Public Access settings:** UNCHECK "Block all public access" (we need this for website hosting)
   - ⚠️ Warning will appear - click "I acknowledge..."
6. Click "Create bucket"

### Enable Static Website Hosting

```bash
# Enable website hosting on the bucket
aws s3 website s3://$BUCKET_NAME/ \
  --index-document index.html \
  --error-document index.html
```

**Why error-document is index.html:** React Router handles all routes client-side, so we redirect all 404s back to index.html.

### Set Bucket Policy for Public Read Access

Your website files need to be publicly readable. Create a policy file:

```bash
cat > bucket-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::$BUCKET_NAME/*"
    }
  ]
}
EOF
```

Apply the policy:

```bash
aws s3api put-bucket-policy \
  --bucket $BUCKET_NAME \
  --policy file://bucket-policy.json
```

✅ **Checkpoint:** Your S3 bucket is created and configured for public website hosting.

---

## Step 4: Upload Website to S3

Now we'll upload your built website to S3.

### Upload All Files

```bash
# From dashboard/frontend directory
aws s3 sync dist/ s3://$BUCKET_NAME/ \
  --delete \
  --cache-control "public, max-age=31536000" \
  --exclude "*.html" \
  --exclude "*.json"

# Upload HTML and JSON with shorter cache (they change more often)
aws s3 sync dist/ s3://$BUCKET_NAME/ \
  --exclude "*" \
  --include "*.html" \
  --include "*.json" \
  --cache-control "public, max-age=3600, must-revalidate"
```

**What these commands do:**
- `sync` - Copies files and only uploads changed files (smart!)
- `--delete` - Removes old files from S3 that don't exist locally
- `--cache-control` - Tells browsers how long to cache files
  - JS/CSS/images: 1 year (they have unique hashes in filenames)
  - HTML/JSON: 1 hour (they change when data updates)

### Verify Upload

```bash
aws s3 ls s3://$BUCKET_NAME/
```

**You should see:**
```
                           PRE assets/
2026-01-17 10:15:23       1234 index.html
2026-01-17 10:15:24       5678 api-trades.json
...
```

### Get S3 Website URL

```bash
echo "http://$BUCKET_NAME.s3-website-us-east-1.amazonaws.com"
```

**Try opening this URL in your browser.** You should see your dashboard!

⚠️ **Note:** This URL is HTTP only (not HTTPS) and not cached globally. That's why we need CloudFront next.

✅ **Checkpoint:** Your website is accessible via the S3 website URL.

---

## Step 5: Create CloudFront Distribution

CloudFront is AWS's Content Delivery Network (CDN). It provides:
- ✅ HTTPS (secure connections)
- ✅ Global caching (fast access worldwide)
- ✅ DDoS protection
- ✅ Custom domain support

### Create Distribution via AWS CLI

This is a bit complex, so we'll use the AWS Console for better visibility.

**Go to CloudFront Console:**
1. Visit https://console.cloudfront.aws.amazon.com
2. Click "Create Distribution"

**Configuration:**

**Origin Settings:**
- **Origin domain:** Click the dropdown and select your S3 bucket
  - ⚠️ **Important:** If you see two versions of your bucket, choose the one that says `.s3-website-` in it, NOT the plain `.s3.` one
  - OR manually enter: `fantasy-trade-dashboard-2026.s3-website-us-east-1.amazonaws.com`
- **Protocol:** HTTP only (S3 website endpoints don't support HTTPS from CloudFront)
- **Name:** Leave default (auto-fills)

**Default Cache Behavior:**
- **Viewer protocol policy:** Redirect HTTP to HTTPS
- **Allowed HTTP methods:** GET, HEAD
- **Cache policy:** CachingOptimized (recommended)

**Settings:**
- **Price class:** Use all edge locations (best performance, but "Use North America and Europe" is cheaper)
- **Alternate domain name (CNAME):** Leave blank for now (we'll add custom domain later)
- **Default root object:** `index.html`

**Click "Create Distribution"**

### Wait for Deployment

CloudFront takes 10-20 minutes to deploy globally. You'll see:
- Status: "Deploying" → "Enabled"
- State: "In Progress" → "Deployed"

**Get Your CloudFront URL:**

After deployment, you'll see a "Distribution domain name" like:
```
d1234567890abc.cloudfront.net
```

**Test it:**
```bash
# Replace with your actual CloudFront domain
curl -I https://d1234567890abc.cloudfront.net
```

✅ **Checkpoint:** CloudFront distribution is created and you have an HTTPS URL.

---

## Step 6: Test Your Website

### Open in Browser

Visit your CloudFront URL: `https://d1234567890abc.cloudfront.net`

**What to test:**
- ✅ Homepage loads
- ✅ Navigation works (Overview, Standings, Playoffs, etc.)
- ✅ Data displays correctly
- ✅ React Router navigation works (no 404s)
- ✅ HTTPS padlock shows in browser

### Troubleshooting Common Issues

**Problem:** Page shows blank or "Cannot GET /"
- **Solution:** Check CloudFront origin is pointing to S3 **website endpoint** (not regular S3 endpoint)

**Problem:** React Router routes show 404
- **Solution:** Create CloudFront custom error response
  1. Go to CloudFront distribution → Error Pages tab
  2. Create custom error response:
     - HTTP error code: 404
     - Customize error response: Yes
     - Response page path: `/index.html`
     - HTTP response code: 200

**Problem:** Old data showing
- **Solution:** CloudFront caches content. Invalidate cache:
  ```bash
  aws cloudfront create-invalidation \
    --distribution-id YOUR_DISTRIBUTION_ID \
    --paths "/*"
  ```

✅ **Checkpoint:** Your website is live on AWS with HTTPS!

---

## Step 7: Set Up CI/CD with GitHub Actions

Now we'll automate deployments so that pushing to GitHub automatically updates your website.

### Create GitHub Secrets

You need to store AWS credentials in GitHub securely.

1. Go to your GitHub repository
2. Click Settings → Secrets and variables → Actions
3. Click "New repository secret"

**Add these secrets:**

| Name | Value | Description |
|------|-------|-------------|
| `AWS_ACCESS_KEY_ID` | Your AWS access key | From Step 1 |
| `AWS_SECRET_ACCESS_KEY` | Your AWS secret key | From Step 1 |
| `AWS_S3_BUCKET` | `fantasy-trade-dashboard-2026` | Your bucket name |
| `AWS_CLOUDFRONT_DISTRIBUTION_ID` | `E1234567890ABC` | From CloudFront console |

**To find CloudFront Distribution ID:**
```bash
aws cloudfront list-distributions --query "DistributionList.Items[*].[Id,DomainName]" --output table
```

### Create GitHub Actions Workflow

Create a new workflow file:

```bash
mkdir -p .github/workflows
```

Create `.github/workflows/deploy-aws.yml`:

```yaml
name: Deploy to AWS

on:
  push:
    branches: [ main ]
    paths:
      - 'dashboard/frontend/**'
      - '.github/workflows/deploy-aws.yml'
  workflow_dispatch:  # Allows manual trigger

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          cache: 'npm'
          cache-dependency-path: 'dashboard/frontend/package-lock.json'
      
      - name: Install dependencies
        run: |
          cd dashboard/frontend
          npm ci
      
      - name: Build
        run: |
          cd dashboard/frontend
          npm run build
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Sync to S3
        run: |
          cd dashboard/frontend
          
          # Upload assets with long cache
          aws s3 sync dist/ s3://${{ secrets.AWS_S3_BUCKET }}/ \
            --delete \
            --cache-control "public, max-age=31536000, immutable" \
            --exclude "*.html" \
            --exclude "*.json"
          
          # Upload HTML and JSON with short cache
          aws s3 sync dist/ s3://${{ secrets.AWS_S3_BUCKET }}/ \
            --exclude "*" \
            --include "*.html" \
            --include "*.json" \
            --cache-control "public, max-age=3600, must-revalidate"
      
      - name: Invalidate CloudFront
        run: |
          aws cloudfront create-invalidation \
            --distribution-id ${{ secrets.AWS_CLOUDFRONT_DISTRIBUTION_ID }} \
            --paths "/*"
      
      - name: Deployment summary
        run: |
          echo "✅ Deployment complete!"
          echo "🌐 Website: https://$(aws cloudfront get-distribution --id ${{ secrets.AWS_CLOUDFRONT_DISTRIBUTION_ID }} --query 'Distribution.DomainName' --output text)"
```

### Commit and Push

```bash
git add .github/workflows/deploy-aws.yml
git commit -m "feat: add AWS deployment workflow"
git push origin main
```

### Monitor Deployment

1. Go to your GitHub repository
2. Click "Actions" tab
3. You should see "Deploy to AWS" workflow running
4. Click on it to see logs

**Deployment takes ~3-5 minutes:**
- Install dependencies (1-2 min)
- Build (30 sec)
- Upload to S3 (30 sec)
- Invalidate CloudFront (1-2 min)

✅ **Checkpoint:** GitHub Actions automatically deploys your site to AWS!

---

## Step 8: (Optional) Custom Domain

If you want a custom domain like `fantasy.yourdomain.com` instead of CloudFront's domain:

### Prerequisites
- Own a domain name (can buy one via Route 53 or use existing)
- Domain managed in Route 53 OR ability to create CNAME records

### Option A: Full Route 53 Setup

**If your domain is in Route 53:**

1. **Request SSL Certificate (in `us-east-1` region - required for CloudFront):**
   ```bash
   aws acm request-certificate \
     --domain-name fantasy.yourdomain.com \
     --validation-method DNS \
     --region us-east-1
   ```

2. **Validate certificate** (follow email or DNS validation steps)

3. **Update CloudFront distribution:**
   - Go to CloudFront console
   - Edit distribution
   - Alternate domain names (CNAMEs): Add `fantasy.yourdomain.com`
   - SSL certificate: Select your ACM certificate
   - Save changes (takes ~10 min to deploy)

4. **Create Route 53 record:**
   ```bash
   # Get your hosted zone ID
   aws route53 list-hosted-zones
   
   # Create alias record pointing to CloudFront
   # (Use Route 53 console for easier setup)
   ```

### Option B: External DNS Provider

**If your domain is NOT in Route 53:**

1. Request SSL certificate (same as above)
2. Validate certificate
3. Update CloudFront (same as above)
4. In your DNS provider, create a CNAME record:
   - Name: `fantasy` (or whatever subdomain)
   - Value: `d1234567890abc.cloudfront.net` (your CloudFront domain)
   - TTL: 300

**Wait for DNS propagation (5-30 minutes), then test:**
```bash
curl -I https://fantasy.yourdomain.com
```

✅ **Checkpoint:** Your website is accessible via custom domain!

---

## Troubleshooting

### S3 Issues

**Problem:** Bucket name already taken
- **Solution:** Choose a different name (must be globally unique)

**Problem:** Access Denied when accessing website
- **Solution:** Check bucket policy allows public read access

**Problem:** Files uploaded but website shows old version
- **Solution:** Check cache headers, may need to hard refresh browser (Cmd+Shift+R)

### CloudFront Issues

**Problem:** 403 Forbidden errors
- **Solution:** Verify CloudFront origin points to S3 **website endpoint** (has `s3-website-` in URL)

**Problem:** React Router routes don't work
- **Solution:** Add custom error response for 404 → 200 with `/index.html`

**Problem:** Updates not showing
- **Solution:** Create CloudFront invalidation to clear cache

### GitHub Actions Issues

**Problem:** Workflow fails with "Access Denied"
- **Solution:** Check AWS credentials in GitHub Secrets are correct

**Problem:** Build fails
- **Solution:** Check build logs, may need to update Node.js version in workflow

**Problem:** Files uploaded but site not updating
- **Solution:** Check CloudFront invalidation is running (can take 1-2 minutes)

### General Debugging

**View S3 bucket contents:**
```bash
aws s3 ls s3://your-bucket-name/ --recursive
```

**Test file directly from S3:**
```bash
curl https://your-bucket-name.s3.amazonaws.com/index.html
```

**Check CloudFront distribution status:**
```bash
aws cloudfront get-distribution --id YOUR_DIST_ID --query "Distribution.Status"
```

**View CloudFront access logs** (if enabled):
- Helpful for debugging 403/404 errors
- Shows which files users are requesting

---

## Cost Estimation

### Monthly Costs (Typical Small Site)

| Service | Usage | Cost |
|---------|-------|------|
| S3 Storage | 1 GB | $0.023 |
| S3 Requests | 10,000 | $0.005 |
| CloudFront Data Transfer | 10 GB | FREE (free tier) |
| CloudFront Requests | 10,000 | FREE (free tier) |
| **Total** | | **~$0.03/month** |

**Free Tier Benefits:**
- S3: 5 GB storage + 20,000 GET requests (first year)
- CloudFront: 1 TB data transfer + 10M requests (always free)

**Cost comparison to Vercel:**
- Vercel Hobby (free): $0/month but limits apply
- AWS: ~$0.03-0.50/month, no limits, full control

---

## Next Steps

### You've Successfully Migrated! 🎉

**What you've accomplished:**
- ✅ Built production-ready static site
- ✅ Deployed to S3 with public access
- ✅ Set up CloudFront for global CDN + HTTPS
- ✅ Automated deployments with GitHub Actions
- ✅ (Optional) Configured custom domain

### Recommended Follow-ups

1. **Set up monitoring:**
   - Enable CloudFront logging
   - Create CloudWatch alarms for unusual traffic

2. **Optimize costs:**
   - Review S3 lifecycle policies
   - Consider CloudFront price class options

3. **Improve security:**
   - Set up AWS WAF (Web Application Firewall) if needed
   - Review bucket policies regularly

4. **Learn more:**
   - AWS Well-Architected Framework
   - AWS Skill Builder courses on S3 and CloudFront

---

## Additional Resources

### AWS Documentation
- [S3 Static Website Hosting](https://docs.aws.amazon.com/AmazonS3/latest/userguide/WebsiteHosting.html)
- [CloudFront Getting Started](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/GettingStarted.html)
- [GitHub Actions AWS Deploy](https://github.com/aws-actions/configure-aws-credentials)

### Internal Amazon Resources (if applicable)
- Search internal wiki for "S3 static hosting best practices"
- Check Sage for "CloudFront distribution setup"
- Review internal security guidelines for public S3 buckets

### Community Resources
- AWS Free Tier: https://aws.amazon.com/free/
- AWS Pricing Calculator: https://calculator.aws/
- React + S3 Deployment Guide: https://create-react-app.dev/docs/deployment/#s3-and-cloudfront

---

## Glossary

**S3 (Simple Storage Service):** Object storage service for storing files
**CloudFront:** Content Delivery Network (CDN) that caches content globally
**Distribution:** A CloudFront configuration that serves your website
**Origin:** The source where CloudFront fetches content (your S3 bucket)
**Edge Location:** Data centers around the world where CloudFront caches content
**Invalidation:** Clearing CloudFront's cache to show updated content
**ACM (AWS Certificate Manager):** Service for managing SSL/TLS certificates
**Route 53:** AWS's DNS service for managing domain names

---

**Questions or issues?** Check the troubleshooting section or search internal Amazon resources (Sage, Wiki) for help.
