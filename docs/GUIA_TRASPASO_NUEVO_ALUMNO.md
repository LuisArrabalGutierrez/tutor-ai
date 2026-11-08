# 📘 Guía de Traspaso y Puesta en Marcha - Tutor IA (TFG)

Bienvenido/a al proyecto **Tutor IA Socrático**. Este documento contiene todo lo necesario para que puedas desplegar, ejecutar y modificar el proyecto al completo utilizando **tus propias cuentas gratuitas** (Supabase, Google AI Studio y Groq), garantizando total independencia técnica sin costes asociados ($0).

---

## 🎯 1. Arquitectura General del Sistema

El proyecto está compuesto por dos partes principales:
1. **Frontend (`/frontend`)**: Single Page Application desarrollada con React, TypeScript, Vite, Monaco Editor (entorno tipo VS Code en navegador) y terminal interactiva xterm.js.
2. **Backend (`/backend`)**: API asíncrona de alto rendimiento con FastAPI, orquestador de agentes de IA con LangGraph/LangChain, sistema RAG con búsqueda por similitud vectorial (pgvector) y ejecución segura de código C++ y terminal Linux en contenedores Docker aislados.

---

## 🔑 2. Cuentas y API Keys Necesarias (100% Gratuitas)

Para que el proyecto funcione en tu ordenador o servidor, solo necesitas registrarte en 3 plataformas gratuitas:

