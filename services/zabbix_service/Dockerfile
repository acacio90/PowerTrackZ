FROM python:3.9-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    openssl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements.txt e instalar dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o código da aplicação
COPY . .

# Configurar variáveis de ambiente
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=development
ENV PORT=5003
ENV HOST=0.0.0.0
ENV PYTHONPATH=/app

# Expor a porta
EXPOSE 5003

# Criar diretório SSL se não existir
RUN mkdir -p /app/ssl

# Healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -k -f https://localhost:5003/health || exit 1

# Comando para iniciar a aplicação
CMD ["python", "run.py"]