FROM python:3.9-slim

# Install Node.js
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy package files
COPY package.json ./
COPY requirements.txt ./

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN npm install

# Copy application files
COPY . .

# Make run.js executable
RUN chmod +x run.js

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8

# Command to run the MCP server
CMD ["node", "run.js"] 