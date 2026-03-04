"""Tenant middleware: authenticate every request and resolve org context.

For every protected route this middleware:
  1. Verifies the Firebase ID token from the Authorization header.
  2. Looks up the user's org and role in Firestore.
  3. Stores uid, org_id, role, and display_name on request.state so
     route handlers never need to repeat auth/org resolution.

Unauthenticated paths (e.g. /api/health) are explicitly skipped.
"""
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.auth import get_uid_from_headers
from app.services.tenant import get_user_org

# Paths that do not require authentication
_PUBLIC_PATHS = {"/api/health"}


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)

        # 1. Verify Firebase ID token
        authorization = request.headers.get("Authorization")
        uid = get_uid_from_headers(authorization)
        if not uid:
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid token"},
            )

        # 2. Resolve org from Firestore users doc
        user_meta = get_user_org(uid)
        if not user_meta or not user_meta.get("org_id"):
            return JSONResponse(
                status_code=403,
                content={"detail": "User not associated with an organization"},
            )

        # 3. Attach to request state — available to every downstream route
        request.state.uid = uid
        request.state.org_id = user_meta["org_id"]
        request.state.role = user_meta.get("role", "member")
        request.state.display_name = user_meta.get("display_name") or "User"

        return await call_next(request)
