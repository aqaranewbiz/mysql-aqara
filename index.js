#!/usr/bin/env node
// MySQL MCP Server for Smithery
// This file exists to make the package compatible with npm

const { Server } = require('@modelcontextprotocol/sdk/server/index.js');
const { StdioServerTransport } = require('@modelcontextprotocol/sdk/server/stdio.js');
const { CallToolRequestSchema, ErrorCode, ListToolsRequestSchema, McpError } = require('@modelcontextprotocol/sdk/types.js');
const mysql = require('mysql2/promise');
const fs = require('fs');
const path = require('path');
const { spawn, exec } = require('child_process');
const { MCP } = require('@modelcontextprotocol/sdk');

// Create a special .local file to tell Smithery this is a local MCP
const scriptDir = path.dirname(__filename);
const localMarkerFile = path.join(scriptDir, '.local');
if (!fs.existsSync(localMarkerFile)) {
  try {
    fs.writeFileSync(localMarkerFile, 'This is a local MCP server');
    console.error('Created .local marker file for Smithery');
  } catch (err) {
    console.error('Warning: Could not create .local marker file', err);
  }
}

// Log current process info
console.error(`Process ID: ${process.pid}`);
console.error(`Node version: ${process.version}`);
console.error(`Current directory: ${process.cwd()}`);
console.error(`Script path: ${__filename}`);

// Configuration
const USE_PYTHON = true; // Set to false to use the Node.js implementation
const PORT = process.env.MCP_PORT || 14000;

// Global connection pool variable for Node.js implementation
let pool = null;

// Get the directory where this script is located
const scriptDir = __dirname;

