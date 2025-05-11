from fastapi import FastAPI
from app.api.auth.routes import router as auth_router
from app.db.session import engine
from app.db.models import Base

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Auth API")

# Include routers
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])

@app.get("/")
def root():
    return {"message": "Welcome to Auth API"}