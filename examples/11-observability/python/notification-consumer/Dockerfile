FROM registry.access.redhat.com/ubi9/python-312:latest
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .
CMD ["python", "main.py"]
