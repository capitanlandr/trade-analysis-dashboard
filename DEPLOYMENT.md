# Deployment Guide

## Prerequisites

- GitHub account with repository access
- Vercel account (free tier works)
- Google Drive folder with Commish Tiers documents

## Initial Setup

### 1. Configure Google Drive Folder

1. Create or identify your Google Drive folder containing Commish Tiers documents
2. Set folder sharing to "Anyone with the link can view"
3. Copy the folder ID from the URL:
   ```
   https://drive.google.com/drive/folders/[FOLDER_ID]
   ```

### 2. Configure Environment Variables

**Local Development:**

Edit `dashboard/frontend/.env`:
```env
VITE_API_BASE_URL=http://localhost:3001/api
VITE_DRIVE_FOLDER_ID=your_folder_id_here
```

**Vercel Production:**

1. Go to your Vercel project dashboard
2. Navigate to Settings → Environment Variables
3. Add the following variables:
   - `VITE_DRIVE_FOLDER_ID` = your folder ID

Note: The folder ID is not sensitive since it's visible in the iframe URL. You can commit it to `.env` if preferred.

### 3. Deploy to Vercel

**Option A: Automatic (Recommended)**

1. Push your code to GitHub:
   ```bash
   git add .
   git commit -m "feat: add commish tiers archive"
   git push origin main
   ```

2. Vercel automatically detects the push and deploys

**Option B: Manual Deploy**

1. Install Vercel CLI:
   ```bash
   npm install -g vercel
   ```

2. Deploy:
   ```bash
   cd trade-analysis-dashboard-clean
   vercel --prod
   ```

## Updating Data

The dashboard data updates automatically via GitHub Actions:

- **Automatic**: Runs daily at 9 AM EST
- **Manual**: Go to Actions tab → "Update Dashboard Data" → "Run workflow"

The workflow:
1. Fetches latest trades from Sleeper API
2. Processes and values all assets
3. Generates JSON files
4. Commits and pushes to GitHub
5. Triggers Vercel deployment

## Verifying Deployment

1. **Check Vercel Dashboard**
   - Verify deployment status is "Ready"
   - Check build logs for errors

2. **Test the Application**
   - Navigate to your Vercel URL
   - Verify all pages load correctly
   - Test the Commish Tiers Archive tab
   - Confirm Google Drive folder displays

3. **Check Console**
   - Open browser DevTools
   - Look for any errors in Console tab
   - Verify API calls succeed

## Troubleshooting

### Google Drive Embed Not Loading

**Symptoms**: Blank iframe or error message

**Solutions**:
1. Verify `VITE_DRIVE_FOLDER_ID` is set correctly
2. Check folder sharing settings (must be "Anyone with the link")
3. Test folder URL directly: `https://drive.google.com/drive/folders/[FOLDER_ID]`
4. Clear browser cache and reload

### Environment Variables Not Applied

**Symptoms**: Features using env vars don't work

**Solutions**:
1. Verify variables are set in Vercel dashboard
2. Redeploy after adding/changing variables
3. Check variable names match exactly (case-sensitive)
4. For local dev, restart dev server after changing `.env`

### Build Failures

**Symptoms**: Vercel deployment fails

**Solutions**:
1. Check build logs in Vercel dashboard
2. Verify all dependencies are in `package.json`
3. Test build locally: `npm run build`
4. Check for TypeScript errors: `npm run lint`

### Data Not Updating

**Symptoms**: Dashboard shows old data

**Solutions**:
1. Check GitHub Actions run history
2. Verify JSON files were committed
3. Manually trigger workflow from Actions tab
4. Check Vercel deployment triggered after commit

## Rollback

If a deployment has issues:

1. **Via Vercel Dashboard**
   - Go to Deployments
   - Find previous working deployment
   - Click "..." → "Promote to Production"

2. **Via Git**
   ```bash
   git revert HEAD
   git push origin main
   ```

## Monitoring

- **Vercel Analytics**: Track page views and performance
- **GitHub Actions**: Monitor pipeline execution
- **Browser Console**: Check for client-side errors
- **Vercel Logs**: View server-side logs

## Security Notes

- Google Drive folder ID is public (visible in iframe)
- No sensitive data in environment variables
- All API calls are client-side (no secrets exposed)
- Folder permissions controlled by Google Drive settings

---

**Need Help?** Check the main [README.md](README.md) or open an issue on GitHub.
