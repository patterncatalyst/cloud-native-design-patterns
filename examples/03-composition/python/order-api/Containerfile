FROM registry.access.redhat.com/ubi9/python-312

COPY order-api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY order-api/ .
EXPOSE 8081
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8081", "--log-level", "info"]
