FROM python:3.12-slim

WORKDIR /app

# Copy proto file from project root context
COPY proto/approval.proto /tmp/proto/approval.proto

# Copy service files
COPY backend/request-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/request-service/ .

# Generate gRPC stubs
RUN python -m grpc_tools.protoc -I/tmp/proto --python_out=. --grpc_python_out=. /tmp/proto/approval.proto

# Run as non-root user
RUN adduser --disabled-password --gecos "" appuser
USER appuser

EXPOSE 3001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3001"]
