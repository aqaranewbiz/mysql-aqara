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

# Verify installations with more detailed output
RUN echo "Python version:" && python --version && \
    echo "Pip version:" && pip --version && \
    echo "Node version:" && node --version && \
    echo "NPM version:" && npm --version

# Debug: Show environment variables
RUN echo "Environment variables:" && env | sort

# Set working directory
WORKDIR /app

# Debug: Show current working directory and contents
RUN echo "Working directory:" && pwd && ls -la

# Copy requirements and package files first (for better layer caching)
COPY requirements.txt package.json ./

# Debug: Verify copied files
RUN echo "Copied files:" && ls -la

# Install Python dependencies with clear error reporting
RUN pip install --no-cache-dir -r requirements.txt || (echo "Failed to install Python dependencies" && cat requirements.txt && exit 1)

# Print installed Python packages for debugging
RUN pip list

# Install Node.js dependencies
RUN npm install --no-optional || (echo "Failed to install Node.js dependencies" && cat package.json && exit 1)

# Copy application files
COPY . .

# Debug: Show all files after copy
RUN echo "All files:" && find . -type f | sort

# Make run.js executable
RUN chmod +x run.js

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8
ENV NODE_ENV=production
ENV DEBUG=true
ENV DOCKER=true

# Command to run the MCP server
CMD ["node", "run.js"] 