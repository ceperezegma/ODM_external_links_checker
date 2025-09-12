import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# -------------------------------
# USER INPUT: Pick environment to work with
# -------------------------------
ENVIRONMENT = "PROD" # DEV, H-PROD, or PROD


EXPECTED_FILES_PATH = "expected_files.json"
DOWNLOAD_DIR = "downloads/"

LOGIN_URL_DEV = "https://edp.dev.agiledrop.com/en/open-data-maturity/2024"
LOGIN_URL_H_PROD = "https://data.europa.eu/en/open-data-maturity/2024"  # Actual PROD URL homepage behind credentials
URL_PROD = "https://data.europa.eu/en/open-data-maturity/2024"  # Actual PROD URL homepage without credentials (public access)

# Select URL based on environment
LOGIN_URL = LOGIN_URL_DEV if ENVIRONMENT == "DEV" else LOGIN_URL_H_PROD if ENVIRONMENT == "H-PROD" else URL_PROD

# Get credentials from environment variables
USERNAME = os.getenv("USERNAME_ODM_DEV") if ENVIRONMENT == "DEV" else os.getenv("USERNAME_ODM_PROD") if ENVIRONMENT == "H-PROD" else None
PASSWORD = os.getenv("PASSWORD_ODM_DEV") if ENVIRONMENT == "DEV" else os.getenv("PASSWORD_ODM_PROD") if ENVIRONMENT == "H-PROD" else None

# Validate credentials are available
if (not USERNAME or not PASSWORD) and ENVIRONMENT != "PROD":
    raise ValueError("❌ Missing credentials: USERNAME and PASSWORD must be set in .env file")

# Validate environment
if ENVIRONMENT not in ['DEV', 'H-PROD', 'PROD']:
    raise ValueError(f"❌ Invalid ENVIRONMENT: {ENVIRONMENT}. Must be 'DEV' or 'PROD'")

print(f"🌍 Environment: {ENVIRONMENT}")
print(f"🔗 Login URL: {LOGIN_URL}")

# Show or not the browser on screen
HEADLESS = False  # Set to True if you don't need to see interaction in the browser
