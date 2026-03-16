import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
import requests
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import create_access_token, hash_password, verify_password
from app.config import GOOGLE_CLIENT_ID
from app.database import get_db
from app.models import User
from app.schemas import AuthLoginRequest, AuthRegisterRequest, GoogleAuthRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


def _build_token_response(email: str, password: str, db: Session) -> TokenResponse:
    user = db.query(User).filter(User.email == email).first()
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    try:
        token = create_access_token(subject=user.id, email=user.email)
    except Exception as exc:
        logger.exception("Token generation failed during login")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service is temporarily unavailable",
        ) from exc

    return TokenResponse(access_token=token)


def _verify_google_id_token(id_token: str) -> str:
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google authentication is not configured",
        )

    try:
        response = requests.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": id_token},
            timeout=10,
        )
    except requests.RequestException as exc:
        logger.exception("Google token verification request failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google authentication service is temporarily unavailable",
        ) from exc

    if response.status_code != 200:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google token")

    token_data = response.json()
    if token_data.get("aud") != GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google token audience")

    if token_data.get("email_verified") not in {"true", True}:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google email is not verified")

    email = token_data.get("email")
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google token has no email")

    return str(email).lower()


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: AuthRegisterRequest, db: Session = Depends(get_db)):
    try:
        existing_user = db.query(User).filter(User.email == payload.email).first()
        if existing_user is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

        try:
            password_hash = hash_password(payload.password)
        except Exception as exc:
            logger.exception("Password hashing failed during register")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service is temporarily unavailable",
            ) from exc

        user = User(email=payload.email, password_hash=password_hash)
        db.add(user)
        db.commit()
        db.refresh(user)
        return {"id": user.id, "email": user.email, "created_at": user.created_at}

    except HTTPException:
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered") from exc
    except OperationalError as exc:
        db.rollback()
        logger.exception("Database unavailable during register")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable. Verify DATABASE_URL and PostgreSQL status.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Database error during register")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while creating user",
        ) from exc


@router.post("/login", response_model=TokenResponse)
def login(payload: AuthLoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        return _build_token_response(email=payload.email, password=payload.password, db=db)

    except HTTPException:
        raise
    except OperationalError as exc:
        logger.exception("Database unavailable during login")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable. Verify DATABASE_URL and PostgreSQL status.",
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception("Database error during login")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while performing login",
        ) from exc


@router.post("/token", response_model=TokenResponse)
def login_oauth2_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    try:
        return _build_token_response(email=form_data.username, password=form_data.password, db=db)

    except HTTPException:
        raise
    except OperationalError as exc:
        logger.exception("Database unavailable during token request")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable. Verify DATABASE_URL and PostgreSQL status.",
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception("Database error during token request")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while issuing token",
        ) from exc


@router.post("/google", response_model=TokenResponse)
def login_google(payload: GoogleAuthRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        email = _verify_google_id_token(payload.id_token)

        user = db.query(User).filter(User.email == email).first()
        if user is None:
            user = User(email=email, password_hash=hash_password(secrets.token_urlsafe(32)))
            db.add(user)
            db.commit()
            db.refresh(user)

        token = create_access_token(subject=user.id, email=user.email)
        return TokenResponse(access_token=token)

    except HTTPException:
        raise
    except OperationalError as exc:
        db.rollback()
        logger.exception("Database unavailable during Google login")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable. Verify DATABASE_URL and PostgreSQL status.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Database error during Google login")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while performing Google login",
        ) from exc
