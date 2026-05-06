import os
from dotenv import load_dotenv

load_dotenv()

# Database Configuration
SQL_SERVER = os.getenv("SQL_SERVER")
SQL_DATABASE = os.getenv("SQL_DATABASE")
SQL_USER = os.getenv("SQL_USER")
SQL_PASSWORD = os.getenv("SQL_PASSWORD")
USE_SQL = os.getenv("USE_SQL", "false").lower() == "true"

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"

# App Configuration
APP_PORT = int(os.getenv("APP_PORT", "5000"))
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5000,http://127.0.0.1:5000,http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000,http://127.0.0.1:3000"
)

# Email Configuration (SendGrid)
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
SENDGRID_FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL", "")
