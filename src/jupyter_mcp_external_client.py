import asyncio
import websockets
import json
import uuid
import argparse
from typing import Dict, Any, Optional

async def execute_code(websocket, code: str, position: Optional[int] = None) -> Dict[str, Any]:
    """Execute code in the Jupyter notebook"""
    request_id = str(uuid.uuid4())
    request_msg = {
        "type": "insert_and_execute_cell",
        "request_id": request_id,
        "cell_type": "code",
        "position": position if position is not None else 0,
        "content": code
    }
    
    await websocket.send(json.dumps(request_msg))
    print(f"Petición de ejecución enviada con request_id: {request_id}")
    
    return await wait_for_response(websocket, request_id)

async def save_notebook(websocket) -> Dict[str, Any]:
    """Save the current notebook"""
    request_id = str(uuid.uuid4())
    request_msg = {
        "type": "save_notebook",
        "request_id": request_id
    }
    
    await websocket.send(json.dumps(request_msg))
    print(f"Petición de guardado enviada con request_id: {request_id}")
    
    return await wait_for_response(websocket, request_id)

async def get_cells_info(websocket) -> Dict[str, Any]:
    """Get information about all cells in the notebook"""
    request_id = str(uuid.uuid4())
    request_msg = {
        "type": "get_cells_info",
        "request_id": request_id
    }
    
    await websocket.send(json.dumps(request_msg))
    print(f"Petición de info de celdas enviada con request_id: {request_id}")
    
    return await wait_for_response(websocket, request_id)

async def get_notebook_info(websocket) -> Dict[str, Any]:
    """Get information about the current notebook"""
    request_id = str(uuid.uuid4())
    request_msg = {
        "type": "get_notebook_info",
        "request_id": request_id
    }
    
    await websocket.send(json.dumps(request_msg))
    print(f"Petición de info del notebook enviada con request_id: {request_id}")
    
    return await wait_for_response(websocket, request_id)

async def run_cell(websocket, index: int) -> Dict[str, Any]:
    """Run a specific cell by its index"""
    request_id = str(uuid.uuid4())
    request_msg = {
        "type": "run_cell",
        "request_id": request_id,
        "index": index
    }
    
    await websocket.send(json.dumps(request_msg))
    print(f"Petición para ejecutar celda en índice {index} enviada con request_id: {request_id}")
    
    return await wait_for_response(websocket, request_id)

async def run_all_cells(websocket) -> Dict[str, Any]:
    """Run all cells in the notebook"""
    request_id = str(uuid.uuid4())
    request_msg = {
        "type": "run_all_cells",
        "request_id": request_id
    }
    
    await websocket.send(json.dumps(request_msg))
    print(f"Petición para ejecutar todas las celdas enviada con request_id: {request_id}")
    
    return await wait_for_response(websocket, request_id)

async def get_cell_output(websocket, index: int, max_length: int = 1500) -> Dict[str, Any]:
    """Get the output content of a specific cell by its index"""
    request_id = str(uuid.uuid4())
    request_msg = {
        "type": "get_cell_output",
        "request_id": request_id,
        "index": index,
        "max_length": max_length
    }
    
    await websocket.send(json.dumps(request_msg))
    print(f"Petición para obtener salida de celda en índice {index} enviada con request_id: {request_id}")
    
    return await wait_for_response(websocket, request_id)

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
    uri = f"ws://localhost:{port}"
    async with websockets.connect(uri) as websocket:
        # Identificarse como cliente externo
        init_msg = {"role": "external"}
        await websocket.send(json.dumps(init_msg))
        print(f"Conectado a {uri} como cliente externo")
        
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
            print("0. Salir")
            
            choice = input("Selecciona una opción: ")
            
            if choice == "0":
                break
            elif choice == "1":
                code = input("Ingresa el código a ejecutar: ")
                pos_input = input("Posición (opcional, presiona Enter para final): ")
                position = int(pos_input) if pos_input.strip() else None
                result = await execute_code(websocket, code, position)
                print("Resultado:", json.dumps(result, indent=2))
            elif choice == "2":
                result = await save_notebook(websocket)
                print("Resultado:", json.dumps(result, indent=2))
            elif choice == "3":
                result = await get_cells_info(websocket)
                print("Resultado:", json.dumps(result, indent=2))
            elif choice == "4":
                result = await get_notebook_info(websocket)
                print("Resultado:", json.dumps(result, indent=2))
            elif choice == "5":
                index = int(input("Índice de la celda a ejecutar: "))
                result = await run_cell(websocket, index)
                print("Resultado:", json.dumps(result, indent=2))
            elif choice == "6":
                result = await run_all_cells(websocket)
                print("Resultado:", json.dumps(result, indent=2))
            elif choice == "7":
                index = int(input("Índice de la celda para obtener salida: "))
                max_len_input = input("Longitud máxima (opcional, presiona Enter para 1500): ")
                max_length = int(max_len_input) if max_len_input.strip() else 1500
                result = await get_cell_output(websocket, index, max_length)
                print("Resultado:", json.dumps(result, indent=2))
            else:
                print("Opción no válida")

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
            code_result = await execute_code(websocket, "print('Prueba de MCP Jupyter')")
            print("Resultado:", json.dumps(code_result, indent=2))
            
            # 2. Probar obtener info del notebook
            print("\n=== TEST: Obtener información del notebook ===")
            notebook_info = await get_notebook_info(websocket)
            print("Resultado:", json.dumps(notebook_info, indent=2))
            
            # 3. Probar obtener info de celdas
            print("\n=== TEST: Obtener información de celdas ===")
            cells_info = await get_cells_info(websocket)
            print("Resultado:", json.dumps(cells_info, indent=2))
            
            # 4. Probar ejecutar celda específica
            if cells_info.get("status") == "success" and len(cells_info.get("cells", [])) > 0:
                print("\n=== TEST: Ejecutar celda específica ===")
                run_cell_result = await run_cell(websocket, 0)  # Ejecuta la primera celda
                print("Resultado:", json.dumps(run_cell_result, indent=2))

                print("\n=== TEST: Obtener salida de celda ===")
                output_result = await get_cell_output(websocket, 0)  # Obtiene salida de la primera celda
                print("Resultado:", json.dumps(output_result, indent=2))
            
            # 5. Probar guardar notebook
            print("\n=== TEST: Guardar notebook ===")
            save_result = await save_notebook(websocket)
            print("Resultado:", json.dumps(save_result, indent=2))
            
            # 6. Probar ejecutar todas las celdas
            print("\n=== TEST: Ejecutar todas las celdas ===")
            run_all_result = await run_all_cells(websocket)
            print("Resultado:", json.dumps(run_all_result, indent=2))
            
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
