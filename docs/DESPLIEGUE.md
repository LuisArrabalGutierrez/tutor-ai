1. Visión General y Arquitectura del Sistema
El presente documento detalla la infraestructura y el pipeline de despliegue continuo (CI/CD) diseñado para el módulo de "Terminal Linux" del proyecto Tutor AI. El objetivo de esta arquitectura es proveer a los alumnos de un entorno de terminal seguro, aislado y accesible desde cualquier navegador web, sin requerir configuraciones locales.

El sistema se compone de los siguientes bloques arquitectónicos:

Frontend (Vercel): Interfaz de usuario (SPA) que renderiza la terminal en el navegador y se comunica mediante WebSockets.

Túnel Inverso (Ngrok): Pasarela de red que expone el servidor local de forma segura a internet mediante encriptación SSL/TLS, solventando las restricciones de contenido mixto (Mixed Content) de los navegadores.

Backend (FastAPI + Uvicorn): Servidor alojado en Google Cloud Platform (GCP) que gestiona las peticiones de los alumnos y orquesta los contenedores.

Motor de Aislamiento (Docker): Sistema de contenerización que crea un entorno Ubuntu efímero e independiente para cada conexión de alumno.

Gestor de Procesos (PM2): Demonio que garantiza la alta disponibilidad (uptime) del backend y del túnel de red.

2. Preparación del Servidor (Host)
El despliegue se realiza sobre una instancia de Google Cloud Platform (Compute Engine) ejecutando Ubuntu 24.04 LTS.

2.1. Optimización de Memoria (SWAP)
Debido a las limitaciones de memoria RAM típicas en instancias de bajo coste (e2-micro o similares), procesos pesados como la construcción de imágenes Docker (docker build) pueden provocar bloqueos (Out Of Memory - OOM). Para mitigarlo, se configuró un archivo de paginación (Swap) de 2GB:

Bash
# Creación y habilitación del archivo Swap
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
Nota: Este paso es crítico. Sin este Swap, el servidor se "congela" al instalar dependencias pesadas como gcc o desempaquetar las librerías de Ubuntu durante la creación del contenedor.

2.2. Instalación de Dependencias Base
Bash
# Actualización del sistema e instalación de herramientas
sudo apt update
sudo apt install -y python3 python3-venv python3-pip docker.io npm curl

# Instalación del gestor de procesos PM2
sudo npm install -g pm2

# Instalación de Ngrok
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install ngrok
3. Configuración del Aislamiento (Docker)
Para que el alumno (ej. "el alumno de Cuenca") pueda ejecutar comandos sin poner en riesgo la máquina virtual principal, se diseñó una imagen Docker personalizada.

3.1. Especificación del Entorno (Dockerfile)
Ruta: backend/docker/Dockerfile

Dockerfile
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Madrid

# Resolución de problemas de red (Timeout) en GCP forzando IPv4
RUN echo 'Acquire::ForceIPv4 "true";' > /etc/apt/apt.conf.d/99force-ipv4
RUN sed -i 's/archive.ubuntu.com/es.archive.ubuntu.com/g' /etc/apt/sources.list

