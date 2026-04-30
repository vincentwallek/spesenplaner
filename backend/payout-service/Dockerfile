FROM python:3.12-slim

WORKDIR /app

COPY backend/payout-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/payout-service/ .

RUN adduser --disabled-password --gecos "" appuser
USER appuser

EXPOSE 3004

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3004"]
