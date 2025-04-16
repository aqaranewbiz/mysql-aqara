import json
import sys
import os
import signal
import time
import mysql.connector
from mysql.connector import Error
import logging
import traceback
from datetime import datetime
import threading
import platform

# Print startup message to stderr
sys.stderr.write(f"""
=== MCP MySQL Server Debugging Information ===
Python version: {platform.python_version()}
Platform: {platform.platform()}
Current directory: {os.getcwd()}
Executable path: {sys.executable}
Arguments: {sys.argv}
Environment:
  PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}
  PYTHONUNBUFFERED: {os.environ.get('PYTHONUNBUFFERED', 'Not set')}
  DOCKER: {os.environ.get('DOCKER', 'Not set')}
  DB_HOST: {os.environ.get('DB_HOST', 'Not set')}
  DB_USER: {os.environ.get('DB_USER', 'Not set')}
  DB_DATABASE: {os.environ.get('DB_DATABASE', 'Not set')}
=================================================
""")
sys.stderr.flush()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if os.environ.get('DEBUG') else logging.INFO,
    format='%(asctime)s [%(name)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S.%fZ'
)
logger = logging.getLogger('mysql-aqara')

# Add stderr handler for improved Docker logging
stderr_handler = logging.StreamHandler(sys.stderr)
stderr_handler.setFormatter(logging.Formatter('%(asctime)s [%(name)s] [%(levelname)s] %(message)s'))
logger.addHandler(stderr_handler)

# Global variables
db_config = None
db_connection = None
last_activity_time = time.time()
KEEP_ALIVE_INTERVAL = 10  # seconds, reduced from 30
TIMEOUT = 300  # seconds
running = True
initialized = False

# Check for environment variables
if all(k in os.environ for k in ['DB_HOST', 'DB_USER', 'DB_PASSWORD', 'DB_DATABASE']):
    logger.info("Found database connection parameters in environment variables")
    db_config = {
        'host': os.environ['DB_HOST'],
        'user': os.environ['DB_USER'],
        'password': os.environ['DB_PASSWORD'],
        'database': os.environ['DB_DATABASE'],
        'charset': 'utf8mb4',
        'collation': 'utf8mb4_general_ci'
    }
    logger.info(f"Using database: {db_config['host']}/{db_config['database']} as {db_config['user']}")

# Log startup information
logger.info(f"MCP Server starting up. Python version: {platform.python_version()}")
logger.info(f"Current working directory: {os.getcwd()}")
logger.info(f"Script path: {os.path.abspath(__file__)}")

def signal_handler(signum, frame):
    """Handle termination signals"""
    global running
    logger.info(f"Received termination signal {signum}, cleaning up...")
    running = False
    cleanup()
    sys.exit(0)

def cleanup():
    """Cleanup resources before exit"""
    global db_connection
    logger.debug("Performing cleanup...")
    if db_connection:
        try:
            db_connection.close()
            logger.info("Database connection closed")
        except Error as e:
            logger.error(f"Error closing database connection: {e}")
    logger.info("Cleanup completed")

def keep_alive_thread():
    """Background thread to send keep-alive messages"""
    global running, last_activity_time
    logger.info("Keep alive thread started")
    
    while running:
        try:
            current_time = time.time()
            elapsed = current_time - last_activity_time
            
            if elapsed > KEEP_ALIVE_INTERVAL:
                logger.info(f"Sending keep-alive after {elapsed:.1f}s of inactivity")
                send_keep_alive()
                
            time.sleep(1)
        except Exception as e:
            logger.error(f"Error in keep-alive thread: {e}", exc_info=True)

def send_keep_alive():
    """Send keep-alive message to prevent timeout"""
    global last_activity_time
    last_activity_time = time.time()
    
    try:
        response = {
            "jsonrpc": "2.0",
            "method": "$/alive",
            "params": {"timestamp": datetime.utcnow().isoformat()}
        }
        print(json.dumps(response), flush=True)
        sys.stderr.write("Keep-alive sent\n")
        sys.stderr.flush()
    except Exception as e:
        logger.error(f"Error sending keep-alive: {e}", exc_info=True)

def connect_db(host, user, password, database):
    """Establish a connection to the MySQL database"""
    global db_config, db_connection
    try:
        logger.info(f"Connecting to database at {host}/{database} as {user}")
        db_config = {
            'host': host,
            'user': user,
            'password': '********',  # Masked for logging
            'database': database,
            'charset': 'utf8mb4',
            'collation': 'utf8mb4_general_ci'
        }
        
        # Create the actual config with real password
        real_config = db_config.copy()
        real_config['password'] = password
        
        # Test the connection
        logger.debug("Testing database connection...")
        test_conn = mysql.connector.connect(**real_config)
        test_conn.close()
        
        # Save the config with real password for future use
        db_config = real_config
        
        logger.info("Database connection established successfully")
        return {"success": True, "message": "Connected to database successfully"}
    except Error as e:
        error_details = str(e)
        logger.error(f"Database connection error: {error_details}", exc_info=True)
        return {"success": False, "error": error_details}
    except Exception as e:
        logger.error(f"Unexpected error connecting to database: {str(e)}", exc_info=True)
        return {"success": False, "error": f"Unexpected error: {str(e)}"}

