"""
Configuración principal de GymManager Backend
"""
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class Config:
    """Configuración base de la aplicación"""
    
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.environ.get('FLASK_ENV', 'development') == 'development'
    
    # Firebase
    FIREBASE_CREDENTIALS_PATH = os.environ.get('FIREBASE_CREDENTIALS_PATH')
    FIREBASE_DATABASE_URL = os.environ.get('FIREBASE_DATABASE_URL')
    
    # Servidor
    PORT = int(os.environ.get('PORT', 5000))
    HOST = '0.0.0.0' if not DEBUG else '127.0.0.1'
    
    # CORS
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:5173').split(',')
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    
    # Rate Limiting
    RATELIMIT_PER_USER = os.environ.get('RATELIMIT_PER_USER', '100')
    
    @staticmethod
    def validate_required():
        """Valida que las variables requeridas estén presentes"""
        required_vars = [
            'FIREBASE_CREDENTIALS_PATH',
            'FIREBASE_DATABASE_URL'
        ]
        
        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        
        if missing_vars:
            raise ValueError(f"Variables de entorno requeridas faltantes: {', '.join(missing_vars)}")

class DevelopmentConfig(Config):
    """Configuración de desarrollo"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(Config):
    """Configuración de producción"""
    DEBUG = False
    LOG_LEVEL = 'WARNING'

# Configuración por ambiente
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

# Obtener configuración actual
def get_config():
    env = os.environ.get('FLASK_ENV', 'development')
    return config_by_name.get(env, DevelopmentConfig)
