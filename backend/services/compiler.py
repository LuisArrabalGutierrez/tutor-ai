import tempfile
import subprocess
import os

# Esta función se encarga de compilar y ejecutar el código C++ que el alumno tiene en su editor.
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
            return {"output": "❌ Error de compilación:\n" + compile_process.stderr, "isError": True}

        try:
            run_process = subprocess.run(
                [exe_file_path],
                capture_output=True, text=True, timeout=5
            )
            final_output = run_process.stdout
            if run_process.stderr:
                final_output += "\n⚠️ Advertencias:\n" + run_process.stderr
                
            return {
                "output": final_output if final_output else "Programa ejecutado con éxito (sin salida por consola).", 
                "isError": run_process.returncode != 0
            }
        except subprocess.TimeoutExpired:
            return {"output": "⏳ Error: Tiempo de ejecución excedido (Timeout). ¿Bucle infinito?", "isError": True}