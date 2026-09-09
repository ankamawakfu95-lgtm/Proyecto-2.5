# Mejoras aplicadas — comprensión y conversación más humana

Resumen de qué se tocó y por qué. Los tres problemas de fondo que tenía el
proyecto para sonar "más humano" e inteligente eran: (1) el LLM recibía todo
aplastado en un solo bloque de texto en vez de turnos con rol, (2) el
historial de charla era brutalmente corto (2 turnos) y se descartaba sin más
al crecer, y (3) no había ninguna instancia de revisión antes de mandar la
respuesta final. Se atacaron los tres.

## 1. `backend/neural/language_model.py`
- Se agregó `chat(messages, **kwargs)`, que llama a `/api/chat` de Ollama en
  vez de `/api/generate`. Esto es lo más importante del cambio: `/api/chat`
  respeta el chat-template real del modelo (bloques `system` / `user` /
  `assistant` con sus tokens especiales), mientras que mandar todo como un
  string plano ("system...\nuser: ...\nassistant:") confunde al modelo
  instruct-tuned y produce respuestas más planas, repetitivas o que pierden
  el hilo. `generate()` se mantiene igual para completions de texto libre
  (documentos, síntesis de investigación, auto-mejora), que no la necesitan.
- Los parámetros de muestreo (`temperature`, `top_p`, `top_k`,
  `repeat_penalty`, `num_ctx`) ahora se leen de la config y se aplican
  siempre por defecto (antes `num_ctx` estaba configurado en `main.py` pero
  nunca se usaba realmente). Por defecto están tuneados para conversación
  natural (temperature 0.75, repeat_penalty 1.15 para evitar que se repita).

## 2. `backend/core/mateo_ultra_core.py`
- `_generate_response`, `_handle_programming_request` y
  `_handle_medical_request` ahora arman una **lista de turnos con rol**
  (`_build_chat_messages`) y llaman a `language_model.chat(...)` en vez de
  concatenar todo en un string y pedirle al modelo que "continúe" después de
  la palabra `assistant:`.
- **Historial e memoria de charla**: antes se mandaban los últimos 4
  mensajes (2 turnos) fijos, sin rol, y el resto se tiraba. Ahora:
  - `history_turns_in_prompt` (default 6) controla cuántos turnos recientes
    se mandan tal cual, con rol.
  - Cuando la charla supera `summarize_after_messages` (default 24
    mensajes), `_maybe_summarize_history` le pide al modelo un resumen
    breve (≤120 palabras) de lo más viejo, y ese resumen se inyecta como
    contexto persistente en el prompt de sistema. Así una charla larga no
    "resetea" el contexto de golpe: se comprime en vez de olvidarse.
- **Auto-revisión (`_reflect_and_refine`)**: para respuestas de charla
  normal, después de generar el borrador se lo pasa por una segunda pasada
  barata que chequea 4 cosas (¿responde lo que se preguntó?, ¿es coherente
  con la charla previa?, ¿suena natural o a plantilla?, ¿respeta el formato
  pedido?) y devuelve una versión pulida solo si hace falta corregir algo.
  Se puede apagar con `enable_reflection: false` si se prioriza velocidad
  sobre calidad (por ejemplo, en hardware más lento).
- El prompt de personalidad (`PERSONALITY_SYSTEM_PROMPT`) suma una sección
  de "COMPRENSIÓN REAL": priorizar la intención por sobre las palabras
  literales, usar el historial como memoria de trabajo real (no como
  resumen forzado), variar la forma de construir las frases entre turnos
  para no sonar a plantilla, y pensar en voz alta con naturalidad cuando el
  tema tiene matices, sin alargar la respuesta innecesariamente.

## 3. `backend/main.py`
- `get_default_config()` expone las nuevas perillas como variables de
  entorno: `MATEO_OLLAMA_TEMPERATURE`, `MATEO_OLLAMA_TOP_P`,
  `MATEO_OLLAMA_TOP_K`, `MATEO_OLLAMA_REPEAT_PENALTY`,
  `MATEO_HISTORY_TURNS`, `MATEO_SUMMARIZE_AFTER`, `MATEO_ENABLE_REFLECTION`.
  Todas tienen default razonable, no hace falta tocar nada para que
  funcione.

