import asyncio
import json
import logging
import websockets
from typing import Optional

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("JupyterWebSocketClient")

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
                try:
                    data = json.loads(message)
                    
                    # Process messages directed to us (external client)
                    request_id = data.get("request_id")
                    if request_id in self.pending_requests:
                        # Resolve the future with the result
                        future = self.pending_requests.pop(request_id)
                        future.set_result(data)
                    elif data.get("type") == "error" and request_id in self.pending_requests:
                        # Handle error messages
                        future = self.pending_requests.pop(request_id)
                        future.set_exception(Exception(data.get("message", "Unknown error")))
                except json.JSONDecodeError as e:
                    logger.error(f"Error decoding JSON from WebSocket: {str(e)}")
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed")
            self.connected = False
            # Reject all pending requests
            for request_id, future in list(self.pending_requests.items()):
                if not future.done():
                    future.set_exception(Exception("WebSocket connection closed"))
            self.pending_requests.clear()
        except Exception as e:
            logger.error(f"Error in WebSocket listener: {str(e)}")
            self.connected = False
            # Reject all pending requests
            for request_id, future in list(self.pending_requests.items()):
                if not future.done():
                    future.set_exception(Exception(f"WebSocket listener error: {str(e)}"))
            self.pending_requests.clear()

    async def send_request(self, request_type, **kwargs):
        """Send a request to the Jupyter notebook and get the result"""
        # First check connection and reconnect if needed
        if not self.connected:
            logger.info("Connection lost, attempting to reconnect...")
            success = await self.connect()
            if not success:
                raise Exception("Could not connect to Jupyter WebSocket server")
        
        # Create a unique request ID
        request_id = f"req_{id(request_type)}_{asyncio.get_event_loop().time()}"
        
        # Create a future to wait for the result
        future = asyncio.get_event_loop().create_future()
        self.pending_requests[request_id] = future
        
        # Prepare the request with explicit direction
        request = {
            "type": request_type,
            "source": "external",
            "target": "notebook",
            "request_id": request_id,
            **kwargs
        }
        
        # Send the request, with retry on connection error
        try:
            await self.websocket.send(json.dumps(request))
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Connection closed when trying to send request, attempting to reconnect...")
            self.connected = False
            success = await self.connect()
            if not success:
                self.pending_requests.pop(request_id, None)
                raise Exception("Connection lost and reconnect failed")
            
            # Try sending again
            try:
                await self.websocket.send(json.dumps(request))
            except Exception as e:
                self.pending_requests.pop(request_id, None)
                raise Exception(f"Failed to send request after reconnect: {str(e)}")
        
        # Wait for the result with a timeout
        try:
            result = await asyncio.wait_for(future, 60.0)  # 60 second timeout
            return result
        except asyncio.TimeoutError:
            self.pending_requests.pop(request_id, None)
            logger.error(f"Request {request_type} timed out after 60 seconds")
            # Connection might be stale, mark as disconnected so next request will reconnect
            self.connected = False
            raise Exception(f"Request {request_type} timed out after 60 seconds")
    
    async def insert_and_execute_cell(
                self,
                cell_type="code",
                position=1,
                content="",
                slideshow_type=None
            ):
        """Insert a cell at the specified position and optionally set slideshow type"""
        result = await self.send_request(
            "insert_and_execute_cell", 
            cell_type=cell_type, 
            position=position, 
            content=content,
        )
        if (result.get("type") != "error") and slideshow_type:
            await self.set_slideshow_type(position, slideshow_type)
        return result
        
    async def save_notebook(self):
        """Save the current notebook"""
        return await self.send_request("save_notebook")
    
    async def get_cells_info(self):
        """Get information about all cells in the notebook"""
        return await self.send_request("get_cells_info")
    
    async def get_notebook_info(self):
        """Get information about the current notebook"""
        return await self.send_request("get_notebook_info")

    async def run_cell(self, index=1):
        """Run a specific cell by its index"""
        return await self.send_request("run_cell", index=index)

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

    async def edit_cell_content(self, index, content, execute=True):
        """Edit the content of a specific cell by its index"""
        return await self.send_request(
            "edit_cell_content", 
            source="external",
            target="notebook",
            index=index,
            content=content,
            execute=execute,
        )
    
    async def set_slideshow_type(self, index, slideshow_type="-"):
        """Set the slideshow type for a specific cell by its index"""
        return await self.send_request(
            "set_slideshow_type", 
            source="external",
            target="notebook",
            index=index,
            slideshow_type=slideshow_type
        )

# Singleton client instance
_jupyter_client: Optional[JupyterWebSocketClient] = None

async def get_jupyter_client(host='localhost', port=8765):
    """Get or create the Jupyter WebSocket client"""
    global _jupyter_client
    
    if _jupyter_client is None:
        _jupyter_client = JupyterWebSocketClient(host=host, port=port)
        await _jupyter_client.connect()
    elif not _jupyter_client.connected:
        if host != _jupyter_client.host or port != _jupyter_client.port:
            _jupyter_client.host = host
            _jupyter_client.port = port
        await _jupyter_client.connect()
    
    return _jupyter_client
