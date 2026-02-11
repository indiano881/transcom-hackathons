"""
Google OAuth implementation for Innovation Airlock
"""
from google_auth_oauthlib.flow import Flow
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from backend directory
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(env_path)

# OAuth 2.0 scopes
SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/drive.readonly',  # Match Google OAuth consent screen config
]

def create_flow():
    """Create OAuth flow"""
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/callback")

    if not client_id or not client_secret:
        raise ValueError("Google OAuth credentials not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env")

    # Create flow from client config
    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri]
        }
    }

    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )

    return flow

def get_authorization_url():
    """Get OAuth authorization URL"""
    flow = create_flow()
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    return authorization_url, state

def get_credentials_from_code(code, state):
    """Exchange authorization code for credentials"""
    flow = create_flow()
    flow.fetch_token(code=code)
    
    credentials = flow.credentials
    return credentials

def verify_token(token):
    """Verify Google ID token"""
    try:
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        idinfo = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            client_id
        )

        # Verify issuer
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Wrong issuer.')

        return idinfo
    except ValueError as e:
        print(f"Token verification failed: {e}")
        return None

def get_user_info(credentials):
    """Get user info from credentials"""
    try:
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        # Verify the ID token
        idinfo = id_token.verify_oauth2_token(
            credentials.id_token,
            google_requests.Request(),
            client_id
        )

        return {
            'google_id': idinfo['sub'],
            'email': idinfo['email'],
            'name': idinfo.get('name', ''),
            'picture_url': idinfo.get('picture', '')
        }
    except Exception as e:
        print(f"Error getting user info: {e}")
        return None
