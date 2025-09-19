# # import subprocess
# # import resource # Used for memory limits (Unix-only)
# # import sys
# #
# # # List of modules that students are not allowed to import
# # FORBIDDEN_IMPORTS = [
# #     "os", "subprocess", "sys", "shutil", "pathlib", "glob",
# #     "socket", "http", "urllib", "requests", "flask", "django"
# # ]
# #
# # # Set the maximum memory usage for the student's process (in bytes)
# # # 200 MB = 200 * 1024 * 1024 = 209715200 bytes
# # MEMORY_LIMIT_BYTES = 1024 * 1024 * 1024
# #
# # def set_memory_limit():
# #     """Sets the memory limit for the current process (for Unix-based systems)."""
# #     try:
# #         # The first value is the soft limit, the second is the hard limit.
# #         resource.setrlimit(resource.RLIMIT_AS, (MEMORY_LIMIT_BYTES, MEMORY_LIMIT_BYTES))
# #     except (ImportError, ValueError) as e:
# #         # resource module is not available on Windows.
# #         # ValueError can happen in some environments (e.g., inside Docker without privileges)
# #         print(f"Warning: Could not set memory limit. {e}", file=sys.stderr)
# #
# #
# # def execute_code(code_string: str, workspace_path: str, main_script_name: str) -> dict:    
# #     """
# #     Executes a string of Python code in a sandboxed environment.
# #     Returns a dictionary with the output, errors, and status.
# #     """
# #     # 1. Security Check: Simple static analysis for forbidden imports
# #     for forbidden in FORBIDDEN_IMPORTS:
# #         if f"import {forbidden}" in code_string or f"from {forbidden}" in code_string:
# #             return {
# #                 "output": "",
# #                 "error": f"Error: The use of module '{forbidden}' is not allowed.",
# #                 "status": "restricted"
# #             }
# #     script_path = pathlib.Path(workspace_path) / main_script_name
# #     script_path.write_text(code_string)
# #     try:
# #         completed_process = subprocess.run(
# #             [sys.executable, str(script_path)], # Run the file directly
# #             capture_output=True,
# #             text=True,
# #             timeout=10,
# #             cwd=workspace_path, # <-- Use the persistent workspace path
# #             preexec_fn=set_memory_limit if sys.platform != "win32" else None
# #         )
# #
# #         output = completed_process.stdout
# #         error = completed_process.stderr
# #         status = "success" if completed_process.returncode == 0 else "runtime_error"
# #
# #     # 2. Execute the code in a separate process
# #     except subprocess.TimeoutExpired:
# #         output = ""
# #         error = "Error: Code execution timed out after 10 seconds."
# #         status = "timeout"
# #     except Exception as e:
# #         output = ""
# #         error = f"An unexpected error occurred: {e}"
# #         status = "system_error"
# #
# #     return {"output": output, "error": error, "status": status}
#
#
# import subprocess
# import resource
# import sys
# import pathlib
# import json
# FORBIDDEN_IMPORTS = [
#     "os", "subprocess", "sys", "shutil", "pathlib", "glob",
#     "socket", "http", "urllib", "requests", "flask", "django"
# ]
# MEMORY_LIMIT_BYTES = 512 * 1024 * 1024
#
# def set_memory_limit():
#     try:
#         resource.setrlimit(resource.RLIMIT_AS, (MEMORY_LIMIT_BYTES, MEMORY_LIMIT_BYTES))
#     except (ImportError, ValueError):
#         pass
#
#
# INSPECTOR_SCRIPT = """
# import json
# import sys
# import inspect
#
# # ---
# # This special block is injected by the platform to inspect variables.
# # ---
# def _gemini_internal_inspect():
#     _vars = []
#     # Grab all global variables
#     _globals = globals()
#     for _name, _val in _globals.items():
#         # Ignore built-ins, modules, and this function itself
#         if _name.startswith('__') or inspect.ismodule(_val) or _name == '_gemini_internal_inspect':
#             continue
#
#         _type_name = type(_val).__name__
#         _repr_val = ''
#         try:
#             # Get a string representation, but truncate it if it's too long
#             _repr_val = repr(_val)
#             if len(_repr_val) > 512:
#                 _repr_val = _repr_val[:512] + '... (truncated)'
#         except Exception:
#             _repr_val = '[Could not get representation]'
#
#         _vars.append({
#             'name': _name,
#             'type': _type_name,
#             'value': _repr_val
#         })
#
#     # Print the collected variables as a JSON string, surrounded by unique delimiters
#     print("\\n---GEMINI_VARIABLE_INSPECTOR_START---")
#     print(json.dumps(_vars))
#     print("---GEMINI_VARIABLE_INSPECTOR_END---")
#
# # Execute the inspection
# _gemini_internal_inspect()
# """
#
#
# def execute_code(code_string: str, workspace_path: str, main_script_name: str) -> dict:
#     for forbidden in FORBIDDEN_IMPORTS:
#         if f"import {forbidden}" in code_string or f"from {forbidden}" in code_string:
#             return { "output": "", "error": f"Error: The use of module '{forbidden}' is not allowed.", "status": "restricted" }
#
#     full_script = code_string + "\n" + INSPECTOR_SCRIPT
#
#     try:
#         if workspace_path:
#             # File Manager mode: run a script file within a specific directory
#             script_path = pathlib.Path(workspace_path) / main_script_name
#             script_path.write_text(full_script)
#             command = [sys.executable, str(script_path)]
#             cwd = workspace_path
#         else:
#             # Simple mode: run code directly as a string
#             command = [sys.executable, "-c", full_script]
#             cwd = None
#
#         completed_process = subprocess.run(
#             command,
#             capture_output=True,
#             text=True,
#             timeout=10,
#             cwd=cwd,
#             preexec_fn=set_memory_limit if sys.platform != "win32" else None
#         )
#         raw_output = completed_process.stdout
#         error = completed_process.stderr
#         status = "success" if completed_process.returncode == 0 else "runtime_error"
#
#         # NEW: Parse the output to separate student prints from our variable data
#         variables = []
#         output = raw_output
#         try:
#             start_delim = "---GEMINI_VARIABLE_INSPECTOR_START---"
#             end_delim = "---GEMINI_VARIABLE_INSPECTOR_END---"
#             if start_delim in raw_output:
#                 parts = raw_output.split(start_delim)
#                 output = parts[0].strip() # The real output is everything before the start delimiter
#                 json_part = parts[1].split(end_delim)[0]
#                 variables = json.loads(json_part)
#         except Exception as e:
#             # If parsing fails, just return the raw output
#             print(f"Variable parsing failed: {e}", file=sys.stderr)
#             output = raw_output
#
#
#     except subprocess.TimeoutExpired:
#         output = ""
#         error = "Error: Code execution timed out after 10 seconds."
#         status = "timeout"
#         variables = []
#     except Exception as e:
#         output = ""
#         error = f"An unexpected error occurred: {e}"
#         status = "system_error"
#         variables = []
#
#     return {"output": output, "error": error, "status": status, "variables": variables}
#
# File: app/sandbox.py

