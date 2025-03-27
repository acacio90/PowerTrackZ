FROM python:3.9-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements.txt e instalar dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o código da aplicação
COPY . .

# Configurar variáveis de ambiente
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=development
ENV PORT=5001
ENV HOST=0.0.0.0
ENV PYTHONPATH=/app

# Expor a porta
EXPOSE 5001

# Healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5001/health || exit 1

# Comando para iniciar a aplicação
CMD ["python", "app/main.py"]