// Python implementation
if (USE_PYTHON) {
  console.log('Starting MySQL MCP server using Python implementation...');
  
  // Determine the script's directory
  const mcp_server_path = path.join(scriptDir, 'mcp_server.py');
  const requirements_path = path.join(scriptDir, 'requirements.txt');
  
  // Function to check if Python is installed and get its version
  function getPythonCommand() {
    return new Promise((resolve, reject) => {
      // Try 'python3' first (common on macOS and Linux)
      exec('python3 --version', (error) => {
        if (!error) {
          resolve('python3');
          return;
        }
        
        // Try 'python' next (common on Windows)
        exec('python --version', (error) => {
          if (!error) {
            resolve('python');
            return;
          }
          
          // If neither worked, Python is not installed or not in PATH
          reject(new Error('Python is not installed or not in PATH. Please install Python 3.6 or later.'));
        });
      });
    });
  }

  // Function to check and install requirements
  function installRequirements(pythonCmd) {
    return new Promise((resolve, reject) => {
      console.log('Checking Python requirements...');
      
      // Check if requirements.txt exists
      if (!fs.existsSync(requirements_path)) {
        console.error(`Error: requirements.txt not found at ${requirements_path}`);
        reject(new Error('Requirements file not found'));
        return;
      }
      
      const install = spawn(pythonCmd, ['-m', 'pip', 'install', '-r', requirements_path]);
      
      install.stdout.on('data', (data) => {
        console.log(`${data}`);
      });
      
      install.stderr.on('data', (data) => {
        console.error(`${data}`);
      });
      
      install.on('close', (code) => {
        if (code !== 0) {
          reject(new Error(`Failed to install requirements (exit code: ${code})`));
          return;
        }
        console.log('Requirements installed successfully');
        resolve();
      });
    });
  }

  // Function to start the MCP server
  function startServer(pythonCmd) {
    console.log(`Starting MCP server using ${pythonCmd}...`);
    console.log(`Server script path: ${mcp_server_path}`);
    
    // Check if the server script exists
    if (!fs.existsSync(mcp_server_path)) {
      console.error(`Error: MCP server script not found at ${mcp_server_path}`);
      process.exit(1);
    }
    
    // Get the settings from the environment variables (set by Smithery)
    const env = {
      ...process.env,
      DB_HOST: process.env.SMITHERY_SETTING_HOST || 'localhost',
      DB_USER: process.env.SMITHERY_SETTING_USER || '',
      DB_PASSWORD: process.env.SMITHERY_SETTING_PASSWORD || '',
      DB_DATABASE: process.env.SMITHERY_SETTING_DATABASE || ''
    };
    
    // Log the settings (masking sensitive data)
    console.error(`DB Settings:
    - Host: ${env.DB_HOST}
    - User: ${env.DB_USER}
    - Database: ${env.DB_DATABASE}
    - Password: ${env.DB_PASSWORD ? '*****' : 'Not set'}
    `);
    
    const serverProcess = spawn(pythonCmd, [mcp_server_path], { env });
    
    // Connect the Python process's stdout to our stdout
    serverProcess.stdout.pipe(process.stdout);
    
    // Log stderr but don't pass it to stdout
    serverProcess.stderr.on('data', (data) => {
      console.error(`Python: ${data}`);
    });
    
    serverProcess.on('close', (code) => {
      if (code !== 0) {
        console.error(`MCP server process exited with code ${code}`);
      }
      process.exit(code);
    });
    
    // Handle process termination signals
    process.on('SIGINT', () => {
      console.log('Received SIGINT. Shutting down MCP server...');
      serverProcess.kill('SIGINT');
    });
    
    process.on('SIGTERM', () => {
      console.log('Received SIGTERM. Shutting down MCP server...');
      serverProcess.kill('SIGTERM');
    });
  }

  // Main function to run the server
  async function main() {
    try {
      // Get the appropriate Python command
      const pythonCmd = await getPythonCommand();
      console.log(`Found Python command: ${pythonCmd}`);
      
      // Install requirements
      await installRequirements(pythonCmd);
      
      // Start the server
      startServer(pythonCmd);
    } catch (error) {
      console.error(`Error: ${error.message}`);
      process.exit(1);
    }
  }

  // Run the main function
  main();
} 
// Node.js implementation
else {
  console.log('Starting MySQL MCP server using Node.js implementation...');

  // Create MCP server
  const server = new MCP.Server({
    port: PORT,
    name: 'mysql-aqara',
    version: '1.0.0',
  });

  // Connect to database
  async function connectDb(host, user, password, database) {
    try {
      // Close existing pool if it exists
      if (pool) {
        await pool.end();
      }

      // Create a new connection pool
      pool = mysql.createPool({
        host,
        user,
        password,
        database,
        waitForConnections: true,
        connectionLimit: 10,
        queueLimit: 0
      });

      // Test the connection
      await pool.query('SELECT 1');
      return { success: true, message: 'Connected to database successfully' };
    } catch (error) {
      console.error('Error connecting to database:', error);
      return { success: false, message: error.message };
    }
  }

  // Execute a query
  async function executeQuery(query, params = []) {
    if (!pool) {
      return { success: false, message: 'Database not connected. Use connect_db first.' };
    }

    try {
      const [rows] = await pool.query(query, params);
      return { success: true, result: rows };
    } catch (error) {
      console.error('Error executing query:', error);
      return { success: false, message: error.message };
    }
  }

  // List tables in the database
  async function listTables() {
    if (!pool) {
      return { success: false, message: 'Database not connected. Use connect_db first.' };
    }

    try {
      const [rows] = await pool.query('SHOW TABLES');
      return { success: true, tables: rows.map(row => Object.values(row)[0]) };
    } catch (error) {
      console.error('Error listing tables:', error);
      return { success: false, message: error.message };
    }
  }

  // Describe a table structure
  async function describeTable(tableName) {
    if (!pool) {
      return { success: false, message: 'Database not connected. Use connect_db first.' };
    }

    try {
      const [rows] = await pool.query('DESCRIBE ??', [tableName]);
      return { success: true, structure: rows };
    } catch (error) {
      console.error(`Error describing table ${tableName}:`, error);
      return { success: false, message: error.message };
    }
  }

  // Register tools
  server.addTool('connect_db', connectDb);
  server.addTool('query', executeQuery);
  server.addTool('execute', executeQuery);
  server.addTool('list_tables', listTables);
  server.addTool('describe_table', describeTable);

  // Start the server
  server.start().then(() => {
    console.log(`MySQL MCP server is running on port ${PORT}`);
  }).catch(err => {
    console.error('Failed to start MCP server:', err);
  });

  // Handle signals for graceful shutdown
  process.on('SIGINT', async () => {
    console.log('Received SIGINT, shutting down...');
    if (pool) {
      await pool.end();
    }
    server.stop();
    process.exit(0);
  });

  process.on('SIGTERM', async () => {
    console.log('Received SIGTERM, shutting down...');
    if (pool) {
      await pool.end();
    }
    server.stop();
    process.exit(0);
  });
} 