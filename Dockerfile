# Use official Python runtime as base image
FROM python:3.11-slim

# Prevent Python from buffering stdout/stderr (critical for Railway logs!)
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set working directory
WORKDIR /app

# Install system dependencies for Tesseract OCR and Poppler
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application
COPY . .

# Expose port (Railway will override this with $PORT)
EXPOSE 8080

# Run the application using gunicorn
# Use shell form to properly expand $PORT variable
# Capture all output so we can see what's happening in Railway logs
CMD ["sh", "-c", "gunicorn -w 2 -b 0.0.0.0:$PORT --timeout 60 --access-logfile - --error-logfile - --log-level info --capture-output wsgi:app"]

