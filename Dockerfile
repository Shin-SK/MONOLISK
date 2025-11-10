FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# psycopg2等のビルドに必要
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# 依存の先入れでキャッシュ活用
COPY requirements.txt .
RUN pip install -r requirements.txt

# プロジェクト本体
COPY . .

# 起動（開発用：自動migrate→runserver）
CMD bash -lc "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"
