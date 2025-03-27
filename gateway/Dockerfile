FROM python:3.9-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar arquivos de requisitos
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o código da aplicação
COPY . .

# Expor a porta
EXPOSE 80

# Configurar variáveis de ambiente
ENV FLASK_APP=app.main
ENV FLASK_ENV=development
ENV PYTHONPATH=/app

# Comando para executar a aplicação
CMD ["flask", "run", "--host=0.0.0.0", "--port=80"]