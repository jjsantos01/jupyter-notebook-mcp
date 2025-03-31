#!/usr/bin/env python3
"""
Jupyter Notebook MCP Server - MCP server that connects to a Jupyter notebook via WebSockets
"""

import json
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, Any
from mcp.server.fastmcp import FastMCP, Context
import mcp.types as types
from jupyter_ws_client import get_jupyter_client

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("JupyterMCPServer")

@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    """Manage server startup and shutdown lifecycle"""
    import os
    ws_host = os.environ.get("JUPYTER_WS_HOST", "localhost")
    ws_port = int(os.environ.get("JUPYTER_WS_PORT", "8765"))
    
    try:
        logger.info("JupyterMCPServer starting up")
        
        # Try to connect to Jupyter WebSocket server on startup
        try:
            await get_jupyter_client(host=ws_host, port=ws_port)
            logger.info("Successfully connected to Jupyter WebSocket server on startup")
        except Exception as e:
            logger.warning(f"Could not connect to Jupyter WebSocket server on startup: {str(e)}")
            logger.warning("Make sure the Jupyter notebook with WebSocket server is running")
        
        yield {}
    finally:
        # Clean up the client on shutdown
        client = await get_jupyter_client(host=ws_host, port=ws_port)
        if client:
            logger.info("Disconnecting from Jupyter WebSocket server on shutdown")
            await client.disconnect()
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
async def insert_and_execute_cell(
        ctx: Context, cell_type:
        str = "code",
        position: int = 1,
        content: str = "",
        slideshow_type=None,
    ) -> str:
    """Insert a cell at the specified position and execute it, and optionally set slideshow type.
    If code cell, it will be executed.
    If markdown cell, it will be rendered.
    
    Args:
        cell_type: The type of cell ('code' or 'markdown')
        position: The position to insert the cell at
        content: The content of the cell
        slideshow_type: Optional slideshow type ('slide', 'subslide', 'fragment', 'skip', 'notes')
    """
    try:
        client = await get_jupyter_client()
        result = await client.insert_and_execute_cell(cell_type, position, content, slideshow_type)
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
        result = await client.run_cell(index)
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

@mcp.tool()
async def edit_cell_content(ctx: Context, index: int, content: str, execute: bool = True) -> str:
    """Edit the content of a specific cell by its index and optionally execute it
    
    Args:
        index: The index of the cell to edit
        content: The new content for the cell
        execute: If True and the cell is code, execute after editing and return output
    """
    try:
        client = await get_jupyter_client()
        result = await client.edit_cell_content(
            index=index,
            content=content,
            execute=execute
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": str(e)
        }, indent=2)

@mcp.tool()
async def set_slideshow_type(ctx: Context, index: int, slideshow_type: str = "") -> str:
    """Set the slideshow type for a specific cell by its index
    
    Args:
        index: The index of the cell to modify
        slideshow_type: The slideshow type to set. Valid values are:
                        "slide" - Start a new slide
                        "subslide" - Start a new subslide
                        "fragment" - Fragment (appear on click)
                        "skip" - Skip cell in slideshow
                        "notes" - Speaker notes
                        "-" or null - Remove slideshow type
    """
    try:
        client = await get_jupyter_client()
        result = await client.set_slideshow_type(index=index, slideshow_type=slideshow_type)
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
    
    parser = argparse.ArgumentParser(description="Jupyter MCP Server")
    parser.add_argument("--port", type=int, default=int(os.environ.get("JUPYTER_MCP_PORT", 5000)),
                        help="Port to run the MCP server on")
    parser.add_argument("--ws-host", type=str, default="localhost",
                        help="Host of the WebSocket server running in Jupyter")
    parser.add_argument("--ws-port", type=int, default=8765,
                        help="Port of the WebSocket server running in Jupyter")
    args = parser.parse_args()
    
    # Set environment variables for the lifespan to use
    os.environ["JUPYTER_WS_HOST"] = args.ws_host
    os.environ["JUPYTER_WS_PORT"] = str(args.ws_port)
    
    logger.info(f"Starting Jupyter MCP server on port {args.port}")
    logger.info(f"Connecting to Jupyter WebSocket server at {args.ws_host}:{args.ws_port}")
    
    mcp.run()

if __name__ == "__main__":
    main()