def create_or_modify_table(table_name, columns, unique_keys=None):
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
        
        # Add unique keys if provided
        if unique_keys:
            for key in unique_keys:
                column_defs.append(f"UNIQUE KEY {key['name']} ({key['columns']})")
        
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

def execute_query(sql, params=None):
    """Execute a SELECT query"""
    if not db_config:
        return {"success": False, "error": "Database not connected"}
    
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
            
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        logger.info(f"Query executed successfully: {sql}")
        return {"success": True, "results": results}
    except Error as e:
        logger.error(f"Error executing query: {e}")
        return {"success": False, "error": str(e)}

def execute_command(sql, params=None):
    """Execute INSERT, UPDATE, or DELETE queries"""
    if not db_config:
        return {"success": False, "error": "Database not connected"}
    
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
            
        affected_rows = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Command executed successfully: {sql}")
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
    global last_activity_time, initialized
    last_activity_time = time.time()
    
    try:
        if not isinstance(request, dict):
            try:
                request = json.loads(request)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON request: {e}")
                sys.stderr.write(f"Invalid JSON request: {request}\n")
                sys.stderr.flush()
                return
        
        method = request.get('method')
        params = request.get('params', {})
        request_id = request.get('id')
        
        logger.info(f"Received request: method={method}, id={request_id}")
        sys.stderr.write(f"Received request: method={method}, id={request_id}\n")
        sys.stderr.flush()
        
        # Handle initialization request
        if method == "initialize":
            logger.info("Handling initialize request")
            initialized = True
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
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
            print(json.dumps(response), flush=True)
            
            # Also log to stderr for debugging
            sys.stderr.write("Sent initialize response\n")
            sys.stderr.flush()
            return
        
        # Handle initialized notification
        if method == "initialized":
            logger.info("Received initialized notification")
            sys.stderr.write("Received initialized notification\n")
            sys.stderr.flush()
            return
        
        # Handle shutdown request
        if method == "shutdown":
            logger.info("Received shutdown request")
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": None
            }
            print(json.dumps(response), flush=True)
            return
        
        # Handle exit notification
        if method == "exit":
            logger.info("Received exit notification")
            cleanup()
            sys.exit(0)
        
        # Handle tool requests - only if initialized
        if not initialized:
            logger.error("Received tool request before initialization")
            error_response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32002,
                    "message": "Server not initialized"
                }
            }
            print(json.dumps(error_response), flush=True)
            return
            
        tool_name = method
        
        # Map tool names from mcp.json to python functions
        tool_mapping = {
            "connect_db": connect_db,
            "create_or_modify_table": create_or_modify_table,
            "query": execute_query,
            "execute": execute_command,
            "list_tables": list_tables,
            "describe_table": describe_table
        }
        
        if tool_name not in tool_mapping:
            logger.error(f"Unknown tool: {tool_name}")
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {tool_name}"
                }
            }
        else:
            # Execute the tool
            logger.info(f"Executing tool: {tool_name}")
            result = tool_mapping[tool_name](**params)
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }
        
        print(json.dumps(response), flush=True)
        sys.stderr.write(f"Sent response for {tool_name}\n")
        sys.stderr.flush()
        
    except Exception as e:
        logger.error(f"Error handling request: {e}", exc_info=True)
        sys.stderr.write(f"Error handling request: {str(e)}\n")
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
        
        error_response = {
            "jsonrpc": "2.0",
            "id": request.get('id') if isinstance(request, dict) else None,
            "error": {
                "code": -32000,
                "message": str(e)
            }
        }
        print(json.dumps(error_response), flush=True)

def main():
    """Main entry point"""
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Initializing server...")
    sys.stderr.write("Server initializing...\n")
    sys.stderr.flush()
    
    # Connect to database if environment variables are set
    if db_config:
        logger.info("Trying to connect to database with environment variables...")
        try:
            conn = mysql.connector.connect(**db_config)
            conn.close()
            logger.info("Successfully connected to database with environment variables")
        except Error as e:
            logger.error(f"Failed to connect with environment variables: {e}")
            db_config = None
    
    # Start keep-alive thread
    keep_alive = threading.Thread(target=keep_alive_thread)
    keep_alive.daemon = True
    keep_alive.start()
    
    try:
        logger.info("Server started and connected successfully")
        sys.stderr.write("Server started successfully\n")
        sys.stderr.flush()
        
        # Describe available tools
        tools = ["connect_db", "create_or_modify_table", "query", "execute", "list_tables", "describe_table"]
        logger.info(f"Available tools: {', '.join(tools)}")
        
        # Main loop
        while running:
            try:
                line = sys.stdin.readline()
                if not line:
                    logger.info("End of input stream detected")
                    sys.stderr.write("End of input stream detected\n")
                    sys.stderr.flush()
                    break
                
                sys.stderr.write(f"Received data: {line[:50]}...\n")
                sys.stderr.flush()
                    
                request = line.strip()
                handle_request(request)
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON received: {e}")
                sys.stderr.write(f"Invalid JSON: {e}\n")
                sys.stderr.flush()
                continue
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                sys.stderr.write(f"Main loop error: {str(e)}\n")
                traceback.print_exc(file=sys.stderr)
                sys.stderr.flush()
                continue
    
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.stderr.write(f"Server error: {str(e)}\n")
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
    finally:
        cleanup()

if __name__ == "__main__":
    main() 