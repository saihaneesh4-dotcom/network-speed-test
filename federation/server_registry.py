import json

def get_servers():
    with open("servers.json", "r") as file:
        data = json.load(file)

    return data["servers"]