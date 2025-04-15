# MySQL MCP Server for Smithery

A MySQL MCP server implementation for Smithery that allows direct database operations.

## Installation

### One-Click Installation

1. Install globally:
```bash
npm install -g @aqaranewbiz/mysql-aqaranewbiz
```

2. Or install locally:
```bash
npm install @aqaranewbiz/mysql-aqaranewbiz
```

### Manual Installation

1. Clone the repository
2. Install dependencies:
```bash
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
npx @aqaranewbiz/mysql-aqaranewbiz
```

### Direct Execution
```bash
python mcp_server.py
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

3. `execute_query`: Execute a SELECT query
   - Parameters:
     - query: SQL query string

4. `execute_command`: Execute INSERT, UPDATE, or DELETE queries
   - Parameters:
     - query: SQL command string

5. `list_tables`: List all tables in the database

6. `describe_table`: Get the structure of a table
   - Parameters:
     - table_name: Name of the table

## Troubleshooting

If you encounter any issues:

1. Verify that Python is installed and in your PATH
2. Check that the required Python packages are installed:
   ```bash
   pip install mysql-connector-python
   ```
3. Ensure the run.js file has execution permissions
4. Check the database connection parameters

## License

MIT

## Contact

If you have any questions, please create an issue. 