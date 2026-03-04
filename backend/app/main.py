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

# CORS must be registered before TenantMiddleware so preflight OPTIONS
# requests are handled without hitting auth checks.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TenantMiddleware)

init_firebase()

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(rooms.router, prefix="/api/rooms", tags=["rooms"])
