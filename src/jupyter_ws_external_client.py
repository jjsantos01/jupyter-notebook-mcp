import asyncio
import websockets
import json
import argparse
from jupyter_ws_client import get_jupyter_client

DEFAULT_CELL_INDEX = 1

async def external_client(host='localhost', port=8765):
        
        try:
            client = await get_jupyter_client(host, port)
            print(f"Connected to WebSocket server at {host}:{port}")
        except Exception as e:
            print(f"Error in initial connection: {e}")
            return
        # Interactive menu
        while True:
            print("\n=== MCP Jupyter TEST CLIENT ===")
            print("1. Execute code")
            print("2. Save notebook")
            print("3. Get cells info")
            print("4. Get notebook info")
            print("5. Run specific cell")
            print("6. Run all cells")
            print("7. Get specific cell output")
            print("8. Get specific cell image")
            print("9. Edit specific cell content")
            print("10. Set slideshow type for a cell")
            print("0. Exit")
            
            choice = input("Select an option: ")
            
            if choice == "0":
                break
            
            try:
                if not client.connected:
                    print("Connection lost, trying to reconnect...")
                    try:
                        await client.connect()
                        print("Reconnected successfully")
                    except Exception as e:
                        print(f"Failed to reconnect: {e}")
                        try:
                            client = await get_jupyter_client(host, port)
                            print("Created new client connection")
                        except Exception as e2:
                            print(f"Failed to create new connection: {e2}")
                            continue
                if choice == "1":
                    code = input("Enter the code to execute: ")
                    pos_input = input("Position (optional, press Enter to finish): ")
                    position = int(pos_input) if pos_input.strip() else None
                    print("Valid types: slide, subslide, fragment, skip, notes, - (none)")
                    slideshow_type = input("Slideshow type: ")
                    result = await client.insert_and_execute_cell("code", position, code, slideshow_type)
                    print("Result:", json.dumps(result, indent=2))
                    
                    if slideshow_type.strip() != "":
                        result_slide = await client.set_slideshow_type(position, slideshow_type)
                        print("Result:", json.dumps(result_slide, indent=2))
                elif choice == "2":
                    result = await client.save_notebook()
                    print("Result:", json.dumps(result, indent=2))
                elif choice == "3":
                    result = await client.get_cells_info()
                    print("Result:", json.dumps(result, indent=2))
                elif choice == "4":
                    result = await client.get_notebook_info()
                    print("Result:", json.dumps(result, indent=2))
                elif choice == "5":
                    index = int(input("Index of the cell to run: "))
                    result = await client.run_cell(index)
                    print("Result:", json.dumps(result, indent=2))
                elif choice == "6":
                    result = await client.run_all_cells()
                    print("Result:", json.dumps(result, indent=2))
                elif choice == "7":
                    index = int(input("Index of the cell to get output: "))
                    max_len_input = input("Maximum length (optional, press Enter for 1500): ")
                    max_length = int(max_len_input) if max_len_input.strip() else 1500
                    result = await client.get_cell_text_output(index, max_length)
                    print("Result:", json.dumps(result, indent=2))
                elif choice == "8":
                    index = int(input("Index of the cell to get images: "))
                    result = await client.get_image_output(index)
                    print("Result:", json.dumps(result, indent=2))
                elif choice == "9":
                    index = int(input("Index of the cell to edit: "))
                    content = input("New content: ")
                    execute_input = input("Execute after editing? (y/n): ").lower()
                    execute = execute_input.startswith('y')
                    result = await client.edit_cell_content(index, content, execute)
                    print("Result:", json.dumps(result, indent=2))
                elif choice == "10":
                    index = int(input("Cell index: "))
                    print("Valid types: slide, subslide, fragment, skip, notes, - (none)")
                    slideshow_type = input("Slideshow type: ")
                    if slideshow_type.strip() == "":
                        slideshow_type = "-"
                    result = await client.set_slideshow_type(index, slideshow_type)
                    print("Result:", json.dumps(result, indent=2))
                else:
                    print("Invalid option")
            except websockets.exceptions.ConnectionClosed:
                print("Connection lost. We will try to reconnect on the next command.")
            except Exception as e:
                print(f"Error executing command: {e}")
        
        if client.connected:
            await client.disconnect()