## 4. Integración de Tavily (búsqueda + aprendizaje) — 2026-09-05
- `backend/tools/web_learner.py` (punto único de búsqueda usado por
  `/buscar`, el ciclo de aprendizaje `core/learning_cycle.py` y el motor de
  auto-investigación `core/auto_research_engine.py`): ahora intenta primero
  **Tavily** (pensado para consumo por LLMs: devuelve contenido ya limpio y
  relevante, no HTML crudo) y si no hay `TAVILY_API_KEY` en el entorno, o la
  llamada falla por lo que sea (sin red, rate limit, etc.), cae solo a
  DuckDuckGo como antes — nada se rompe si Tavily no está disponible.
  Se agregó también `get_instant_answer(query)`, que pide a Tavily una
  respuesta ya sintetizada (`include_answer=True`).
- `backend/tools/external_apis.py`: `search_duckduckgo()` (se mantiene el
  nombre por compatibilidad, aunque ahora puede usar Tavily por debajo)
  muestra primero la **respuesta directa** de Tavily si hay una, y después
  las fuentes. `get_available_tools()` ahora reporta si Tavily está
  disponible según si hay clave configurada.
- `backend/main.py`: se agregó `MATEO_TAVILY_SEARCH_DEPTH` (`basic` por
  defecto, `advanced` busca más a fondo pero consume más créditos de la
  cuenta de Tavily) a la configuración documentada. La clave
  `TAVILY_API_KEY` se lee directo del entorno (no se duplica en el dict de
  config) — solo hace falta que esté en tu `.env`.

### Cómo activarlo
Tu archivo de entorno (el `_env` que subiste) ya tiene `TAVILY_API_KEY`.
Para que Mateo lo use, ese archivo tiene que llamarse `.env` (no `_env`) y
estar en `Mateo IA/backend/.env` o en `Mateo IA/.env` — `main.py` busca en
esos dos lugares al arrancar (usa `python-dotenv`, que ya estaba en
`requirements.txt`, no hace falta instalar nada nuevo). No hizo falta tocar
`learning_cycle.py` ni `auto_research_engine.py`: como ambos ya usan
`search_internet()` de `web_learner.py`, se benefician automáticamente sin
cambios propios.

### No se tocó
`NEWSAPI_KEY`, `OPENWEATHER_KEY` y `GEMINI_API_KEY` están en tu `.env` pero
`get_weather()`/`get_news()` siguen siendo stubs sin usarlos — no era parte
de este pedido (solo Tavily), pero quedan ahí listos si en algún momento
querés que los use.

## 5. Modelo por defecto: qwen2.5:1.5b + respaldo en la nube con Gemini — 2026-09-05
- `backend/main.py`: el default de `MATEO_OLLAMA_MODEL` pasó de `llama3.1:8b`
  a `qwen2.5:1.5b` (el que ya usás según tu `.env`), y lo mismo en el
  fallback interno de `neural/language_model.py`. Si tu `.env` ya trae
  `MATEO_OLLAMA_MODEL=qwen2.5:1.5b`, esto no cambia nada en la práctica;
  ahora también queda así aunque el `.env` no se cargue por algún motivo.
- `neural/language_model.py`: se agregó un **respaldo automático con
  Gemini** (`GEMINI_API_KEY`). El modelo principal sigue siendo siempre
  Ollama/qwen — Gemini solo entra si Ollama no responde (proceso caído,
  modelo no descargado, host inalcanzable) tanto en `generate()` como en
  `chat()`, para que un problema puntual del servidor local no deje a Mateo
  sin poder contestar. Usa el endpoint `generateContent` de Gemini con el
  alias `gemini-flash-latest` (configurable con `MATEO_GEMINI_MODEL`): ese
  alias sigue siempre al modelo flash vigente, para no repetir el problema
  que ya habías tenido antes con un nombre de modelo fijo (`gemini-1.5-flash`)
  que Google terminó dando de baja.
- `get_available_tools()` ahora reporta si Gemini está disponible como
  respaldo, igual que hace con Tavily.

## 6. Clima (OpenWeatherMap) y noticias (NewsAPI) reales — 2026-09-05
- `backend/tools/external_apis.py`:
  - `get_weather()` ahora consulta OpenWeatherMap de verdad (clima actual:
    temperatura, sensación térmica, humedad, viento) usando `OPENWEATHER_KEY`.
    Si la ciudad no se puede extraer del mensaje, pide que se aclare; si la
    ciudad no existe para la API, lo avisa en vez de fallar en silencio.
  - `get_news()` ahora consulta NewsAPI (`/v2/everything`, en español, las 5
    más recientes) usando `NEWSAPI_KEY`. Si no hay clave, o la consulta
    falla, cae automáticamente a la búsqueda web normal (Tavily/DuckDuckGo)
    en vez de devolver un error.
  - `get_available_tools()` reporta si cada una está configurada.

