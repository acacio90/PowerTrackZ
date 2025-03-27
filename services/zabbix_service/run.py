import os
import ssl
from pathlib import Path
from app import create_app, Config

def generate_ssl_certificates():
    """Gera certificados SSL auto-assinados"""
    ssl_dir = Config.SSL_DIR
    ssl_dir.mkdir(exist_ok=True)
    
    if not (Config.SSL_CERT_PATH.exists() and Config.SSL_KEY_PATH.exists()):
        print("Gerando certificados SSL auto-assinados...")
        os.system(f'openssl req -x509 -newkey rsa:4096 -nodes -out {Config.SSL_CERT_PATH} -keyout {Config.SSL_KEY_PATH} -days 365 -subj "/CN=localhost"')

if __name__ == '__main__':
    # Gera certificados SSL
    generate_ssl_certificates()
    
    # Cria a aplicação
    app = create_app()
    
    # Configura o SSL
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(Config.SSL_CERT_PATH, Config.SSL_KEY_PATH)
    
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG,
        ssl_context=ssl_context
    ) 