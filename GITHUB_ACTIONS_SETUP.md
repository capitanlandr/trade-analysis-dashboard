# Running the Pipeline on GitHub (Not Local Machine)

## Overview

Instead of running `update_dashboard.py` on your local machine, you can have GitHub run it automatically in the cloud using **GitHub Actions**.

## Benefits

- ✅ **Automated**: Runs on a schedule (daily, weekly, etc.)
- ✅ **No local machine needed**: Runs in GitHub's cloud
- ✅ **Manual trigger**: Can also run on-demand with one click
- ✅ **Free**: GitHub Actions is free for public repos (2,000 minutes/month for private)
- ✅ **Reliable**: Runs even if your computer is off

## Setup Steps

### Step 1: Push Your Code to GitHub

First, make sure all your pipeline code is pushed to GitHub:

```bash
cd trade-analysis-dashboard-clean

# Add all files
git add .

# Commit
git commit -m "feat: add pipeline code and GitHub Actions workflow"

# Push to GitHub
git push origin main
```

### Step 2: Verify the Workflow File

The workflow file is already created at:
```
.github/workflows/update-dashboard.yml
```

This file tells GitHub:
- **When to run**: Daily at 9 AM EST (2 PM UTC)
- **What to do**: Install Python, run the pipeline, push results

### Step 3: Enable GitHub Actions (if needed)

1. Go to your GitHub repo: `https://github.com/capitanlandr/trade-analysis-dashboard`
2. Click the **"Actions"** tab
3. If prompted, click **"I understand my workflows, go ahead and enable them"**

### Step 4: Test Manual Run

1. Go to **Actions** tab on GitHub
2. Click **"Update Dashboard Data"** workflow on the left
3. Click **"Run workflow"** button (top right)
4. Click the green **"Run workflow"** button in the dropdown
5. Watch it run! (takes 2-3 minutes)

## How It Works

### Automatic Schedule
The workflow runs automatically every day at 9 AM EST:
```yaml
schedule:
  - cron: '0 14 * * *'  # 2 PM UTC = 9 AM EST
```

### Manual Trigger
You can also run it manually anytime:
1. Go to Actions tab
2. Select the workflow
3. Click "Run workflow"

### What Happens When It Runs

```
GitHub Actions Server (in the cloud):
1. Checks out your code
2. Installs Python 3.11
3. Installs dependencies (pandas, requests, etc.)
4. Runs: python3 update_dashboard.py
   - Fetches trades from Sleeper API
   - Processes data through all 7 stages
   - Copies 3 files to git root
   - Commits and pushes to GitHub
5. Vercel detects the push
6. Vercel deploys updated dashboard
```

## Customizing the Schedule

Edit `.github/workflows/update-dashboard.yml` to change when it runs:

```yaml
# Every day at 9 AM EST
- cron: '0 14 * * *'

# Every day at 6 AM EST
- cron: '0 11 * * *'

# Every Monday at 9 AM EST
- cron: '0 14 * * 1'

# Twice daily: 9 AM and 9 PM EST
- cron: '0 14,2 * * *'

# Every hour
- cron: '0 * * * *'
```

Cron format: `minute hour day month weekday`
- Use https://crontab.guru/ to help build cron schedules

## Monitoring

### View Run History
1. Go to **Actions** tab
2. See all past runs with status (✅ success or ❌ failed)
3. Click any run to see detailed logs

### Get Notifications
GitHub will email you if a workflow fails (you can configure this in Settings → Notifications)

### Check Logs
Click on any workflow run to see:
- Each step's output
- Any errors that occurred
- How long each stage took

## Troubleshooting

### Workflow Not Running?
- Check if Actions are enabled (Settings → Actions → General)
- Verify the workflow file is in `.github/workflows/`
- Check if the cron schedule is correct

### Pipeline Failing?
1. Click on the failed run
2. Expand the "Run pipeline and update dashboard" step
3. Read the error message
4. Common issues:
   - Missing dependencies → Check `requirements.txt`
   - API errors → Check Sleeper API status
   - Config errors → Verify `config/default.yaml`

### Need to Debug?
Add this step before running the pipeline to see what's in the directory:
```yaml
- name: Debug - List files
  run: |
    ls -la
    ls -la pipeline/
```

## Secrets (If Needed)

If you need to add API keys or secrets:

1. Go to repo Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Add your secret (e.g., `SLEEPER_API_KEY`)
4. Reference it in the workflow:
```yaml
env:
  SLEEPER_API_KEY: ${{ secrets.SLEEPER_API_KEY }}
```

## Cost

- **Public repos**: Free (unlimited minutes)
- **Private repos**: 2,000 free minutes/month
- Your pipeline takes ~2-3 minutes per run
- Daily runs = ~90 minutes/month (well under the limit)

## Disabling Automatic Runs

To stop automatic runs but keep manual trigger:

1. Edit `.github/workflows/update-dashboard.yml`
2. Comment out or remove the `schedule:` section:
```yaml
# schedule:
#   - cron: '0 14 * * *'
```
3. Commit and push

Or disable the entire workflow:
1. Go to Actions tab
2. Click the workflow
3. Click "..." menu → "Disable workflow"

## Re-enabling Local Runs

You can still run locally anytime:
```bash
cd trade-analysis-dashboard-clean
python3 update_dashboard.py
```

Both local and GitHub Actions can coexist!

## Next Steps

1. ✅ Push your code to GitHub
2. ✅ Test manual run from Actions tab
3. ✅ Wait for automatic run tomorrow at 9 AM EST
4. ✅ Check your dashboard updates automatically!

## Summary

**Before**: You had to manually run the script on your computer
**After**: GitHub runs it automatically in the cloud every day

Your dashboard stays up-to-date without you doing anything! 🎉
