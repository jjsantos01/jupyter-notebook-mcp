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
        if (data.type === "execute") {
            var code = data.code;
            var request_id = data.request_id;
            
            // Execute code in a new cell
            var cell = Jupyter.notebook.insert_cell_at_bottom();
            cell.set_text(code);
            
            // Generate a cell_id if not available
            var cell_id = cell.cell_id || Date.now().toString();
            
            // Function to send execution results back
            var sendResult = function() {
                var outputs = cell.output_area.outputs;
                var resultMsg = {
                    type: "result",
                    request_id: request_id,
                    cell_id: cell_id,
                    output: outputs
                };
                ws.send(JSON.stringify(resultMsg));
                console.log("Execution result sent");
            };
            
            // Listen for execution completion
            cell.events.one('finished_execute.CodeCell', function() {
                sendResult();
            });
            
            // Execute the cell
            cell.execute();
        }
    };
    
    ws.onerror = function(error) {
        console.error("WebSocket error:", error);
    };
    
    ws.onclose = function() {
        console.log("WebSocket connection closed");
    };
})();