# Tutor con IA - TFG


#1.- npm create vite@latest -> React -> TypeScript

#2.- creamos la carpeta frontend, con sus respectivas sub-carpetas

#3.- usamos monaco editor porque nos permite pegar el codigo y trabajar sobre el como si estuvieramos en vscode

#4.- hacemos la UI para el frontend

#5.- creamos la carpeta backend, donde instalaremos un entorno virtual que nos permite no ensuciar y trabajar en nuestro ordenador con librerias
        mkdir backend; python3 -m venv venv

...........  5.1.- para ejecutar el entorno virtual source venv/bin/activate ( en la terminal sale a la izquierda (venv))

#6.- creamos el archivo requirements.txt, donde ponemos todas las dependencias que vamos a usar
    6.1.- con el entorno activado: pip install -r requirements.txt

#7.- creamos el main.py con el codigo que queramos

#8.- ejecutar el servidor web: .....................   uvicorn main:app --reload   ..........................................

#8.- en el front creamos el nuevo servicio para llamar a la api de python

#9.- conectamos el front (app.tsx) con el servicio para conectar el front con el back

#10.- creamos la api key en groq, y modificamos el main.py para hacer la llamada al llm y darle el contexto con el codigo del alumno y lo que nos dice por chat


#11.- Creamos el proyecto de supabase y una cuenta (luisarrabal5@gmail), y usando postgresql creamos la tabla donde se guardaran los apuntes

#12.- pip install -U google-generativeai pypdf supabase // para hacer el embedding de datos
#13.- usamos google ai studio mediante la api, para hacer el emedding

#14.- hacemos el script para embeber y subir los apuntes a supabase
    #14.- usamos la similitud del coseno para comparar los vectores ( lo que hace es sacar la distancia de dos vectores, y comprara entre sus valores y direccion [ + - ] )
    ##haciendo un script en supabase para hacer el coseno


#######################################
#######################################

¿Cuál es la diferencia entre search.py y tutor.py?
search.py: Se encarga exclusivamente de hablar con la base de datos y Google (buscar la teoría y calcular los porcentajes).

tutor.py: Se encarga exclusivamente de hablar con la IA (Groq y Langchain), importando la información que le da search.py.
############################################


#15.-Instalamos fastapi para crear un servidor web para que el front se comunique con el back   

#16.- resumen por ahora del flujo a pedir algo a la IA:

        React (api.ts) ➡️ main.py ➡️ routers/chat.py ➡️ tutor.py ➡️ search.py ➡️ Supabase ➡️ search.py ➡️ tutor.py ➡️ Groq (LLaMA) ➡️ tutor.py ➡️ routers/chat.py ➡️ React.