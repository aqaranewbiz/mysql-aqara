import json
import sys
import os
import signal
import time
import mysql.connector
from mysql.connector import Error
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S.%fZ'
)
logger = logging.getLogger('mysql-aqara')

# Global variables
db_config = None
last_activity_time = time.time()
KEEP_ALIVE_INTERVAL = 30  # seconds
TIMEOUT = 300  # seconds (increased from 60 to 300)

def signal_handler(signum, frame):
    """Handle termination signals"""
    logger.info("Received termination signal, cleaning up...")
    cleanup()
    sys.exit(0)

def cleanup():
    """Cleanup resources before exit"""
    if db_config:
        try:
            conn = mysql.connector.connect(**db_config)
            conn.close()
            logger.info("Database connection closed")
        except Error as e:
            logger.error(f"Error closing database connection: {e}")

def check_timeout():
    """Check if the connection has timed out"""
    current_time = time.time()
    if current_time - last_activity_time > TIMEOUT:
        logger.warning("Connection timeout detected")
        return True
    return False

def send_keep_alive():
    """Send keep-alive message to prevent timeout"""
    global last_activity_time
    last_activity_time = time.time()
    response = {
        "jsonrpc": "2.0",
        "method": "keepAlive",
        "params": {"timestamp": datetime.utcnow().isoformat()}
    }
    print(json.dumps(response), flush=True)

def connect_db(host, user, password, database):
    """Establish a connection to the MySQL database"""
    global db_config
    try:
        db_config = {
            'host': host,
            'user': user,
            'password': password,
            'database': database,
            'charset': 'utf8mb4',
            'collation': 'utf8mb4_unicode_ci'
        }
        
        # Test the connection
        conn = mysql.connector.connect(**db_config)
        conn.close()
        
        logger.info("Database connection established successfully")
        return {"success": True, "message": "Connected to database successfully"}
    except Error as e:
        logger.error(f"Database connection error: {e}")
        return {"success": False, "error": str(e)}

def create_or_modify_table(table_name, columns):
    """Create or modify a table"""
    if not db_config:
        return {"success": False, "error": "Database not connected"}
    
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        # Drop existing table if it exists
        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        # Create new table
        column_defs = []
        for col in columns:
            col_def = f"{col['name']} {col['type']}"
            if col.get('not_null'):
                col_def += " NOT NULL"
            if col.get('default'):
                col_def += f" DEFAULT {col['default']}"
            if col.get('auto_increment'):
                col_def += " AUTO_INCREMENT"
            if col.get('primary_key'):
                col_def += " PRIMARY KEY"
            column_defs.append(col_def)
        
        create_table_sql = f"CREATE TABLE {table_name} ({', '.join(column_defs)})"
        cursor.execute(create_table_sql)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Table {table_name} created/modified successfully")
        return {"success": True, "message": f"Table {table_name} created/modified successfully"}
    except Error as e:
        logger.error(f"Error creating/modifying table: {e}")
        return {"success": False, "error": str(e)}

def execute_query(query):
    """Execute a SELECT query"""
    if not db_config:
        return {"success": False, "error": "Database not connected"}
    
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        logger.info(f"Query executed successfully: {query}")
        return {"success": True, "results": results}
    except Error as e:
        logger.error(f"Error executing query: {e}")
        return {"success": False, "error": str(e)}

def execute_command(query):
    """Execute INSERT, UPDATE, or DELETE queries"""
    if not db_config:
        return {"success": False, "error": "Database not connected"}
    
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute(query)
        affected_rows = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Command executed successfully: {query}")
        return {"success": True, "affected_rows": affected_rows}
    except Error as e:
        logger.error(f"Error executing command: {e}")
        return {"success": False, "error": str(e)}

def list_tables():
    """List all tables in the database"""
    if not db_config:
        return {"success": False, "error": "Database not connected"}
    
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor.fetchall()]
        cursor.close()
        conn.close()
        
        logger.info("Tables listed successfully")
        return {"success": True, "tables": tables}
    except Error as e:
        logger.error(f"Error listing tables: {e}")
        return {"success": False, "error": str(e)}