# Instalación del stack tecnológico para el alumno
RUN apt-get update && \
    apt-get install -y \
    build-essential gcc g++ make nano vim python3 python3-pip curl \
    && rm -rf /var/lib/apt/lists/*

# Securización: Creación de un usuario no-root
RUN useradd -ms /bin/bash alumno
WORKDIR /home/alumno
USER alumno

CMD ["/bin/bash"]
3.2. Construcción de la Imagen
Bash
cd ~/tutor-ai/backend/docker
docker build -t tutor-ugr-image:latest .
Esta imagen se queda en caché en el servidor, permitiendo que las nuevas terminales de los alumnos se lancen en milisegundos.

3.3. Contenedores que crea la aplicación
La API crea y destruye estos contenedores sola; no hay que lanzarlos a mano:

Nombre | Cuántos | Para qué | Límites
tutor_warm_0..2 | 3 | Compilar desde /api/execute. Cada uno se destruye y se recrea tras usarse | sin red, 256 MB (sin swap), 0,5 CPU, 64 procesos, sin capabilities, usuario alumno
tutor_mcp_0..1 | 2 (MCP_POOL_SIZE) | Compilar cuando lo pide el tutor por MCP. Los crea el servidor MCP, un proceso hijo de la API | los mismos
tutor_term_<id> | 1 por terminal abierta, máx. 10 (MAX_TERMINALS) | Terminal Linux interactiva | sin red, 512 MB, 1 CPU, 100 procesos, sin capabilities, usuario 1000:1000

Con la API parada no debe quedar ningún contenedor tutor_*; si la API muere de golpe, el siguiente arranque elimina los huérfanos por nombre. En una VM pequeña, el consumo de memoria de estos contenedores es bajo mientras están inactivos, pero cada terminal abierta puede llegar a 512 MB: ajusta MAX_TERMINALS y MCP_POOL_SIZE según la RAM disponible.

4. Gestión de Red y Alta Disponibilidad (PM2 + Ngrok)
Para que el sistema sea autónomo y no dependa de terminales SSH abiertas, se implementó PM2. Además, se utilizó Ngrok con un dominio estático para asegurar que la URL del servidor nunca cambie y posea certificado WSS (WebSocket Secure).

4.1. Inicialización Limpia de Procesos
Para evitar conflictos de puertos o conexiones de WebSocket fallidas (Error 143 o duplicación de procesos), se estableció el siguiente flujo:

Bash
# Limpieza de procesos huérfanos o duplicados
pm2 delete all

# 1. Arranque del Backend (FastAPI) en el puerto 8000
cd ~/tutor-ai/backend
source venv/bin/activate
pm2 start "./venv/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 8000" --name backend

# 2. Arranque del Túnel Ngrok con dominio estático vinculado al puerto 8000
pm2 start "ngrok http --domain=tu-dominio.ngrok-free.dev 8000" --name ngrok
4.2. Persistencia ante Reinicios
Para garantizar que los servicios se restauren automáticamente si Google Cloud reinicia la máquina por mantenimiento:

Bash
pm2 save
pm2 startup
(Se debe ejecutar el comando sudo env PATH... que devuelve PM2 para registrar el demonio en el sistema operativo).

5. Automatización Continua (CI/CD con GitHub Actions)
El flujo está en .github/workflows/deploy.yml y tiene tres trabajos:

backend-tests: en cada push y pull request a main instala las dependencias de backend/requirements.txt, construye la imagen del sandbox y ejecuta pytest tests/ -m "not llm".
frontend-checks: ejecuta npm ci, npm run lint y npm run build en frontend/.
deploy: solo en un push a main y solo si los dos anteriores pasan, entra por SSH en la VM y despliega.

Los tests marcados llm (chat real con Gemini y Groq) no se ejecutan en la CI porque necesitan claves y consumen cuota.

5.1. Script de despliegue (trabajo deploy)
Secretos necesarios en GitHub (Settings > Secrets and variables > Actions): SSH_HOST, SSH_USER, SSH_PRIVATE_KEY y NGROK_DOMAIN.

Bash
cd ~/tutor-ai
git reset --hard origin/main
git pull origin main

# Reconstruir la imagen del sandbox
cd backend/docker && docker build -t tutor-ugr-image:latest .

# Dependencias del backend (versiones fijadas en requirements.txt)
cd ~/tutor-ai/backend
[ -d venv ] || python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Reiniciar servicios
pm2 restart backend || pm2 start "./venv/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 8000" --name backend
pm2 restart ngrok || pm2 start "ngrok http --domain=$NGROK_DOMAIN 8000" --name ngrok
pm2 save

Estrategia adoptada: el script es idempotente (usa ||); si los procesos existen, los reinicia ordenadamente; si el servidor es nuevo o los procesos murieron, los crea desde cero. Al reiniciar el backend, la API vuelve a lanzar el servidor MCP y los pools de contenedores.

6. Configuración del Frontend (Vercel)
El frontend está programado para ser agnóstico a la IP real del servidor de Google Cloud.

En el panel de Vercel > Environment Variables, se ha configurado:

VITE_GOOGLE_IP = tu-dominio.ngrok-free.dev

El código fuente lee esta variable y establece dinámicamente la conexión wss:// (WebSocket Seguro). Esto evita que navegadores como Chrome o Safari bloqueen la conexión por políticas de "Mixed Content" al intentar conectar una web segura (https) con una IP insegura (http).

7. Resolución de Problemas Frecuentes (Troubleshooting)
A lo largo del desarrollo se documentaron los siguientes bloqueos y sus soluciones para futuras referencias:

Problema: El comando docker build se queda congelado indefinidamente mostrando done. tras instalar paquetes APT.

Causa: Falta de memoria RAM en el servidor host.

Solución: Habilitar un archivo Swap de 2GB (sección 2.1).

Problema: Error en la consola del frontend: WebSocket connection to 'wss://...' failed.

Causa: Conflicto de red originado por tener múltiples instancias de ngrok o backend compitiendo por el puerto 8000 en PM2.

Solución: Ejecutar pm2 delete all y reconstruir los procesos uno a uno para asegurar una única instancia por servicio.

Problema: Error de Docker: Unable to find image 'tutor-ugr-image:latest' locally.

Causa: El backend intenta lanzar un contenedor cuya imagen no ha sido construida en ese servidor.

Solución: Asegurar que el paso docker build -t tutor-ugr-image:latest . esté incluido y se ejecute correctamente dentro del pipeline de CI/CD.