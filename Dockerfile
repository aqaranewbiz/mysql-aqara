FROM python:3.11-alpine

# Install system dependencies and Node.js
RUN apk add --no-cache gcc musl-dev linux-headers nodejs npm

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Make run.js executable
RUN chmod +x run.js

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8

# Run the MCP server via Node.js
CMD ["node", "run.js"] 