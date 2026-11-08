import sys, os, asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
from langchain_core.messages import AIMessage
from services import analyst


class FakeLLM:
    def __init__(self, content):
        self.content = content

    async def ainvoke(self, _prompt):
        return AIMessage(content=self.content)


class FakeSupabase:
    def __init__(self):
        self.actualizado = None

    def table(self, _nombre):
        return self

    def update(self, datos):
        self.actualizado = datos
        return self

    def eq(self, *_a):
        return self

    def execute(self):
        return None


JSON = '{"carencia": "punteros", "fortaleza": "bucles"}'


@pytest.mark.parametrize("contenido", [
    JSON,
    f"```json\n{JSON}\n```",
    [{"type": "text", "text": JSON}],           # formato de bloques de Gemini
    [JSON],
])
def test_el_analista_acepta_contenido_en_texto_o_en_bloques(monkeypatch, contenido):
    monkeypatch.setattr(analyst, "analyst_llm", FakeLLM(contenido))
    db = FakeSupabase()
    asyncio.run(analyst.update_student_profile("u1", [{"role": "user", "content": "no entiendo los punteros"}], {}, db))
    assert db.actualizado == {"carencias": "punteros", "fortalezas": "bucles"}


def test_sin_modelo_no_hace_nada(monkeypatch):
    monkeypatch.setattr(analyst, "analyst_llm", None)
    db = FakeSupabase()
    asyncio.run(analyst.update_student_profile("u1", [{"role": "user", "content": "hola que tal"}], {}, db))
    assert db.actualizado is None
