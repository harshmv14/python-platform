import subprocess
import resource # Used for memory limits (Unix-only)
import sys

# List of modules that students are not allowed to import
FORBIDDEN_IMPORTS = [
    "os", "subprocess", "sys", "shutil", "pathlib", "glob",
    "socket", "http", "urllib", "requests", "flask", "django"
]

# Set the maximum memory usage for the student's process (in bytes)
# 200 MB = 200 * 1024 * 1024 = 209715200 bytes
MEMORY_LIMIT_BYTES = 1024 * 1024 * 1024

def set_memory_limit():
    """Sets the memory limit for the current process (for Unix-based systems)."""
    try:
        # The first value is the soft limit, the second is the hard limit.
        resource.setrlimit(resource.RLIMIT_AS, (MEMORY_LIMIT_BYTES, MEMORY_LIMIT_BYTES))
    except (ImportError, ValueError) as e:
        # resource module is not available on Windows.
        # ValueError can happen in some environments (e.g., inside Docker without privileges)
        print(f"Warning: Could not set memory limit. {e}", file=sys.stderr)


def execute_code(code_string: str) -> dict:
    """
    Executes a string of Python code in a sandboxed environment.
    Returns a dictionary with the output, errors, and status.
    """
    # 1. Security Check: Simple static analysis for forbidden imports
    for forbidden in FORBIDDEN_IMPORTS:
        if f"import {forbidden}" in code_string or f"from {forbidden}" in code_string:
            return {
                "output": "",
                "error": f"Error: The use of module '{forbidden}' is not allowed.",
                "status": "restricted"
            }

    # 2. Execute the code in a separate process
    try:
        # subprocess.run is used to execute the code.
        # preexec_fn=set_memory_limit is a hook to run our function in the child process
        # right before the student's code is executed. This is Unix-only.
        completed_process = subprocess.run(
            [sys.executable, "-c", code_string],
            capture_output=True,
            text=True,
            timeout=15,  # 5-second timeout
            preexec_fn=set_memory_limit if sys.platform != "win32" else None
        )
        
        output = completed_process.stdout
        error = completed_process.stderr

        if completed_process.returncode == 0:
            status = "success"
        else:
            status = "runtime_error"

    except subprocess.TimeoutExpired:
        output = ""
        error = "Error: Code execution timed out after 5 seconds."
        status = "timeout"
    except Exception as e:
        output = ""
        error = f"An unexpected error occurred: {e}"
        status = "system_error"

    return {"output": output, "error": error, "status": status}
