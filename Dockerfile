FROM python:3.9-slim

# Install system dependencies and Node.js LTS
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    build-essential \
    default-libmysqlclient-dev \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Verify installations
RUN python --version && pip --version && node --version && npm --version

# Set working directory
WORKDIR /app

# Copy requirements and package files first (for better layer caching)
COPY requirements.txt package.json ./

# Install Python dependencies with clear error reporting
RUN pip install --no-cache-dir -r requirements.txt || (echo "Failed to install Python dependencies" && exit 1)

# Install Node.js dependencies
RUN npm install || (echo "Failed to install Node.js dependencies" && exit 1)

# Copy application files
COPY . .

# Make run.js executable
RUN chmod +x run.js

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8
ENV NODE_ENV=production

# Command to run the MCP server
CMD ["node", "run.js"] 