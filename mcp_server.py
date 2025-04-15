import json
import sys
import os
from typing import Dict, Any, Optional, List
import mysql.connector
from mysql.connector import Error

# Global database configuration
db_config = None

def connect_db(params: Dict[str, Any]) -> Dict[str, Any]:
    """Establish database connection"""
    global db_config
    try:
        # Store the connection parameters
        db_config = {
            'host': params.get('host') or os.getenv('MYSQL_HOST'),
            'user': params.get('user') or os.getenv('MYSQL_USER'),
            'password': params.get('password') or os.getenv('MYSQL_PASSWORD'),
            'database': params.get('database') or os.getenv('MYSQL_DATABASE'),
            'charset': 'utf8mb4',
            'collation': 'utf8mb4_general_ci'
        }
        
        # Test the connection
        conn = mysql.connector.connect(**db_config)
        conn.close()
        
        return {"status": "success", "message": "Database connection established"}
    except Error as e:
        return {"status": "error", "message": str(e)}

def create_or_modify_table(params: Dict[str, Any]) -> Dict[str, Any]:
    """Create or modify a table"""
    if not db_config:
        return {"status": "error", "message": "Database not connected. Please connect first."}
    
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        table_name = params['table_name']
        columns = params['columns']
        unique_keys = params.get('unique_keys', [])
        
        # Drop existing table
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
        
        # Add unique keys
        for key in unique_keys:
            column_defs.append(f"UNIQUE KEY {key['name']} ({key['columns']})")
        
        create_table_sql = f"CREATE TABLE {table_name} ({', '.join(column_defs)})"
        cursor.execute(create_table_sql)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return {"status": "success", "message": f"Table {table_name} created successfully"}
    except Error as e:
        return {"status": "error", "message": str(e)}

def execute_query(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute SELECT query"""
    if not db_config:
        return {"status": "error", "message": "Database not connected. Please connect first."}
    
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        if params.get('params'):
            cursor.execute(params['sql'], params['params'])
        else:
            cursor.execute(params['sql'])
            
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return {"status": "success", "results": results}
    except Error as e:
        return {"status": "error", "message": str(e)}

def execute_command(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute INSERT, UPDATE, or DELETE query"""
    if not db_config:
        return {"status": "error", "message": "Database not connected. Please connect first."}
    
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        if params.get('params'):
            cursor.execute(params['sql'], params['params'])
        else:
            cursor.execute(params['sql'])
            
        conn.commit()
        affected_rows = cursor.rowcount
        cursor.close()
        conn.close()
        
        return {
            "status": "success",
            "affected_rows": affected_rows
        }
    except Error as e:
        return {"status": "error", "message": str(e)}

def list_tables() -> Dict[str, Any]:
    """List all tables in database"""
    if not db_config:
        return {"status": "error", "message": "Database not connected. Please connect first."}
    
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor.fetchall()]
        cursor.close()
        conn.close()
        
        return {"status": "success", "tables": tables}
    except Error as e:
        return {"status": "error", "message": str(e)}

def describe_table(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get table structure"""
    if not db_config:
        return {"status": "error", "message": "Database not connected. Please connect first."}
    
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute(f"DESCRIBE {params['table']}")
        structure = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return {"status": "success", "structure": structure}
    except Error as e:
        return {"status": "error", "message": str(e)}

def handle_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """Handle MCP requests"""
    try:
        request_type = request.get("type")
        request_id = request.get("id")

        if request_type == "getServerInfo":
            return {
                "type": "response",
                "id": request_id,
                "result": {
                    "name": "@aqaranewbiz/mysql-aqaranewbiz",
                    "version": "1.0.0",
                    "tools": {
                        "connect_db": {
                            "description": "Establish connection to MySQL database",
                            "parameters": {
                                "host": {"type": "string"},
                                "user": {"type": "string"},
                                "password": {"type": "string"},
                                "database": {"type": "string"}
                            }
                        },
                        "create_table": {
                            "description": "Create or modify a table",
                            "parameters": {
                                "table_name": {"type": "string"},
                                "columns": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "name": {"type": "string"},
                                            "type": {"type": "string"},
                                            "not_null": {"type": "boolean", "optional": true},
                                            "default": {"type": "string", "optional": true},
                                            "auto_increment": {"type": "boolean", "optional": true},
                                            "primary_key": {"type": "boolean", "optional": true}
                                        }
                                    }
                                },
                                "unique_keys": {
                                    "type": "array",
                                    "optional": true,
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "name": {"type": "string"},
                                            "columns": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        },
                        "query": {
                            "description": "Execute SELECT queries",
                            "parameters": {
                                "sql": {"type": "string"},
                                "params": {"type": "array", "optional": true}
                            }
                        },
                        "execute": {
                            "description": "Execute INSERT, UPDATE, or DELETE queries",
                            "parameters": {
                                "sql": {"type": "string"},
                                "params": {"type": "array", "optional": true}
                            }
                        },
                        "list_tables": {
                            "description": "List all tables in database",
                            "parameters": {}
                        },
                        "describe_table": {
                            "description": "Get table structure",
                            "parameters": {
                                "table": {"type": "string"}
                            }
                        }
                    }
                }
            }
        elif request_type == "executeTool":
            tool_name = request.get("tool")
            params = request.get("params", {})
            
            if tool_name == "connect_db":
                result = connect_db(params)
            elif tool_name == "create_table":
                result = create_or_modify_table(params)
            elif tool_name == "query":
                result = execute_query(params)
            elif tool_name == "execute":
                result = execute_command(params)
            elif tool_name == "list_tables":
                result = list_tables()
            elif tool_name == "describe_table":
                result = describe_table(params)
            else:
                return {
                    "type": "error",
                    "id": request_id,
                    "error": f"Unknown tool: {tool_name}"
                }
            
            if result.get("status") == "error":
                return {
                    "type": "error",
                    "id": request_id,
                    "error": result["message"]
                }
            
            return {
                "type": "response",
                "id": request_id,
                "result": result
            }
        else:
            return {
                "type": "error",
                "id": request_id,
                "error": f"Unknown request type: {request_type}"
            }
    except Exception as e:
        return {
            "type": "error",
            "id": request.get("id"),
            "error": str(e)
        }

def main():
    """Main function to handle stdin/stdout communication"""
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
                
            request = json.loads(line)
            response = handle_request(request)
            
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
            
        except json.JSONDecodeError as e:
            sys.stderr.write(f"Invalid JSON input: {str(e)}\n")
            sys.stderr.flush()
        except Exception as e:
            sys.stderr.write(f"Error: {str(e)}\n")
            sys.stderr.flush()

if __name__ == "__main__":
    main() 