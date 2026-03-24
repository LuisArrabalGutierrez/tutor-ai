import tempfile
import subprocess
import os
import re

PALABRAS_PROHIBIDAS = ["system(", "exec(", "popen(", "fork(", "remove(", "rename("]

def es_codigo_seguro(codigo: str) -> tuple[bool, str]:
    codigo_sin_espacios = codigo.lower().replace(" ", "") 
    for palabra in PALABRAS_PROHIBIDAS:
        if palabra.replace(" ", "") in codigo_sin_espacios:
            return False, f"Uso restringido: '{palabra}'"
    return True, ""

def compile_and_run_project(archivos: dict) -> dict:
    with tempfile.TemporaryDirectory() as temp_dir:
        cpp_files = []
        usa_makefile = False
        makefile_content = ""
        
        # Comprueba si hay Makefile
        for nombre, contenido in archivos.items():
            if nombre.lower().split('/')[-1] == "makefile":
                usa_makefile = True
                makefile_content = contenido
                break
        
        # Crea directorios y archivos
        for nombre_archivo, contenido in archivos.items():
            if nombre_archivo.endswith((".cpp", ".h", ".hpp", ".c")):
                seguro, msg = es_codigo_seguro(contenido)
                if not seguro:
                    return {"output": f"Bloqueo de seguridad en {nombre_archivo}: {msg}", "isError": True}
            
            ruta = os.path.join(temp_dir, nombre_archivo)
            os.makedirs(os.path.dirname(ruta), exist_ok=True)
            
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(contenido)
                
            if nombre_archivo.endswith(".cpp"):
                cpp_files.append(ruta)

        exe_file_path = os.path.join(temp_dir, "main.out")

        if usa_makefile:
            # Ejecuta make
            compile_process = subprocess.run(["make"], cwd=temp_dir, capture_output=True, text=True)
            
            if compile_process.returncode != 0:
                return {"output": "Error de Make:\n" + compile_process.stderr, "isError": True}
                
            # Verifica regla run
            tiene_make_run = bool(re.search(r'^run\s*:', makefile_content, re.MULTILINE))
            
            if tiene_make_run:
                # Ejecuta make run
                try:
                    run_process = subprocess.run(
                        ["make", "run"], 
                        capture_output=True, 
                        text=True, 
                        timeout=5,
                        cwd=temp_dir 
                    )
                    final_output = run_process.stdout
                    if run_process.stderr:
                        final_output += "\nLog:\n" + run_process.stderr
                        
                    return {
                        "output": final_output if final_output else "Ejecutado correctamente.", 
                        "isError": run_process.returncode != 0
                    }
                except subprocess.TimeoutExpired:
                    return {"output": "Error: Timeout.", "isError": True}
            else:
                # Busca ejecutable
                exe_encontrado = None
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        filepath = os.path.join(root, file)
                        if os.access(filepath, os.X_OK) and not file.endswith((".cpp", ".h", ".hpp", ".o", ".txt", ".csv", ".json")) and file.lower() != "makefile":
                            exe_encontrado = filepath
                            break
                    if exe_encontrado:
                        break
                        
                if exe_encontrado:
                    exe_file_path = exe_encontrado
                else:
                    return {"output": "Error: Ejecutable no encontrado.", "isError": True}
                
        else:
            # Compilacion manual
            if not cpp_files:
                return {"output": "Error: Faltan archivos .cpp.", "isError": True}

            compile_cmd = [
                "g++"
            ] + cpp_files + [
                "-I", temp_dir, 
                "-I", os.path.join(temp_dir, "include"),
                "-I", os.path.join(temp_dir, "src"),
                "-o", exe_file_path
            ]
            
            compile_process = subprocess.run(compile_cmd, capture_output=True, text=True)

            if compile_process.returncode != 0:
                return {"output": "Error de compilación:\n" + compile_process.stderr, "isError": True}

        # Ejecuta programa
        try:
            run_process = subprocess.run(
                [exe_file_path], 
                capture_output=True, 
                text=True, 
                timeout=5,
                cwd=temp_dir 
            )
            
            final_output = run_process.stdout
            if run_process.stderr:
                final_output += "\nLog:\n" + run_process.stderr
                
            return {
                "output": final_output if final_output else "Ejecutado correctamente.", 
                "isError": run_process.returncode != 0
            }
        except subprocess.TimeoutExpired:
            return {"output": "Error: Timeout.", "isError": True}