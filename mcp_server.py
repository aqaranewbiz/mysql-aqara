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
  DB_HOST: {os.environ.get('DB_HOST', 'Not set')}
  DB_USER: {os.environ.get('DB_USER', 'Not set')}
  DB_PASSWORD: {os.environ.get('DB_PASSWORD', 'Not set (length masked)' if os.environ.get('DB_PASSWORD') else 'Not set')}
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
if all(k in os.environ for k in ['DB_HOST', 'DB_USER', 'DB_PASSWORD']):
    logger.info("Found database connection parameters in environment variables")
    db_config = {
        'host': os.environ['DB_HOST'],
        'user': os.environ['DB_USER'],
        'password': os.environ['DB_PASSWORD'],
        'database': os.environ.get('DB_DATABASE', ''),  # Database is optional
        'charset': 'utf8mb4',
        'collation': 'utf8mb4_general_ci'
    }
    logger.info(f"Using database: {db_config['host']}/{db_config['database'] or 'None'} as {db_config['user']}")
    # Try to auto-connect if environment variables are set
    try:
        if db_config['database']:  # Only if database name is provided
            conn = mysql.connector.connect(**db_config)
            db_connection = conn
            logger.info("Auto-connected to database using environment variables")
    except Error as e:
        logger.error(f"Failed to auto-connect to database: {e}")
        db_connection = None

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

def connect_db(host, user, password, database=""):
    """Establish a connection to the MySQL database"""
    global db_config, db_connection
    try:
        logger.info(f"Connecting to database at {host}/{database} as {user}")
        db_config = {
            'host': host,
            'user': user,
            'password': password,
            'database': database,
            'charset': 'utf8mb4',
            'collation': 'utf8mb4_general_ci'
        }
        
        # Test the connection
        logger.debug("Testing database connection...")
        
        # Create connection with database if specified
        if database:
            test_conn = mysql.connector.connect(**db_config)
        else:
            # Connect without database
            config_without_db = db_config.copy()
            del config_without_db['database']
            test_conn = mysql.connector.connect(**config_without_db)
        
        # Save the connection
        db_connection = test_conn
        
        logger.info("Database connection established successfully")
        return {"success": True, "message": "Connected to database successfully"}
    except Error as e:
        error_details = str(e)
        logger.error(f"Database connection error: {error_details}", exc_info=True)
        return {"success": False, "error": error_details}
    except Exception as e:
        logger.error(f"Unexpected error connecting to database: {str(e)}", exc_info=True)
        return {"success": False, "error": f"Unexpected error: {str(e)}"}

def create_or_modify_table(query, bind_vars=None):
    """Create or modify a table with raw SQL"""
    global db_connection
    
    if not db_connection:
        error_msg = "Database not connected. Use connect_db first."
        logger.error(error_msg)
        return {"success": False, "error": error_msg}
    
    try:
        cursor = db_connection.cursor()
        
        if bind_vars:
            cursor.execute(query, bind_vars)
        else:
            cursor.execute(query)
            
        db_connection.commit()
        cursor.close()
        
        logger.info(f"Table creation/modification query executed successfully")
        return {"success": True, "message": "Query executed successfully"}
    except Error as e:
        logger.error(f"Error creating/modifying table: {e}")
        return {"success": False, "error": str(e)}

def execute_query(query, bind_vars=None):
    """Execute a SELECT query"""
    global db_connection
    
    if not db_connection:
        error_msg = "Database not connected. Use connect_db first."
        logger.error(error_msg)
        return {"success": False, "error": error_msg}
    
    try:
        cursor = db_connection.cursor(dictionary=True)
        
        if bind_vars:
            cursor.execute(query, bind_vars)
        else:
            cursor.execute(query)
            
        results = cursor.fetchall()
        cursor.close()
        
        logger.info(f"Query executed successfully: {query}")
        return {"success": True, "results": results}
    except Error as e:
        logger.error(f"Error executing query: {e}")
        return {"success": False, "error": str(e)}

def execute_command(query, bind_vars=None):
    """Execute INSERT, UPDATE, or DELETE queries"""
    global db_connection
    
    if not db_connection:
        error_msg = "Database not connected. Use connect_db first."
        logger.error(error_msg)
        return {"success": False, "error": error_msg}
    
    try:
        cursor = db_connection.cursor()
        
        if bind_vars:
            cursor.execute(query, bind_vars)
        else:
            cursor.execute(query)
            
        affected_rows = cursor.rowcount
        db_connection.commit()
        cursor.close()
        
        logger.info(f"Command executed successfully: {query} (Affected rows: {affected_rows})")
        return {"success": True, "affected_rows": affected_rows}
    except Error as e:
        logger.error(f"Error executing command: {e}")
        return {"success": False, "error": str(e)}

