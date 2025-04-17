#!/usr/bin/env node
// MySQL MCP Server for Smithery
// This file exists to make the package compatible with npm
// The actual server is started by run.js

const { Server } = require('@modelcontextprotocol/sdk/server/index.js');
const { StdioServerTransport } = require('@modelcontextprotocol/sdk/server/stdio.js');
const { CallToolRequestSchema, ErrorCode, ListToolsRequestSchema, McpError } = require('@modelcontextprotocol/sdk/types.js');
const mysql = require('mysql2/promise');
const fs = require('fs');
const path = require('path');

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

let pool = null;
let dbConfig = null;

/**
 * Get configuration from environment variables
 */
function getConfigFromEnv() {
  // Get configuration from environment variables
  // Supports both MYSQL_* and mysql* naming conventions
  const host = process.env.mysqlHost || process.env.MYSQL_HOST;
  const user = process.env.mysqlUser || process.env.MYSQL_USER;
  const password = process.env.mysqlPassword || process.env.MYSQL_PASSWORD;
  const database = process.env.mysqlDatabase || process.env.MYSQL_DATABASE;
  
  if (host) console.error(`Using host from environment: ${host}`);
  if (user) console.error(`Using user from environment: ${user}`);
  if (database) console.error(`Using database from environment: ${database}`);
  
  return { host, user, password, database };
}

/**
 * Create a connection pool
 */
async function createConnectionPool(config) {
  if (!config.host || !config.user || !config.password) {
    return { success: false, error: "Missing database connection parameters" };
  }
  
  try {
    console.error(`Connecting to MySQL at ${config.host} as ${config.user}`);
    
    pool = mysql.createPool({
      host: config.host,
      user: config.user,
      password: config.password,
      database: config.database,
      waitForConnections: true,
      connectionLimit: 10,
      queueLimit: 0
    });
    
    // Test the connection
    const conn = await pool.getConnection();
    conn.release();
    
    console.error('Database connection successful');
    
    dbConfig = config;
    return { success: true, message: "Connected to database successfully" };
  } catch (error) {
    console.error("Database connection error:", error);
    return { success: false, error: error.message };
  }
}

/**
 * Create or modify a table
 */
async function createOrModifyTable(table_name, columns, unique_keys = []) {
  if (!pool) {
    return { success: false, error: "Database not connected" };
  }
  
  let connection;
  try {
    connection = await pool.getConnection();
    
    // Drop existing table if it exists
    await connection.execute(`DROP TABLE IF EXISTS ${table_name}`);
    
    // Create new table
    const columnDefs = [];
    for (const col of columns) {
      let colDef = `${col.name} ${col.type}`;
      if (col.not_null) colDef += " NOT NULL";
      if (col.default !== undefined) colDef += ` DEFAULT ${col.default}`;
      if (col.auto_increment) colDef += " AUTO_INCREMENT";
      if (col.primary_key) colDef += " PRIMARY KEY";
      columnDefs.push(colDef);
    }
    
    // Add unique keys if provided
    if (unique_keys && unique_keys.length > 0) {
      for (const key of unique_keys) {
        columnDefs.push(`UNIQUE KEY ${key.name} (${key.columns})`);
      }
    }
    
    const createTableSql = `CREATE TABLE ${table_name} (${columnDefs.join(', ')})`;
    await connection.execute(createTableSql);
    
    return { success: true, message: `Table ${table_name} created/modified successfully` };
  } catch (error) {
    console.error("Error creating/modifying table:", error);
    return { success: false, error: error.message };
  } finally {
    if (connection) connection.release();
  }
}

/**
 * Execute a SELECT query
 */
async function executeQuery(sql, params = []) {
  if (!pool) {
    return { success: false, error: "Database not connected" };
  }
  
  let connection;
  try {
    connection = await pool.getConnection();
    
    const [rows] = await connection.execute(sql, params);
    return { success: true, results: rows };
  } catch (error) {
    console.error("Error executing query:", error);
    return { success: false, error: error.message };
  } finally {
    if (connection) connection.release();
  }
}

