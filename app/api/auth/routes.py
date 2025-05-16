from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import timedelta
import os

from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_active_user
)
from app.db.session import get_db
from app.db.models import User
from app.core.config import settings
from app.core.email import send_email
from app.api.auth.schemas import UserCreate, UserLogin, Token, User as UserSchema

router = APIRouter()

@router.post("/signup", response_model=dict, status_code=status.HTTP_201_CREATED)
async def signup(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    # Check if username exists
    db_user_by_username = db.query(User).filter(User.username == user_in.username).first()
    if db_user_by_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email exists
    db_user_by_email = db.query(User).filter(User.email == user_in.email).first()
    if db_user_by_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    try:
        hashed_password = get_password_hash(user_in.password)
        db_user = User(
            username=user_in.username,
            email=user_in.email,
            hashed_password=hashed_password,
            is_active=False
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        # Send verification email
        verification_link = f"{settings.FRONTEND_URL}/verify?token={db_user.verification_token}"
        html_content = f"""
        <html>
            <body>
                <h1>Welcome to Auth API!</h1>
                <p>Hi {db_user.username},</p>
                <p>Thanks for signing up. Please verify your email by clicking the link below:</p>
                <p><a href="{verification_link}">Verify Email</a></p>
                <p>Or copy and paste this link: {verification_link}</p>
                <p>This link will expire in 24 hours.</p>
            </body>
        </html>
        """
        
        # Send email in background to not block the response
        background_tasks.add_task(
            send_email,
            email_to=db_user.email,
            subject="Verify your email",
            html_content=html_content
        )
        
        return {
            "message": "User created successfully. Please check your email for verification."
        }
    
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error creating user. Please try again."
        )

@router.post("/verify/{token}")
async def verify_email(token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.verification_token == token).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token"
        )
    
    if user.is_active:
        return {"message": "Email already verified"}
    
    user.is_active = True
    db.commit()
    
    return {"message": "Email verified successfully. You can now log in."}

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    # Check if user exists by username or email
    user = db.query(User).filter(
        (User.username == form_data.username) | (User.email == form_data.username)
    ).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not verified. Please check your email for verification link."
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.post("/login-with-schema", response_model=Token)
async def login_with_schema(
    user_in: UserLogin,
    db: Session = Depends(get_db)
):
    # Check if user exists by username or email
    user = db.query(User).filter(
        (User.username == user_in.username_or_email) | (User.email == user_in.username_or_email)
    ).first()
    
    if not user or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not verified. Please check your email for verification link."
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.get("/me", response_model=UserSchema)
async def read_users_me(current_user: UserSchema = Depends(get_current_active_user)):
    return current_user

@router.post("/send-verification-mail-again", response_model=dict)
async def send_verification_mail_again(
    email: str,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with this email does not exist."
        )
    if user.is_active:
        return {"message": "Email already verified."}
    verification_link = f"{settings.FRONTEND_URL}/verify?token={user.verification_token}"
    html_content = f"""
    <html>
        <body>
            <h1>Verify your email again!</h1>
            <p>Hi {user.username},</p>
            <p>Please verify your email by clicking the link below:</p>
            <p><a href=\"{verification_link}\">Verify Email</a></p>
            <p>Or copy and paste this link: {verification_link}</p>
            <p>This link will expire in 24 hours.</p>
        </body>
    </html>
    """
    background_tasks.add_task(
        send_email,
        email_to=user.email,
        subject="Verify your email again",
        html_content=html_content
    )
    return {"message": "Verification email sent again. Please check your inbox."}

@router.post("/upload-profile-pic", response_model=dict)
async def upload_profile_pic(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Only allow image files
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed.")

    # Save file to a directory (e.g., 'profile_pics/')
    upload_dir = os.path.join(os.getcwd(), "profile_pics")
    os.makedirs(upload_dir, exist_ok=True)
    file_ext = os.path.splitext(file.filename)[1]
    filename = f"user_{current_user.id}{file_ext}"
    file_path = os.path.join(upload_dir, filename)

    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    # Update user profile_pic path in DB
    current_user.profile_pic = file_path
    db.commit()

    return {"message": "Profile picture uploaded successfully.", "profile_pic": file_path}


