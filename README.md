# 🎓 Tutor IA Socrático - TFG

Un entorno de desarrollo integrado (IDE) web asistido por un Tutor de Inteligencia Artificial Socrático. Diseñado específicamente para ayudar a los alumnos de la Universidad de Granada (UGR) en asignaturas como **Metodología de la Programación (C++)** y **Sistemas Unix/Linux**.

Este proyecto implementa una arquitectura de microservicios con ejecución segura de código (Sandboxing) y un sistema de Recuperación de Información (RAG) basado en los apuntes oficiales.

---

## 🚀 Arquitectura y Tecnologías Clave

El sistema se divide en dos entornos independientes, comunicados mediante API REST y WebSockets:

### Frontend (IDE Interactivo)
* **React + TypeScript + Vite:** Base del desarrollo ágil y tipado seguro.
* **Monaco Editor:** Proporciona la experiencia de Visual Studio Code directamente en el navegador.
* **React Markdown & Syntax Highlighter:** Renderizado de las respuestas de la IA con formato académico y colores de código.
* **JSZip:** Generación dinámica de archivos comprimidos para descargar proyectos al instante.

### Backend (Orquestador IA y Sandboxing)
* **FastAPI (Python):** Servidor asíncrono de altísimo rendimiento.
* **Protocolo MCP (Model Context Protocol):** Desacopla las herramientas de la IA, permitiendo un código modular.
* **Groq (LLaMA 3.3 70B):** Motor principal de inferencia. Elegido por su velocidad ultra-baja (LPU) y capacidad de *Tool Calling*.
* **Supabase (PostgreSQL) + Google Generative AI:** Base de datos vectorial para el sistema RAG (Búsqueda por similitud de coseno).
* **Docker:** Sandbox de seguridad para la ejecución de código C++ y terminal interactiva de Linux.
* **DuckDuckGoSearch:** Búsqueda web gratuita y anti-scraping para complementar la teoría.

---

## 🛡️ Seguridad y Robustez (Grado de Producción)

El sistema ha sido fortificado contra ataques comunes de alumnos y cuellos de botella:

1. **Aislamiento de Ejecución (Docker Sandbox):** El código C++ de los alumnos se compila y ejecuta en contenedores efímeros sin acceso a internet (`--network none`), con límite de memoria RAM (256MB) y procesador.
2. **Prevención de Bucles Infinitos:** Implementación de *Timeouts* estrictos (5 segundos) para abortar procesos bloqueantes.
3. **Protección Anti-Spam (DoS):** Integración de `SlowAPI` con Rate Limiting (Máximo 5 peticiones por minuto por IP) para proteger los costes de la API de Groq.
4. **Prevención OOM (Out Of Memory):** Validación previa en la subida de apuntes en PDF, bloqueando instantáneamente archivos superiores a 10MB antes de cargarlos en RAM.

---

## ⚙️ Guía de Instalación Rápida

### Prerrequisitos
* Node.js (v18+)
* Python (3.11+)
* Docker Desktop (En ejecución)
* Claves de API: Supabase, Groq y Google Gemini.

### 1. Configuración del Frontend
cd frontend
npm install
npm run dev
### 2. Configuración del Backend
Abre una nueva terminal:

Bash
cd backend
# 1. Crear y activar el entorno virtual
python3 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Descargar la imagen de C++ para el Sandbox (Solo la primera vez)
docker pull gcc:latest

# 4. Iniciar el servidor
uvicorn main:app --reload
Nota: Recuerda crear un archivo .env en la carpeta backend/ con las variables: GROQ_API_KEY, GOOGLE_API_KEY, SUPABASE_URL y SUPABASE_KEY.

### 🧪 Suite de Pruebas Automatizadas (Testing)
El backend cuenta con una suite integral de pruebas desarrollada con pytest, dividida en cuatro módulos principales:

test_compiler.py: Valida la compilación (Makefiles, múltiples headers) y el bloqueo de red.

test_ia.py: Comprueba el enrutamiento del chat y el funcionamiento del limitador Anti-Spam.

test_archivos.py: Verifica la subida de PDFs y el límite de RAM.

test_terminal.py: Asegura la conectividad del túnel WebSocket de Linux.

Para ejecutar todas las pruebas, colócate en la carpeta backend/ (con el entorno virtual activado) y ejecuta:

pytest tests/ -v


### 🧠 Flujo de Datos del Tutor Socrático
El camino que recorre un mensaje desde que el alumno lo envía hasta que recibe respuesta:

Frontend: React empaqueta la pregunta, los archivos de código actuales y el contexto de la terminal (api.ts).

API: FastAPI recibe el payload, valida la IP (Rate Limiter) y pasa los datos al agente.

Agente IA: tutor.py construye el prompt con etiquetas <XML> y decide la estrategia usando LLaMA 3.3.

Herramientas (MCP): * Si es teoría: Llama a search.py, vectoriza la duda (Google AI) y busca en Supabase.

Si es web: Llama a DuckDuckGo.

Respuesta Estricta: La IA genera la respuesta obligando a usar un formato literal para los enlaces ([Doc](URL)).

Renderizado: React recibe el Markdown y aplica coloreado de sintaxis a las explicaciones.