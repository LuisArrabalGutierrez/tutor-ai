import tempfile
import subprocess
import os

def compile_and_run_project(archivos: dict) -> dict:
    with tempfile.TemporaryDirectory(dir=os.getcwd()) as temp_dir:
        usa_makefile = False
        
        for nombre_archivo, contenido in archivos.items():
            if nombre_archivo.lower() == "makefile":
                usa_makefile = True
            
            ruta = os.path.join(temp_dir, nombre_archivo)
            os.makedirs(os.path.dirname(ruta), exist_ok=True)
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(contenido)

        # 2. Construir el script que se ejecutará DENTRO de Docker
        if usa_makefile:
            # Hacemos que bash sea inteligente y busque el ejecutable en la raíz, en dist/ o en bin/
            script_interno = (
                "make > compile_log.txt 2>&1 && "
                "if [ -f ./main ]; then ./main; "
                "elif [ -f ./dist/main ]; then ./dist/main; "
                "elif [ -f ./bin/main ]; then ./bin/main; "
                "else echo '🚨 Error: Ejecutable no encontrado. El Makefile debe generar un archivo main, dist/main o bin/main.'; exit 1; fi"
            )
        else:
            archivos_cpp = " ".join([f for f in archivos.keys() if f.endswith(('.cpp', '.c'))])
            if not archivos_cpp:
                return {"output": "Error: No se encontraron archivos fuente (.cpp).", "isError": True}
            script_interno = f"g++ {archivos_cpp} -I. -o programa.out > compile_log.txt 2>&1 && ./programa.out"


        # Mapear el usuario actual a Docker para evitar crear archivos propiedad de root
        uid = os.getuid()
        gid = os.getgid()

        docker_cmd = [
            "docker", "run", "--rm",
            "--user", f"{uid}:{gid}",  
            "--network", "none",       
            "--memory", "256m",        
            "--cpus", "0.5",           
            "-v", f"{temp_dir}:/app",  
            "-w", "/app",              
            "tutor-ugr-image:latest",              
            "bash", "-c", script_interno
        ]

        try:
            run_process = subprocess.run(
                docker_cmd, 
                capture_output=True, 
                text=True, 
                timeout=40
            )
            
            log_compilacion = ""
            ruta_log = os.path.join(temp_dir, "compile_log.txt")
            if os.path.exists(ruta_log):
                with open(ruta_log, "r") as log_file:
                    log_compilacion = log_file.read()

            if run_process.returncode != 0:
                error_msg = log_compilacion if log_compilacion else run_process.stderr
                return {"output": f"🚨 Error de Compilación o Ejecución:\n{error_msg}", "isError": True}

            LIMITE_SALIDA = 40000
            salida = run_process.stdout[:LIMITE_SALIDA]
            if len(run_process.stdout) > LIMITE_SALIDA:
                salida += "\n... [Salida truncada por límite de seguridad]"
                
            return {"output": salida if salida else "[Programa finalizado con éxito]", "isError": False}

        except subprocess.TimeoutExpired:
            return {"output": "⏳ Error: Límite de tiempo excedido.", "isError": True}
        except Exception as e:
            return {"output": f"Error interno: {str(e)}", "isError": True}