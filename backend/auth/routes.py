"""
Authentication routes for FastAPI
"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from .google_oauth import get_authorization_url, get_credentials_from_code, get_user_info

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
async def login(request: Request):
    """Initiate Google OAuth login"""
    try:
        authorization_url, state = get_authorization_url()
        # Store state in session
        request.session['oauth_state'] = state
        return RedirectResponse(url=authorization_url)
    except ValueError as e:
        return JSONResponse(
            status_code=500,
            content={
                'error': 'OAuth not configured',
                'message': str(e),
                'instructions': 'Please configure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in your .env file'
            }
        )


@router.get("/callback")
async def callback(request: Request):
    """Handle OAuth callback"""
    # Verify state
    stored_state = request.session.get('oauth_state')
    returned_state = request.query_params.get('state')

    if not stored_state or stored_state != returned_state:
        raise HTTPException(status_code=400, detail='Invalid state parameter')

    # Get authorization code
    code = request.query_params.get('code')
    if not code:
        raise HTTPException(status_code=400, detail='No authorization code received')

    try:
        # Exchange code for credentials
        credentials = get_credentials_from_code(code, stored_state)

        # Get user info
        user_info = get_user_info(credentials)
        if not user_info:
            raise HTTPException(status_code=500, detail='Failed to get user info')

        # Store user info in session
        request.session['user_id'] = user_info['google_id']
        request.session['user_email'] = user_info['email']
        request.session['user_name'] = user_info['name']
        request.session['user_picture'] = user_info['picture_url']

        # Redirect to frontend
        return RedirectResponse(url='http://localhost:5173')

    except Exception as e:
        print(f"OAuth callback error: {e}")
        raise HTTPException(status_code=500, detail=f'Authentication failed: {str(e)}')


@router.get("/logout")
async def logout(request: Request):
    """Logout user"""
    request.session.clear()
    return RedirectResponse(url='http://localhost:5173')


@router.get("/status")
async def status(request: Request):
    """Check authentication status"""
    if 'user_id' in request.session:
        return {
            'authenticated': True,
            'user': {
                'id': request.session['user_id'],
                'email': request.session['user_email'],
                'name': request.session['user_name'],
                'picture': request.session.get('user_picture')
            }
        }
    else:
        return {'authenticated': False}