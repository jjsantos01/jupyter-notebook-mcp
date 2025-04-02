"""
Jupyter Notebook MCP Client - Setup code to run in a Jupyter notebook cell
to enable MCP integration with LLMs
"""

import asyncio
import nest_asyncio
import json
import os
from IPython.display import display, HTML

# Apply nest_asyncio to allow async code in IPython
nest_asyncio.apply()

# WebSocket server setup for Jupyter integration
def setup_jupyter_mcp_integration(ws_port=8765, max_port_attempts=10):
    """
    Set up the Jupyter notebook to work with MCP by:
    1. Starting a WebSocket server in the notebook
    2. Injecting client-side JavaScript to handle WebSocket connections
    3. Providing instructions for connecting the MCP server
    
    Args:
        ws_port: Port for the WebSocket server (default: 8765)
        max_port_attempts: Maximum number of alternative ports to try if the specified port is busy
    """
    
    # WebSocket server implementation
    async def ws_handler(websocket):
        """Handle WebSocket connections from clients"""
        global notebook_client, external_clients
        
        try:
            # Initial message to identify client type
            init_msg = await websocket.recv()
            init_data = json.loads(init_msg)
            client_role = init_data.get("role")
            
            if client_role == "notebook":
                notebook_client = websocket
                print("Jupyter client connected")
            else:
                external_clients.add(websocket)
                print("External client connected (likely MCP server)")
            
            async for message in websocket:
                data = json.loads(message)
                
                # Route message based on explicit target field
                target = data.get("target", "all")
                
                # Add source information to outgoing messages if not already present
                if "source" not in data:
                    data["source"] = client_role
                
                if target == "notebook" and notebook_client:
                    await notebook_client.send(json.dumps(data))
                elif target == "external":
                    for client in external_clients:
                        if client != websocket:
                            await client.send(json.dumps(data))
                elif target == "all":
                    # Broadcast to all connected clients
                    for client in list(external_clients) + ([notebook_client] if notebook_client else []):
                        if client != websocket:
                            await client.send(json.dumps(data))
                elif target == "server":
                    # Message meant for the server itself, handle internally
                    pass
                else:
                    print(f"Unknown target: {target}")
        
        except Exception as e:
            print(f"WebSocket error: {str(e)}")
        
        finally:
            # Clean up when connection is closed
            if websocket == notebook_client:
                notebook_client = None
                print("Notebook Client disconnected")
            elif websocket in external_clients:
                external_clients.remove(websocket)
                print("External Client disconnected")
    
    # Start WebSocket server
    async def start_server(port, max_attempts=max_port_attempts):
        """Start the WebSocket server"""
        import websockets
        
        # Try the specified port and incremental alternatives if busy
        attempt = 0
        current_port = port
        last_error = None
        
        while attempt < max_attempts:
            try:
                server = await websockets.serve(ws_handler, "localhost", current_port)
                print(f"WebSocket server started on ws://localhost:{current_port}")
                return server, current_port
            except OSError as e:
                # Port is likely in use
                if e.errno == 10048 or e.errno == 98:  # Windows or Linux error code for address in use
                    print(f"Port {current_port} is busy, trying next port...")
                    current_port += 1
                    attempt += 1
                    last_error = e
                else:
                    # Different error, raise it
                    raise
        
        # If we get here, we've exhausted our attempts
        raise OSError(f"Could not bind to any port after {max_attempts} attempts. Last error: {str(last_error)}")
    
    # Read the client.js file
    client_js_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "client.js")
    try:
        with open(client_js_path, "r") as f:
            client_js_content = f.read()
        
        # Format with port placeholder
        client_js = f"""
        <script>
        {client_js_content}
        </script>
        """.replace("ws://localhost:%s", f"ws://localhost:{ws_port}")
        print(f"Loaded client.js from {client_js_path}")
    except FileNotFoundError:
        print(f"Warning: client.js not found at {client_js_path}")
        print("Please ensure client.js is in the same directory as this script")
        raise
    
    # Initialize global variables
    global notebook_client, external_clients
    notebook_client = None
    external_clients = set()
    
    # Start the WebSocket server
    loop = asyncio.get_event_loop()
    server, actual_port = loop.run_until_complete(start_server(ws_port))
    
    # Update client_js with the actual port that was used
    actual_client_js = client_js.replace(f"ws://localhost:{ws_port}", f"ws://localhost:{actual_port}")
    
    # Add JavaScript to establish WebSocket connection in notebook
    display(HTML(actual_client_js))
    
    # Display setup instructions
    display(HTML(f"""
    <div style="background-color: #f0f0f0; padding: 10px; border-radius: 5px; margin: 10px 0;">
        <h3>Jupyter MCP Integration Setup Complete</h3>
        <p>WebSocket server is running on port {actual_port}</p>
    </div>
    """))
    
    return server, actual_port

# Execute the setup function if run directly
if __name__ == "__main__":
    setup_jupyter_mcp_integration()