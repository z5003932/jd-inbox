# JD Inbox - Backend Deployment Guide

## Session 1: Core Backend + File Upload + Extraction ✅

### What's Working
- ✅ FastAPI backend structure
- ✅ SQLite database with schema
- ✅ File upload endpoint (PDF, images, Word docs)
- ✅ JD extraction using Claude vision API
- ✅ `/api/jobs` endpoint to fetch all jobs for table
- ✅ Health check endpoint at `/health`

### What's Coming
- 🔜 Session 2: Rapid execution
- 🔜 Session 3: Tier A/B/C/D execution
- 🔜 Session 4: CV generation + download
- 🔜 Session 5: Chat refinement + final polish

---

## Deploy to Render (Cloud)

### 1. Push to GitHub

```bash
# Initialize git repo
cd jd-inbox-backend/
git init
git add .
git commit -m "Session 1: Core backend + file upload"

# Create GitHub repo (do this on github.com)
# Then push:
git remote add origin https://github.com/YOUR_USERNAME/jd-inbox-backend.git
git branch -M main
git push -u origin main
```

### 2. Deploy on Render

1. Go to [render.com](https://render.com) and sign up/login
2. Click "New +" → "Web Service"
3. Connect your GitHub repo
4. Configure:
   - **Name**: `jd-inbox-dav` (or your choice)
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free

5. Add environment variable:
   - Key: `ANTHROPIC_API_KEY`
   - Value: `your-claude-api-key-here`

6. Click "Create Web Service"

**Deploy time:** ~3-5 minutes

**Your URL:** `https://jd-inbox-dav.onrender.com`

---

## Test the Deployment

### Health Check
```bash
curl https://jd-inbox-dav.onrender.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

### Upload a File (via browser)
1. Visit: `https://jd-inbox-dav.onrender.com`
2. HTML interface loads
3. Drop a PDF/screenshot of a JD
4. File uploads → extraction runs → row appears in table

### Check Jobs List
```bash
curl https://jd-inbox-dav.onrender.com/api/jobs
```

Should return array of jobs (empty at first).

---

## Local Testing (Optional)

```bash
# Install dependencies
pip install -r requirements.txt

# Set API key
export ANTHROPIC_API_KEY="your-key-here"

# Run locally
python main.py
```

Visit: `http://localhost:8000`

---

## Project Structure

```
jd-inbox-backend/
├── main.py                 # FastAPI app entry point
├── models.py               # Database models (SQLite)
├── routes/
│   ├── upload.py          # ✅ File upload + extraction
│   ├── rapid.py           # 🔜 Session 2
│   ├── tier.py            # 🔜 Session 3
│   ├── download.py        # 🔜 Session 4
│   └── chat.py            # 🔜 Session 5
├── services/
│   ├── extraction.py      # ✅ JD extraction (Claude API)
│   ├── rapid_engine.py    # 🔜 Session 2
│   ├── tier_engine.py     # 🔜 Session 3
│   └── cv_generator.py    # 🔜 Session 4
├── static/
│   └── jd_inbox.html      # ✅ Frontend interface
├── uploads/               # Uploaded files
├── outputs/               # Generated CVs
├── data/                  # Evidence base CSVs
├── requirements.txt       # Python dependencies
├── render.yaml            # Render config
└── jd_inbox.db           # SQLite database (created on first run)
```

---

## API Endpoints (Current)

### Session 1 - Working Now
- `GET /` - Serve HTML interface
- `GET /health` - Health check
- `GET /api/jobs` - List all jobs
- `POST /api/upload` - Upload JD file
- `GET /api/upload/status/{job_id}` - Check extraction status

### Session 2 - Coming Next
- `POST /api/rapid/{job_id}` - Run JD Rapid

### Session 3 - After That
- `POST /api/tier/a/{job_id}` - Tier A (upload as-is)
- `POST /api/tier/b/{job_id}` - Tier B (fast CV)
- `POST /api/tier/c/{job_id}` - Tier C (targeted tweak)
- `POST /api/tier/d/{job_id}` - Tier D (full engine)

### Session 4
- `GET /api/download/{job_id}` - Download generated CV

### Session 5
- `POST /api/chat/{job_id}` - Chat refinement
- `WebSocket /ws/chat/{job_id}` - Chat streaming

---

## Database Schema

```sql
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY,
    filename TEXT,
    role TEXT,
    company TEXT,
    sector TEXT,
    mode TEXT,
    source TEXT,
    jd_text TEXT,
    jd_file_path TEXT,
    
    status TEXT,            -- pending/rapid/tier/cv/applied/skipped
    score INTEGER,          -- 1-10
    tier TEXT,              -- A/B/C/D/SKIP
    archetype TEXT,
    brief TEXT,
    why TEXT,
    green_flags TEXT,       -- JSON array
    red_flags TEXT,         -- JSON array
    
    rapid_output TEXT,
    tier_output TEXT,
    cv_text TEXT,
    cv_file_path TEXT,
    cover_letter_text TEXT,
    
    chat_history TEXT,      -- JSON array
    
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

---

## Next Steps

**After Session 1 is deployed:**
1. Test file upload with real JD (PDF/screenshot)
2. Verify extraction works (role/company/sector populated)
3. Confirm row appears in table
4. Ready for Session 2 (Rapid execution)

**To iterate the UI:**
1. Edit `static/jd_inbox.html`
2. `git commit -am "UI tweak"`
3. `git push`
4. Render auto-deploys in 2 min
5. Refresh browser to see changes

---

## Troubleshooting

**File upload fails:**
- Check Render logs: Dashboard → Service → Logs
- Verify `ANTHROPIC_API_KEY` is set
- Check file size (Render free tier max 512MB total storage)

**Extraction returns "Not specified":**
- Claude API might be rate-limited
- Check logs for API errors
- Verify file is readable (not corrupted PDF)

**Database errors:**
- SQLite file persists on Render disk (not ephemeral)
- Database resets if service restarts (free tier limitation)
- Upgrade to paid plan for persistent disk if needed

---

**Session 1 Status: READY TO DEPLOY** 🚀
