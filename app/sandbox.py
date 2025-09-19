# import subprocess
# import resource # Used for memory limits (Unix-only)
# import sys
#
# # List of modules that students are not allowed to import
# FORBIDDEN_IMPORTS = [
#     "os", "subprocess", "sys", "shutil", "pathlib", "glob",
#     "socket", "http", "urllib", "requests", "flask", "django"
# ]
#
# # Set the maximum memory usage for the student's process (in bytes)
# # 200 MB = 200 * 1024 * 1024 = 209715200 bytes
# MEMORY_LIMIT_BYTES = 1024 * 1024 * 1024
#
# def set_memory_limit():
#     """Sets the memory limit for the current process (for Unix-based systems)."""
#     try:
#         # The first value is the soft limit, the second is the hard limit.
#         resource.setrlimit(resource.RLIMIT_AS, (MEMORY_LIMIT_BYTES, MEMORY_LIMIT_BYTES))
#     except (ImportError, ValueError) as e:
#         # resource module is not available on Windows.
#         # ValueError can happen in some environments (e.g., inside Docker without privileges)
#         print(f"Warning: Could not set memory limit. {e}", file=sys.stderr)
#
#
# def execute_code(code_string: str, workspace_path: str, main_script_name: str) -> dict:    
#     """
#     Executes a string of Python code in a sandboxed environment.
#     Returns a dictionary with the output, errors, and status.
#     """
#     # 1. Security Check: Simple static analysis for forbidden imports
#     for forbidden in FORBIDDEN_IMPORTS:
#         if f"import {forbidden}" in code_string or f"from {forbidden}" in code_string:
#             return {
#                 "output": "",
#                 "error": f"Error: The use of module '{forbidden}' is not allowed.",
#                 "status": "restricted"
#             }
#     script_path = pathlib.Path(workspace_path) / main_script_name
#     script_path.write_text(code_string)
#     try:
#         completed_process = subprocess.run(
#             [sys.executable, str(script_path)], # Run the file directly
#             capture_output=True,
#             text=True,
#             timeout=10,
#             cwd=workspace_path, # <-- Use the persistent workspace path
#             preexec_fn=set_memory_limit if sys.platform != "win32" else None
#         )
#
#         output = completed_process.stdout
#         error = completed_process.stderr
#         status = "success" if completed_process.returncode == 0 else "runtime_error"
#
#     # 2. Execute the code in a separate process
#     except subprocess.TimeoutExpired:
#         output = ""
#         error = "Error: Code execution timed out after 10 seconds."
#         status = "timeout"
#     except Exception as e:
#         output = ""
#         error = f"An unexpected error occurred: {e}"
#         status = "system_error"
#
#     return {"output": output, "error": error, "status": status}


import subprocess
import resource
import sys
import pathlib

FORBIDDEN_IMPORTS = [
    "os", "subprocess", "sys", "shutil", "pathlib", "glob",
    "socket", "http", "urllib", "requests", "flask", "django"
]
MEMORY_LIMIT_BYTES = 512 * 1024 * 1024

def set_memory_limit():
    try:
        resource.setrlimit(resource.RLIMIT_AS, (MEMORY_LIMIT_BYTES, MEMORY_LIMIT_BYTES))
    except (ImportError, ValueError):
        pass

def execute_code(code_string: str, workspace_path: str, main_script_name: str) -> dict:
    for forbidden in FORBIDDEN_IMPORTS:
        if f"import {forbidden}" in code_string or f"from {forbidden}" in code_string:
            return { "output": "", "error": f"Error: The use of module '{forbidden}' is not allowed.", "status": "restricted" }
    
    try:
        if workspace_path:
            # File Manager mode: run a script file within a specific directory
            script_path = pathlib.Path(workspace_path) / main_script_name
            script_path.write_text(code_string)
            command = [sys.executable, str(script_path)]
            cwd = workspace_path
        else:
            # Simple mode: run code directly as a string
            command = [sys.executable, "-c", code_string]
            cwd = None

        completed_process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            cwd=cwd,
            preexec_fn=set_memory_limit if sys.platform != "win32" else None
        )
        output = completed_process.stdout
        error = completed_process.stderr
        status = "success" if completed_process.returncode == 0 else "runtime_error"

    except subprocess.TimeoutExpired:
        output = ""
        error = "Error: Code execution timed out after 10 seconds."
        status = "timeout"
    except Exception as e:
        output = ""
        error = f"An unexpected error occurred: {e}"
        status = "system_error"

    return {"output": output, "error": error, "status": status}
