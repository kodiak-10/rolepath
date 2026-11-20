FROM python:3.12-slim-bookworm

WORKDIR /app
ENV PYTHONUNBUFFERED=1

COPY packages.txt requirements.txt ./
RUN apt-get update \
    && xargs -r apt-get install -y --no-install-recommends < packages.txt \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501
CMD ["sh", "-c", "exec python -m streamlit run cloud_app.py --server.address=0.0.0.0 --server.port=${PORT:-8501}"]
