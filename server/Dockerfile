FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    BOOKEATER_CATALOG_HOST=0.0.0.0 \
    BOOKEATER_CATALOG_PORT=8787

WORKDIR /app
COPY server ./server

EXPOSE 8787

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import os,urllib.request; p=os.environ.get('BOOKEATER_CATALOG_PORT','8787'); urllib.request.urlopen('http://127.0.0.1:'+p+'/health',timeout=2).read()" || exit 1

CMD ["python", "-m", "server.catalog_proxy"]