def list_tables():
    """List all tables in the connected database"""
    global db_connection
    
    if not db_connection:
        error_msg = "Database not connected. Use connect_db first."
        logger.error(error_msg)
        return {"success": False, "error": error_msg}
    
    try:
        cursor = db_connection.cursor()
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor.fetchall()]
        cursor.close()
        
        logger.info(f"Retrieved {len(tables)} tables from database")
        return {"success": True, "tables": tables}
    except Error as e:
        logger.error(f"Error listing tables: {e}")
        return {"success": False, "error": str(e)}

def describe_table(table_name):
    """Get the structure of a table"""
    global db_connection
    
    if not db_connection:
        error_msg = "Database not connected. Use connect_db first."
        logger.error(error_msg)
        return {"success": False, "error": error_msg}
    
    try:
        cursor = db_connection.cursor(dictionary=True)
        cursor.execute(f"DESCRIBE {table_name}")
        structure = cursor.fetchall()
        cursor.close()
        
        logger.info(f"Retrieved structure for table {table_name}")
        return {"success": True, "structure": structure}
    except Error as e:
        logger.error(f"Error describing table {table_name}: {e}")
        return {"success": False, "error": str(e)}

def handle_request(request):
    """Handle incoming JSON-RPC requests"""
    global last_activity_time, initialized
    
    # Update last activity time to prevent timeout
    last_activity_time = time.time()
    
    try:
        # Parse JSON request
        parsed_request = json.loads(request)
        request_id = parsed_request.get('id')
        method = parsed_request.get('method')
        params = parsed_request.get('params', {})
        
        logger.info(f"Received request: method={method}, id={request_id}")
        
        # Handle initialization request
        if method == 'initialize':
            logger.info("Processing initialize request")
            initialized = True
            
            # Return server capabilities
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'result': {
                    'capabilities': {
                        'textDocumentSync': 1,
                        'completionProvider': {
                            'resolveProvider': True,
                            'triggerCharacters': ['.']
                        },
                        'hoverProvider': True
                    },
                    'serverInfo': {
                        'name': 'mysql-aqara',
                        'version': '1.0.0'
                    }
                }
            }
            
        # Handle shutdown request
        elif method == 'shutdown':
            logger.info("Processing shutdown request")
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'result': None
            }
            
        # Handle exit notification
        elif method == 'exit':
            logger.info("Received exit notification, shutting down...")
            cleanup()
            sys.exit(0)
            
        # Handle MCP/listTools request
        elif method == 'MCP/listTools':
            logger.info("Processing MCP/listTools request")
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'result': {
                    'tools': {
                        'connect_db': {
                            'description': 'Connect to a MySQL database',
                            'parameters': {
                                'properties': {
                                    'host': {
                                        'type': 'string',
                                        'description': 'Database host',
                                        'default': 'localhost'
                                    },
                                    'user': {
                                        'type': 'string',
                                        'description': 'Database username'
                                    },
                                    'password': {
                                        'type': 'string',
                                        'description': 'Database password',
                                        'format': 'password'
                                    },
                                    'database': {
                                        'type': 'string',
                                        'description': 'Database name (optional)'
                                    }
                                },
                                'required': ['host', 'user', 'password']
                            }
                        },
                        'create_or_modify_table': {
                            'description': 'Create a new table or modify an existing table schema',
                            'parameters': {
                                'properties': {
                                    'query': {
                                        'type': 'string',
                                        'description': 'CREATE TABLE or ALTER TABLE SQL query'
                                    },
                                    'bind_vars': {
                                        'type': 'object',
                                        'description': 'Optional bind variables for parameterized queries'
                                    }
                                },
                                'required': ['query']
                            }
                        },
                        'query': {
                            'description': 'Execute a SELECT query',
                            'parameters': {
                                'properties': {
                                    'query': {
                                        'type': 'string',
                                        'description': 'SELECT SQL query'
                                    },
                                    'bind_vars': {
                                        'type': 'object',
                                        'description': 'Optional bind variables for parameterized queries'
                                    }
                                },
                                'required': ['query']
                            }
                        },
                        'execute': {
                            'description': 'Execute INSERT, UPDATE, or DELETE query',
                            'parameters': {
                                'properties': {
                                    'query': {
                                        'type': 'string',
                                        'description': 'SQL query (INSERT, UPDATE, DELETE)'
                                    },
                                    'bind_vars': {
                                        'type': 'object',
                                        'description': 'Optional bind variables for parameterized queries'
                                    }
                                },
                                'required': ['query']
                            }
                        },
                        'list_tables': {
                            'description': 'List all tables in the connected database',
                            'parameters': {
                                'properties': {}
                            }
                        },
                        'describe_table': {
                            'description': 'Get the structure of a table',
                            'parameters': {
                                'properties': {
                                    'table_name': {
                                        'type': 'string',
                                        'description': 'Name of the table to describe'
                                    }
                                },
                                'required': ['table_name']
                            }
                        }
                    }
                }
            }
            
        # Handle MCP/callTool request
        elif method == 'MCP/callTool':
            logger.info(f"Processing MCP/callTool request: {params}")
            
            tool_name = params.get('tool')
            tool_params = params.get('parameters', {})
            
            # Execute the appropriate tool based on name
            result = None
            if tool_name == 'connect_db':
                result = connect_db(
                    host=tool_params.get('host', 'localhost'),
                    user=tool_params.get('user', ''),
                    password=tool_params.get('password', ''),
                    database=tool_params.get('database', '')
                )
            elif tool_name == 'create_or_modify_table':
                result = create_or_modify_table(
                    query=tool_params.get('query', ''),
                    bind_vars=tool_params.get('bind_vars')
                )
            elif tool_name == 'query':
                result = execute_query(
                    query=tool_params.get('query', ''),
                    bind_vars=tool_params.get('bind_vars')
                )
            elif tool_name == 'execute':
                result = execute_command(
                    query=tool_params.get('query', ''),
                    bind_vars=tool_params.get('bind_vars')
                )
            elif tool_name == 'list_tables':
                result = list_tables()
            elif tool_name == 'describe_table':
                result = describe_table(
                    table_name=tool_params.get('table_name', '')
                )
            else:
                error_msg = f"Unknown tool: {tool_name}"
                logger.error(error_msg)
                return {
                    'jsonrpc': '2.0',
                    'id': request_id,
                    'error': {
                        'code': -32601,
                        'message': error_msg
                    }
                }
            
            logger.info(f"Tool {tool_name} execution completed with success={result.get('success', False)}")
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'result': result
            }
            
        # Handle unknown method
        else:
            error_msg = f"Unknown method: {method}"
            logger.error(error_msg)
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'error': {
                    'code': -32601,
                    'message': error_msg
                }
            }
            
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {e}", exc_info=True)
        return {
            'jsonrpc': '2.0',
            'id': None,
            'error': {
                'code': -32700,
                'message': f"Parse error: {str(e)}"
            }
        }
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return {
            'jsonrpc': '2.0',
            'id': request_id if 'request_id' in locals() else None,
            'error': {
                'code': -32603,
                'message': f"Internal error: {str(e)}"
            }
        }

