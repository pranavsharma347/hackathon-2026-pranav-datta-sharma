# Use official Python image
FROM python:3.11

# Set working directory
WORKDIR /app

# Copy files
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt


# Set environment variables (optional)
ENV PYTHONUNBUFFERED=1

# Run your script
CMD ["python", "customerSupport.py"]