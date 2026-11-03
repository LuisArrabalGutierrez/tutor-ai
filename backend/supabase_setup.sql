-- ====================================================================
-- ESQUEMA COMPLETO DE BASE DE DATOS PARA TUTOR IA (SUPABASE / POSTGRESQL)
-- ====================================================================
-- Instrucciones:
-- 1. Ve a tu proyecto de Supabase: https://supabase.com/dashboard
-- 2. Entra en "SQL Editor" (icono de consola a la izquierda).
-- 3. Pega todo este script y pulsa "Run" (ejecutar).
-- ====================================================================

-- 1. Habilitar la extensión pgvector para almacenar y buscar embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Tabla para almacenar los fragmentos de apuntes y sus vectores
CREATE TABLE IF NOT EXISTS public.apuntes (
    id BIGSERIAL PRIMARY KEY,
    tema TEXT NOT NULL,
    contenido TEXT NOT NULL,
    embedding VECTOR(768),
    asignatura TEXT NOT NULL,
    diapositiva INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Índice HNSW optimizado para búsqueda por similitud de coseno
CREATE INDEX IF NOT EXISTS apuntes_embedding_hnsw_idx 
ON public.apuntes 
USING hnsw (embedding vector_cosine_ops);

-- 3. Función RPC (Remote Procedure Call) para búsqueda semántica RAG
CREATE OR REPLACE FUNCTION match_apuntes (
  query_embedding VECTOR(768),
  match_threshold FLOAT,
  match_count INT
)
RETURNS TABLE (
  id BIGINT,
  tema TEXT,
  contenido TEXT,
  asignatura TEXT,
  diapositiva INT,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    apuntes.id,
    apuntes.tema,
    apuntes.contenido,
    apuntes.asignatura,
    apuntes.diapositiva,
    (1 - (apuntes.embedding <=> query_embedding))::FLOAT AS similarity
  FROM public.apuntes
  WHERE (1 - (apuntes.embedding <=> query_embedding)) > match_threshold
  ORDER BY apuntes.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- 4. Tabla de perfiles pedagógicos de los alumnos (seguimiento de carencias y fortalezas)
CREATE TABLE IF NOT EXISTS public.perfiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    carencias TEXT DEFAULT 'Ninguna detectada',
    fortalezas TEXT DEFAULT 'Ninguna detectada',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Políticas de seguridad RLS para perfiles
ALTER TABLE public.perfiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Los usuarios pueden consultar su propio perfil" 
ON public.perfiles FOR SELECT 
USING (auth.uid() = id);

CREATE POLICY "Los usuarios pueden actualizar su propio perfil" 
ON public.perfiles FOR UPDATE 
USING (auth.uid() = id);

-- 5. Trigger automático: Al registrarse un usuario en Supabase Auth, se crea su fila en 'perfiles'
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.perfiles (id, carencias, fortalezas)
  VALUES (new.id, 'Ninguna detectada', 'Ninguna detectada')
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();

-- 6. Configuración de Storage para los PDFs:
-- En el panel de Supabase:
--   a) Ve a "Storage" > "New Bucket".
--   b) Nómbralo exactamente: apuntes
--   c) Marca la casilla "Public Bucket" (para que los alumnos puedan descargar y visualizar los PDFs citados).
