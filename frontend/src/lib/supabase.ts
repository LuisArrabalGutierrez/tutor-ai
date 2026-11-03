import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://placeholder.supabase.co';
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || 'placeholder-anon-key';

if (!import.meta.env.VITE_SUPABASE_URL) {
  console.warn('⚠️ [Supabase] VITE_SUPABASE_URL no está configurada. La autenticación estará deshabilitada temporalmente.');
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey);