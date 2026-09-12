from server_selector import select_best_server

server = select_best_server()

if server is not None:
    print()
    print("Server returned to another module:")
    print(server)
else:
    print("No server available")