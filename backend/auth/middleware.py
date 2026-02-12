"""
Authentication middleware
"""
from functools import wraps
from flask import session, jsonify, redirect, url_for, request

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # For API requests, return JSON error
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required'}), 401
            # For page requests, redirect to login
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user_id():
    """Get current user ID from session"""
    return session.get('user_id')

def get_current_user_email():
    """Get current user email from session"""
    return session.get('user_email')
