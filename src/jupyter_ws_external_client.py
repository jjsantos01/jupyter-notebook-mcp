import asyncio
import websockets
import json
import argparse
from jupyter_ws_client import get_jupyter_client

DEFAULT_CELL_INDEX = 1

async def external_client(host='localhost', port=8765):
        
        # Intentar la conexión inicial
        try:
            client = await get_jupyter_client(host, port)
            print(f"Conectado al servidor WebSocket en {host}:{port}")
        except Exception as e:
            print(f"Error en la conexión inicial: {e}")
            return
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
            print("9. Editar contenido de celda específica")
            print("10. Establecer tipo de slideshow para una celda")
            print("0. Salir")
            
            choice = input("Selecciona una opción: ")
            
            if choice == "0":
                break
            
            try:
                if choice == "1":
                    code = input("Ingresa el código a ejecutar: ")
                    pos_input = input("Posición (opcional, presiona Enter para final): ")
                    position = int(pos_input) if pos_input.strip() else None
                    print("Tipos válidos: slide, subslide, fragment, skip, notes, - (ninguno)")
                    slideshow_type = input("Tipo de slideshow: ")
                    result = await client.insert_and_execute_cell("code", position, code, slideshow_type)
                    print("Resultado:", json.dumps(result, indent=2))
                    
                    if slideshow_type.strip() != "":
                        result_slide = await client.set_slideshow_type(position, slideshow_type)
                        print("Resultado:", json.dumps(result_slide, indent=2))
                elif choice == "2":
                    result = await client.save_notebook()
                    print("Resultado:", json.dumps(result, indent=2))
                elif choice == "3":
                    result = await client.get_cells_info()
                    print("Resultado:", json.dumps(result, indent=2))
                elif choice == "4":
                    result = await client.get_notebook_info()
                    print("Resultado:", json.dumps(result, indent=2))
                elif choice == "5":
                    index = int(input("Índice de la celda a ejecutar: "))
                    result = await client.run_cell(index)
                    print("Resultado:", json.dumps(result, indent=2))
                elif choice == "6":
                    result = await client.run_all_cells()
                    print("Resultado:", json.dumps(result, indent=2))
                elif choice == "7":
                    index = int(input("Índice de la celda para obtener salida: "))
                    max_len_input = input("Longitud máxima (opcional, presiona Enter para 1500): ")
                    max_length = int(max_len_input) if max_len_input.strip() else 1500
                    result = await client.get_cell_text_output(index, max_length)
                    print("Resultado:", json.dumps(result, indent=2))
                elif choice == "8":
                    index = int(input("Índice de la celda para obtener imágenes: "))
                    result = await client.get_image_output(index)
                    print("Resultado:", json.dumps(result, indent=2))
                elif choice == "9":
                    index = int(input("Índice de la celda a editar: "))
                    content = input("Nuevo contenido: ")
                    execute_input = input("¿Ejecutar después de editar? (s/n): ").lower()
                    execute = execute_input.startswith('s')
                    result = await client.edit_cell_content(index, content, execute)
                    print("Resultado:", json.dumps(result, indent=2))
                elif choice == "10":
                    index = int(input("Índice de la celda: "))
                    print("Tipos válidos: slide, subslide, fragment, skip, notes, - (ninguno)")
                    slideshow_type = input("Tipo de slideshow: ")
                    if slideshow_type.strip() == "":
                        slideshow_type = "-"
                    result = await client.set_slideshow_type(index, slideshow_type)
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

async def execute_batch_tests(host='localhost', port=8765):
    """Ejecuta una serie de pruebas automáticas para todos los comandos"""
    uri = f"ws://localhost:{port}"
    print(f"Iniciando pruebas automáticas en {uri}")
    
    try:
        client = await get_jupyter_client(host, port)
        print(f"Conectado al servidor WebSocket en {host}:{port}")
        
        # 1. Probar ejecución de código
        print("\n=== TEST: Ejecutar código ===")
        code_result = await client.insert_and_execute_cell("code", DEFAULT_CELL_INDEX, "print('Prueba de MCP Jupyter')")
        print("Resultado:", json.dumps(code_result, indent=2))
        
        # 2. Probar obtener info del notebook
        print("\n=== TEST: Obtener información del notebook ===")
        notebook_info = await client.get_notebook_info()
        print("Resultado:", json.dumps(notebook_info, indent=2))
        
        # 3. Probar obtener info de celdas
        print("\n=== TEST: Obtener información de celdas ===")
        cells_info = await client.get_cells_info()
        print("Resultado:", json.dumps(cells_info, indent=2))
        
        # 4. Probar ejecutar celda específica
        if cells_info.get("status") == "success" and len(cells_info.get("cells", [])) > 0:
            print("\n=== TEST: Ejecutar celda específica ===")
            run_cell_result = await client.run_cell(DEFAULT_CELL_INDEX)  # Ejecuta la primera celda
            print("Resultado:", json.dumps(run_cell_result, indent=2))

            print("\n=== TEST: Obtener salida de celda ===")
            output_result = await client.get_cell_text_output(0)  # Obtiene salida de la primera celda
            print("Resultado:", json.dumps(output_result, indent=2))
        
        # 5. Probar guardar notebook
        print("\n=== TEST: Guardar notebook ===")
        save_result = await client.save_notebook()
        print("Resultado:", json.dumps(save_result, indent=2))
        
        # 6. Probar ejecutar todas las celdas
        print("\n=== TEST: Ejecutar todas las celdas ===")
        run_all_result = await client.run_all_cells()
        print("Resultado:", json.dumps(run_all_result, indent=2))

        # 7. Obtener imágenes de una celda
        print("\n=== TEST: Obtener imagen de una celda ===")
        code_result = await client.insert_and_execute_cell(
            "code",
            DEFAULT_CELL_INDEX,
            """
from IPython.display import Image
Image("../assets/img/notebook-setup.png")
            """
        )
        get_image_output_result = await client.get_image_output(DEFAULT_CELL_INDEX)
        print("Resultado:", json.dumps(get_image_output_result, indent=2))
        
        # Edit cell content
        if cells_info.get("status") == "success" and len(cells_info.get("cells", [])) > 0:
            print("\n=== TEST: Editar contenido de celda ===")
            edit_result = await client.edit_cell_content(DEFAULT_CELL_INDEX, "# Celda modificada por MCP\nprint('MCP was here :)')")
            print("Resultado:", json.dumps(edit_result, indent=2))
        
        # set slideshow type
        if cells_info.get("status") == "success" and len(cells_info.get("cells", [])) > 0:
            print("\n=== TEST: Establecer tipo de slideshow ===")
            slideshow_result = await client.set_slideshow_type(DEFAULT_CELL_INDEX, "slide")
            print("Resultado:", json.dumps(slideshow_result, indent=2))

        print("\n=== TODOS LOS TESTS COMPLETADOS ===")
    except Exception as e:
        print(f"Error durante las pruebas: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cliente de prueba para MCP Jupyter")
    parser.add_argument("--host", type=str, default="localhost", help="Host del servidor WebSocket")
    parser.add_argument("--port", type=int, default=8765, help="Puerto del servidor WebSocket")
    parser.add_argument("--batch", action="store_true", help="Ejecutar pruebas automáticas en lote")
    args = parser.parse_args()
    
    if args.batch:
        asyncio.run(execute_batch_tests(args.host, args.port))
    else:
        asyncio.run(external_client(args.host, args.port))
