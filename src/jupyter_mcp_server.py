#!/usr/bin/env python3
"""
Jupyter Notebook MCP Server - MCP server that connects to a Jupyter notebook via WebSockets
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, Any, Optional
import websockets
from mcp.server.fastmcp import FastMCP, Context

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("JupyterMCPServer")

class JupyterWebSocketClient:
    """Client that connects to the Jupyter WebSocket server"""
    
    def __init__(self, host='localhost', port=8765):
        self.host = host
        self.port = port
        self.websocket = None
        self.connected = False
        self.pending_requests = {}
    
    async def connect(self):
        """Connect to the Jupyter WebSocket server"""
        if self.connected:
            return True
            
        try:
            uri = f"ws://{self.host}:{self.port}"
            self.websocket = await websockets.connect(uri)
            
            # Identify as an external client
            await self.websocket.send(json.dumps({"role": "external"}))
            
            # Start listening for messages in the background
            asyncio.create_task(self._listen_for_messages())
            
            self.connected = True
            logger.info(f"Connected to Jupyter WebSocket server at {uri}")
            return True
        except Exception as e:
            logger.error(f"Error connecting to Jupyter WebSocket server: {str(e)}")
            self.connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from the WebSocket server"""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            self.connected = False
    
    async def _listen_for_messages(self):
        """Background task to listen for messages from the WebSocket server"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                
                # Handle different message types
                if data.get("type") == "result":
                    request_id = data.get("request_id")
                    if request_id in self.pending_requests:
                        # Resolve the future with the result
                        future = self.pending_requests.pop(request_id)
                        future.set_result(data)
                elif data.get("type") == "error":
                    # Handle error messages
                    request_id = data.get("request_id")
                    if request_id in self.pending_requests:
                        future = self.pending_requests.pop(request_id)
                        future.set_exception(Exception(data.get("message", "Unknown error")))
                else:
                    logger.warning(f"Received unknown message type: {data.get('type')}")
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed")
            self.connected = False
        except Exception as e:
            logger.error(f"Error in WebSocket listener: {str(e)}")
            self.connected = False
    
    async def execute_code(self, code):
        """Execute code in the Jupyter notebook and get the result"""
        if not self.connected:
            success = await self.connect()
            if not success:
                raise Exception("Could not connect to Jupyter WebSocket server")
        
        # Create a unique request ID
        request_id = f"req_{id(code)}_{asyncio.get_event_loop().time()}"
        
        # Create a future to wait for the result
        future = asyncio.get_event_loop().create_future()
        self.pending_requests[request_id] = future
        
        # Send the execute request
        execute_request = {
            "type": "execute",
            "code": code,
            "request_id": request_id
        }
        
        await self.websocket.send(json.dumps(execute_request))
        
        # Wait for the result with a timeout
        try:
            result = await asyncio.wait_for(future, 60.0)  # 60 second timeout
            return result
        except asyncio.TimeoutError:
            self.pending_requests.pop(request_id, None)
            raise Exception("Execution timed out after 60 seconds")

# Singleton client instance
_jupyter_client: Optional[JupyterWebSocketClient] = None

async def get_jupyter_client(port=None):
    """Get or create the Jupyter WebSocket client"""
    global _jupyter_client
    
    if _jupyter_client is None:
        _jupyter_client = JupyterWebSocketClient(port=port or 8765)
        await _jupyter_client.connect()
    elif not _jupyter_client.connected:
        # Update port if specified and different
        if port is not None and port != _jupyter_client.port:
            _jupyter_client.port = port
        await _jupyter_client.connect()
    
    return _jupyter_client

@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    """Manage server startup and shutdown lifecycle"""
    try:
        logger.info("JupyterMCPServer starting up")
        
        # Try to connect to Jupyter WebSocket server on startup
        try:
            _ = await get_jupyter_client()
            logger.info("Successfully connected to Jupyter WebSocket server on startup")
        except Exception as e:
            logger.warning(f"Could not connect to Jupyter WebSocket server on startup: {str(e)}")
            logger.warning("Make sure the Jupyter notebook with WebSocket server is running")
        
        yield {}
    finally:
        # Clean up the client on shutdown
        global _jupyter_client
        if _jupyter_client:
            logger.info("Disconnecting from Jupyter WebSocket server on shutdown")
            await _jupyter_client.disconnect()
            _jupyter_client = None
        logger.info("JupyterMCPServer shut down")

# Create the MCP server
mcp = FastMCP(
    "jupyter_mcp",
    description="Jupyter Notebook integration through the Model Context Protocol",
    lifespan=server_lifespan
)

@mcp.tool()
async def ping(ctx: Context) -> str:
    """Simple ping command to check server connectivity"""
    try:
        _ = await get_jupyter_client()
        return json.dumps({"status": "success", "message": "Connected to Jupyter WebSocket server"})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@mcp.tool()
async def execute_notebook_code(ctx: Context, code: str) -> str:
    """Execute code in the Jupyter notebook and return the result"""
    try:
        client = await get_jupyter_client()
        result = await client.execute_code(code)
        
        # Format the output for display
        output_data = result.get("output", [])
        formatted_output = []
        
        for output in output_data:
            output_type = output.get("output_type")
            
            if output_type == "stream":
                # Text output
                formatted_output.append({
                    "type": "text",
                    "content": output.get("text", "")
                })
            elif output_type == "execute_result" or output_type == "display_data":
                # Result data - could be text, HTML, image, etc.
                data = output.get("data", {})
                if "text/html" in data:
                    formatted_output.append({
                        "type": "html",
                        "content": data["text/html"]
                    })
                elif "image/png" in data:
                    formatted_output.append({
                        "type": "image",
                        "format": "png",
                        "data": data["image/png"]
                    })
                elif "text/plain" in data:
                    formatted_output.append({
                        "type": "text",
                        "content": data["text/plain"]
                    })
            elif output_type == "error":
                # Error output
                formatted_output.append({
                    "type": "error",
                    "ename": output.get("ename", "Error"),
                    "evalue": output.get("evalue", ""),
                    "traceback": output.get("traceback", [])
                })
        
        return json.dumps({
            "status": "success",
            "cell_id": result.get("cell_id"),
            "output": formatted_output
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": str(e)
        }, indent=2)

@mcp.tool()
async def get_notebook_info(ctx: Context) -> str:
    """Get information about the current Jupyter notebook"""
    code = """
