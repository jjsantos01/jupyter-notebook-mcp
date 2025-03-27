(function(){
    // Connect to WebSocket server
    var ws = new WebSocket("ws://localhost:%s");
    
    ws.onopen = function() {
        // Identify as notebook client
        ws.send(JSON.stringify({ role: "notebook" }));
        console.log("Connected to WebSocket server as notebook client");
    };
    
    ws.onmessage = function(event) {
        var data = JSON.parse(event.data);
        
        // Handle different action types
        switch(data.type) {
            case "insert_and_execute_cell":
                handleInsertCell(data);
                break;
            case "save_notebook":
                handleSaveNotebook(data);
                break;
            case "get_cells_info":
                handleGetCellsInfo(data);
                break;
            case "get_notebook_info":
                handleGetNotebookInfo(data);
                break;
            case "run_cell":
                handleRunCell(data);
                break;
            case "run_all_cells":
                handleRunAllCells(data);
                break;
            default:
                console.warn("Unknown message type:", data.type);
        }
    };
    // Handle inserting and executing a cell
    function handleInsertCell(data) {
        var request_id = data.request_id;
        var position = data.position || 0;
        var cell_type = data.cell_type || "code";
        var content = data.content || "";
        
        try {
            var cell = Jupyter.notebook.insert_cell_at_index(cell_type, position);
            cell.set_text(content);
            
            if (cell_type === "code") {
                cell.execute();
            }

            if (cell_type === "markdown") {
                cell.render();
            }
            
            var response = {
                type: "insert_cell_result",
                request_id: request_id,
                status: "success",
                cell_id: cell.cell_id || "cell_" + position,
                position: position
            };
            
            ws.send(JSON.stringify(response));
            console.log("Cell inserted at position " + position);
        } catch (error) {
            var errorResponse = {
                type: "insert_cell_result",
                request_id: request_id,
                status: "error",
                message: error.toString()
            };
            
            ws.send(JSON.stringify(errorResponse));
            console.error("Error inserting cell:", error);
        }
    }

    // Handle saving the notebook
    function handleSaveNotebook(data) {
        var request_id = data.request_id;
        
        try {
            Jupyter.notebook.save_checkpoint();
            
            var response = {
                type: "save_result",
                request_id: request_id,
                status: "success",
                notebook_path: Jupyter.notebook.notebook_path
            };
            
            ws.send(JSON.stringify(response));
            console.log("Notebook saved successfully");
        } catch (error) {
            var errorResponse = {
                type: "save_result",
                request_id: request_id,
                status: "error",
                message: error.toString()
            };
            
            ws.send(JSON.stringify(errorResponse));
            console.error("Error saving notebook:", error);
        }
    }
    
    // Handle getting information about all cells
    function handleGetCellsInfo(data) {
        var request_id = data.request_id;
        
        try {
            var cells = Jupyter.notebook.get_cells();
            var cellsInfo = cells.map(function(cell, index) {
                return {
                    id: cell.cell_id || "cell_" + index,
                    position: index,
                    content: cell.get_text(),
                    type: cell.cell_type,
                    prompt_number: cell.input_prompt_number,
                };
            });
            
            var response = {
                type: "cells_info_result",
                request_id: request_id,
                status: "success",
                cells: cellsInfo
            };
            
            ws.send(JSON.stringify(response));
            console.log("Sent info for " + cellsInfo.length + " cells");
        } catch (error) {
            var errorResponse = {
                type: "cells_info_result",
                request_id: request_id,
                status: "error",
                message: error.toString()
            };
            
            ws.send(JSON.stringify(errorResponse));
            console.error("Error getting cells info:", error);
        }
    }

    // Handle getting notebook information
    function handleGetNotebookInfo(data) {
        var request_id = data.request_id;
        
        try {
            var nbInfo = {
                notebook_name: Jupyter.notebook.notebook_name,
                notebook_path: Jupyter.notebook.notebook_path,
                kernel_name: Jupyter.notebook.kernel.name,
                cell_count: Jupyter.notebook.get_cells().length,
                modified: Jupyter.notebook.dirty,
                trusted: Jupyter.notebook.trusted
            };
            
            var response = {
                type: "notebook_info_result",
                request_id: request_id,
                status: "success",
                notebook_info: nbInfo
            };
            
            ws.send(JSON.stringify(response));
            console.log("Sent notebook info");
        } catch (error) {
            var errorResponse = {
                type: "notebook_info_result",
                request_id: request_id,
                status: "error",
                message: error.toString()
            };
            
            ws.send(JSON.stringify(errorResponse));
            console.error("Error getting notebook info:", error);
        }
    }
    
    // Handle running a specific cell by index
    function handleRunCell(data) {
        var request_id = data.request_id;
        var index = data.index || 0;
        
        try {
            Jupyter.notebook.select(index);
            var cell = Jupyter.notebook.get_selected_cell();
            
            // Generate a cell_id if not available
            var cell_id = cell.cell_id || Date.now().toString();
            
            // Function to send execution results back
            var sendResult = function() {
                var outputs = cell.output_area.outputs;
                var resultMsg = {
                    type: "run_cell_result",
                    request_id: request_id,
                    status: "success",
                    cell_id: cell_id,
                    index: index,
                    output: outputs
                };
                ws.send(JSON.stringify(resultMsg));
                console.log("Cell execution result sent");
            };
            
            // Listen for execution completion
            cell.events.one('finished_execute.CodeCell', function() {
                sendResult();
            });
            
            // Execute the cell
            cell.execute();
            
        } catch (error) {
            var errorResponse = {
                type: "run_cell_result",
                request_id: request_id,
                status: "error",
                message: error.toString()
            };
            
            ws.send(JSON.stringify(errorResponse));
            console.error("Error running cell:", error);
        }
    }    
    
    // Handle running all cells
    function handleRunAllCells(data) {
        var request_id = data.request_id;
        
        try {
            Jupyter.notebook.execute_all_cells();
            
            var response = {
                type: "run_all_cells_result",
                request_id: request_id,
                status: "success"
            };
            
            ws.send(JSON.stringify(response));
            console.log("Running all cells");
        } catch (error) {
            var errorResponse = {
                type: "run_all_cells_result",
                request_id: request_id,
                status: "error",
                message: error.toString()
            };
            
            ws.send(JSON.stringify(errorResponse));
            console.error("Error running all cells:", error);
        }
    }
        
    ws.onerror = function(error) {
        console.error("WebSocket error:", error);
    };
    
    ws.onclose = function() {
        console.log("WebSocket connection closed");
    };
})();