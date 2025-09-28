# Use official slim Python image
FROM python:3.11-slim

# Install system dependencies (ffmpeg, libgl1 for OpenCV)
RUN apt-get update && \
    apt-get install -y ffmpeg libgl1 && \
    rm -rf /var/lib/apt/lists/*

# Set working directory inside container
WORKDIR /app

# Copy requirements first (for caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend code
COPY . .

# Expose port (Render uses $PORT env var)
EXPOSE 8000

# Start the app using gunicorn
CMD ["gunicorn", "backend_api:app", "-w", "2", "-k", "gthread", "-b", "0.0.0.0:8000", "--timeout", "120"]
