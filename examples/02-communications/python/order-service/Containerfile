FROM registry.access.redhat.com/ubi9/python-312

COPY order-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY proto/inventory.proto proto/inventory.proto
RUN python -m grpc_tools.protoc \
    -Iproto \
    --python_out=. \
    --grpc_python_out=. \
    proto/inventory.proto

COPY order-service/ .
EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--log-level", "info"]
