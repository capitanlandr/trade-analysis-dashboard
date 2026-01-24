# Dashboard URLs Reference

## Your Production URLs

### AWS CloudFront (Primary)
```
https://d137gsvp1einvh.cloudfront.net
```
**Status:** ✅ Live and working
**Hosted:** AWS S3 + CloudFront CDN
**Deployment:** GitHub Actions (deploy-aws.yml)
**Cost:** ~$0.03/month

### Vercel (Backup)
```
https://dynasuiiiianalytics.vercel.app
```
**Status:** ✅ Live and working
**Hosted:** Vercel
**Deployment:** Vercel Git integration (automatic)
**Cost:** $0/month (free tier)

---

## Important: URLs Are Public (Not Secret!)

**These URLs are meant to be shared** - they're public websites!

**It's totally safe that they're in your git repo** because:
- ✅ Anyone can visit them (they're public websites)
- ✅ No security risk
- ✅ Similar to sharing "https://google.com"
- ✅ AWS resource IDs (S3 bucket name, CloudFront ID) are also safe to share

**What IS secret (protected in .gitignore):**
- ❌ AWS Access Key ID: `AKIATE3FIQU45YXIACV3`
- ❌ AWS Secret Access Key: `x6lA6ZjbDGpgMW7uwJNK/...`

---

## Where Your URLs Are Documented

### Committed to Git (Public - Safe) ✅
- `AWS_MIGRATION_GUIDE.md` - CloudFront URL
- `CUSTOM_DOMAIN_OPTIONS.md` - CloudFront URL
- `VERCEL_DOMAIN_OPTIONS.md` - Both URLs
- `WEEKLY_UPDATE_GUIDE.md` - Vercel URL
- `plans/MULTI_SEASON_LEAGUE_ID_ARCHITECTURE.md` - Vercel URL

### Protected (Local Only - Has AWS Keys) 🔒
- `DEPLOYMENT_SUMMARY.md` - Both URLs + AWS keys
- `GITHUB_SECRETS_SETUP.md` - URLs + AWS keys
- `AWS_ACCOUNT_SETUP_CHECKLIST.md` - URLs + AWS keys
- `cloudfront-details.txt` - CloudFront details only

---

## AWS Resource IDs (Safe to Share)

**These are also public information:**
- S3 Bucket: `dynasuiiii-website`
- CloudFront Distribution ID: `EL6SCNZ7VJGN2`
- AWS Account: `216571348281`
- Region: `us-east-1`

**Why they're safe:**
- Can't access your AWS account without credentials
- Anyone can see them by visiting your website
- Similar to knowing a website's IP address

---

## Quick Reference

**Both URLs work and will continue to work:**
- CloudFront → Serves from AWS (updated by GitHub Actions)
- Vercel → Serves from Vercel (updated by Vercel Git integration)

**Daily workflow updates both automatically!**