def describe_table(table_name):
    """Get the structure of a table"""
    if not db_config:
        return {"success": False, "error": "Database not connected"}
    
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute(f"DESCRIBE {table_name}")
        columns = cursor.fetchall()
        cursor.close()
        conn.close()
        
        logger.info(f"Table {table_name} described successfully")
        return {"success": True, "columns": columns}
    except Error as e:
        logger.error(f"Error describing table: {e}")
        return {"success": False, "error": str(e)}

def handle_request(request):
    """Handle incoming MCP requests"""
    global last_activity_time
    last_activity_time = time.time()
    
    try:
        # Handle initialization request
        if request.get("method") == "initialize":
            logger.info("Received initialization request")
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "capabilities": {
                        "textDocumentSync": 1,
                        "hoverProvider": True,
                        "completionProvider": {
                            "resolveProvider": True,
                            "triggerCharacters": ["."]
                        }
                    },
                    "serverInfo": {
                        "name": "mysql-aqara",
                        "version": "1.0.0"
                    }
                }
            }
        
        elif request.get("method") == "getServerInfo":
            logger.info("Received getServerInfo request")
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "name": "mysql-aqara",
                    "version": "1.0.0",
                    "tools": [
                        {
                            "name": "connect_db",
                            "description": "Connect to MySQL database",
                            "parameters": {
                                "host": {"type": "string", "description": "Database host"},
                                "user": {"type": "string", "description": "Database user"},
                                "password": {"type": "string", "description": "Database password"},
                                "database": {"type": "string", "description": "Database name"}
                            }
                        },
                        {
                            "name": "create_or_modify_table",
                            "description": "Create or modify a table",
                            "parameters": {
                                "table_name": {"type": "string", "description": "Name of the table"},
                                "columns": {"type": "array", "description": "Array of column definitions"}
                            }
                        },
                        {
                            "name": "execute_query",
                            "description": "Execute a SELECT query",
                            "parameters": {
                                "query": {"type": "string", "description": "SQL query string"}
                            }
                        },
                        {
                            "name": "execute_command",
                            "description": "Execute INSERT, UPDATE, or DELETE queries",
                            "parameters": {
                                "query": {"type": "string", "description": "SQL command string"}
                            }
                        },
                        {
                            "name": "list_tables",
                            "description": "List all tables in the database"
                        },
                        {
                            "name": "describe_table",
                            "description": "Get the structure of a table",
                            "parameters": {
                                "table_name": {"type": "string", "description": "Name of the table"}
                            }
                        }
                    ]
                }
            }
        
        elif request.get("method") == "executeTool":
            tool_name = request["params"].get("name")
            tool_params = request["params"].get("parameters", {})
            
            logger.info(f"Executing tool: {tool_name}")
            
            if tool_name == "connect_db":
                result = connect_db(**tool_params)
            elif tool_name == "create_or_modify_table":
                result = create_or_modify_table(**tool_params)
            elif tool_name == "execute_query":
                result = execute_query(**tool_params)
            elif tool_name == "execute_command":
                result = execute_command(**tool_params)
            elif tool_name == "list_tables":
                result = list_tables()
            elif tool_name == "describe_table":
                result = describe_table(**tool_params)
            else:
                logger.error(f"Unknown tool requested: {tool_name}")
                return {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {tool_name}"
                    }
                }
            
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": result
            }
        
        else:
            logger.error(f"Unknown method requested: {request.get('method')}")
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {request.get('method')}"
                }
            }
    
    except Exception as e:
        logger.error(f"Error handling request: {e}", exc_info=True)
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        }

def main():
    """Main function to handle MCP server operations"""
    logger.info("Initializing server...")
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Main loop
    while True:
        try:
            # Read request from stdin
            line = sys.stdin.readline()
            if not line:
                logger.info("No more input, shutting down...")
                break
            
            # Parse request
            try:
                request = json.loads(line)
                logger.debug(f"Received request: {request}")
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON: {e}")
                print(json.dumps({
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32700,
                        "message": "Parse error"
                    }
                }), flush=True)
                continue
            
            # Handle request
            response = handle_request(request)
            
            # Send response
            print(json.dumps(response), flush=True)
            logger.debug(f"Sent response: {response}")
            
            # Check for timeout
            if check_timeout():
                logger.warning("Connection timeout detected, sending keep-alive")
                send_keep_alive()
            
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
            print(json.dumps({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }), flush=True)
            continue
    
    logger.info("Server shutting down...")
    cleanup()

if __name__ == "__main__":
    main() 