import subprocess
import resource
import sys
import pathlib
import json

# List of modules that students are not allowed to import
FORBIDDEN_IMPORTS = [
    "os", "subprocess", "sys", "shutil", "pathlib", "glob",
    "socket", "http", "urllib", "requests", "flask", "django"
]

# Increased memory limit for libraries like NumPy
MEMORY_LIMIT_BYTES = 512 * 1024 * 1024

def set_memory_limit():
    """Sets the memory limit for the child process (Unix-based systems only)."""
    try:
        resource.setrlimit(resource.RLIMIT_AS, (MEMORY_LIMIT_BYTES, MEMORY_LIMIT_BYTES))
    except (ImportError, ValueError):
        # This will fail on non-Unix systems (like Windows) or in some restricted environments.
        # We fail silently as the timeout is our primary defense on all platforms.
        pass

# This is the script that will be automatically appended to the student's code to capture variables.
INSPECTOR_SCRIPT = """
import json
import sys
import inspect

# ---
# This special block is injected by the platform to inspect variables.
# ---
def _gemini_internal_inspect():
    _vars = []
    # Grab all global variables from the student's script scope
    _globals = globals()
    for _name, _val in _globals.items():
        # Ignore built-in variables, imported modules, and this function itself to reduce noise
        if _name.startswith('__') or inspect.ismodule(_val) or _name == '_gemini_internal_inspect':
            continue
        
        _type_name = type(_val).__name__
        _repr_val = ''
        try:
            # Get a string representation of the variable's value
            _repr_val = repr(_val)
            # Truncate very long values to keep the UI clean
            if len(_repr_val) > 512:
                _repr_val = _repr_val[:512] + '... (truncated)'
        except Exception:
            _repr_val = '[Could not get representation]'
            
        _vars.append({
            'name': _name,
            'type': _type_name,
            'value': _repr_val
        })
    
    # Print the collected variables as a JSON string, surrounded by unique delimiters
    # so the main application can parse it out from the regular output.
    print("\\n---GEMINI_VARIABLE_INSPECTOR_START---")
    print(json.dumps(_vars))
    print("---GEMINI_VARIABLE_INSPECTOR_END---")

# Execute the inspection function
_gemini_internal_inspect()
"""

