#!/usr/bin/env node

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

// Set flag to identify this as an MCP server
global.isMCPServer = true;

// Get script directory
const scriptDir = path.dirname(__filename);
console.error(`Script directory: ${scriptDir}`);

// Path to Python script
const pythonScript = path.join(scriptDir, 'mcp_server.py');
console.error(`Python script path: ${pythonScript}`);

// Check if Python script exists
if (!fs.existsSync(pythonScript)) {
  console.error(`Error: Python script not found at ${pythonScript}`);
  process.exit(1);
}

// In Docker or Smithery environment, we know python is installed
const isDocker = fs.existsSync('/.dockerenv') || process.env.DOCKER;
const isSmithery = process.env.SMITHERY === 'true';
const pythonCmd = (isDocker || isSmithery) ? 'python' : detectPythonCommand();

// Log environment for debugging
console.error(`Environment: Docker=${isDocker}, Smithery=${isSmithery}`);
console.error(`MySQL config: Host=${process.env.MYSQL_HOST}, User=${process.env.MYSQL_USER}, DB=${process.env.MYSQL_DATABASE}`);

// Detect Python command for non-Docker environments
function detectPythonCommand() {
  console.error('Detecting Python command...');
  const commands = process.platform === 'win32' 
    ? ['python', 'py'] 
    : ['python3', 'python'];
  
  for (const cmd of commands) {
    try {
      const result = require('child_process').spawnSync(cmd, ['--version']);
      if (result.status === 0) {
        console.error(`Found Python command: ${cmd}`);
        return cmd;
      }
    } catch (err) {
      // Command not found, try next
    }
  }
  
  console.error('No Python command found. Defaulting to "python"');
  return 'python';
}

// Environment setup
const env = {
  ...process.env,
  PYTHONUNBUFFERED: '1',
  PYTHONIOENCODING: 'utf-8',
  MCP_SERVER: '@aqaranewbiz/mysql-aqara'
};

// If config was provided through environment variables, pass it to Python script
if (process.env.MYSQL_HOST && process.env.MYSQL_USER && process.env.MYSQL_PASSWORD && process.env.MYSQL_DATABASE) {
  console.error('MySQL connection parameters found in environment');
  env.DB_HOST = process.env.MYSQL_HOST;
  env.DB_USER = process.env.MYSQL_USER;
  env.DB_PASSWORD = process.env.MYSQL_PASSWORD;
  env.DB_DATABASE = process.env.MYSQL_DATABASE;
}

// Export for use as a module
if (module.parent) {
  module.exports = {
    start: function(config) {
      // Add config to environment if provided
      if (config) {
        env.MCP_CONFIG = JSON.stringify(config);
        
        // Set specific MySQL environment variables if provided
        if (config.mysqlHost) env.DB_HOST = config.mysqlHost;
        if (config.mysqlUser) env.DB_USER = config.mysqlUser;
        if (config.mysqlPassword) env.DB_PASSWORD = config.mysqlPassword;
        if (config.mysqlDatabase) env.DB_DATABASE = config.mysqlDatabase;
      }
      startServer();
    }
  };
} else {
  // Direct execution from command line
  startServer();
}

function startServer() {
  // Spawn Python process
  console.error(`Starting MCP server with Python command: ${pythonCmd}`);
  try {
    const pythonProcess = spawn(pythonCmd, [pythonScript], {
      stdio: ['pipe', 'pipe', 'pipe'],
      env
    });

    console.error(`Python process started with PID: ${pythonProcess.pid}`);

    // Handle stdout
    pythonProcess.stdout.on('data', (data) => {
      try {
        process.stdout.write(data);
      } catch (err) {
        console.error('Error writing to stdout:', err);
      }
    });

    // Handle stderr
    pythonProcess.stderr.on('data', (data) => {
      try {
        console.error(`[Python] ${data.toString().trim()}`);
      } catch (err) {
        console.error('Error writing to stderr:', err);
      }
    });

    // Handle errors
    pythonProcess.on('error', (err) => {
      console.error('Failed to start Python process:', err);
      process.exit(1);
    });

    // Handle process exit
    pythonProcess.on('exit', (code, signal) => {
      if (signal) {
        console.error(`Python process was killed with signal: ${signal}`);
        process.exit(1);
      }
      
      if (code !== 0) {
        console.error(`Python process exited with code ${code}`);
        process.exit(code);
      }
      
      console.error('Python process exited normally');
      process.exit(0);
    });

    // Pipe stdin to Python process
    process.stdin.pipe(pythonProcess.stdin);

    // Handle signals
    process.on('SIGINT', () => {
      console.error('Received SIGINT, terminating Python process...');
      pythonProcess.kill('SIGINT');
    });

    process.on('SIGTERM', () => {
      console.error('Received SIGTERM, terminating Python process...');
      pythonProcess.kill('SIGTERM');
    });
    
    // Handle uncaught exceptions
    process.on('uncaughtException', (err) => {
      console.error('Uncaught exception:', err);
      pythonProcess.kill('SIGTERM');
      process.exit(1);
    });
  } catch (err) {
    console.error('Failed to start Python process:', err);
    process.exit(1);
  }
} 