async def execute_batch_tests(host='localhost', port=8765):
    """Executes a series of automatic tests for all commands"""
    uri = f"ws://localhost:{port}"
    print(f"Starting automatic tests at {uri}")
    
    try:
        client = await get_jupyter_client(host, port)
        print(f"Connected to WebSocket server at {host}:{port}")
        
        # 1. Test code execution
        print("\n=== TEST: Execute code ===")
        code_result = await client.insert_and_execute_cell("code", DEFAULT_CELL_INDEX, "print('MCP Jupyter test')")
        print("Result:", json.dumps(code_result, indent=2))
        
        # 2. Test getting notebook info
        print("\n=== TEST: Get notebook info ===")
        notebook_info = await client.get_notebook_info()
        print("Result:", json.dumps(notebook_info, indent=2))
        
        # 3. Test getting cells info
        print("\n=== TEST: Get cells info ===")
        cells_info = await client.get_cells_info()
        print("Result:", json.dumps(cells_info, indent=2))
        
        # 4. Test running a specific cell
        if cells_info.get("status") == "success" and len(cells_info.get("cells", [])) > 0:
            print("\n=== TEST: Run specific cell ===")
            run_cell_result = await client.run_cell(DEFAULT_CELL_INDEX)
            print("Result:", json.dumps(run_cell_result, indent=2))

            print("\n=== TEST: Get cell output ===")
            output_result = await client.get_cell_text_output(DEFAULT_CELL_INDEX)
            print("Result:", json.dumps(output_result, indent=2))
        
        # 5. Test saving notebook
        print("\n=== TEST: Save notebook ===")
        save_result = await client.save_notebook()
        print("Result:", json.dumps(save_result, indent=2))
        
        # 6. Test running all cells
        print("\n=== TEST: Run all cells ===")
        run_all_result = await client.run_all_cells()
        print("Result:", json.dumps(run_all_result, indent=2))

        # 7. Test getting image from a cell
        print("\n=== TEST: Get image from a cell ===")
        code_result = await client.insert_and_execute_cell(
            "code",
            DEFAULT_CELL_INDEX,
            """
from IPython.display import Image
Image("../assets/img/notebook-setup.png")
            """
        )
        get_image_output_result = await client.get_image_output(DEFAULT_CELL_INDEX)
        print("Result:", json.dumps(get_image_output_result, indent=2))
        
        # Test editing cell content
        if cells_info.get("status") == "success" and len(cells_info.get("cells", [])) > 0:
            print("\n=== TEST: Edit cell content ===")
            edit_result = await client.edit_cell_content(DEFAULT_CELL_INDEX, "# Cell modified by MCP\nprint('MCP was here :)')")
            print("Result:", json.dumps(edit_result, indent=2))
        
        # Test setting slideshow type
        if cells_info.get("status") == "success" and len(cells_info.get("cells", [])) > 0:
            print("\n=== TEST: Set slideshow type ===")
            slideshow_result = await client.set_slideshow_type(DEFAULT_CELL_INDEX, "slide")
            print("Result:", json.dumps(slideshow_result, indent=2))

        print("\n=== ALL TESTS COMPLETED ===")
    except Exception as e:
        print(f"Error during tests: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MCP Jupyter test client")
    parser.add_argument("--host", type=str, default="localhost", help="WebSocket server host")
    parser.add_argument("--port", type=int, default=8765, help="WebSocket server port")
    parser.add_argument("--batch", action="store_true", help="Run batch automatic tests")
    args = parser.parse_args()
    
    if args.batch:
        asyncio.run(execute_batch_tests(args.host, args.port))
    else:
        asyncio.run(external_client(args.host, args.port))
