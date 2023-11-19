import json


def write_file(fname, content):
    with open(fname, "w") as f:
        f.write(content)


def write_json_file(fname, json_str: str):
    # convert ' to "
    json_str = json_str.replace("'", '"')

    # Convert the string to a Python object
    data = json.loads(json_str)

    # Write the Python object to the file as JSON
    with open(fname, "w") as f:
        json.dump(data, f, indent=4)
