from time import time, sleep
from typing import Dict, Callable
import logging

_logger = logging.getLogger(__name__)

def generate_id() -> int:
    """ Get the current timestamp to be used as unique ID during this execution. """
    return int(time())

def validate_instance_mode(instance_data: Dict) -> Dict:
    """ Validate if the instance is already configured as rescue mode. """
    result = {
        'rescue-mode': False,
        'ts': generate_id()
    }

    if "metadata" in instance_data and  "items" in instance_data["metadata"]:
        metadata = instance_data["metadata"]
        for item in metadata["items"]:
            if item["key"] == "rescue-mode":
                result = {
                    'rescue-mode': True,
                    'ts': item['value']
                }

    return result

def wait_for_operation(instance_obj: Callable, oper: Dict):
    while True:
        result = instance_obj.compute.zoneOperations().get(
            **instance_obj.project_data,
            operation = oper['name']).execute()
        if result['status'] == 'DONE':
            _logger.info("done.")
            if 'error' in result:
                raise Exception(result['error'])
            return result
        sleep(1)