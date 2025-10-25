"""
Configuración centralizada del Sistema de Gestión de Extintores
"""
import os

class Config:
    """Configuración base de la aplicación"""
    
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'tu-clave-secreta-aqui-cambiar-en-produccion'
    
    # Base de datos
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///extintores.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Servidor
    HOST = '0.0.0.0'
    PORT = 5000
    DEBUG = False
    USE_RELOADER = False
    
    # Consulta RUC
    METODO_CONSULTA_RUC = 'WEB_SCRAPING'  # WEB_SCRAPING o API
    
    # URLs SUNAT
    SUNAT_URL_CONSULTA = "https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsruc/jcrS00Alias"
    SUNAT_TIMEOUT = 15  # segundos
    
    # Logging
    LOG_LEVEL = 'INFO'
    LOG_FORMAT = '%(message)s'
    
    # Paginación
    ITEMS_PER_PAGE = 50
    
    # Archivos
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max
    
    @staticmethod
    def init_app(app):
        """Inicializar configuración en la app"""
        pass

class DevelopmentConfig(Config):
    """Configuración para desarrollo"""
    DEBUG = False  # Mantener en False para tener control de logs
    USE_RELOADER = False

class ProductionConfig(Config):
    """Configuración para producción"""
    DEBUG = False
    USE_RELOADER = False
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Log de errores en producción
        import logging
        from logging.handlers import RotatingFileHandler
        
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler(
            'logs/extintores.log',
            maxBytes=10240000,
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Sistema de Extintores iniciado')

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
