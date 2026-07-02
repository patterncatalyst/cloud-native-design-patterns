FROM registry.access.redhat.com/ubi9/python-312:latest

COPY inventory-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY proto/inventory.proto proto/inventory.proto
RUN python -m grpc_tools.protoc \
    -Iproto \
    --python_out=. \
    --grpc_python_out=. \
    proto/inventory.proto

COPY inventory-service/main.py .
EXPOSE 50051
CMD ["python", "main.py"]
