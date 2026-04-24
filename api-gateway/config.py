"""
API Gateway Configuration.
Centralized configuration for service URLs, JWT settings, and routing.
"""

import os


# --- JWT Configuration ---
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-change-in-production-2024")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# --- Service URLs (overridable via environment variables for K8s) ---
REQUEST_SERVICE_URL = os.getenv("REQUEST_SERVICE_URL", "http://localhost:3001")
APPROVAL_SERVICE_URL = os.getenv("APPROVAL_SERVICE_URL", "http://localhost:3002")
BUDGET_SERVICE_URL = os.getenv("BUDGET_SERVICE_URL", "http://localhost:3003")
PAYOUT_SERVICE_URL = os.getenv("PAYOUT_SERVICE_URL", "http://localhost:3004")

# --- Service Routing Map ---
SERVICE_ROUTES = {
    "/api/v1/expenses": REQUEST_SERVICE_URL,
    "/api/v1/approvals": APPROVAL_SERVICE_URL,
    "/api/v1/budgets": BUDGET_SERVICE_URL,
    "/api/v1/payouts": PAYOUT_SERVICE_URL,
}

# --- Database ---
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./gateway.db")

# --- CORS ---
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:4200").split(",")
