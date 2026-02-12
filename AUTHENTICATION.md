# Google OAuth Authentication

This document explains the Google OAuth authentication implementation in Innovation Airlock.

## Overview

Users can sign in with their Google account. Authentication is session-based using encrypted cookies, with no database storage required for user data.

## Architecture

### Backend (FastAPI)

**Session Management:**
- Uses `starlette.middleware.sessions.SessionMiddleware`
- Session data stored in encrypted browser cookies
- No database needed for user sessions

**Auth Endpoints** (`backend/auth/routes.py`):
- `GET /api/auth/login` - Initiates Google OAuth flow
- `GET /api/auth/callback` - Handles OAuth redirect from Google
- `GET /api/auth/status` - Returns current user info if logged in
- `GET /api/auth/logout` - Clears session

**OAuth Flow** (`backend/auth/google_oauth.py`):
- Uses `google-auth-oauthlib` library
- Scopes: `openid`, `userinfo.email`, `userinfo.profile`, `drive.readonly`
- Stores user info in session: `user_id`, `user_email`, `user_name`, `user_picture`

### Frontend (React)

**Auth State** (`App.tsx`):
- Checks auth status on page load
- Stores auth state in React: `{ authenticated: boolean, user?: {...} }`
- Passes state to Header component

**UI** (`Header.tsx`):
- **Not logged in:** "Sign in with Google" button (white, top-right)
- **Logged in:** User name + "Sign out" button (subtle, gray)

**API Layer** (`api.ts`):
- `checkAuthStatus()` - Fetch current auth state
- `login()` - Redirect to Google OAuth
- `logout()` - Clear session

## Setup Instructions

### 1. Google Cloud Console Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select a project
3. Enable **Google+ API** (for userinfo)
4. Go to **APIs & Services > Credentials**
5. Create **OAuth 2.0 Client ID** (Web application)

**Configure OAuth Client:**

```
Authorized JavaScript origins:
  http://localhost:5173
  http://localhost:8000

Authorized redirect URIs:
  http://localhost:8000/api/auth/callback
```

6. Copy **Client ID** and **Client Secret**

### 2. Environment Variables

Add to `.env` file in project root:

```bash
# Google OAuth
GOOGLE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your-client-secret-here
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/callback
SESSION_SECRET_KEY=your-random-secret-key-for-session-encryption
```

**Generate a secure session key:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

Required packages:
- `google-auth-oauthlib`
- `google-auth`
- `python-dotenv`
- `itsdangerous`

### 4. Run the Application

**Backend:**
```bash
cd backend
python run.py
```

**Frontend:**
```bash
cd frontend
npm run dev
```

## How It Works

### Login Flow

1. User clicks "Sign in with Google" button
2. Frontend redirects to `/api/auth/login`
3. Backend generates OAuth URL and redirects to Google
4. User authenticates with Google
5. Google redirects to `/api/auth/callback?code=...&state=...`
6. Backend exchanges code for user credentials
7. User info stored in encrypted session cookie
8. User redirected to frontend (`http://localhost:5173`)
9. Frontend checks `/api/auth/status` and shows user name

### Session Data

Stored in encrypted cookie:
```javascript
{
  user_id: "google-user-id-123",
  user_email: "user@example.com",
  user_name: "John Doe",
  user_picture: "https://..."
}
```

### Logout Flow

1. User clicks "Sign out"
2. Frontend calls `/api/auth/logout`
3. Backend clears session cookie
4. Frontend updates UI to show "Sign in with Google"

## Security Notes

- **Session cookies** are encrypted using `SESSION_SECRET_KEY`
- **CORS** is configured to allow credentials from `localhost:5173`
- **No passwords** are stored (delegated to Google)
- **HTTPS required** for production (change redirect URIs)

## Production Deployment

For production, update:

1. **Google Cloud Console:**
   - Add production domain to authorized origins/redirect URIs
   - Example: `https://airlock.yourdomain.com`

2. **Environment Variables:**
   ```bash
   GOOGLE_REDIRECT_URI=https://airlock.yourdomain.com/api/auth/callback
   SESSION_SECRET_KEY=<production-secret-key>
   ```

3. **CORS Settings** (`backend/app/main.py`):
   ```python
   allow_origins=["https://airlock.yourdomain.com"]
   ```

## Troubleshooting

### "OAuth not configured" error
- Check `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in `.env`
- Ensure backend is restarted after changing `.env`

### "Invalid state parameter" error
- Clear browser cookies for `localhost`
- Check that session middleware is properly configured

### Redirect URI mismatch
- Ensure Google Cloud Console redirect URI exactly matches:
  `http://localhost:8000/api/auth/callback`
- No trailing slash

### "Scope has changed" error
- Google OAuth consent screen scopes must match code scopes
- Currently configured: `openid`, `email`, `profile`, `drive.readonly`

## Files Modified/Created

**Backend:**
- `backend/auth/google_oauth.py` - OAuth flow implementation
- `backend/auth/routes.py` - FastAPI auth endpoints
- `backend/auth/middleware.py` - Auth middleware (not currently used)
- `backend/app/main.py` - Added SessionMiddleware & auth router
- `backend/requirements.txt` - Added auth dependencies

**Frontend:**
- `frontend/src/api.ts` - Auth API functions
- `frontend/src/App.tsx` - Auth state management
- `frontend/src/components/Header.tsx` - Login/logout UI
- `frontend/src/App.css` - Auth button styles

**Config:**
- `.env` - Google OAuth credentials