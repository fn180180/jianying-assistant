# Hugging Face Spaces / 通用容器部署用
FROM python:3.11-slim

WORKDIR /app

# 系統依賴（極少）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# HF Spaces 預設 PORT 7860
ENV PORT=7860
EXPOSE 7860

CMD streamlit run streamlit_app.py \
    --server.port=$PORT \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --browser.gatherUsageStats=false
