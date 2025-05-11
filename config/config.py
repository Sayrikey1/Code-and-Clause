import os
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# Get database credentials from environment variables
db_name = os.getenv('DB_NAME')
db_password = os.getenv('DB_PASSWORD')
db_host = os.getenv('DB_HOST')
db_port = os.getenv('DB_PORT')
db_user = os.getenv('DB_USERNAME')

# Construct the SQLAlchemy database URL
DATABASE_URL = f'postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?sslmode=require'
