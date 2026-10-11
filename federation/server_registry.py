import json
import os


def get_servers():

    file_path = os.path.join(
        os.path.dirname(__file__),
        "servers.json"
    )

    with open(file_path, "r") as file:
        data = json.load(file)

    return data["servers"]