## 7. Modo Agente autónomo, inspirado en AgentGPT — 2026-09-06
- Nuevo `backend/core/agent_engine.py`: motor de agente que planifica y
  ejecuta objetivos de varios pasos, portando la idea central de AgentGPT
  (planificar → elegir herramienta → ejecutar → proponer tarea de
  seguimiento → resumir) pero reimplementada 100% local sobre el mismo
  Ollama que ya usa Mateo. No se agregó Node.js, LangChain, Pinecone, AWS
  ni ninguna clave nueva; el "AgentGPT" original de la carpeta subida es
  una plataforma SaaS completa (Next.js + Prisma + OpenAI) pensada para
  correr en la nube, no algo para pegar tal cual en un proyecto local-first.
  - Herramientas que el agente puede elegir por subtarea: `buscar_web`
    (Tavily/DuckDuckGo), `wikipedia`, `calculadora`, `memoria_obsidian`
    (la propia bóveda de Mateo) y `razonar` (el modelo resuelve
    directamente con lo ya reunido).
  - Topes duros de seguridad: máximo 5 tareas iniciales, máximo 8 pasos
    totales por ejecución, deduplicación simple de tareas repetidas — un
    objetivo mal planteado nunca deja al agente corriendo indefinidamente
    ni golpeando la web sin límite.
  - Al terminar, arma un informe final en markdown usando solo lo que
    reunió (nunca completa con información inventada) y opcionalmente lo
    guarda como nota en la bóveda de Obsidian (categoría `projects`, tag
    `agente_autonomo`).
- `core/mateo_ultra_core.py`: nuevo comando `/agente [objetivo]`
  (clasificación de intención + manejo en `_execute_tool`), agregado a
  `/ayuda`, y nuevo contador `agent_runs` en `/estadisticas`.
- `api.py`: nuevo endpoint `POST /agent/run` (goal, max_steps,
  save_to_obsidian) para uso programático — devuelve el desglose completo
  de pasos y el informe final como JSON, sin pasar por el formato de chat.
- `frontend/UI NEW.HTML`: nuevo botón `/agente · Modo Agente 🤖` en la
  barra lateral, y aviso en el chat de que una tarea de agente puede
  tardar más que una respuesta normal (son varias llamadas al modelo en
  cadena, no una sola).

### Ejemplo de uso
```
/agente investigá las ventajas de Rust sobre C++ para sistemas embebidos y armame un resumen con fuentes
```

### Qué NO hace este modo (a propósito)
- No modifica código (para eso ya existe `/automejora`, con su propio
  flujo de proponer + confirmar).
- No navega páginas web ni hace clic en nada (a diferencia de agentes
  tipo "computer use"): solo busca, lee resultados de texto y razona.
- No corre en segundo plano ni se dispara solo: siempre requiere el
  comando explícito `/agente`, igual que `/automejora`.

## 8. Bugs reales encontrados en un log de uso y arreglados — 2026-09-07
A partir de una sesión real que mostró varios fallos, se diagnosticaron y arreglaron 4 problemas
concretos (no hipotéticos: cada uno se reprodujo con un test antes de arreglarse):

1. **Búsqueda web rota de raíz.** El paquete `duckduckgo_search` fue renombrado a `ddgs` (el propio
   paquete lo avisa por warning) y dejó de traer resultados confiables. Como el código atrapaba
   cualquier excepción y devolvía `[]` en silencio, tanto `/aprender` como el nuevo Modo Agente
   fallaban con un genérico "no encontré información" sin ninguna pista del motivo real.
   - `tools/web_learner.py`: ahora prueba primero `ddgs` (el paquete activo) y cae a
     `duckduckgo_search` solo por compatibilidad; y loggea la excepción real en vez de tragarla.
   - `requirements.txt`: `duckduckgo-search` → `ddgs`.
