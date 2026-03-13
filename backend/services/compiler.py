import tempfile
import subprocess
import os
from langchain_core.tools import tool

# Endpoint de FastAPI
def compile_and_run_cpp(code: str) -> dict:
    with tempfile.TemporaryDirectory() as temp_dir:
        cpp_file_path = os.path.join(temp_dir, "main.cpp")
        exe_file_path = os.path.join(temp_dir, "main.out")

        with open(cpp_file_path, "w") as f:
            f.write(code)

        compile_process = subprocess.run(
            ["g++", cpp_file_path, "-o", exe_file_path],
            capture_output=True, text=True
        )

        if compile_process.returncode != 0:
            return {"output": "Error de compilación:\n" + compile_process.stderr, "isError": True}

        try:
            run_process = subprocess.run(
                [exe_file_path],
                capture_output=True, text=True, timeout=5
            )
            final_output = run_process.stdout
            
            if run_process.stderr:
                final_output += "\nAdvertencias:\n" + run_process.stderr
                
            return {
                "output": final_output if final_output else "Programa ejecutado.", 
                "isError": run_process.returncode != 0
            }
            
        except subprocess.TimeoutExpired:
            return {"output": "Error: Timeout.", "isError": True}

@tool
def compiler_tool(codigo: str) -> str:
    """
    Compila y ejecuta codigo C++.
    Usar para ver errores reales en consola.
    """
    resultado = compile_and_run_cpp(codigo)
    return resultado["output"]