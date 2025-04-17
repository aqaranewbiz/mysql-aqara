# MySQL MCP Server for Smithery

A MySQL connector for Smithery that allows you to connect to your MySQL database directly from Smithery.

## One-Click Installation

### Global Installation
```bash
npm install -g mysql-aqara
```

### Local Installation
```bash
npm install mysql-aqara
```

## Manual Installation

1. Clone this repository:
```bash
git clone https://github.com/aqaranewbiz/mysql-aqara.git
```

2. Install dependencies:
```bash
cd mysql-aqara
npm install
pip install -r requirements.txt
```

3. Make the run.js file executable (Unix/Linux/Mac):
```bash
chmod +x run.js
```

## Usage

### Using Global Installation
```bash
mysql-aqara
```

### Using Local Installation
```bash
npx mysql-aqara
```

### Direct Execution
```bash
node run.js
```

## Features

- **Smart Path Detection**: Automatically finds the Python script in various locations
- **Cross-Platform Support**: Works on Windows, macOS, and Linux
- **Automatic Python Detection**: Uses `python3` or `python` depending on your system
- **Automatic Requirements Installation**: Installs required Python packages on startup
- **Improved Error Handling**: Better feedback for troubleshooting

## Configuration

No environment variables required! When connecting to a database, you'll need to provide:

- **host**: Database server hostname or IP address
- **user**: Database username
- **password**: Database password
- **database**: Database name

## Available Tools

### connect_db
Establishes a connection to the MySQL database.

**Parameters:**
- **host**: Database server hostname
- **user**: Database username
- **password**: Database password
- **database**: Database name

### create_or_modify_table
Creates a new table or modifies an existing one.

**Parameters:**
- **table_name**: Name of the table
- **columns**: Array of column definitions

### execute_query
Executes a SELECT query on the database.

**Parameters:**
- **query**: SQL SELECT query
- **params** (optional): Parameters for the query

### execute_command
Executes an INSERT, UPDATE, or DELETE query.

**Parameters:**
- **command**: SQL command to execute
- **params** (optional): Parameters for the command

### list_tables
Lists all tables in the connected database.

**Parameters:** None

### describe_table
Gets the structure of a specific table.

**Parameters:**
- **table_name**: Name of the table to describe

## Troubleshooting

If you encounter issues:

1. **Python Not Found**: The server will automatically detect `python3` or `python`. If neither works, ensure Python is installed and in your PATH.

2. **Missing Modules**: The server will attempt to install required packages automatically. If this fails, manually run:
   ```bash
   pip install mysql-connector-python>=8.0.0
   ```

3. **Connection Issues**: Verify your database credentials and ensure the MySQL server is running and accessible.

4. **Script Path Issues**: The server checks multiple locations for the Python script. If it can't find it, ensure the `mcp_server.py` file is in the same directory as `index.js` or in the current working directory.

## License

MIT

## Contact

If you have any questions, please create an issue. 