# Use Python base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the entire project
COPY . .

# Ensure the directory for inventory.db exists
RUN mkdir -p /app/app/utils/inventory

# Expose the port your app runs on
EXPOSE 8000

# Command to run the application
CMD ["python", "run.py"]