import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
from tutor import _es_saludo_o_charla


@pytest.mark.parametrize("texto", ["Hola", "hola buenas tardes", "¿Qué tal?", "buenos días a todos", "hey!", "ayuda", ""])
def test_saludos_puros_usan_fast_path(texto):
    assert _es_saludo_o_charla(texto) is True


@pytest.mark.parametrize("texto", [
    "necesito ayuda con punteros",
    "hola tengo un error",
    "hola, ¿cómo funciona new y delete en C++?",
    "they said hello",
    "ayuda con mi código",
    "hola buenas tardes tengo una duda",
])
def test_consultas_con_contenido_no_son_saludo(texto):
    assert _es_saludo_o_charla(texto) is False
