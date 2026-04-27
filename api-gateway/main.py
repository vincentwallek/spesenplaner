"""
API Gateway — Main Application.
Central entry point handling OAuth2 login, user management,
and reverse-proxy routing to backend microservices.
"""

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Depends, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from auth import (
    init_db,
    get_db,
    authenticate_user,
    create_access_token,
    get_current_user,
    register_user,
    Token,
    TokenData,
    UserCreate,
    UserResponse,
    async_session,
)
from config import (
    ALLOWED_ORIGINS,
    REQUEST_SERVICE_URL,
    APPROVAL_SERVICE_URL,
    BUDGET_SERVICE_URL,
    PAYOUT_SERVICE_URL,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize DB and HTTP client."""
    await init_db()
    app.state.http_client = httpx.AsyncClient(timeout=30.0)
    yield
    await app.state.http_client.aclose()


app = FastAPI(
    title="Reise-Spesen-Planer — API Gateway",
    description="Zentraler API-Einstiegspunkt mit OAuth2-Authentifizierung und Service-Routing",
    version="1.0.0",
    lifespan=lifespan,
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================
# Auth Endpoints
# =============================================

@app.post("/token", response_model=Token, tags=["Authentication"])
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db),
):
    """OAuth2 Password Grant: Authenticate and receive JWT token."""
    user = await authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    return Token(access_token=access_token)


@app.post("/register", response_model=UserResponse, status_code=201, tags=["Authentication"])
async def register(user_data: UserCreate, session: AsyncSession = Depends(get_db)):
    """Register a new user account."""
    db_user = await register_user(session, user_data)
    return UserResponse.model_validate(db_user)


@app.get("/users/me", response_model=dict, tags=["Authentication"])
async def read_users_me(
    current_user: TokenData = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get current authenticated user information."""
    from auth import UserDB
    from sqlalchemy import select
    result = await session.execute(select(UserDB).where(UserDB.username == current_user.username))
    user = result.scalar_one_or_none()
    return {
        "username": current_user.username,
        "role": current_user.role,
        "full_name": user.full_name if user else None
    }


@app.get("/users", response_model=list[UserResponse], tags=["Authentication"])
async def read_users(
    current_user: TokenData = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get all users (admin/manager only)."""
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    from auth import get_all_users
    users = await get_all_users(session)
    return users


from pydantic import BaseModel
class RoleUpdate(BaseModel):
    role: str

@app.patch("/users/{username}/role", response_model=UserResponse, tags=["Authentication"])
async def update_role(
    username: str,
    role_update: RoleUpdate,
    current_user: TokenData = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Update a user's role (admin/manager only)."""
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    if role_update.role not in ["user", "manager", "admin"]:
        raise HTTPException(status_code=400, detail="Invalid role")
        
    if current_user.username == username:
        raise HTTPException(status_code=403, detail="You cannot change your own role")
        
    if current_user.role == "admin" and role_update.role == "manager":
        raise HTTPException(status_code=403, detail="Admins cannot assign the manager role")
        
    from sqlalchemy import select
    from auth import UserDB, update_user_role
    
    result = await session.execute(select(UserDB).where(UserDB.username == username))
    target_user = result.scalar_one_or_none()
    
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if current_user.role == "admin" and target_user.role == "manager":
        raise HTTPException(status_code=403, detail="Admins cannot change the role of a manager")

    updated_user = await update_user_role(session, username, role_update.role)
    return updated_user

# =============================================
# Health Check
# =============================================

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for Kubernetes probes."""
    return {"status": "healthy", "service": "api-gateway"}


# =============================================
# Monitoring Endpoints (Admin/Manager only)
# =============================================

import asyncio
import time

SERVICE_ENDPOINTS = {
    "request-service": {"url": REQUEST_SERVICE_URL, "port": 3001},
    "approval-service": {"url": APPROVAL_SERVICE_URL, "port": 3002},
    "budget-service": {"url": BUDGET_SERVICE_URL, "port": 3003},
    "payout-service": {"url": PAYOUT_SERVICE_URL, "port": 3004},
}


async def _check_service_health(client: httpx.AsyncClient, name: str, base_url: str) -> dict:
    """Check a single service's health and measure response time."""
    start = time.monotonic()
    try:
        resp = await client.get(f"{base_url}/health", timeout=5.0)
        elapsed_ms = round((time.monotonic() - start) * 1000, 1)
        data = resp.json()
        return {
            "service": name,
            "status": "healthy" if resp.status_code == 200 else "degraded",
            "response_time_ms": elapsed_ms,
            "details": data,
        }
    except Exception:
        elapsed_ms = round((time.monotonic() - start) * 1000, 1)
        return {
            "service": name,
            "status": "unhealthy",
            "response_time_ms": elapsed_ms,
            "details": None,
        }


async def _fetch_service_metrics(client: httpx.AsyncClient, name: str, base_url: str) -> dict:
    """Fetch metrics from a single service."""
    try:
        resp = await client.get(f"{base_url}/metrics", timeout=10.0)
        if resp.status_code == 200:
            return {"service": name, "metrics": resp.json()}
    except Exception:
        pass
    return {"service": name, "metrics": None}


@app.get("/api/v1/monitoring/dashboard", tags=["Monitoring"])
async def monitoring_dashboard(
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """
    Aggregated monitoring dashboard data.
    Fetches health status and metrics from all backend services in parallel.
    Only accessible by admin and manager roles.
    """
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Monitoring requires admin or manager role")

    client: httpx.AsyncClient = request.app.state.http_client

    # Parallel health checks
    health_tasks = [
        _check_service_health(client, name, info["url"])
        for name, info in SERVICE_ENDPOINTS.items()
    ]
    health_results = await asyncio.gather(*health_tasks)

    # Parallel metrics collection
    metrics_tasks = [
        _fetch_service_metrics(client, name, info["url"])
        for name, info in SERVICE_ENDPOINTS.items()
    ]
    metrics_results = await asyncio.gather(*metrics_tasks)

    # Build metrics dict keyed by service name
    metrics_by_service = {m["service"]: m["metrics"] for m in metrics_results}

    # Overall system status
    statuses = [h["status"] for h in health_results]
    if all(s == "healthy" for s in statuses):
        overall_status = "healthy"
    elif any(s == "unhealthy" for s in statuses):
        overall_status = "degraded"
    else:
        overall_status = "partial"

    # Count registered users
    from auth import get_all_users
    async with async_session() as session:
        users = await get_all_users(session)
        user_count = len(users)

    from datetime import datetime, timezone
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "overall_status": overall_status,
        "services": health_results,
        "metrics": {
            "expenses": metrics_by_service.get("request-service"),
            "approvals": metrics_by_service.get("approval-service"),
            "budgets": metrics_by_service.get("budget-service"),
            "payouts": metrics_by_service.get("payout-service"),
        },
        "system": {
            "registered_users": user_count,
            "services_count": len(SERVICE_ENDPOINTS),
            "healthy_services": statuses.count("healthy"),
        },
    }


@app.get("/api/v1/monitoring/logs", tags=["Monitoring"])
async def monitoring_logs(
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """
    Aggregated activity log from all services — recent expenses as audit trail.
    Only accessible by admin and manager roles.
    """
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Monitoring requires admin or manager role")

    client: httpx.AsyncClient = request.app.state.http_client

    logs = []

    # Fetch recent expenses from request-service
    try:
        resp = await client.get(f"{REQUEST_SERVICE_URL}/metrics", timeout=10.0)
        if resp.status_code == 200:
            data = resp.json()
            for exp in data.get("recent_expenses", []):
                logs.append({
                    "timestamp": exp.get("created_at"),
                    "service": "request-service",
                    "action": f"Expense {exp.get('status', 'UNKNOWN')}",
                    "details": f"{exp.get('title', '?')} — {exp.get('amount', 0)} {exp.get('currency', 'EUR')}",
                    "user": exp.get("created_by", "unknown"),
                    "currency": exp.get("currency", "EUR"),
                })
    except Exception:
        pass

    # Sort by timestamp descending
    logs.sort(key=lambda x: x.get("timestamp") or "", reverse=True)

    from datetime import datetime, timezone
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total": len(logs),
        "logs": logs,
    }


# =============================================
# Reverse Proxy to Backend Services
# =============================================

async def _proxy_request(
    request: Request,
    target_base_url: str,
    path: str,
    current_user: TokenData,
) -> Response:
    """Forward request to a backend service with user context headers."""
    client: httpx.AsyncClient = request.app.state.http_client

    # Build target URL
    target_url = f"{target_base_url}{path}"
    if request.url.query:
        target_url += f"?{request.url.query}"

    # Read request body
    body = await request.body()

    # Forward headers + inject user context
    headers = {
        "Content-Type": request.headers.get("Content-Type", "application/json"),
        "X-User-Name": current_user.username,
        "X-User-Role": current_user.role,
    }

    try:
        response = await client.request(
            method=request.method,
            url=target_url,
            content=body,
            headers=headers,
        )
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.headers.get("content-type"),
        )
    except httpx.ConnectError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Backend service unavailable: {target_base_url}",
        )


