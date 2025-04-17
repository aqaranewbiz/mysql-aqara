FROM python:3.9-slim

WORKDIR /app

# Copy application files
COPY . .

# Install Node.js
RUN apt-get update && \
    apt-get install -y nodejs npm && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies with pip
RUN pip install --no-cache-dir mysql-connector-python==8.0.33

# Make index.js executable
RUN chmod +x index.js

# Expose port if needed (for Smithery deployments)
EXPOSE 14000

# Set environment variables
ENV NODE_ENV=production
ENV PYTHONUNBUFFERED=1

# Create .local marker file
RUN echo "This is a local MCP server" > .local

# Run the server
CMD ["node", "index.js"] 