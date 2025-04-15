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
            logger.info("Handling initialize request")
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
        
        # Handle tool requests
        tool_name = request.get("params", {}).get("tool")
        params = request.get("params", {}).get("args", {})
        
        if not tool_name:
            logger.error("No tool specified in request")
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32602,
                    "message": "Invalid params: no tool specified"
                }
            }
        
        # Map tool names to functions
        tools = {
            "connect_db": connect_db,
            "create_or_modify_table": create_or_modify_table,
            "execute_query": execute_query,
            "execute_command": execute_command,
            "list_tables": list_tables,
            "describe_table": describe_table
        }
        
        if tool_name not in tools:
            logger.error(f"Unknown tool: {tool_name}")
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {tool_name}"
                }
            }
        
        # Execute the tool
        result = tools[tool_name](**params)
        
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Error handling request: {str(e)}", exc_info=True)
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        }

def main():
    """Main entry point"""
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("MySQL MCP Server starting...")
    
    # Keep-alive timer
    last_keep_alive = time.time()
    
    try:
        while True:
            # Check for timeout
            if check_timeout():
                logger.warning("Connection timed out, exiting...")
                break
            
            # Send keep-alive if needed
            current_time = time.time()
            if current_time - last_keep_alive >= KEEP_ALIVE_INTERVAL:
                send_keep_alive()
                last_keep_alive = current_time
            
            # Read request from stdin
            try:
                line = sys.stdin.readline()
                if not line:
                    logger.warning("End of input stream, exiting...")
                    break
                
                request = json.loads(line)
                response = handle_request(request)
                
                # Send response
                print(json.dumps(response), flush=True)
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON received: {e}")
                continue
            except Exception as e:
                logger.error(f"Error processing request: {e}", exc_info=True)
                continue
    
    finally:
        cleanup()

if __name__ == "__main__":
    main() 