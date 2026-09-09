# 🤖 Mateo AI Ultra v2.1

**Mateo AI Ultra** es un asistente de IA local-first: conversa usando un modelo de lenguaje que corre en tu propia máquina (Ollama), mantiene una memoria semántica ligera en disco y usa herramientas externas puntuales solo cuando el mensaje lo pide explícitamente. No requiere ninguna API key para conversar.

> La interfaz oficial es un único archivo HTML (`frontend/UI NEW.HTML`), servido directamente por el backend en `/ui`. No hay build ni dependencias de Node para usarlo.

> "Creado por Leonardo con ❤️ para hacer del mundo un lugar mejor"

---

## ✨ Características Principales

### 🧠 Motor de Lenguaje
- **Ollama local**: genera respuestas usando un modelo local (por defecto `llama3.1:8b`), sin conexión a internet ni API key.
- **Modo fallback**: si Ollama no está disponible, Mateo lo indica en vez de fallar en silencio.
- **Modos de personalidad**: prompts especializados para conversación general, programación (Modo Programador Avanzado) y apoyo clínico (Modo Médico, pensado para Leonardo como profesional tratante).

### 📊 Memoria Semántica Ligera
- **Almacén vectorial propio**: guarda documentos en un `documents.json` local y busca por similitud de tokens (intersección de palabras), sin depender de FAISS ni de modelos de embeddings.
- **Memoria de Obsidian**: indexa notas Markdown de tu bóveda y las recupera por coincidencia de términos y título, priorizando notas más recientes.
- Es una memoria simple y explicable, no una búsqueda semántica por embeddings — funciona bien para bóvedas curadas, pero no capta sinónimos ni parafraseos.

### 🔌 Herramientas Externas
- **Wikipedia** (idioma español): resumen real vía API pública.
- **Búsqueda web**: DuckDuckGo (`duckduckgo-search`), sin necesidad de API key.
- **Calculadora**: evaluación aritmética segura (AST, sin `eval()`).
- **Clima y noticias**: puntos de extensión ya definidos en el código (`ExternalAPIManager`), pero **no conectados todavía** a un proveedor real — hoy devuelven un mensaje indicando que falta configuración, o redirigen a la búsqueda web.

### 🎯 Capacidades actuales
- ✅ Conversación con memoria de corto plazo (historial de la sesión)
- ✅ **Modo Agente** (`/agente [objetivo]`): planifica varias subtareas, elige y combina herramientas (búsqueda web, Wikipedia, calculadora, su propia memoria de Obsidian) para cada una, y arma un informe final — inspirado en AgentGPT pero corriendo 100% local sobre Ollama, sin claves ni servicios adicionales
- ✅ Búsqueda y aprendizaje autónomo: investiga un tema en la web y lo guarda como nota en Obsidian
- ✅ Motor de investigación en segundo plano (ciclos de 30 min activos / 30 min de descanso)
- ✅ Motor de auto-mejora en dos pasos: **propone** cambios y solo los **aplica si el usuario confirma explícitamente** el id de la propuesta; nunca se dispara con lenguaje natural suelto
- ✅ Cálculos matemáticos seguros
- ✅ Carga de archivos (PDF, Word, Excel, CSV, texto) como contexto de memoria
- ✅ Generación de archivos (PDF, Word, Excel, Markdown) desde el chat o por API
- ✅ Voz: transcripción (STT) y síntesis (TTS) 100% locales — el instalador incluye `requirements-voice.txt`
- ✅ Autenticación opcional por API key para los endpoints que modifican estado
- ⚠️ Clima, noticias y traducción: parcialmente implementados o pendientes de proveedor

---

## 📎 Archivos: cargar y generar

**Cargar un archivo** (desde la UI con el botón 📎, o directamente por API):

```bash
curl -F "file=@informe.pdf" http://localhost:8000/upload
```

Extrae el texto (PDF, Word, Excel, CSV, texto plano) y lo agrega a la memoria vectorial de Mateo, para que pueda usarlo como contexto en la conversación.

**Generar un archivo**, ya sea pidiéndoselo por chat ("genera un documento sobre...", "genera un pdf de...") o directo por API:

