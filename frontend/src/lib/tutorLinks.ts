const APUNTES_PATH = '/storage/v1/object/public/apuntes/';
const SUPABASE_URL = ((import.meta.env.VITE_SUPABASE_URL as string | undefined) || '').replace(/\/+$/, '');

/** True si el enlace apunta al bucket público de apuntes de nuestro Supabase (la única cita oficial del tutor). */
export function isApuntesLink(href?: string): boolean {
  if (!href || !href.includes(APUNTES_PATH)) return false;
  return SUPABASE_URL ? href.startsWith(SUPABASE_URL) : true;
}

/** Convierte `<a href="url">texto</a>` (el LLM a veces devuelve HTML) en el Markdown `[texto](url)`. */
export function normalizeTutorMarkdown(text: string): string {
  return text.replace(
    /<a\s+[^>]*href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/gi,
    (_match, href: string, label: string) => {
      const limpio = label.replace(/<[^>]+>/g, '').trim();
      return `[${limpio || href}](${href})`;
    }
  );
}
