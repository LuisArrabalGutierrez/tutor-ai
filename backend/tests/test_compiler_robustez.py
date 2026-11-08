import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
from fastapi.testclient import TestClient
from main import app
from services.compiler import _write_project, _build_script


def _ejecutar(archivos):
    with TestClient(app) as client:
        r = client.post("/api/execute", json={"archivos": archivos}, headers={"X-Forwarded-For": "203.0.113.55"})
    return r


def test_error_de_ejecucion_muestra_lo_que_imprimio_el_programa():
    r = _ejecutar({"main.cpp": '#include <iostream>\nint main(){ std::cout << "antes del fallo"; return 3; }'})
    data = r.json()
    assert data["isError"] is True
    assert "antes del fallo" in data["output"] and "código de salida 3" in data["output"]


def test_error_de_compilacion_muestra_el_mensaje_del_compilador():
    data = _ejecutar({"main.cpp": "int main() { return 0 }"}).json()
    assert data["isError"] is True and "error" in data["output"].lower() and "main.cpp" in data["output"]


def test_stderr_del_programa_aparece_aunque_termine_bien():
    data = _ejecutar({"main.cpp": '#include <iostream>\nint main(){ std::cerr << "aviso"; return 0; }'}).json()
    assert data["isError"] is False and "aviso" in data["output"]


def test_salida_infinita_se_corta_y_no_llena_la_memoria():
    data = _ejecutar({"main.cpp": '#include <cstdio>\nint main(){ for(;;) printf("xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\\n"); }'}).json()
    assert data["isError"] is True
    assert "Salida cortada" in data["output"]
    assert len(data["output"]) < 100_000


def test_nombre_de_archivo_con_metacaracteres_no_ejecuta_comandos():
    nombre = "a b;echo HACKEADO.cpp"
    data = _ejecutar({nombre: '#include <iostream>\nint main(){ std::cout << "ok"; }'}).json()
    assert "HACKEADO" not in data["output"].replace(nombre, "")


@pytest.mark.parametrize("ruta", ["../fuera.cpp", "/etc/passwd", "a/../../b.cpp", "..", ""])
def test_la_api_rechaza_rutas_peligrosas(ruta):
    r = _ejecutar({ruta: "x"})
    assert r.status_code == 422


def test_la_api_rechaza_proyectos_demasiado_grandes():
    r = _ejecutar({"main.cpp": "a" * (3 * 1024 * 1024)})
    assert r.status_code == 422


def test_el_chat_tambien_valida_las_rutas():
    with TestClient(app) as client:
        r = client.post("/api/chat", json={"historial": [{"role": "user", "content": "hola"}], "archivos": {"../x": "y"}})
    assert r.status_code == 422


def test_write_project_no_escribe_fuera_del_directorio(tmp_path):
    with pytest.raises(ValueError):
        _write_project(str(tmp_path), {"../escapa.txt": "x"})
    assert not (tmp_path.parent / "escapa.txt").exists()


def test_build_script_sin_fuentes_devuelve_none():
    assert _build_script({"notas.txt": "x"}, False) is None
