# init_database.py - Database initialization for Railway deployment
import os
import sys
from pathlib import Path

# Add the watch directory to Python path
watch_dir = Path(__file__).resolve().parent / 'watch'
sys.path.insert(0, str(watch_dir))

# Import and run the init_database from watch
from init_database import init_database

if __name__ == "__main__":
    init_database()

