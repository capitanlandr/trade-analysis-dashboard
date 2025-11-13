# Quick Start: Automated Dashboard Updates

## 🎯 Goal
Have your dashboard update automatically every day without touching your computer.

## 📋 3-Step Setup

### Step 1: Push to GitHub (One Time)
```bash
cd trade-analysis-dashboard-clean
git add .
git commit -m "feat: add automated pipeline"
git push origin main
```

### Step 2: Test on GitHub (One Time)
1. Go to: https://github.com/capitanlandr/trade-analysis-dashboard
2. Click **"Actions"** tab at the top
3. Click **"Update Dashboard Data"** on the left
4. Click **"Run workflow"** button (green button, top right)
5. Click **"Run workflow"** again in the dropdown
6. Watch it run! ⏱️ Takes 2-3 minutes

### Step 3: Done! ✅
- Now it runs **automatically every day at 9 AM EST**
- You can also run it manually anytime from the Actions tab
- Your dashboard updates without you doing anything

## 🔄 How It Works

```
Every day at 9 AM EST:

GitHub Actions (cloud) 
    ↓
Runs your pipeline
    ↓
Fetches trades from Sleeper
    ↓
Processes all data
    ↓
Pushes to GitHub
    ↓
Vercel deploys dashboard
    ↓
✅ Dashboard updated!
```

## 🎮 Manual Run Anytime

Want to update right now?
1. Go to Actions tab on GitHub
2. Click "Run workflow"
3. Done in 2-3 minutes!

## 📅 Change the Schedule

Edit `.github/workflows/update-dashboard.yml`:

```yaml
# Current: Daily at 9 AM EST
- cron: '0 14 * * *'

# Change to: Daily at 6 AM EST
- cron: '0 11 * * *'

# Change to: Twice daily (9 AM and 9 PM EST)
- cron: '0 14,2 * * *'
```

Use https://crontab.guru/ to create custom schedules.

## 🔍 View Run History

Actions tab shows:
- ✅ Successful runs (green checkmark)
- ❌ Failed runs (red X)
- ⏱️ How long each run took
- 📝 Detailed logs for debugging

## 💰 Cost

**FREE!** 
- Public repos: Unlimited
- Private repos: 2,000 minutes/month free
- Your pipeline uses ~90 minutes/month (daily runs)

## 🚨 Troubleshooting

**Workflow not showing up?**
- Make sure you pushed `.github/workflows/update-dashboard.yml`
- Check Actions are enabled in repo Settings

**Run failed?**
- Click on the failed run
- Read the error logs
- Most common: API rate limits or config issues

**Want to stop automatic runs?**
- Go to Actions → Click workflow → "..." menu → "Disable workflow"
- Or delete the `schedule:` section from the workflow file

## 🎉 That's It!

Your dashboard now updates automatically every day. No more manual work!

**Questions?** See `GITHUB_ACTIONS_SETUP.md` for detailed docs.
