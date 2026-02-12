#!/usr/bin/env python3.12
import sys
import time
import os
import json

def get_deployment_file_path():
    """
    The backend system writes the absolute path of the deployment artifacts
    to the plugin process via standard input when invoking the plugin.
    """
    return sys.stdin.readline().strip()


def log_to_backend_system(msg: str):
    """
    Any content written to standard output by the plugin will be captured
    and recorded as backend system logs.

    NOTE:
    Only a single line containing a valid JSON string will be processed by
    the backend system. Any non-JSON or multi-line output will be ignored.
    """
    log = {'type': 'log', 'msg': msg}
    print(json.dumps(log), flush=True)


def return_result(result):
    """
    The plugin writes the execution result to standard output.
    The backend system will parse this output and treat it as the plugin result.
    """
    res = {'type': 'result', 'result': result}
    print(json.dumps(res), flush=True)
    


if __name__ == "__main__":
    """
    You can simulate a plugin being invoked by executing the command: 
        echo /tmp/deployment-file-path | python3.12 main.py.
    """
    deployment_file_path = get_deployment_file_path()
    if not deployment_file_path:
        log_to_backend_system('No input received.')
        sys.exit(1)

    log_to_backend_system(f'Received deployment file path: {deployment_file_path}.')
    
    if os.path.exists(deployment_file_path) and os.path.isdir(deployment_file_path):
        log_to_backend_system(f'Deployment file path exists and is a directory.')
    else:
        log_to_backend_system(f'Deployment file path does not exist or is not a directory.')
    
    time.sleep(3)
    
    result = {
        "status": "pass",
        "summary": "Single Python Script Plugin Summary",
        "details": ["detail1", "detail2"]
    }
    return_result(result)
