# Dashboard API - Lambda Function Reference

> **STATUS (June 2026):** Lambda API is deployed and functional but the frontend is NOT wired to it in production. Production uses static JSON from the pipeline. Lambda data has diverged from pipeline output. See `.env.production` for toggle details.

## 🎉 Your Live Serverless API

**Base URL:** https://aucuc2yvd4.execute-api.us-east-1.amazonaws.com/Prod/api/

**Lambda Function:** `fantasy-backend-DashboardApiFunction-fZRCWacynkMU`
**Stack:** `fantasy-backend`
**Region:** us-east-1
**Account:** 216571348281 (personal)

---

## 📍 API Endpoints

### 1. Health Check
```
GET /api/health
```
**Returns:** API status and available endpoints
**Test:**
```bash
curl https://aucuc2yvd4.execute-api.us-east-1.amazonaws.com/Prod/api/health
```

### 2. Trades (Real-Time)
```
GET /api/trades
```
**Returns:** All trades from Sleeper API in real-time
**Data:** League ID 1312166810505719808
**Test:**
```bash
curl https://aucuc2yvd4.execute-api.us-east-1.amazonaws.com/Prod/api/trades
```

### 3. Standings (Real-Time)
```
GET /api/standings
```
**Returns:** Current league standings with wins/losses/points
**Data:** Fetched from Sleeper rosters + users APIs
**Test:**
```bash
curl https://aucuc2yvd4.execute-api.us-east-1.amazonaws.com/Prod/api/standings
```

### 4. Waiver Wire (Real-Time)
```
GET /api/waivers
```
**Returns:** All waiver and free agent transactions
**Data:** Filtered from Sleeper transactions API
**Test:**
```bash
curl https://aucuc2yvd4.execute-api.us-east-1.amazonaws.com/Prod/api/waivers
```

### 5. League Info
```
GET /api/league-info
```
**Returns:** League metadata (name, season, status, roster count)
**Test:**
```bash
curl https://aucuc2yvd4.execute-api.us-east-1.amazonaws.com/Prod/api/league-info
```

---

## 🔧 Technical Details

### CORS Headers (Enabled)
```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET,OPTIONS
```
**Allows** your frontend (CloudFront or Vercel) to call this API

### Response Format
All endpoints return JSON:
```json
{
  "success": true,
  "source": "real-time-sleeper-api",
  "timestamp": "2026-01-21T08:20:46Z",
  "data": { ... }
}
```

### Error Handling
```json
{
  "error": "error message",
  "endpoint": "/api/endpoint-name"
}
```

---

## 💰 Cost

**Free Tier Covers:**
- Lambda: 1M invocations/month
- API Gateway: 1M requests/month
- **Your usage:** Likely <1000 requests/month
- **Cost:** $0.00/month

---

## 🚀 How to Update Lambda

### 1. Edit Code
```bash
# Edit: backend-api/fantasy-backend/dashboard_api/app.py
```

### 2. Deploy
```bash
cd backend-api/fantasy-backend
sam deploy
```

### 3. Test
```bash
curl https://aucuc2yvd4.execute-api.us-east-1.amazonaws.com/Prod/api/health
```

---

## 📊 What You Built

**Monolithic Lambda Architecture:**
```
API Gateway: /api/{proxy+}
    ↓
Lambda: dashboard_api
    ├── /api/health      → Status check
    ├── /api/trades      → Sleeper trades API
    ├── /api/standings   → Sleeper rosters + users API
    ├── /api/waivers     → Sleeper transactions API
    └── /api/league-info → Sleeper league metadata
```

**All endpoints:**
- ✅ Deployed to AWS
- ✅ Fetching real-time Sleeper data
- ✅ CORS enabled for frontend
- ✅ Error handling included
- ✅ FREE (within free tier)

---

## 🔗 Integration with Frontend

### Current (Static)
```typescript
// Frontend fetches static JSON
fetch('/api-standings.json')
```

### Future (Dynamic)
```typescript
// Frontend calls Lambda API
fetch('https://aucuc2yvd4.execute-api.us-east-1.amazonaws.com/Prod/api/standings')
```

---

## 📝 Next Steps

### Option A: Integrate with Frontend (Next!)
1. Update React to call Lambda endpoints
2. Deploy updated frontend
3. Dashboard shows real-time data

### Option B: Keep Both (Hybrid)
1. Use Lambda for real-time endpoints
2. Keep static JSON for heavy computations
3. Best of both worlds

### Option C: Just Keep Lambda Deployed (Learning Complete)
1. Lambda proves you can do it
2. Keep current static dashboard working
3. Integrate later if needed

---

## 🎓 What You Learned

**AWS Services:**
- ✅ Lambda (serverless functions)
- ✅ API Gateway (HTTP APIs)
- ✅ CloudFormation (infrastructure as code)
- ✅ IAM (function roles and permissions)
- ✅ CloudWatch (automatic logging)

**Concepts:**
- ✅ Serverless architecture
- ✅ RESTful API design
- ✅ CORS for frontend-backend communication
- ✅ Error handling in Lambda
- ✅ Real-time data fetching

---

Your Lambda API is LIVE and working! Ready to connect it to your dashboard?
