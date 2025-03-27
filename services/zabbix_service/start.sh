#!/bin/bash

# Criar diretório SSL se não existir
mkdir -p ssl

# Instalar dependências se necessário
pip install --no-cache-dir -r requirements.txt
pip install --no-cache-dir pyzabbix==1.3.1

# Iniciar a aplicação
python app/main.py 