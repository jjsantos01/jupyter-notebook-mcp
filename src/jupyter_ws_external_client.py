import asyncio
import websockets
import json
import uuid
import argparse
from typing import Dict, Any

current_websocket = None


async def ensure_connected(port=8765):
    """Asegura que hay una conexión activa al servidor WebSocket, reconectando si es necesario"""
    global current_websocket
    
    # Si no hay conexión o está cerrada, crear una nueva
    if current_websocket is None or current_websocket.closed:
        uri = f"ws://localhost:{port}"
        try:
            print(f"Conectando a {uri}...")
            current_websocket = await websockets.connect(uri)
            
            # Identificarse como cliente externo
            init_msg = {"role": "external"}
            await current_websocket.send(json.dumps(init_msg))
            print(f"Conectado a {uri} como cliente externo")
        except Exception as e:
            print(f"Error al conectar: {e}")
            current_websocket = None
            raise
    
    return current_websocket

async def send_command(command_type, **kwargs):
    """send a command to server"""
    try:
        websocket = await ensure_connected()
        request_id = str(uuid.uuid4())
        
        request_msg = {
            "type": command_type,
            "source": "external",
            "target": "notebook",
            "request_id": request_id,
            **kwargs
        }
        
        await websocket.send(json.dumps(request_msg))
        print(f"Petición {command_type} enviada con request_id: {request_id}")
        
        return await wait_for_response(websocket, request_id)
    except websockets.exceptions.ConnectionClosed:
        print("Conexión cerrada. Intentaremos reconectar en el próximo comando.")
        global current_websocket
        current_websocket = None
        raise
    except Exception as e:
        print(f"Error al enviar comando: {e}")
        raise

async def execute_code(code, position=None):
    """Execute code in the Jupyter notebook"""
    return await send_command("insert_and_execute_cell",
                            cell_type="code", 
                            position=position if position is not None else 0, 
                            content=code)

async def save_notebook():
    """Save the current notebook"""
    return await send_command("save_notebook")

async def get_cells_info():
    """Get information about all cells in the notebook"""
    return await send_command("get_cells_info")

async def get_notebook_info():
    """Get information about the current notebook"""
    return await send_command("get_notebook_info")

async def run_cell(index):
    """Run a specific cell by its index"""
    return await send_command("run_cell", index=index)

async def run_all_cells():
    """Run all cells in the notebook"""
    return await send_command("run_all_cells")

async def get_cell_text_output(index, max_length=1500):
    """Get the output content of a specific cell by its index"""
    return await send_command("get_cell_text_output", index=index, max_length=max_length)

async def get_image_output(index: int):
    """Get the image output of a specific cell by its index"""
    return await send_command("get_cell_image_output", index=index)

async def wait_for_response(websocket, request_id: str, timeout: int = 60) -> Dict[str, Any]:
    """Wait for a response with the given request_id or an error"""
    try:
        # Configurar un timeout para la espera
        for _ in range(timeout):
            try:
                response = await asyncio.wait_for(websocket.recv(), 1.0)
                data = json.loads(response)
                
                # Verificar si es una respuesta a nuestra petición
                if data.get("request_id") == request_id:
                    return data
                elif data.get("type") == "error" and data.get("request_id") == request_id:
                    print(f"Error recibido: {data.get('message')}")
                    return data
            except asyncio.TimeoutError:
                # Continuar esperando hasta alcanzar el timeout total
                continue
            
        # Si llegamos aquí, se superó el timeout
        return {"type": "error", "message": f"Timeout esperando respuesta para request_id: {request_id}"}
    except websockets.exceptions.ConnectionClosed as e:
        return {"type": "error", "message": f"Conexión cerrada: {e}"}

