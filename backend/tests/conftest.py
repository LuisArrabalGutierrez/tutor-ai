import os

# Los tests no necesitan el servidor MCP precalentado: se arranca solo si algún test usa el chat
os.environ.setdefault("TUTOR_MCP_EAGER", "0")
