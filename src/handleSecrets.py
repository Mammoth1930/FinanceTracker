"""
This file contains functions used for handling secrets stored in 
./src/secrets.json.
"""

import json
from typing import Any

def get_secret(key: str, sub_key: str) -> Any:
    """
    Retrieves a secret from the secrets.json file.

    Params:
        key: Key describing the application/owner entity of the key.
        sub_key: A key describing the specific type of secret looking to be returned
            e.g. password, PAT, ect.

    Returns:
        any: Returns the value of the specified secret from the .json file.
    """

    with open('./src/secrets.json') as f:
        data = json.load(f)
    return data[key][sub_key]