2. **Clasificación de intención demasiado agresiva.** El patrón `\bfuncion que\b` (pensado para "creá
   una función que sume...") también disparaba con preguntas puramente descriptivas ("dime sobre esta
   función que hace X"), mandando la charla a Modo Programador y haciendo que el modelo alucinara
   código genérico sin relación con el proyecto real.
   - `core/mateo_ultra_core.py`: los patrones ambiguos (`función que`, `clase que`, `test`) ya no
     disparan Modo Programador si el mensaje es una pregunta descriptiva ("qué hace", "cómo
     funciona", "contame sobre", etc.).
3. **Mateo no puede consultar su propio código, así que inventaba.** Al preguntarle qué hace el Motor
   de Agente, no tenía forma de leer `agent_engine.py` y completó con un ejemplo de auto genérico que
   no existe en el proyecto.
   - Nuevo registro `SELF_FEATURES` en `mateo_ultra_core.py`: hechos verificados y reales sobre cada
     módulo propio (Modo Agente, Auto-mejora, memoria de Obsidian, ciclo de aprendizaje, investigación
     en segundo plano). Preguntas descriptivas sobre estos módulos ahora se responden ancladas a ese
     hecho real (nuevo tipo de intención `self_feature` + `_handle_self_feature_query`), no al Modo
     Programador ni a una alucinación libre.
4. **Temas de aprendizaje larguísimos y mal armados.** Pedidos como "quiero que investigues en
   internet información actualizada 2026 sobre agentes autónomos y aprendas todo lo que te sea útil
   para tu desarrollo" quedaban casi intactos tras la extracción por regex, y esa frase entera se
   usaba como consulta de búsqueda — pésimo resultado incluso si la búsqueda funcionara bien.
   - Nuevo método `_compress_topic`: si el tema extraído tiene más de 8 palabras, se le pide al
     propio modelo que lo comprima a 3-6 palabras antes de buscar. Si falla, se sigue con el tema
     original en vez de romper el flujo.
5. **La auto-revisión (`_reflect_and_refine`) leakeaba su propio proceso interno — el bug que más se
   nota como "respuesta rota".** En el log real, dos respuestas de chat normal salieron con
   `"Borrador de respuesta: ..."` como prefijo, y una tercera reemplazó la respuesta real por una
   evaluación tipo rúbrica (`**Análisis:** ... **Estrategia:** ... **Criterios Revisado:** ...`) que
   literalmente repetía los 4 criterios que el prompt de revisión le pedía aplicar, en vez de
   aplicarlos en silencio. Esto es un fallo típico de modelos chicos con instrucciones "meta"
   (evaluar un texto en vez de solo reescribirlo).
   - `REFLECTION_SYSTEM_PROMPT` reescrito: ya no le pide "evaluar contra estos criterios" (estructura
     fácil de repetir en voz alta), sino directamente "dejalo listo para mandarse", con ejemplos
     explícitos de qué NO hacer.
   - Nuevas funciones `_clean_response_text` (saca etiquetas sueltas tipo "Borrador de respuesta:" al
     principio) y `_is_meta_commentary` (detecta cuando la auto-revisión devolvió una rúbrica en vez
     de una respuesta) — si esto último pasa, se descarta y se usa el borrador original, que es
     sistemáticamente mejor que una rúbrica. Se probó con un modelo simulado que reproduce el bug
     exacto del log: la rúbrica ya no llega al usuario.
   - `PERSONALITY_SYSTEM_PROMPT` reescrito más corto y concreto, con ejemplos de tono positivos y un
     ejemplo explícito de qué NO hacer (los modelos chicos siguen ejemplos mucho mejor que reglas
     abstractas, que es lo que tenía la versión anterior).

### Qué NO se resolvió (limitación real, no hay forma barata de arreglarlo)
El modelo local por defecto (`qwen2.5:1.5b`) es chico: incluso con estos arreglos, en tareas de
razonamiento largo puede seguir sonando algo mecánico o cometer errores de gramática ocasionales
(se vio en el log: mezcla de español e inglés en una respuesta de código). Los prompts ahora reducen
mucho la superficie de fallo, pero no hay prompt que compense del todo un modelo de ese tamaño. Si
la calidad de las respuestas sigue sin convencer, la palanca más efectiva es probar un modelo Ollama
más grande (`qwen2.5:7b` o similar) en vez de seguir ajustando el prompt.

## Qué más no se tocó (del pedido original de comprensión/fluidez)
- La lógica de clasificación de intención (`_classify_query`, regex), el
  motor de auto-mejora, el ciclo de aprendizaje y la memoria de Obsidian
  (RAG) quedaron igual: el pedido era mejorar comprensión y fluidez
  conversacional, no reescribir el enrutamiento de comandos ni el sistema
  de memoria de largo plazo.

## v2.4 — Personalidad "amigo multitarea" (2026-09-07)
Pedido: que Mateo se sienta natural, ingenioso, creativo y que sorprenda — no un asistente formulaico.

1. **`PERSONALITY_SYSTEM_PROMPT` reescrito** con ejemplos concretos de ingenio (comparaciones
   inesperadas, humor que nace de la charla real) en vez de solo "sonar natural". Incluye ejemplos de
   qué NO hacer: chistes forzados metidos con calzador, exclamaciones vacías, recordar que es una IA
   sin que se lo pidan.
2. **`REFLECTION_SYSTEM_PROMPT` ajustado**: además de corregir errores, ahora empuja hacia más
   personalidad cuando el borrador suena "correcto pero soso" (genérico, sin voz propia) — y protege
   explícitamente un chiste o frase con onda que ya funcionaba, para que la revisión no se lo "prolijice"
   y lo aplane.
3. **Temperatura de muestreo separada por modo**: nuevas `chat_temperature` (default 0.95, charla
   normal — más variedad e imprevisibilidad) y `precise_temperature` (default 0.3, modo programador y
   modo médico — donde la precisión importa más que la sorpresa). Antes los tres modos usaban el mismo
   valor general (`ollama_temperature`, pensado como término medio). Configurables sin tocar código vía
   `MATEO_CHAT_TEMPERATURE` y `MATEO_PRECISE_TEMPERATURE` en `.env`.

### Ideas para una próxima vuelta (no implementadas todavía)
- Callbacks espontáneos a notas viejas de la bóveda de Obsidian, no solo contexto relevante al tema.
- Probabilidad baja de que Mateo agregue un comentario u observación propia no pedida.
- Variar más el largo de respuesta según si la pregunta es liviana o pesada (hoy usa un tope de tokens
  bastante fijo).

## v2.5 — Reparación tras charla cruzada con otra IA (2026-09-08)
Se hizo hablar a Mateo con otra IA (de puente, Leonardo) para ver si la personalidad de v2.4 se
notaba en la práctica. Aparecieron 3 bugs reales, los tres arreglados:

1. **Clasificador de intención con falsos positivos graves.** El patrón viejo
   (`\b(wikipedia|quien es|que es)\b`) disparaba con que la palabra apareciera en cualquier parte
   del mensaje, sin importar el contexto. Al pedirle "contame algo, **no** un dato de Wikipedia",
   activaba igual la búsqueda en Wikipedia — literalmente lo opuesto a lo pedido. Y "que es" es una
   superposición tan común en español que preguntas autorreferenciales tipo "¿qué es lo que más te
   copa hacer?" también caían ahí por error. Arreglado: ahora respeta una negación explícita cerca
   de "wikipedia" y exige que "quién es"/"qué es" venga con signo de pregunta y no sea
   autorreferencial.
2. **Ejemplo del prompt "quemado".** Al pedirle "algo random", repitió CASI TEXTUAL el ejemplo de
   los pulpos que estaba en `PERSONALITY_SYSTEM_PROMPT` — memorizó el contenido del ejemplo en vez
   de aprender el estilo. Arreglado: el prompt ahora rota entre 3 variantes de ejemplo elegidas al
   azar (`_personality_system_prompt()` en vez de la constante fija) y se sumó una instrucción
   explícita de no repetir literalmente el contenido de los ejemplos.
3. **Tics que violaban las propias reglas del prompt** ("¡Vale!" de arranque, "Saludos!" de cierre,
   pregunta de reflejo al final) pese a que el prompt ya pedía explícitamente no hacerlo — un modelo
   de 7B no sigue reglas de "no hagas X" de forma confiable solo con prompting. Se agregó
   `_strip_assistant_tics()` como red de seguridad mecánica (regex), aplicada en el mismo punto
   donde ya corría `_clean_response_text()`, que saca interjecciones vacías de arranque y sign-offs
   formales sin tocar el contenido real de la respuesta.

Los 3 fixes probados con casos que reproducen exactamente lo visto en la charla real, no solo
revisión de código.

## Requisito para que se note el cambio
Todo esto depende de que el modelo servido por Ollama soporte bien el
endpoint `/api/chat` con su chat-template (los modelos `instruct`/`chat`
modernos como `llama3.1:8b-instruct` lo soportan). Si `MATEO_OLLAMA_MODEL`
apunta a un modelo base sin fine-tune de chat, el salto de calidad va a ser
menor porque el modelo en sí no fue entrenado para seguir turnos de rol.