import json
from IPython import get_ipython
from IPython.display import display, JSON

# Get notebook path
try:
    notebook_path = get_ipython().kernel.session.config.get('IPKernelApp', {}).get('connection_file', '')
except:
    notebook_path = "Unknown"

# Get kernel info
kernel_info = get_ipython().kernel.shell.user_ns.get('_dh', ['Unknown'])

# Get Python version info
import sys
python_info = {
    "version": sys.version,
    "executable": sys.executable,
    "platform": sys.platform
}

# Get installed packages
import pkg_resources
installed_packages = [{"name": d.project_name, "version": d.version} 
                    for d in pkg_resources.working_set]

# Output as JSON
notebook_info = {
    "notebook_path": notebook_path,
    "kernel_info": kernel_info,
    "python_info": python_info,
    "installed_packages": installed_packages[:20]  # Limit to first 20 packages
}

notebook_info
"""
    
    try:
        client = await get_jupyter_client()
        result = await client.execute_code(code)
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": str(e)
        }, indent=2)

def main():
    """Run the MCP server"""
    import os
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Jupyter MCP Server")
    parser.add_argument("--port", type=int, default=int(os.environ.get("JUPYTER_MCP_PORT", 5000)),
                        help="Port to run the MCP server on")
    parser.add_argument("--ws-port", type=int, default=8765,
                        help="Port of the WebSocket server running in Jupyter")
    args = parser.parse_args()
    
    # Update the WebSocket client port
    global _jupyter_client
    if _jupyter_client:
        _jupyter_client.port = args.ws_port
    else:
        _jupyter_client = JupyterWebSocketClient(port=args.ws_port)
    
    logger.info(f"Starting Jupyter MCP server on port {args.port}")
    logger.info(f"Connecting to Jupyter WebSocket server on port {args.ws_port}")
    mcp.run()

if __name__ == "__main__":
    main()
