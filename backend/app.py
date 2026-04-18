"""
Aplicación principal de GymManager Backend
"""
import os
import logging
from datetime import datetime
from flask import Flask, jsonify, g
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

# Cargar configuración
load_dotenv()

# Importar blueprints
from routes import auth_bp, clients_bp, payments_bp, reports_bp, branches_bp
from config import get_config, Config

def create_app():
    """Factory principal de la aplicación Flask"""
    
    # Validar configuración requerida
    try:
        Config.validate_required()
    except ValueError as e:
        print(f"ERROR DE CONFIGURACIÓN: {str(e)}")
        print("Por favor, revisa tu archivo .env")
        exit(1)
    
    # Crear aplicación Flask
    app = Flask(__name__)
    
    # Cargar configuración
    config = get_config()
    app.config.from_object(config)
    
    # Configurar logging
    log_level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO'))
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('gymmanager.log')
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Iniciando GymManager Backend")
    
    # Configurar CORS con credentials explícito
    logger.info("Configurando CORS con supports_credentials=true")
    
    CORS(app, 
         supports_credentials=True)  # Explicitamente permitir credenciales
    
    # Configurar rate limiting
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=[f"{app.config.get('RATELIMIT_PER_USER', '100')}/minute"]
    )
    
    # Registrar blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(clients_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(branches_bp)
    
    # Middleware global para limpiar contexto
    @app.teardown_appcontext
    def teardown_db(exception=None):
        g.pop('current_user', None)
    
    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        """Endpoint para verificar salud del servicio"""
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0'
        }), 200
    
    # Global OPTIONS handler for CORS preflight
    @app.route('/<path:path>', methods=['OPTIONS'])
    @app.route('/', methods=['OPTIONS'])
    def handle_options(path=''):
        """Handle OPTIONS requests for CORS preflight"""
        from flask import request
        origin = request.headers.get('Origin', 'unknown')
        logger.info(f"OPTIONS request recibida - Origin: {origin}, Path: {path}")
        
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', origin)
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With, Accept, Origin, Cache-Control, Pragma')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        
        logger.info(f"OPTIONS response enviada - Status: 200, Origin: {origin}")
        return response, 200
    
    # Error handlers globales
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'error': {
                'code': 404,
                'message': 'Recurso no encontrado'
            }
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Error interno: {str(error)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 500,
                'message': 'Error interno del servidor'
            }
        }), 500
    
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({
            'success': False,
            'error': {
                'code': 429,
                'message': 'Demasiadas peticiones. Intenta más tarde.'
            }
        }), 429
    
    # Inicializar Firebase (esto verificará la conexión)
    try:
        from services.firebase_service import FirebaseService
        firebase_service = FirebaseService()
        logger.info("Firebase inicializado correctamente")
    except Exception as e:
        logger.error(f"Error inicializando Firebase: {str(e)}")
        print(f"ERROR DE FIREBASE: {str(e)}")
        print("Verifica tu archivo serviceAccountKey.json")
        exit(1)
    
    logger.info("GymManager Backend iniciado correctamente")
    return app

# Crear instancia de la aplicación para producción
app = create_app()

if __name__ == '__main__':
    # Ejecutar en modo desarrollo
    config = get_config()
    port = config.PORT
    host = config.HOST
    debug = config.DEBUG
    
    print(f"🚀 Iniciando GymManager Backend en http://{host}:{port}")
    print(f"📝 Modo: {'Desarrollo' if debug else 'Producción'}")
    print(f"🔥 Firebase: {os.environ.get('FIREBASE_DATABASE_JSON', 'No configurado')}")
    
    app.run(host=host, port=port, debug=debug)
