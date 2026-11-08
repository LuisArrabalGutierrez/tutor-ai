#!/usr/bin/env python3
"""
setup_rag.py - Asistente integral para inicializar el RAG en un nuevo entorno Supabase.

Funcionalidades:
1. Verifica la conexión con Supabase y Google Gemini (API Keys).
2. Sube automáticamente todos los PDFs de apuntes_pdf/ al bucket 'apuntes' de Supabase Storage.
3. Vectoriza e indexa los apuntes (FP, FS, MP) en la tabla 'apuntes' con embeddings de 768 dimensiones.
4. Realiza una búsqueda de prueba para verificar que el pipeline RAG funciona correctamente.
"""

import os
import sys
import glob
import time
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno del backend
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def check_credentials():
    print("==================================================")
    print("🔍 1. COMPROBANDO CREDENCIALES...")
    print("==================================================")
    faltan = []
    if not GOOGLE_API_KEY:
        faltan.append("GOOGLE_API_KEY")
    if not SUPABASE_URL:
        faltan.append("SUPABASE_URL")
    if not SUPABASE_KEY:
        faltan.append("SUPABASE_KEY")

    if faltan:
        print(f"❌ Error: Faltan las siguientes variables en backend/.env: {', '.join(faltan)}")
        print("Por favor, rellena tu backend/.env basándote en backend/.env.example")
        sys.exit(1)
    
    print("✅ Variables de entorno detectadas correctamente.")

def upload_pdfs_to_storage(supabase):
    print("\n==================================================")
    print("📤 2. SUBIENDO APUNTES PDF A SUPABASE STORAGE...")
    print("==================================================")
    base_dir = Path(__file__).resolve().parent / "apuntes_pdf"
    carpetas = ["MP", "FP", "FS"]
    total_subidos = 0
    total_errores = 0

    for carpeta in carpetas:
        ruta_carpeta = base_dir / carpeta
        if not ruta_carpeta.exists():
            continue
        archivos = list(ruta_carpeta.glob("*.pdf"))
        print(f"\n📂 Asignatura {carpeta} ({len(archivos)} PDFs encontrados):")
        for pdf_path in archivos:
            nombre = pdf_path.name
            try:
                with open(pdf_path, "rb") as f:
                    file_bytes = f.read()
                
                # Subir archivo al bucket 'apuntes' (con upsert)
                res = supabase.storage.from_("apuntes").upload(
                    path=nombre,
                    file=file_bytes,
                    file_options={"upsert": "true", "content-type": "application/pdf"}
                )
                print(f"  ✓ Subido: {nombre}")
                total_subidos += 1
            except Exception as e:
                # Si el error es que ya existe o fallo en storage, lo reportamos
                err_str = str(e)
                if "Duplicate" in err_str or "already exists" in err_str:
                    print(f"  ℹ️ Ya existía en Storage: {nombre}")
                else:
                    print(f"  ⚠️ Error al subir {nombre}: {e}")
                    total_errores += 1

    print(f"\nResumen Storage: {total_subidos} archivos procesados.")
    if total_errores > 0:
        print("⚠️ Nota: Asegúrate de haber creado el bucket público 'apuntes' en Supabase Storage.")

def run_ingestion():
    print("\n==================================================")
    print("🧠 3. VECTORIZANDO APUNTES EN POSTGRESQL (PGVECTOR)...")
    print("==================================================")
    backend_dir = Path(__file__).resolve().parent

    scripts = [
        ("Metodología de la Programación (MP)", backend_dir / "ingestMP.py"),
        ("Fundamentos de Programación (FP)", backend_dir / "ingestFP.py"),
        ("Fundamentos del Software (FS)", backend_dir / "ingestFS.py"),
    ]

    for nombre, script in scripts:
        if not script.exists():
            print(f"⚠️ Script no encontrado: {script.name}")
            continue
        print(f"\n▶️ Ejecutando vectorización de {nombre} ({script.name})...")
        os.system(f"{sys.executable} '{script}'")

def test_rag_search():
    print("\n==================================================")
    print("🧪 4. PRUEBA DE BÚSQUEDA RAG (VERIFICACIÓN FINAL)...")
    print("==================================================")
    try:
        from services.search import search_theory_logic
        pregunta_test = "¿Cómo funciona la memoria dinámica y los punteros en C++?"
        print(f"Pregunta: \"{pregunta_test}\"")
        resultado = search_theory_logic(pregunta_test)
        print("\nResultado RAG obtenido del sistema:")
        print("--------------------------------------------------")
        print(resultado[:350] + ("..." if len(resultado) > 350 else ""))
        print("--------------------------------------------------")
        if "Diapositiva" in resultado or "http" in resultado:
            print("🎉 ¡TODO CONFIGURADO Y FUNCIONANDO A LA PERFECCIÓN!")
        else:
            print("ℹ️ Búsqueda completada. Si no devuelve enlaces, revisa si los apuntes fueron vectorizados.")
    except Exception as e:
        print(f"❌ Error al ejecutar prueba de búsqueda: {e}")

def main():
    check_credentials()
    try:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"❌ Error conectando a Supabase: {e}")
        sys.exit(1)

    print("\nSelecciona qué acción deseas realizar:")
    print("1) Configuración COMPLETA (Subir PDFs a Storage + Vectorizar todo + Test)")
    print("2) Solo subir PDFs a Supabase Storage")
    print("3) Solo ejecutar vectorización (RAG pgvector)")
    print("4) Solo verificar búsqueda RAG")

    if len(sys.argv) > 1:
        opcion = sys.argv[1].strip()
    else:
        try:
            opcion = input("\nElige una opción (1-4) [default: 1]: ").strip() or "1"
        except EOFError:
            opcion = "1"

    if opcion == "1":
        upload_pdfs_to_storage(supabase)
        run_ingestion()
        test_rag_search()
    elif opcion == "2":
        upload_pdfs_to_storage(supabase)
    elif opcion == "3":
        run_ingestion()
        test_rag_search()
    elif opcion == "4":
        test_rag_search()
    else:
        print("Opción no válida.")

if __name__ == "__main__":
    main()


