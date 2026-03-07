import firebase_admin
from firebase_admin import credentials, auth
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from core.config import settings
import os

security = HTTPBearer()

def initialize_firebase():
    """Initializes Firebase Admin SDK."""
    try:
        if not firebase_admin._apps:
            # We assume the credential file is in the root of vins_backend
            cred_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), settings.FIREBASE_CREDENTIALS)
            if os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
            else:
                print(f"Warning: Firebase credentials not found at {cred_path}. Authentication will fail.")
    except Exception as e:
        print(f"Error initializing Firebase: {e}")

def verify_firebase_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    """
    Verifies the short-lived Firebase ID token.
    Raises an HTTPException if token is invalid.
    """
    token = credentials.credentials
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
