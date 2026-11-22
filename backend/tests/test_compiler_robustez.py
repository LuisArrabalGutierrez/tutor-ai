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


def test_run_no_se_cuelga_si_otro_proceso_sigue_escribiendo_tras_cortar():
    """Regresión: al cortar la salida se mata al cliente, pero un proceso hijo puede seguir escribiendo.
    asyncio pausa la tubería con el búfer lleno, nunca lee el EOF y proc.wait() no volvía."""
    import asyncio
    from services.compiler import _run

    async def inundar():
        # stderr cerrado desde el principio; `yes` sobrevive 2 s a la muerte de bash
        orden = "exec 2>&-; timeout 2 yes " + "x" * 200 + " & wait"
        return await asyncio.wait_for(_run("bash", "-c", orden, max_output=1024), timeout=10)

    _, out, _, cortado = asyncio.run(inundar())
    assert cortado is True and len(out) == 1024


def test_makefile_puede_escribir_en_subcarpetas_del_proyecto():
    """Regresión: `docker cp` dejaba los archivos con el uid del host y el alumno no podía escribir en src/."""
    data = _ejecutar({
        "Makefile": "main: src/main.o\n\tg++ -o main src/main.o\nsrc/main.o: src/main.cpp\n\tg++ -c src/main.cpp -o src/main.o\n",
        "src/main.cpp": '#include <fstream>\n#include <iostream>\nint main(){ std::ofstream f("src/datos.txt", std::ios::app); f << 1; std::cout << (f.good() ? "escrito" : "sin permiso"); }',
        "src/datos.txt": "0",
    }).json()
    assert data["isError"] is False, data["output"]
    assert "escrito" in data["output"]


def test_los_archivos_copiados_son_del_usuario_del_contenedor():
    data = _ejecutar({
        "main.cpp": '#include <cstdlib>\nint main(){ return system("test \\"$(stat -c %u dir/a.txt)\\" = \\"$(id -u)\\" && echo MISMO_USUARIO"); }',
        "dir/a.txt": "x",
    }).json()
    assert "MISMO_USUARIO" in data["output"], data["output"]


ESCRIBE_1GIB = """#include <cstdio>
#include <cstring>
#include <fcntl.h>
#include <unistd.h>
int main() {
    static char b[1 << 20]; memset(b, 7, sizeof b);
    int fd = open("RUTA", O_WRONLY | O_CREAT | O_TRUNC, 0600);
    if (fd < 0) { printf("OPEN_FALLA\\n"); return 0; }
    for (int mb = 1; mb <= 1024; ++mb)
        if (write(fd, b, sizeof b) != (ssize_t)sizeof b) { printf("WRITE_FALLA_EN_MB=%d\\n", mb); return 0; }
    printf("SIN_LIMITE\\n");
}
"""


@pytest.mark.parametrize("ruta", ["/tmp/relleno.bin", "relleno.bin"])
def test_el_programa_no_puede_llenar_el_disco(ruta):
    """F-3: sin --read-only y tmpfs el alumno escribía 1 GiB en la capa del contenedor (disco del host)."""
    data = _ejecutar({"main.cpp": ESCRIBE_1GIB.replace("RUTA", ruta)}).json()
    assert "SIN_LIMITE" not in data["output"], data["output"]
    assert "WRITE_FALLA_EN_MB=" in data["output"], data["output"]
    mb = int(data["output"].split("WRITE_FALLA_EN_MB=")[1].split()[0])
    assert mb <= 64


def test_el_programa_no_puede_escribir_en_su_home():
    data = _ejecutar({"main.cpp": ESCRIBE_1GIB.replace("RUTA", "/home/alumno/x.bin")}).json()
    assert "OPEN_FALLA" in data["output"], data["output"]


def test_makefile_con_varios_objetos_en_subcarpetas_compila_en_el_tmpfs():
    data = _ejecutar({
        "Makefile": (
            "main: obj/a.o obj/b.o obj/main.o\n\tg++ -o main obj/a.o obj/b.o obj/main.o\n"
            "obj/%.o: src/%.cpp\n\tmkdir -p obj && g++ -O2 -c $< -o $@\n"
        ),
        "src/a.cpp": "int a(){ return 1; }",
        "src/b.cpp": "int b(){ return 2; }",
        "src/main.cpp": '#include <iostream>\nint a(); int b();\nint main(){ std::cout << "suma=" << a() + b(); }',
    }).json()
    assert data["isError"] is False, data["output"]
    assert "suma=3" in data["output"]
