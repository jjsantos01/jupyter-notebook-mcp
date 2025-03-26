import asyncio
import websockets
import json
import uuid

async def external_client(port=8765):
    uri = f"ws://localhost:{port}"
    async with websockets.connect(uri) as websocket:
        # Identificarse como cliente externo
        init_msg = {"role": "external"}
        await websocket.send(json.dumps(init_msg))
        
        # Generar un identificador único para la petición
        request_id = str(uuid.uuid4())
        # code_to_execute = f"stata.run(\"\"\"{stata_code}\"\"\")"
        code_to_execute = """
        print("Bienvenido a MCP Jupyter Classic")
        """
        request_msg = {
            "type": "execute",
            "request_id": request_id,
            "code": code_to_execute
        }
        
        # Enviar la petición de ejecución
        await websocket.send(json.dumps(request_msg))
        print(f"Petición de ejecución enviada con request_id: {request_id}")
        
        # Esperar la respuesta que corresponda a nuestro request_id o un mensaje de error
        while True:
            try:
                response = await websocket.recv()
                data = json.loads(response)
                
                if data.get("type") == "result" and data.get("request_id") == request_id:
                    print("Resultado recibido:")
                    print("ID de celda:", data.get("cell_id"))
                    print("Output:", data.get("output"))
                    break
                elif data.get("type") == "error":
                    print("Error recibido:", data.get("message"))
                    break
            except websockets.exceptions.ConnectionClosed as e:
                print(f"Conexión cerrada: {e}")
                break

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765, help="Puerto del servidor WebSocket")
    args = parser.parse_args()
    asyncio.run(external_client(args.port))