```bash
curl -X POST "http://localhost:8000/generate-file?title=Mi+informe&content=Contenido...&format=docx"
# Descargar:
curl -O http://localhost:8000/files/<nombre_devuelto>.docx
```

Formatos soportados: `docx`, `pdf`, `xlsx`, `md`, `txt`.

---

## 🎙️ Voz (100% local)

Instalación:

```bash
pip install -r requirements.txt
```

Configurá en `.env`:

```env
MATEO_WHISPER_MODEL=base
MATEO_WHISPER_DEVICE=cpu
MATEO_WHISPER_COMPUTE_TYPE=int8
MATEO_PIPER_VOICE_MODEL=C:\ruta\a\tu\voz\es_ES-modelo.onnx
```

- El instalador descarga y configura automáticamente una voz española Piper de aproximadamente 60 MB.
- Si usás el instalador, no necesitas descargar manualmente el modelo ni editar `MATEO_PIPER_VOICE_MODEL`.
- También puedes descargar otra voz desde https://github.com/rhasspy/piper/blob/master/VOICES.md y cambiar `MATEO_PIPER_VOICE_MODEL` en `.env`.
- faster-whisper descarga su modelo automáticamente la primera vez que se usa
- Por defecto la transcripción usa CPU (`int8`), para no requerir CUDA ni sus DLL. Solo configura `MATEO_WHISPER_DEVICE=cuda` si tu equipo tiene CUDA instalada.

Podés comprobar si están disponibles con `GET /voice-status`. En la UI, el botón 🎤 graba y transcribe tu mensaje, y el botón 🔊 junto a cada respuesta de Mateo la lee en voz alta.

---

## 🤖 Modo Agente: objetivos de varios pasos

`/agente [objetivo]` planifica hasta 5 subtareas, ejecuta cada una con la herramienta que
más conviene (búsqueda web, Wikipedia, cálculo, su propia bóveda de Obsidian, o razonamiento
directo), puede proponer una tarea adicional sobre la marcha, y termina con un informe final
en markdown que solo usa la información realmente reunida. Ejemplo:

```
/agente investigá las ventajas de Rust sobre C++ para sistemas embebidos y armame un resumen con fuentes
```

Tiene topes duros (máximo 8 pasos por ejecución) para que un objetivo mal planteado nunca deje
al agente corriendo indefinidamente. También hay un endpoint dedicado para uso programático:

```bash
curl -X POST http://localhost:8000/agent/run \
  -H "Content-Type: application/json" \
  -d '{"goal": "Comparar Postgres y MongoDB para un proyecto con datos muy relacionales", "save_to_obsidian": true}'
```

A diferencia de `/automejora`, el Modo Agente nunca modifica el código de Mateo ni navega
páginas web — solo busca, lee resultados de texto y razona.

---

## 🚀 Auto-mejora: cómo confirmarla

`/automejora [area]` (área opcional: `prompts`, `tools`, `classification`, `memory`, `learning_cycle`, `all`) analiza el código y devuelve una lista de propuestas con un id cada una — **no modifica nada todavía**. Para aplicar una propuesta puntual:

```
/automejora confirmar si_1_121236
```

Cada propuesta pasa por lista blanca de archivos, validación de sintaxis (AST) y un sandbox que ejecuta el fragmento en un subproceso aislado antes de aplicarlo; se crea un backup automático de cada archivo modificado en `backend/backups/auto_improvement/`. Aun así, ningún chequeo automático reemplaza una revisión humana del diff antes de confirmar.

---

## 🚀 Instalación Rápida (Windows)

### Opción 1: Instalador Automático (Recomendado)

1. **Descarga el proyecto** y extrae el ZIP
2. **Haz doble clic en** `Instalar_Mateo.bat`
3. **Espera** a que se instalen las dependencias de Python
4. **Haz doble clic en** `Iniciar_Mateo.bat` para ejecutar

### Opción 2: Instalación Manual

