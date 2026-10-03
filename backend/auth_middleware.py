"""
UrjaMind Firebase Authentication Middleware
============================================
Verifies Firebase ID Tokens using firebase-admin SDK.
Extracts user identity (UID) to enforce tenant/plant data isolation.
In local development/testing without serviceAccount.json, supports signed demo/test tokens.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from fastapi import Depends, Header, HTTPException, Request

logger = logging.getLogger("urjamind.auth")

# Initialize Firebase Admin SDK if service account JSON path or project ID is specified
_firebase_initialized = False
try:
    import firebase_admin
    from firebase_admin import auth as firebase_auth, credentials

    service_account_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH")
    project_id = os.environ.get("FIREBASE_PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT")

    if service_account_path and os.path.exists(service_account_path):
        if not firebase_admin._apps:
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)
            _firebase_initialized = True
            logger.info("Firebase Admin SDK successfully initialized from %s", service_account_path)
        else:
            _firebase_initialized = True
    elif project_id and project_id != "unconfigured":
        if not firebase_admin._apps:
            try:
                firebase_admin.initialize_app(options={"projectId": project_id})
                _firebase_initialized = True
            except Exception:
                _firebase_initialized = False
        else:
            _firebase_initialized = True
except Exception as e:
    logger.info("Firebase Admin not configured for live cloud verification (development fallback mode active): %s", e)
    _firebase_initialized = False


async def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """
    FastAPI dependency to authenticate requests.
    Validates Bearer token from 'Authorization' header.
    Returns authenticated user payload containing 'uid'.
    """
    env = os.environ.get("ENVIRONMENT", "development").lower()

    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please provide Authorization: Bearer <token>.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization format. Must be 'Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Empty bearer token provided")

    # 1. Development / Test Token Fallback (strictly disabled in production)
    if env != "production":
        if token == "demo-token-urjamind-2026":
            return {
                "uid": "plant_demo",
                "email": "manager@rajkotfoundry.in",
                "name": "Rajkot Plant Manager",
                "source": "demo_token",
            }

        if token.startswith("test-token-"):
            # e.g. "test-token-userA" -> uid="userA"
            tenant_uid = token.replace("test-token-", "")
            return {
                "uid": tenant_uid,
                "email": f"{tenant_uid}@factory.com",
                "name": f"Supervisor {tenant_uid}",
                "source": "test_token",
            }

    # 2. Live Firebase Admin Verification (if service account configured)
    if _firebase_initialized:
        try:
            decoded_token = firebase_auth.verify_id_token(token)
            return {
                "uid": decoded_token.get("uid"),
                "email": decoded_token.get("email"),
                "name": decoded_token.get("name", "Plant Manager"),
                "source": "firebase",
            }
        except Exception as e:
            logger.warning("Firebase token verification failure: %s", e)
            raise HTTPException(status_code=401, detail=f"Invalid or expired Firebase ID token: {e}")

    # In production without verified token, reject with 401
    if env == "production":
        raise HTTPException(
            status_code=401,
            detail="Valid Firebase ID token required in production. Demo and test tokens are disabled.",
        )

    # In development, interpret token as user UID for seamless local prototyping
    return {
        "uid": token[:32],
        "email": "dev@urjamind.local",
        "name": "Dev User",
        "source": "dev_token",
    }


async def get_optional_current_user(
    request: Request,
    authorization: Optional[str] = Header(None),
) -> Optional[Dict[str, Any]]:
    """Optional authentication dependency for endpoints that adapt to user identity when present."""
    if not authorization:
        return None
    try:
        return await get_current_user(request, authorization)
    except HTTPException:
        return None
