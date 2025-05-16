from fastapi import FastAPI
from app.api.auth.routes import router as auth_router
from app.db.session import engine
from app.db.models import Base
from fastapi.middleware.cors import CORSMiddleware
# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Auth API")
origins = [
    "http://localhost:3000",  # Example: React/Vue/Angular frontend
    "http://127.0.0.1:3000",
    "https://your-frontend-domain.com",  # Your production frontend domain
]

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # List of allowed origins
    allow_credentials=True,  # Allow cookies and credentials
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)
# Include routers
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])

@app.get("/")
def root():
    return {"message": "Welcome to Auth API"}