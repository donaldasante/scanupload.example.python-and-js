FROM python:3.11-slim

WORKDIR /app

# Install dependencies first so this layer is cached unless requirements change
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ .

ENV PORT=8080

EXPOSE 8080

CMD ["python", "main.py"]
