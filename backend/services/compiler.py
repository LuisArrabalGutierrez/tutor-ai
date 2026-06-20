import tempfile
import subprocess
import os
import uuid
from services.warm_pool import pool

# Crear una carpeta local en tu proyecto para evitar el aislamiento de Snap/Ubuntu
LOCAL_TEMP_DIR = os.path.join(os.getcwd(), "temp_workspaces")
os.makedirs(LOCAL_TEMP_DIR, exist_ok=True)

async def compile_and_run_project(archivos: dict) -> dict:
    container_name = await pool.get_container()
    session_id = str(uuid.uuid4())
    container_workdir = f"/tmp/{session_id}"

    # Forzamos a tempfile a usar nuestra carpeta local en lugar del /tmp del sistema
    with tempfile.TemporaryDirectory(dir=LOCAL_TEMP_DIR) as temp_dir:
        usa_makefile = False
        for nombre, contenido in archivos.items():
            if nombre.lower() == "makefile": usa_makefile = True
            ruta = os.path.join(temp_dir, nombre)
            os.makedirs(os.path.dirname(ruta), exist_ok=True)
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(contenido)

        if usa_makefile:
            script_interno = (
                "make > compile_log.txt 2>&1 && "
                "if [ -f ./main ]; then timeout 10 ./main; "
                "elif [ -f ./dist/main ]; then timeout 10 ./dist/main; "
                "elif [ -f ./bin/main ]; then timeout 10 ./bin/main; "
                "else echo '🚨 Error: Ejecutable no encontrado.'; exit 1; fi"
            )
        else:
            fuentes = " ".join([f for f in archivos.keys() if f.endswith(('.cpp', '.c'))])
            if not fuentes:
                pool.return_container(container_name)
                return {"output": "Error: No hay archivos .cpp", "isError": True}
            script_interno = f"g++ {fuentes} -I. -o programa.out > compile_log.txt 2>&1 && timeout 10 ./programa.out"

        try:
            # Crear directorio en el contenedor
            subprocess.run(
                ["docker", "exec", container_name, "mkdir", "-p", container_workdir], 
                check=True, capture_output=True, text=True
            )
            
            # Copiar archivos desde nuestra carpeta local al contenedor
            subprocess.run(
                ["docker", "cp", f"{temp_dir}/.", f"{container_name}:{container_workdir}/"], 
                check=True, capture_output=True, text=True
            )
            
            # Compilar
            res = subprocess.run(
                ["docker", "exec", "-w", container_workdir, container_name, "bash", "-c", script_interno], 
                capture_output=True, text=True, timeout=40
            )
            
            # Extraer log de compilación
            cat_log = subprocess.run(
                ["docker", "exec", "-w", container_workdir, container_name, "cat", "compile_log.txt"], 
                capture_output=True, text=True
            )
            
            if res.returncode != 0:
                output = cat_log.stdout if cat_log.stdout else res.stderr
                return {"output": f"🚨 Error:\n{output}", "isError": True}

            return {"output": res.stdout if res.stdout else "[Éxito]", "isError": False}

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            return {"output": f"🚨 Error interno Docker:\n{error_msg}", "isError": True}
        except Exception as e:
            return {"output": f"Error de sistema: {str(e)}", "isError": True}
        finally:
            # Limpiar entorno en el contenedor
            subprocess.run(["docker", "exec", container_name, "rm", "-rf", container_workdir], capture_output=True)
            pool.return_container(container_name)