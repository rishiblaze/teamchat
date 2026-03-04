from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, health, rooms
from app.core.firebase import init_firebase
from app.core.middleware import TenantMiddleware

app = FastAPI(
    title="TeamChat AI API",
    description="Multi-tenant collaborative AI chat backend",
    version="1.0.0",
)

# Middleware execution order in Starlette is LIFO (last registered = outermost = runs first).
# TenantMiddleware is registered first (innermost) so it runs after CORS.
# CORSMiddleware is registered last (outermost) so it handles OPTIONS preflight
# before TenantMiddleware ever sees the request.
app.add_middleware(TenantMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_firebase()

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(rooms.router, prefix="/api/rooms", tags=["rooms"])