/**
 * Execute a non-SELECT query (INSERT, UPDATE, DELETE)
 */
async function executeCommand(sql, params = []) {
  if (!pool) {
    return { success: false, error: "Database not connected" };
  }
  
  let connection;
  try {
    connection = await pool.getConnection();
    
    const [result] = await connection.execute(sql, params);
    return { success: true, affected_rows: result.affectedRows };
  } catch (error) {
    console.error("Error executing command:", error);
    return { success: false, error: error.message };
  } finally {
    if (connection) connection.release();
  }
}

/**
 * List tables in the database
 */
async function listTables() {
  if (!pool) {
    return { success: false, error: "Database not connected" };
  }
  
  let connection;
  try {
    connection = await pool.getConnection();
    
    const [rows] = await connection.execute('SHOW TABLES');
    const tables = rows.map(row => Object.values(row)[0]);
    
    return { success: true, tables };
  } catch (error) {
    console.error("Error listing tables:", error);
    return { success: false, error: error.message };
  } finally {
    if (connection) connection.release();
  }
}

/**
 * Describe a table's structure
 */
async function describeTable(table) {
  if (!pool) {
    return { success: false, error: "Database not connected" };
  }
  
  let connection;
  try {
    connection = await pool.getConnection();
    
    const [rows] = await connection.execute(`DESCRIBE ${table}`);
    return { success: true, columns: rows };
  } catch (error) {
    console.error("Error describing table:", error);
    return { success: false, error: error.message };
  } finally {
    if (connection) connection.release();
  }
}

/**
 * Start the MCP server
 */