#### Requisitos
- Python 3.8 o superior
- [Ollama](https://ollama.com) instalado y corriendo localmente (`ollama serve`), con el modelo configurado descargado (`ollama pull llama3.1:8b` o el que elijas)
- No hace falta Node.js: el frontend es un HTML estático servido por el propio backend

#### Pasos

```bash
# 1. Clonar o descargar el proyecto
cd "Mateo IA"

# 2. Crear entorno virtual
python -m venv venv

# 3. Activar entorno virtual
venv\Scripts\activate

# 4. Instalar dependencias
pip install -r backend\requirements.txt

# 5. Iniciar Mateo
Iniciar_Mateo.bat
```

---

## 🎮 Uso

### Interfaz Web (Recomendado)

1. Ejecuta `Iniciar_Mateo.bat`
2. Selecciona opción 1 (Interfaz Web)
3. Abre tu navegador en http://localhost:8000/ui

### Modo Terminal

1. Ejecuta `Iniciar_Mateo.bat`
2. Selecciona opción 2 (Terminal)
3. Escribe tus mensajes directamente

---

## 💬 Ejemplos de Uso

### Preguntas Generales
```
"¿Qué es la inteligencia artificial?"
"Investiga sobre la teoría de la relatividad"
```

### Cálculos
```
"Calcula 125 * 48 / 12"
```

### Búsqueda / Wikipedia
```
"¿Qué es el cambio climático? Wikipedia"
"Busca en la web las últimas noticias de tecnología"
```

---

## ⚙️ Configuración

Edita el archivo `.env` en la carpeta principal (o usa la opción correspondiente del menú de inicio):

```env
MATEO_USE_OLLAMA=true
MATEO_OLLAMA_HOST=http://127.0.0.1:11434
MATEO_OLLAMA_MODEL=llama3.1:8b
MATEO_OBSIDIAN_VAULT=C:\ruta\a\tu\boveda\Cerebro
MATEO_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
MATEO_AUTO_LEARN=false

# Opcional: si se define, los endpoints que modifican estado (chat, upload,
# learn, clear, transcribe, speak) exigen el header "X-API-Key" con este valor.
# Recomendado si vas a exponer Mateo más allá de tu propia máquina.
MATEO_API_KEY=

# Voz (opcional, ver sección "🎙️ Voz")
MATEO_WHISPER_MODEL=base
MATEO_PIPER_VOICE_MODEL=
```

Las claves de Wolfram Alpha / NewsAPI / OpenWeather **no están integradas aún** en el código; si se agregan en el futuro, deberán conectarse en `tools/external_apis.py`.

---

## 🏗️ Arquitectura

```
Mateo IA/
├── backend/
│   ├── neural/
│   │   ├── language_model.py      # Adaptador a Ollama local (con fallback)
│   │   └── vector_store.py        # Memoria vectorial ligera basada en JSON
│   ├── tools/
│   │   ├── external_apis.py       # Wikipedia, DuckDuckGo, calculadora
│   │   ├── obsidian_memory.py     # Índice de lectura de la bóveda Obsidian
│   │   ├── obsidian_writer.py     # Escritura curada de notas en la bóveda
│   │   ├── web_learner.py         # Búsqueda web (DuckDuckGo)
│   │   ├── file_processor.py      # Carga y generación de PDF/Word/Excel/Markdown
│   │   └── voice.py               # STT (faster-whisper) y TTS (Piper), opcional
│   ├── core/
│   │   ├── mateo_ultra_core.py        # Núcleo integrador y clasificador de intención
│   │   ├── learning_cycle.py          # Ciclo de aprendizaje puntual (bajo demanda)
│   │   ├── auto_research_engine.py    # Investigación autónoma en segundo plano
│   │   ├── self_improvement_engine.py # Motor de auto-mejora de código (whitelist + backups)
│   │   └── agent_engine.py            # 🤖 Modo Agente: planifica, ejecuta y resume objetivos de varios pasos
│   ├── main.py                    # Punto de entrada / modo CLI
│   ├── api.py                     # API REST (FastAPI) + WebSocket
│   └── requirements.txt           # Dependencias Python
├── frontend/
│   └── UI NEW.HTML                # Interfaz de chat, HTML/CSS/JS sin build
├── Instalar_Mateo.bat
├── Iniciar_Mateo.bat
└── README.md
```

---

## 🧠 Modelo de Lenguaje Utilizado

| Componente | Uso | Notas |
|---|---|---|
| Ollama (`llama3.1:8b` por defecto) | Conversación y síntesis de conocimiento | Corre 100% local, configurable vía `.env` |
| Memoria vectorial propia | Recuperación de contexto | Similitud por tokens, no embeddings |

No se usan modelos de HuggingFace Transformers ni FAISS en esta versión — se retiraron para reducir la instalación a lo que realmente se usa.

---

## 📊 Rendimiento

Depende casi enteramente del modelo elegido en Ollama y del hardware disponible; el backend en sí (FastAPI + JSON) tiene una huella mínima de RAM/CPU.

---

## 🔧 Solución de Problemas

### Error: "Python no está instalado"
- Descarga Python 3.8+ desde https://python.org
- Asegúrate de marcar "Add Python to PATH"

### Error: "No se puede conectar al servidor"
- Verifica que el backend esté corriendo en http://localhost:8000
- Comprueba que no haya otro programa usando el puerto 8000

### Mateo responde "[Modo Fallback]" o "[Modo local] No hay un modelo..."
- Verificá que Ollama esté corriendo (`ollama serve`) y que el modelo configurado en `MATEO_OLLAMA_MODEL` esté descargado (`ollama list`).

---

## 🛠️ Desarrollo

### Estructura del Código

**Backend (Python):**
- `NeuralLanguageProcessor`: adaptador a Ollama, con mensaje de fallback si no hay modelo disponible
- `VectorStore`: memoria vectorial ligera persistida en JSON
- `ExternalAPIManager`: Wikipedia, DuckDuckGo, calculadora (clima/noticias parcialmente implementados)
- `MateoUltraCore`: clasifica la intención del mensaje (por reglas/regex) y orquesta el resto de módulos
- `SelfImprovementEngine`: analiza y aplica mejoras a un conjunto acotado de archivos, con validación de sintaxis, backup y rollback

**Frontend:**
- HTML/CSS/JS plano, sin frameworks ni build, servido directamente por FastAPI

### Verificar el backend

Desde la carpeta `backend`, ejecuta las pruebas de regresión y la comprobación de sintaxis:

```bash
PYTHONPATH=. python -m unittest discover -s tests -v
python -m compileall -q .
```

Las pruebas cubren el aislamiento del historial por usuario, la persistencia selectiva de conversaciones y casos críticos de clasificación de intenciones.

### Memoria persistente de conversaciones

Mateo guarda localmente las conversaciones del usuario en `backend/data/conversations/memory.json`. Al iniciar de nuevo, no carga todo el historial en cada respuesta: busca únicamente coincidencias relevantes con la consulta actual. Por eso un saludo normal no debería provocar referencias a conversaciones antiguas.

La memoria se separa por `user_id` y `/clear` borra también la memoria persistente de ese usuario. Para cambiar la ubicación del archivo, configura `MATEO_CONVERSATION_MEMORY_PATH` en `.env`.

### Añadir Nuevas Funcionalidades

1. **Nueva herramienta externa:**
   ```python
   # En tools/external_apis.py
   async def nueva_funcion(self, param):
       # Implementación
       return resultado
   ```

2. **Nuevo comando:**
   ```python
   # En core/mateo_ultra_core.py, dentro de _classify_query / _execute_tool
   if query_type == "nuevo_tipo":
       return await self.external_apis.nueva_funcion(param)
   ```

---

## 📝 Changelog

### v2.1.0 - Local-first
- ✅ Memoria vectorial ligera persistente en `documents.json`
- ✅ Sandbox de auto-mejora con el mismo intérprete de Python
- ✅ Instalación reducida a dependencias realmente utilizadas (se retiraron Transformers/FAISS/sentence-transformers)
- ✅ Iniciador seguro sin cerrar procesos ajenos
- ✅ UI oficial servida directamente por FastAPI en `/ui`

### v1.0.0
- ✅ Sistema base de conversación
- ✅ Memoria persistente
- ✅ Navegación web autónoma

---

## 🙏 Agradecimientos

- **Ollama** — por hacer trivial correr modelos de lenguaje en local
- **Leonardo** — Creador y padre de Mateo
- **Comunidad de código abierto**

---

## 📄 Licencia

Este proyecto es de código abierto bajo la licencia MIT.

---

**¡Disfruta conversando con Mateo AI Ultra!** 🤖✨
