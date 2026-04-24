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
