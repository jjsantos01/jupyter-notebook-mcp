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
import mcp.types as types

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
                if data.get("type") in [
                    "save_result", "cells_info_result", 
                    "insert_cell_result", "notebook_info_result",
                    "run_cell_result", "run_all_cells_result",
                    "get_cell_text_output_result", "get_cell_image_output_result"
                ]:
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
    
    async def send_request(self, request_type, **kwargs):
        """Send a request to the Jupyter notebook and get the result"""
        if not self.connected:
            success = await self.connect()
            if not success:
                raise Exception("Could not connect to Jupyter WebSocket server")
        
        # Create a unique request ID
        request_id = f"req_{id(request_type)}_{asyncio.get_event_loop().time()}"
        
        # Create a future to wait for the result
        future = asyncio.get_event_loop().create_future()
        self.pending_requests[request_id] = future
        
        # Prepare the request
        request = {
            "type": request_type,
            "request_id": request_id,
            **kwargs
        }
        
        # Send the request
        await self.websocket.send(json.dumps(request))
        
        # Wait for the result with a timeout
        try:
            result = await asyncio.wait_for(future, 60.0)  # 60 second timeout
            return result
        except asyncio.TimeoutError:
            self.pending_requests.pop(request_id, None)
            raise Exception(f"Request {request_type} timed out after 60 seconds")
    
    async def insert_and_execute_cell(self, cell_type="code", position=0, content=""):
        """Insert a cell at the specified position"""
        return await self.send_request(
            "insert_and_execute_cell", 
            cell_type=cell_type, 
            position=position, 
            content=content,
        )
        
    async def save_notebook(self):
        """Save the current notebook"""
        return await self.send_request("save_notebook")
    
    async def get_cells_info(self):
        """Get information about all cells in the notebook"""
        return await self.send_request("get_cells_info")
    
    async def get_notebook_info(self):
        """Get information about the current notebook"""
        return await self.send_request("get_notebook_info")
        
    async def run_all_cells(self):
        """Run all cells in the notebook"""
        return await self.send_request("run_all_cells")

    async def get_cell_text_output(self, index, max_length=1500):
        """Get the output content of a specific cell by its index"""
        return await self.send_request(
            "get_cell_text_output", 
            index=index,
            max_length=max_length
        )
    
    async def get_image_output(self, index):
        """Get the image outputs of a specific cell by its index"""
        return await self.send_request(
            "get_cell_image_output", 
            index=index
        )
    
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
async def insert_and_execute_cell(ctx: Context, cell_type: str = "code", position: int = 1, content: str = "") -> str:
    """Insert a cell at the specified position and execute it. 
    If code cell, it will be executed.
    If markdown cell, it will be rendered.
    
    Args:
        cell_type: The type of cell ('code' or 'markdown')
        position: The position to insert the cell at
        content: The content of the cell
    """
    try:
        client = await get_jupyter_client()
        result = await client.insert_and_execute_cell(cell_type, position, content)
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": str(e)
        }, indent=2)

@mcp.tool()
async def save_notebook(ctx: Context) -> str:
    """Save the current Jupyter notebook"""
    try:
        client = await get_jupyter_client()
        result = await client.save_notebook()
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": str(e)
        }, indent=2)

@mcp.tool()
async def get_cells_info(ctx: Context) -> str:
    """Get information about all cells in the notebook"""
    try:
        client = await get_jupyter_client()
        result = await client.get_cells_info()
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": str(e)
        }, indent=2)

@mcp.tool()
async def get_notebook_info(ctx: Context) -> str:
    """Get information about the current Jupyter notebook"""
    try:
        client = await get_jupyter_client()
        result = await client.get_notebook_info()
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": str(e)
        }, indent=2)

@mcp.tool()
async def run_cell(ctx: Context, index: int) -> str:
    """Run a specific cell by its index
    
    Args:
        index: The index of the cell to run
    """
    try:
        client = await get_jupyter_client()
        result = await client.send_request("run_cell", index=index)
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": str(e)
        }, indent=2)

@mcp.tool()
async def run_all_cells(ctx: Context) -> str:
    """Restart and run all cells in the notebook.
    You need to wait for user approval"""
    try:
        client = await get_jupyter_client()
        result = await client.run_all_cells()
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": str(e)
        }, indent=2)

@mcp.tool()
async def get_cell_text_output(ctx: Context, index: int, max_length: int = 1500) -> str:
    """Get the text output content of a specific code cell by its index
    
    Args:
        index: The index of the cell to get output from
        max_length: Maximum length of text output to return (default: 1500 characters)
    """
    try:
        client = await get_jupyter_client()
        result = await client.send_request("get_cell_text_output", index=index, max_length=max_length)
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": str(e)
        }, indent=2)

@mcp.tool()
async def get_image_output(ctx: Context, index: int) -> list[types.ImageContent]:
    """Get image outputs from a specific cell by its index
    
    Args:
        index: The index of the cell to get images from
    
    Returns:
        A list of images from the cell output
    """
    try:
        client = await get_jupyter_client()
        result = await client.get_image_output(index)
        
        images = []
        if result.get("status") == "success":
            for i, img_data in enumerate(result.get("images", [])):
                try:
                    format_raw = img_data.get("format", "image/png")
                    format_name = format_raw.split("/")[1]
                    mcp_image = types.ImageContent(
                        type="image",
                        data=img_data.get("data", ""),
                        mimeType=f"image/{format_name}",
                    )
                    images.append(mcp_image)
                except Exception as e:
                    logger.error(f"Error processing image {i}: {str(e)}")
        
        return images
    except Exception as e:
        logger.error(f"Error in get_image_output: {e}")
        return []

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
