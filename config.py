# config.py - UPDATED VERSION (just add Supabase config)
import os
from datetime import timedelta

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # ========== SUPABASE CONFIGURATION ==========
    SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')  # anon/public key
    SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', '')  # service role key
    
    # ========== DATABASE CONFIGURATION ==========
    # Use Supabase PostgreSQL if available, otherwise SQLite
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    if DATABASE_URL:
        # Use Supabase PostgreSQL
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    elif SUPABASE_URL:
        # Construct from Supabase credentials
        db_password = os.environ.get('SUPABASE_PASSWORD', '')
        if db_password:
            # Extract host from Supabase URL
            host = SUPABASE_URL.replace('https://', '').replace('.supabase.co', '')
            SQLALCHEMY_DATABASE_URI = f'postgresql://postgres:{db_password}@db.{host}.supabase.co:5432/postgres'
        else:
            SQLALCHEMY_DATABASE_URI = 'sqlite:///kanban_tickets.db'
    else:
        # Fallback to SQLite
        SQLALCHEMY_DATABASE_URI = 'sqlite:///kanban_tickets.db'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 300,
        'pool_pre_ping': True,
    }
    
    # ========== EXISTING SETTINGS (keep as is) ==========
    # CORS settings
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    
    # Rate limiting (if you add it later)
    RATELIMIT_DEFAULT = "100 per day"
    RATELIMIT_STORAGE_URL = "memory://"
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    
    # AI Settings
    AI_MODEL = os.environ.get('AI_MODEL', 'gpt-3.5-turbo')
    AI_MAX_TOKENS = int(os.environ.get('AI_MAX_TOKENS', 500))
    AI_TEMPERATURE = float(os.environ.get('AI_TEMPERATURE', 0.3))
    
    # Local estimation settings
    USE_LOCAL_ESTIMATION = os.environ.get('USE_LOCAL_ESTIMATION', 'false').lower() == 'true'

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    # In production, use a proper secret key
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    # More restrictive CORS in production
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '').split(',')

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True

# Configuration dictionary - KEEP AS IS
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}