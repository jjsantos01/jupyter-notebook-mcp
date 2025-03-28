# JupyterMCP - Jupyter Notebook Model Context Protocol Integration

JupyterMCP connects [Jupyter Notebook](https://jupyter.org/) to [Claude AI](https://claude.ai/chat) through the Model Context Protocol (MCP), allowing Claude to directly interact with and control Jupyter Notebooks. This integration enables AI-assisted code execution, data analysis, visualization, and more.

## ⚠️ Compatibility Warning

**This tool is compatible ONLY with Jupyter Notebook version 6.x.**

It does NOT work with:

- Jupyter Lab
- Jupyter Notebook v7.x
- VS Code Notebooks
- Google Colab
- Any other notebook interfaces

## Features

- **Two-way communication**: Connect Claude AI to Jupyter Notebook through a WebSocket-based server
- **Cell manipulation**: Insert, execute, and manage notebook cells
- **Notebook management**: Save notebooks and retrieve notebook information
- **Cell execution**: Run specific cells or execute all cells in a notebook
- **Output retrieval**: Get output content from executed cells with text limitation options

## Components

The system consists of three main components:

1. **WebSocket Server (`jupyter_ws_server.py`)**: Sets up a WebSocket server inside Jupyter that bridges communication between notebook and external clients
2. **Client JavaScript (`client.js`)**: Runs in the notebook to handle operations (inserting cells, executing code, etc.)
3. **MCP Server (`jupyter_mcp_server.py`)**: Implements the Model Context Protocol and connects to the WebSocket server

## Installation

### Prerequisites

- Jupyter Notebook 6.x
- Python 3.10 or newer
- Claude AI desktop application
- `uv` package manager

#### Installing uv

If you're on Mac:

```bash
brew install uv
```

On Windows (PowerShell):

```bash
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

For other platforms, see the [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/).

### Setup

1. Clone or download this repository to your computer:
   ```bash
   git clone https://github.com/jjsantos01/jupyter-notebook-mcp.git
   ```

2. Install required Python packages:
   ```bash
   uv pip install websockets nest-asyncio
   ```

3. Configure Claude desktop integration:
   Go to `Claude` > `Settings` > `Developer` > `Edit Config` > `claude_desktop_config.json` to include the following:

   ```json
      {
       "mcpServers": {
           "jupyter": {
               "command": "uv",
               "args": [
                   "--directory",
                   "/ABSOLUTE/PATH/TO/PARENT/REPO/FOLDER/src",
                   "run",
                   "jupyter_mcp_server.py"
               ]
           }
       }
   }
   ```

   Replace `/ABSOLUTE/PATH/TO/` with the actual path to the `src` folder on your system.

## Usage

### Starting the Connection

1. Start your Jupyter Notebook (version 6.x) server:

   ```bash
   jupyter nbclassic
   ```

2. In a notebook cell, run the following code to initialize the WebSocket server:

   ```python
   import sys
   sys.path.append('/path/to/jupyter-notebook-mcp/src')  # Add the path to where the scripts are located
   
   from jupyter_ws_server import setup_jupyter_mcp_integration
   
   # Start the WebSocket server inside Jupyter
   server, port = setup_jupyter_mcp_integration()
   ```
   
   ![Notebook setup](/assets/img/notebook-setup.png)

3. Launch Claude desktop with MCP enabled.

### Using with Claude

Once connected, Claude will have access to the following tools:

- `ping` - Check server connectivity
- `insert_and_execute_cell` - Insert a cell at the specified position and execute it
- `save_notebook` - Save the current Jupyter notebook
- `get_cells_info` - Get information about all cells in the notebook
- `get_notebook_info` - Get information about the current notebook
- `run_cell` - Run a specific cell by its index
- `run_all_cells` - Run all cells in the notebook
- `get_cell_text_output` - Get the output content of a specific cell
- `get_image_output` - Get the images output of a specific cell

### Example Prompts

Ask Claude to perform notebook operations:

```plain
You have access to my Jupyter Notebook through MCP tools. Can you:
   1. First check if the connection is working with a ping
   2. 
```

## Testing with External Client

You can test the functionality with the included external client:

```bash
python jupyter_ws_external_client.py
```

This will provide an interactive menu to test some available functions.

For automated testing of all commands:

```bash
python jupyter_ws_external_client.py --batch
```

## Troubleshooting

- **Connection Issues**: If you experience connection timeouts, the client includes a reconnection mechanism. You can also try restarting the WebSocket server.
- **Cell Execution Problems**: If cell execution doesn't work, check that the cell content is valid Python/Markdown and that the notebook kernel is running.
- **WebSocket Port Conflicts**: If the default port (8765) is already in use, the server will automatically try to find an available port.

## Limitations

- Only supports Jupyter Notebook 6.x
- Text output from cells is limited to 1500 characters by default
- Does not support advanced Jupyter widget interactions
- Connection may timeout after periods of inactivity

## License

[MIT](/LICENSE)

## Other Jupyter MCPs

This project is inspired by similar MCP integrations for Jupyter as:

- [ihrpr](https://github.com/ihrpr/mcp-server-jupyter)
- [Datalayer](https://github.com/datalayer/jupyter-mcp-server/tree/main)