async def external_client(port=8765):
        global current_websocket
        
        # Intentar la conexión inicial
        try:
            await ensure_connected(port)
        except Exception as e:
            print(f"Error en la conexión inicial: {e}")
        
        # Menú interactivo
        while True:
            print("\n=== CLIENTE DE PRUEBA MCP JUPYTER ===")
            print("1. Ejecutar código")
            print("2. Guardar notebook")
            print("3. Obtener información de celdas")
            print("4. Obtener información del notebook")
            print("5. Ejecutar celda específica")
            print("6. Ejecutar todas las celdas")
            print("7. Obtener salida de celda específica")
            print("8. Obtener Imagen de celda específica")
            print("0. Salir")
            
            choice = input("Selecciona una opción: ")
            
            if choice == "0":
                break
            
            try:
                if choice == "1":
                    code = input("Ingresa el código a ejecutar: ")
                    pos_input = input("Posición (opcional, presiona Enter para final): ")
                    position = int(pos_input) if pos_input.strip() else None
                    result = await execute_code(code, position)
                    print("Resultado:", json.dumps(result, indent=2))
                elif choice == "2":
                    result = await save_notebook()
                    print("Resultado:", json.dumps(result, indent=2))
                elif choice == "3":
                    result = await get_cells_info()
                    print("Resultado:", json.dumps(result, indent=2))
                elif choice == "4":
                    result = await get_notebook_info()
                    print("Resultado:", json.dumps(result, indent=2))
                elif choice == "5":
                    index = int(input("Índice de la celda a ejecutar: "))
                    result = await run_cell(index)
                    print("Resultado:", json.dumps(result, indent=2))
                elif choice == "6":
                    result = await run_all_cells()
                    print("Resultado:", json.dumps(result, indent=2))
                elif choice == "7":
                    index = int(input("Índice de la celda para obtener salida: "))
                    max_len_input = input("Longitud máxima (opcional, presiona Enter para 1500): ")
                    max_length = int(max_len_input) if max_len_input.strip() else 1500
                    result = await get_cell_text_output(index, max_length)
                    print("Resultado:", json.dumps(result, indent=2))
                elif choice == "8":
                    index = int(input("Índice de la celda para obtener imágenes: "))
                    result = await get_image_output(index)
                    print("Resultado:", json.dumps(result, indent=2))
                else:
                    print("Opción no válida")
            except websockets.exceptions.ConnectionClosed:
                print("Se perdió la conexión. Intentaremos reconectar en el próximo comando.")
                current_websocket = None
            except Exception as e:
                print(f"Error al ejecutar comando: {e}")
        
        if current_websocket and not current_websocket.closed:
            await current_websocket.close()

async def execute_batch_tests(port=8765):
    """Ejecuta una serie de pruebas automáticas para todos los comandos"""
    uri = f"ws://localhost:{port}"
    print(f"Iniciando pruebas automáticas en {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            # Identificarse como cliente externo
            init_msg = {"role": "external"}
            await websocket.send(json.dumps(init_msg))
            print(f"Conectado a {uri} como cliente externo")
            
            # 1. Probar ejecución de código
            print("\n=== TEST: Ejecutar código ===")
            code_result = await execute_code("print('Prueba de MCP Jupyter')")
            print("Resultado:", json.dumps(code_result, indent=2))
            
            # 2. Probar obtener info del notebook
            print("\n=== TEST: Obtener información del notebook ===")
            notebook_info = await get_notebook_info()
            print("Resultado:", json.dumps(notebook_info, indent=2))
            
            # 3. Probar obtener info de celdas
            print("\n=== TEST: Obtener información de celdas ===")
            cells_info = await get_cells_info()
            print("Resultado:", json.dumps(cells_info, indent=2))
            
            # 4. Probar ejecutar celda específica
            if cells_info.get("status") == "success" and len(cells_info.get("cells", [])) > 0:
                print("\n=== TEST: Ejecutar celda específica ===")
                run_cell_result = await run_cell(1)  # Ejecuta la primera celda
                print("Resultado:", json.dumps(run_cell_result, indent=2))

                print("\n=== TEST: Obtener salida de celda ===")
                output_result = await get_cell_text_output(0)  # Obtiene salida de la primera celda
                print("Resultado:", json.dumps(output_result, indent=2))
            
            # 5. Probar guardar notebook
            print("\n=== TEST: Guardar notebook ===")
            save_result = await save_notebook()
            print("Resultado:", json.dumps(save_result, indent=2))
            
            # 6. Probar ejecutar todas las celdas
            print("\n=== TEST: Ejecutar todas las celdas ===")
            run_all_result = await run_all_cells()
            print("Resultado:", json.dumps(run_all_result, indent=2))

            # 7. Obtener imágenes de una celda
            print("\n=== TEST: Obtener imagen de una celda ===")
            code_result = await execute_code(
                """
from IPython.display import Image
Image("../assets/img/notebook-setup.png")
                """
            )
            get_image_output_result = await get_image_output(0)
            print("Resultado:", json.dumps(get_image_output_result, indent=2))
            

            print("\n=== TODOS LOS TESTS COMPLETADOS ===")
    except Exception as e:
        print(f"Error durante las pruebas: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cliente de prueba para MCP Jupyter")
    parser.add_argument("--port", type=int, default=8765, help="Puerto del servidor WebSocket")
    parser.add_argument("--batch", action="store_true", help="Ejecutar pruebas automáticas en lote")
    args = parser.parse_args()
    
    if args.batch:
        asyncio.run(execute_batch_tests(args.port))
    else:
        asyncio.run(external_client(args.port))
