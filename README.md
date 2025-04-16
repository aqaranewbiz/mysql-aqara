# MySQL MCP Server for Smithery

A MySQL MCP server implementation for Smithery that allows direct database operations.

## Installation

### One-Click Installation

1. Install globally:
```bash
npm install -g mysql-aqara
```

2. Or install locally:
```bash
npm install mysql-aqara
```

### Manual Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
npm install
```
3. Make run.js executable:
```bash
chmod +x run.js
```

## Usage

### Global Installation
```bash
mcp-mysql-server
```

### Local Installation
```bash
npx mysql-aqara
```

### Direct Execution
```bash
node run.js
```

## Configuration

The server requires database credentials to be provided during the initial connection. You will be prompted to enter:
- Host
- User
- Password
- Database name

## Available Tools

1. `connect_db`: Establish a connection to the MySQL database
   - Parameters:
     - host: Database host
     - user: Database user
     - password: Database password
     - database: Database name

2. `create_or_modify_table`: Create or modify a table
   - Parameters:
     - table_name: Name of the table
     - columns: Array of column definitions
     - unique_keys: (optional) Array of unique key definitions

3. `execute_query`: Execute a SELECT query (equivalent to the `query` method in mcp.json)
   - Parameters:
     - sql: SQL query string
     - params: (optional) Array of parameters for prepared statements

4. `execute_command`: Execute INSERT, UPDATE, or DELETE queries (equivalent to the `execute` method in mcp.json)
   - Parameters:
     - sql: SQL command string
     - params: (optional) Array of parameters for prepared statements

5. `list_tables`: List all tables in the database
   - No parameters required

6. `describe_table`: Get the structure of a table
   - Parameters:
     - table: Name of the table

## Troubleshooting

If you encounter any issues with server connection:

1. Verify that Python and Node.js are installed and in your PATH:
   ```bash
   python --version
   node --version
   ```

2. Check that the required Python packages are installed:
   ```bash
   pip install -r requirements.txt
   ```

3. Ensure the run.js file has execution permissions:
   ```bash
   chmod +x run.js
   ```

4. Check for errors in the server logs:
   - Look for messages with `[error]` level
   - Check for Python exceptions in stderr output

5. If the server disconnects immediately after initialization:
   - Verify your MySQL connection parameters
   - Ensure MySQL server is running and accessible
   - Check firewall rules allowing the connection

## License

MIT

## Contact

If you have any questions, please create an issue. 