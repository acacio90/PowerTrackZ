FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Instalar sqlite3
RUN apt-get update && apt-get install -y sqlite3

COPY . .

CMD ["python", "app/main.py"]