def main():
    """Main function to run the server"""
    global running
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start keep-alive thread
    keep_alive_thread = threading.Thread(target=keep_alive_thread, daemon=True)
    keep_alive_thread.start()
    
    # Print startup message
    logger.info("MySQL MCP server started, waiting for messages...")
    
    # Main loop to read requests from stdin
    while running:
        try:
            # Read a line from stdin
            request = sys.stdin.readline()
            
            # Check if stdin is closed
            if not request:
                logger.warning("End of input stream detected. Exiting...")
                running = False
                break
                
            # Handle empty lines
            request = request.strip()
            if not request:
                continue
                
            # Process the request
            logger.debug(f"Raw request: {request}")
            response = handle_request(request)
            
            # Send the response
            response_json = json.dumps(response)
            print(response_json, flush=True)
            logger.debug(f"Response sent: {response_json}")
            
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, exiting...")
            running = False
            break
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
            # Try to send an error response
            try:
                error_response = {
                    'jsonrpc': '2.0',
                    'id': None,
                    'error': {
                        'code': -32603,
                        'message': f"Internal error: {str(e)}"
                    }
                }
                print(json.dumps(error_response), flush=True)
            except:
                pass
    
    # Cleanup before exit
    cleanup()

if __name__ == "__main__":
    main() 