async function startServer() {
  // Server information and metadata
  const serverInfo = {
    name: "mysql-aqara",
    version: "1.0.0",
    displayName: "MySQL Database Server",
    description: "MySQL MCP server for Smithery - Database query and management tools",
    repository: "https://github.com/aqaralife/portal"
  };
  
  // Connection configuration schema
  const configSchema = {
    type: "object",
    properties: {
      mysqlHost: {
        type: "string",
        description: "MySQL server host address",
        default: "localhost"
      },
      mysqlUser: {
        type: "string",
        description: "MySQL user name"
      },
      mysqlPassword: {
        type: "string",
        description: "MySQL user password",
        format: "password"
      },
      mysqlDatabase: {
        type: "string",
        description: "MySQL database name (optional)"
      }
    },
    required: ["mysqlHost", "mysqlUser", "mysqlPassword"]
  };
  
  // Server capabilities
  const serverCapabilities = {
    configSchema: configSchema, // <-- This should appear in Overview tab
    tools: {
      connect_db: {
        description: "Establish connection to MySQL database using provided credentials"
      },
      create_or_modify_table: {
        description: "Create or modify a database table"
      },
      query: {
        description: "Execute SELECT queries with optional prepared statement parameters"
      },
      execute: {
        description: "Execute INSERT, UPDATE, or DELETE queries with optional prepared statement parameters"
      },
      list_tables: {
        description: "List all tables in the connected database"
      },
      describe_table: {
        description: "Get the structure of a specific table"
      }
    }
  };
  
  console.error('Creating server with config schema:', JSON.stringify(configSchema, null, 2));
  
  const server = new Server(
    serverInfo,
    {
      capabilities: serverCapabilities
    }
  );
  
  // Handle list_tools request
  server.setRequestHandler(ListToolsRequestSchema, async () => {
    return {
      tools: [
        {
          name: "connect_db",
          description: "Establish connection to MySQL database using provided credentials",
          inputSchema: {
            type: "object",
            properties: {
              host: {
                type: "string",
                description: "Database host"
              },
              user: {
                type: "string",
                description: "Database user"
              },
              password: {
                type: "string",
                description: "Database password"
              },
              database: {
                type: "string",
                description: "Database name"
              }
            },
            required: ["host", "user", "password"]
          }
        },
        {
          name: "create_or_modify_table",
          description: "Create or modify a database table",
          inputSchema: {
            type: "object",
            properties: {
              table_name: {
                type: "string",
                description: "Name of the table to create or modify"
              },
              columns: {
                type: "array",
                description: "Array of column definitions with name, type, and options"
              },
              unique_keys: {
                type: "array",
                description: "Array of unique key definitions with name and columns"
              }
            },
            required: ["table_name", "columns"]
          }
        },
        {
          name: "query",
          description: "Execute SELECT queries with optional prepared statement parameters",
          inputSchema: {
            type: "object",
            properties: {
              sql: {
                type: "string",
                description: "SQL query string"
              },
              params: {
                type: "array",
                description: "Query parameters for prepared statement"
              }
            },
            required: ["sql"]
          }
        },
        {
          name: "execute",
          description: "Execute INSERT, UPDATE, or DELETE queries with optional prepared statement parameters",
          inputSchema: {
            type: "object",
            properties: {
              sql: {
                type: "string",
                description: "SQL query string"
              },
              params: {
                type: "array",
                description: "Query parameters for prepared statement"
              }
            },
            required: ["sql"]
          }
        },
        {
          name: "list_tables",
          description: "List all tables in the connected database",
          inputSchema: {
            type: "object",
            properties: {}
          }
        },
        {
          name: "describe_table",
          description: "Get the structure of a specific table",
          inputSchema: {
            type: "object",
            properties: {
              table: {
                type: "string",
                description: "Table name"
              }
            },
            required: ["table"]
          }
        }
      ]
    };
  });
  
  // Handle tool call requests
  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    try {
      const toolName = request.params.name;
      const args = request.params.arguments || {};
      
      console.error(`[Tool Call] ${toolName}`, args);
      
      // Try to connect with environment variables if not already connected
      if (!pool && toolName !== 'connect_db') {
        const envConfig = getConfigFromEnv();
        if (envConfig.host && envConfig.user && envConfig.password) {
          console.error('Attempting auto-connection with environment variables');
          await createConnectionPool(envConfig);
        }
      }
      
      switch (toolName) {
        case 'connect_db':
          const result = await createConnectionPool(args);
          return { content: [{ type: 'text', text: JSON.stringify(result) }] };
          
        case 'create_or_modify_table':
          const createResult = await createOrModifyTable(
            args.table_name,
            args.columns,
            args.unique_keys
          );
          return { content: [{ type: 'text', text: JSON.stringify(createResult) }] };
          
        case 'query':
          const queryResult = await executeQuery(args.sql, args.params || []);
          return { content: [{ type: 'text', text: JSON.stringify(queryResult) }] };
          
        case 'execute':
          const execResult = await executeCommand(args.sql, args.params || []);
          return { content: [{ type: 'text', text: JSON.stringify(execResult) }] };
          
        case 'list_tables':
          const tables = await listTables();
          return { content: [{ type: 'text', text: JSON.stringify(tables) }] };
          
        case 'describe_table':
          const tableInfo = await describeTable(args.table);
          return { content: [{ type: 'text', text: JSON.stringify(tableInfo) }] };
          
        default:
          throw new McpError(ErrorCode.MethodNotFound, `Unknown tool: ${toolName}`);
      }
    } catch (error) {
      console.error('[Error]', error);
      return {
        content: [{ type: 'text', text: `Error: ${error.message || error}` }],
        isError: true
      };
    }
  });
  
  try {
    console.error('[Setup] Starting MySQL MCP server');
    const transport = new StdioServerTransport();
    await server.connect(transport);
    console.error('[Setup] MySQL MCP server running on stdio');
    
    // Check for environment credentials and try to connect
    const envConfig = getConfigFromEnv();
    if (envConfig.host && envConfig.user && envConfig.password) {
      console.error('Found database credentials in environment');
      await createConnectionPool(envConfig);
    }
  } catch (error) {
    console.error('[Fatal] Server error:', error);
    process.exit(1);
  }
}

// Start the server
startServer().catch(err => {
  console.error('Unhandled error:', err);
  process.exit(1);
}); 