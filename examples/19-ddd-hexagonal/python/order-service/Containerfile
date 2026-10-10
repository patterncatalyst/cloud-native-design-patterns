FROM registry.access.redhat.com/ubi9/python-312:latest
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY domain/ domain/
COPY adapters/ adapters/
COPY main.py .
COPY cli_place_order.py .
EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