| Servicio | Finalidad | Dónde obtener la clave |
| :--- | :--- | :--- |
| **Google AI Studio** | LLM principal del tutor (Gemini) y embeddings del RAG (`gemini-embedding-001`, 768 dimensiones) | [aistudio.google.com](https://aistudio.google.com) (Crear API Key) |
| **Groq Cloud** | LLM de respaldo del tutor (entra si falla Gemini) y modelo rápido para el análisis pedagógico | [console.groq.com](https://console.groq.com) (Sección *API Keys*) |
| **Supabase** | Base de datos PostgreSQL con `pgvector`, autenticación de alumnos y almacenamiento de PDFs | [supabase.com](https://supabase.com) (Crear nuevo proyecto) |

---

## 🚀 3. Paso a Paso: Configuración desde Cero

### Paso 3.1: Inicializar tu Base de Datos en Supabase

1. Crea una cuenta y un nuevo proyecto gratuito en [Supabase](https://supabase.com).
2. En el menú lateral izquierdo de tu proyecto, entra en **SQL Editor** > **New Query**.
3. Abre el archivo [`backend/supabase_setup.sql`](file:///home/luis/Escritorio/clase/TFG/tutor-ai/backend/supabase_setup.sql) de este repositorio, copia todo su contenido, pégalo en el editor SQL de Supabase y pulsa **Run**.
   * Esto activará la extensión `pgvector`.
   * Creará la tabla `apuntes` con índice HNSW optimizado.
   * Creará la función almacenada `match_apuntes` para la búsqueda semántica.
   * Creará la tabla `perfiles` y el trigger que enlaza el registro de usuarios con su perfil pedagógico.
4. En el menú lateral, ve a **Storage** > **New Bucket**:
   * Nombre del bucket: `apuntes` *(exactamente este nombre)*.
   * **Marca la casilla "Public Bucket"** (imprescindible para que los alumnos puedan abrir las diapositivas citadas por el tutor).
5. Ve a **Project Settings** (icono de engranaje) > **API** y ten a mano:
   * **Project URL**
   * **anon / public key**
   * **service_role key** *(clave secreta de servidor)*

---

### Paso 3.2: Configurar Variables de Entorno (`.env`)

#### Backend:
En la carpeta `backend/`, copia la plantilla y crea tu `.env`:
```bash
cd backend
cp .env.example .env
```
Edita `backend/.env` con tus claves:
```env
GROQ_API_KEY=gsk_...
GROQ_MODEL=openai/gpt-oss-20b
GROQ_FAST_MODEL=openai/gpt-oss-20b

GOOGLE_API_KEY=AIzaSy...
GEMINI_MODEL=gemini-flash-lite-latest

SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_KEY=tu_supabase_service_role_key
```

#### Frontend:
En la carpeta `frontend/`, copia la plantilla y crea tu `.env`:
```bash
cd ../frontend
cp .env.example .env
```
Edita `frontend/.env`:
```env
VITE_API_URL=http://127.0.0.1:8000
VITE_SUPABASE_URL=https://tu-proyecto.supabase.co
VITE_SUPABASE_ANON_KEY=tu_supabase_anon_public_key
# Para desarrollo local, deja VITE_GOOGLE_IP vacío (usará ws://localhost:8000 automáticamente)
VITE_GOOGLE_IP=
```

---

### Paso 3.3: Ingesta de Documentos y Vectorización (Pipeline RAG)

El repositorio ya incluye todos los apuntes oficiales de la UGR organizados en `backend/apuntes_pdf/` (FP, FS y MP).

Hemos preparado un script unificado que automatiza tanto la subida a Supabase Storage como la vectorización en la base de datos:

1. Asegúrate de tener tu entorno virtual activo con las dependencias instaladas:
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. Ejecuta el asistente de inicialización RAG:
   ```bash
   python setup_rag.py
   ```
3. Elige la **Opción 1 (Configuración COMPLETA)**. El script:
   * Subirá automáticamente todos los PDFs al bucket `apuntes` de Supabase Storage.
   * Procesará las diapositivas, eliminará encabezados y generará los embeddings con Google Gemini.
   * Guardará los vectores en PostgreSQL.
   * Realizará una búsqueda semántica de prueba para validar que el tutor puede responder citando diapositivas exactas.

> **Nota sobre cuotas:** Si usas la capa gratuita de Google, el script incluye control de pausas automático (*backoff*) en caso de alcanzar el límite de peticiones por minuto (error 429).

---

## 💻 4. Ejecución en Local (Desarrollo y Modificación)

### 1. Construir la imagen Docker para la terminal y compilación C++
Docker es indispensable para que los alumnos ejecuten código C++ y usen la terminal de forma aislada y segura:
```bash
# Con Docker Desktop o el servicio Docker arrancado:
cd backend/docker
docker build -t tutor-ugr-image:latest .
```

### 2. Iniciar el Backend
```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```
La API estará disponible en `http://localhost:8000` (documentación Swagger interactiva en `http://localhost:8000/docs`).

### 3. Iniciar el Frontend
En otra terminal:
```bash
cd frontend
npm install
npm run dev
```
Abre en tu navegador `http://localhost:5173`. ¡Ya tienes el Tutor IA funcionando al 100% con tu infraestructura!

---

## 🧪 5. Verificación con Tests Automatizados

Para comprobar que todo el sistema (compilador C++, seguridad de Docker, RAG de IA, WebSocket de la terminal y rate limiting) está en perfecto estado, corre la suite de pruebas:

```bash
cd backend
pytest tests/ -v
```
Todos los tests (13/13) deben finalizar en verde (`PASSED`).

---

## ☁️ 6. Despliegue en Servidor (Opcional)

Si deseas desplegar el backend en un servidor propio (Google Cloud Compute Engine, Hetzner, AWS EC2, DigitalOcean, etc.) y el frontend en Vercel:
* Consulta la guía completa de producción en [`DESPLIEGUE.md`](file:///home/luis/Escritorio/clase/TFG/tutor-ai/DESPLIEGUE.md).
* Si utilizas GitHub Actions para CI/CD continuo, configura los secretos del repositorio en *Settings > Secrets and variables > Actions*:
  * `SSH_HOST`: IP de tu servidor.
  * `SSH_USER`: Tu usuario SSH en la máquina remota.
  * `SSH_PRIVATE_KEY`: Clave privada SSH.
  * `NGROK_DOMAIN`: Tu dominio estático de Ngrok (para túnel SSL seguro con WebSockets).
