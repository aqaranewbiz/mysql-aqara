# MySQL MCP Server for Smithery

[![smithery badge](https://smithery.ai/badge/@aqaranewbiz/mysql-aqara)](https://smithery.ai/server/@aqaranewbiz/mysql-aqara)

A MySQL MCP server implementation for Smithery that allows direct database operations.

## Installation

### One-Click Installation

1. Install globally:
```bash
npm install -g @aqaranewbiz/mysql-aqara
```

2. Or install locally:
```bash
npm install @aqaranewbiz/mysql-aqara
```

### Installing via Smithery

To install MySQL Database Server for Claude Desktop automatically via [Smithery](https://smithery.ai/server/@aqaranewbiz/mysql-aqara):

```bash
npx -y @smithery/cli install @aqaranewbiz/mysql-aqara --client claude
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
npx @aqaranewbiz/mysql-aqara
```

### Direct Execution
```bash
node run.js
```

### Using with Smithery CLI

```bash
# Use Interactive Prompt (Recommended)
npx @smithery/cli@latest run @aqaranewbiz/mysql-aqara

# Or provide config as JSON (replace with your own values)
npx @smithery/cli@latest run @aqaranewbiz/mysql-aqara --config '{"host":"<YOUR_HOST>","user":"<YOUR_USER>","password":"<YOUR_PASSWORD>","database":"<YOUR_DATABASE>"}'
```

## Configuration

The server requires database credentials to be provided during the initial connection. You will be prompted to enter:
- Host (usually "localhost" or an IP address)
- User (your database username)
- Password (your database user's password)
- Database name (the name of the database you want to connect to)

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

6. When using Smithery CLI with the --config parameter:
   - Use single quotes around the JSON object
   - Use double quotes for the JSON property names and values
   - Do not include spaces in the JSON string
   - Example:
     ```bash
     npx @smithery/cli@latest run @aqaranewbiz/mysql-aqara --config '{"host":"localhost","user":"<YOUR_USER>","password":"<YOUR_PASSWORD>","database":"<YOUR_DATABASE>"}'
     ```

## Security Considerations

- Never commit real database credentials to version control
- Use environment variables or config files for sensitive data when possible
- The `password` parameter is sensitive - be careful when logging or displaying it

## License

MIT

## Contact

If you have any questions, please create an issue.