def execute_code(code_string: str, workspace_path: str, main_script_name: str) -> dict:
    """
    Executes a student's code string in a secure, sandboxed subprocess.
    This function handles both simple (string-based) and file-manager (workspace-based) execution.
    """
    # First, perform a static check for any obviously forbidden imports.
    for forbidden in FORBIDDEN_IMPORTS:
        if f"import {forbidden}" in code_string or f"from {forbidden}" in code_string:
            return {
                "output": "",
                "error": f"Error: The use of module '{forbidden}' is not allowed.",
                "status": "restricted",
                "variables": []
            }
    
    # Append our variable inspector to the student's code.
    full_script = code_string + "\n" + INSPECTOR_SCRIPT
    
    temp_script_path = None
    
    try:
        if workspace_path:
            # File Manager mode: create a temporary script inside the user's workspace to run.
            # This avoids overwriting the user's actual source file.
            temp_script_name = "._gemini_temp_exec.py"
            temp_script_path = pathlib.Path(workspace_path) / temp_script_name
            temp_script_path.write_text(full_script)
            
            command = [sys.executable, str(temp_script_path)]
            cwd = workspace_path
        else:
            # Simple mode: run the code directly as a string.
            command = [sys.executable, "-c", full_script]
            cwd = None

        # Execute the code in a new process with resource limits.
        completed_process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            cwd=cwd,
            preexec_fn=set_memory_limit if sys.platform != "win32" else None
        )
        
        raw_output = completed_process.stdout
        error = completed_process.stderr
        status = "success" if completed_process.returncode == 0 else "runtime_error"

        # After execution, parse the raw output to separate the user's print() statements
        # from our JSON block of variable data.
        variables = []
        output = raw_output
        try:
            start_delim = "---GEMINI_VARIABLE_INSPECTOR_START---"
            end_delim = "---GEMINI_VARIABLE_INSPECTOR_END---"
            if start_delim in raw_output:
                parts = raw_output.split(start_delim)
                output = parts[0].strip() # The real output is everything before our delimiter.
                json_part = parts[1].split(end_delim)[0]
                variables = json.loads(json_part)
        except Exception as e:
            print(f"Variable parsing failed: {e}", file=sys.stderr)
            output = raw_output # If parsing fails, return the raw output to not lose data.

    except subprocess.TimeoutExpired:
        output = ""
        error = "Error: Code execution timed out after 10 seconds."
        status = "timeout"
        variables = []
    except Exception as e:
        output = ""
        error = f"An unexpected error occurred: {e}"
        status = "system_error"
        variables = []
    finally:
        # CRITICAL: Always clean up the temporary script file if it was created.
        if temp_script_path and temp_script_path.exists():
            temp_script_path.unlink()

    return {"output": output, "error": error, "status": status, "variables": variables}