# --- Request Service Routes ---
@app.api_route(
    "/api/v1/expenses/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    tags=["Expenses (Proxy)"],
)
async def proxy_expenses_with_path(
    request: Request,
    path: str,
    current_user: TokenData = Depends(get_current_user),
):
    """Proxy requests to request-service (with sub-path)."""
    return await _proxy_request(request, REQUEST_SERVICE_URL, f"/expenses/{path}", current_user)


@app.api_route(
    "/api/v1/expenses",
    methods=["GET", "POST"],
    tags=["Expenses (Proxy)"],
)
async def proxy_expenses(
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Proxy requests to request-service (root)."""
    return await _proxy_request(request, REQUEST_SERVICE_URL, "/expenses", current_user)


# --- Approval Service Routes ---
@app.api_route(
    "/api/v1/approvals/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    tags=["Approvals (Proxy)"],
)
async def proxy_approvals_with_path(
    request: Request,
    path: str,
    current_user: TokenData = Depends(get_current_user),
):
    """Proxy requests to approval-service."""
    return await _proxy_request(request, APPROVAL_SERVICE_URL, f"/approvals/{path}", current_user)


@app.api_route(
    "/api/v1/approvals",
    methods=["GET", "POST"],
    tags=["Approvals (Proxy)"],
)
async def proxy_approvals(
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Proxy requests to approval-service (root)."""
    return await _proxy_request(request, APPROVAL_SERVICE_URL, "/approvals", current_user)


# --- Budget Service Routes ---
@app.api_route(
    "/api/v1/budgets/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    tags=["Budgets (Proxy)"],
)
async def proxy_budgets_with_path(
    request: Request,
    path: str,
    current_user: TokenData = Depends(get_current_user),
):
    """Proxy requests to budget-service."""
    return await _proxy_request(request, BUDGET_SERVICE_URL, f"/budgets/{path}", current_user)


@app.api_route(
    "/api/v1/budgets",
    methods=["GET", "POST"],
    tags=["Budgets (Proxy)"],
)
async def proxy_budgets(
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Proxy requests to budget-service (root)."""
    return await _proxy_request(request, BUDGET_SERVICE_URL, "/budgets", current_user)


# --- Payout Service Routes ---
@app.api_route(
    "/api/v1/payouts/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    tags=["Payouts (Proxy)"],
)
async def proxy_payouts_with_path(
    request: Request,
    path: str,
    current_user: TokenData = Depends(get_current_user),
):
    """Proxy requests to payout-service."""
    return await _proxy_request(request, PAYOUT_SERVICE_URL, f"/payouts/{path}", current_user)


@app.api_route(
    "/api/v1/payouts",
    methods=["GET", "POST"],
    tags=["Payouts (Proxy)"],
)
async def proxy_payouts(
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Proxy requests to payout-service (root)."""
    return await _proxy_request(request, PAYOUT_SERVICE_URL, "/payouts", current_user)
