"""One browser authentication boundary shared by users and operators."""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from recase.accounts import COOKIE, SESSION_SECONDS, normalize_email


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class Registration(Credentials):
    name: str = Field(min_length=1, max_length=40)


def require_json(request):
    if request.headers.get("content-type", "").split(";", 1)[0] != "application/json":
        raise HTTPException(415, detail="JSON_REQUIRED")


def signed_in(request, token, profile, status=200):
    old = request.cookies.get(COOKIE, "")
    if old:
        request.app.state.accounts.revoke(old)
    response = JSONResponse(profile, status)
    response.set_cookie(COOKIE, token, max_age=SESSION_SECONDS, httponly=True, samesite="strict", secure=request.url.scheme == "https", path="/")
    return response


def routes():
    router = APIRouter(prefix="/api/auth")

    @router.post("/register", status_code=201)
    def register(body: Registration, request: Request):
        require_json(request)
        accounts = request.app.state.accounts
        accounts.throttle("register", request.client.host, normalize_email(body.email))
        user = accounts.create(body.email, body.password, body.name)  # Public registration never accepts a role.
        token, profile = accounts.new_session(user)
        return signed_in(request, token, profile, 201)

    @router.post("/login")
    def login(body: Credentials, request: Request):
        require_json(request)
        token, profile = request.app.state.accounts.login(body.email, body.password, request.client.host)
        return signed_in(request, token, profile)

    @router.get("/session")
    def session(request: Request):
        return request.app.state.accounts.require(request)

    @router.post("/logout")
    def logout(request: Request):
        request.app.state.accounts.require(request, write=True)
        request.app.state.accounts.revoke(request.cookies.get(COOKIE, ""))
        response = JSONResponse({"logged_out": True})
        response.delete_cookie(COOKIE, path="/", httponly=True, samesite="strict")
        return response

    return router
