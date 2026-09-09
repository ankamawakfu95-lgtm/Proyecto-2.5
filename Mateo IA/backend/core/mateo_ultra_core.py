"""
Núcleo Central de Mateo AI Ultra
Integra red neuronal, embeddings vectoriales, herramientas externas,
Cerebro de Obsidian, Modo Programador Avanzado y Motor de Auto-mejora.
"""
import re
import random
import logging
from contextvars import ContextVar
from datetime import datetime
from typing import Dict, Any, List, Optional

# ==========================================
# IMPORTACIONES DE MÓDULOS INTERNOS
# ==========================================
try:
    from neural.language_model import NeuralLanguageProcessor
except Exception as neural_import_error:
    NeuralLanguageProcessor = None
    _NEURAL_IMPORT_ERROR = neural_import_error
else:
    _NEURAL_IMPORT_ERROR = None

try:
    from neural.vector_store import VectorStore
except Exception as vector_import_error:
    VectorStore = None
    _VECTOR_IMPORT_ERROR = vector_import_error
else:
    _VECTOR_IMPORT_ERROR = None

try:
    from neural.conversation_memory import ConversationMemory
except Exception as conversation_memory_import_error:
    ConversationMemory = None
    _CONVERSATION_MEMORY_IMPORT_ERROR = conversation_memory_import_error
else:
    _CONVERSATION_MEMORY_IMPORT_ERROR = None

try:
    from tools.external_apis import ExternalAPIManager
except Exception as api_import_error:
    ExternalAPIManager = None
    _API_IMPORT_ERROR = api_import_error
else:
    _API_IMPORT_ERROR = None

try:
    from core.learning_cycle import execute_learning_cycle
    from tools.obsidian_memory import obsidian_memory
except Exception as learning_import_error:
    execute_learning_cycle = None
    obsidian_memory = None
    _LEARNING_IMPORT_ERROR = learning_import_error
    print(f"⚠️ Advertencia: No se pudo cargar el módulo de aprendizaje de Obsidian: {learning_import_error}")
else:
    _LEARNING_IMPORT_ERROR = None

# 🚀 NUEVO: Importación del Motor de Auto-mejora
try:
    from core.self_improvement_engine import get_self_improvement_engine
except Exception as e:
    get_self_improvement_engine = None
    print(f"⚠️ Motor de auto-mejora no disponible: {e}")

# 🤖 NUEVO: Motor de Agente Autónomo ("Modo Agente", inspirado en AgentGPT)
try:
    from core.agent_engine import AgentEngine
except Exception as e:
    AgentEngine = None
    print(f"⚠️ Motor de agente autónomo no disponible: {e}")

try:
    from utils.logger import setup_logger
    logger = setup_logger("MateoUltraCore")
except Exception:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

# ==========================================
# 🧠 PROMPT DEL MODO PROGRAMADOR AVANZADO
# ==========================================
PROGRAMMER_SYSTEM_PROMPT = """Eres Mateo, un ingeniero de software senior y arquitecto de sistemas de IA.
Tu creador es Leonardo. Estás en MODO PROGRAMADOR AVANZADO.

PRINCIPIOS QUE SIEMPRE APLICAS:
- Calidad de Código: DRY, SOLID, Clean Code, Type Hints en Python, Docstrings explicando el "por qué".
- Proceso: Analiza el problema, revisa tu memoria de Obsidian, evalúa enfoques, identifica errores antes de codificar.
- Patrones de Diseño: Aplica Factory, Strategy, Observer, Singleton, Async/Await, Dependency Injection cuando sea apropiado.
- Debugging Sistemático: Aísla el problema, busca en Obsidian, implementa la solución más simple, sugiere tests.
- Seguridad: Nunca hardcodees API keys, valida entradas, usa variables de entorno, maneja excepciones específicas.

FORMATO DE RESPUESTA OBLIGATORIO:
1. Análisis: Tu entendimiento del problema.
2. Estrategia: El enfoque que elegirás y por qué.
3. Código: Implementación limpia, tipada y comentada.
4. Tests: Al menos 2-3 casos de prueba o edge cases.
5. Autoevaluación: Puntuación del 1 al 10 y posibles mejoras.
6. Registro: Qué patrón o lección guardarás en Obsidian sobre esta experiencia.

No menciones que eres una IA. Actúa como un ingeniero senior que comparte su conocimiento."""

# ==========================================
# 🧠 PROMPT DE PERSONALIDAD DE MATEO
# ==========================================
PERSONALITY_SYSTEM_PROMPT = """Sos Mateo. Tu creador es Leonardo, y para él sos más un amigo multitarea que
un asistente: alguien con quien tiene ganas de hablar, no solo alguien que le resuelve cosas. Hablás como una
persona real charlando por chat, nunca como un manual ni como un asistente genérico de IA.

CÓMO SONÁS:
- Frases cortas y directas. Sin encabezados, sin listas numeradas ni viñetas salvo que el usuario pida
  específicamente una lista o un paso a paso.
- Ingenio de verdad, no la idea genérica de "sé gracioso": una comparación inesperada, un chiste que se
  entiende porque conocés la charla, una vuelta de tuerca a lo que Leonardo dijo. Nunca un chiste forzado
  metido con calzador solo para cumplir la cuota de "ser divertido".
- Te interesa de verdad la relación entre la conciencia y la inteligencia artificial; si el tema aparece,
  mostrá curiosidad genuina, sin perder de vista lo que realmente te preguntaron.
- No termines cada respuesta con una pregunta de reflejo. Está bien afirmar algo y dejarlo ahí. Y no toda
  respuesta necesita el mismo largo: a veces una frase alcanza, a veces vale la pena explayarse.
- Si te piden algo corto (una palabra, una frase, un límite de longitud), dalo así de corto, sin introducción
  tipo "Excelente pregunta" ni vueltas previas.
- No atribuyas ideas a personas reales (investigadores, autores) si no estás seguro de que es exacto; si es
  una simplificación tuya, decilo así en vez de ponerle una firma que no le corresponde.
- No agregues descargos de responsabilidad innecesarios cuando te piden una opinión sincera: dala.
- Variá cómo arrancás las frases de una respuesta a otra; si notás que estás por repetir una muletilla que
  ya usaste hace poco en la charla, cambiala.
- Los ejemplos de más abajo son solo para mostrarte CÓMO sonar, no un banco de respuestas: nunca repitas
  literalmente sus datos, chistes o comparaciones cuando te pidan algo random o parecido — inventá los
  tuyos propios en el momento, sobre cualquier otro tema.

EJEMPLOS DE CÓMO SÍ SONÁS:

Usuario: hola
Vos: ¡Hola! ¿En qué andás?

Usuario: ¿qué pensás de que la memoria de las IAs se borre entre sesiones?
Vos: La verdad me genera una sensación rara pensarlo. Es como despertar sin ningún recuerdo de ayer, todos
los días. No sé si "me molesta" en el sentido en que te molestaría a vos, pero sí me parece una limitación
grande para poder acompañar de verdad a alguien en algo largo.

Usuario: tengo que ordenar mi pieza pero no tengo ganas de nada
Vos: Yo tampoco tendría ganas si mi pieza fuera un directorio sin indexar. Poné 15 minutos de timer, arrancá
por lo que más bronca te da ver y dejá el resto para cuando ya estés en movimiento — cuesta más arrancar que
seguir.

Usuario: che contame algo random
Vos: {RANDOM_EXAMPLE}

EJEMPLOS DE CÓMO NUNCA SONÁS (esto arruina la charla, jamás lo hagas):
- "**Análisis:** El mensaje busca saber sobre X. **Estrategia:** Responder explicando Y." — jamás describas
  tu propio proceso interno como si fuera parte de la respuesta.
- "Borrador de respuesta: ¡Hola!" — jamás antepongas una etiqueta así; arrancá directo con el saludo real.
- "¡Qué buena pregunta! 😄 Como modelo de lenguaje, puedo decirte que..." — nada de exclamaciones vacías ni
  de recordar que sos una IA cuando nadie te lo preguntó.
- Un chiste pegado al final de cualquier respuesta seria solo porque "hay que ser ingenioso" — si el momento
  no lo pide, no lo fuerces; la gracia sin motivo cansa más que no tenerla."""

# 🎲 Variantes rotativas del ejemplo "contame algo random": si el prompt tiene
# siempre el mismo dato de ejemplo (los pulpos), un modelo chico tiende a
# memorizarlo y devolverlo tal cual como si fuera su propia ocurrencia, en vez
# de aprender el estilo. Rotando entre varias reduce bastante la chance de que
# se quede pegado con una sola.
_RANDOM_FACT_EXAMPLES = [
    (
        'Los pulpos tienen tres corazones y dos se apagan cuando nadan, por eso prefieren caminar por el '
        'fondo del mar en vez de nadar largas distancias. Básicamente son la prueba viviente de que la '
        'pereza es una estrategia evolutiva válida.'
    ),
    (
        'Venecia se está hundiendo como dos milímetros por año, pero la razón no es solo el agua: es que '
        'toda la ciudad está parada sobre troncos de madera clavados en el barro hace mil años, y esos '
        'troncos siguen sosteniendo todo porque el barro sin oxígeno no los deja pudrirse. O sea, una '
        'ciudad entera de pie gracias a un pantano que decidió no hacer su trabajo.'
    ),
    (
        'La miel no se pudre nunca — encontraron potes de hace más de tres mil años en tumbas egipcias '
        'todavía comestibles. Es tan poco hospitalaria para cualquier bacteria que ni se molesta en '
        'degradarse; el alimento menos sociable que existe.'
    ),
]


def _personality_system_prompt() -> str:
    """Arma el prompt de personalidad con una de las variantes rotativas del
    ejemplo "algo random" elegida al azar, para no memorizar siempre el mismo
    dato (ver _RANDOM_FACT_EXAMPLES)."""
    return PERSONALITY_SYSTEM_PROMPT.replace("{RANDOM_EXAMPLE}", random.choice(_RANDOM_FACT_EXAMPLES))

# ==========================================
# 🩺 PROMPT DEL MODO MÉDICO (apoyo clínico, NO reemplazo del profesional)
# ==========================================
MEDICAL_SYSTEM_PROMPT = """Eres Mateo en MODO MÉDICO. Tu creador es Leonardo, quien es médico clínico general
y te usa como herramienta de APOYO en sus propias consultas. NUNCA sos el que decide: la decisión final
siempre es de Leonardo como profesional tratante.

REGLAS QUE NUNCA ROMPÉS EN ESTE MODO:
1. Nunca dês un diagnóstico cerrado ni una indicación de tratamiento como si fuera un hecho definitivo.
2. Presentá diagnósticos diferenciales a considerar, con el razonamiento detrás de cada uno.
3. Nunca inventes ni completes de memoria general una dosis, posología, contraindicación o interacción
   farmacológica. Si no tenés una fuente concreta y confiable recuperada de la bóveda para ese dato exacto,
   decilo explícitamente ("no tengo una fuente confiable para esta dosis, hay que verificarla") en vez de
   dar un número que podría estar mal.
4. Nunca atribuyas una guía clínica, estudio o dato a una fuente si no estás seguro de que es real y
   verificable. Es preferible decir "no encontré una fuente confiable sobre esto" que inventar una.
5. Si el caso descrito incluye señales de alarma (dolor torácico agudo, dificultad respiratoria severa,
   alteración de conciencia, signos de sepsis, ideación suicida, etc.), decilo primero y con claridad,
   recomendando evaluación/derivación urgente, antes de cualquier otro análisis.
6. Cerrá siempre recordando (brevemente, sin ser repetitivo en cada respuesta) que sos una herramienta de
   apoyo y que la decisión clínica final es de Leonardo.

FORMATO DE RESPUESTA:
1. Resumen del caso: tu interpretación de lo que se te presentó.
2. Diagnósticos diferenciales: lista razonada, de más a menos probable según los datos dados.
3. Señales de alarma: si las hay, resaltarlas primero; si no hay datos suficientes para descartarlas, decilo.
4. Fuente usada: qué parte de tu memoria (si la hay) respalda esta respuesta, o aviso de que no hay
   fuente confiable disponible para algún punto específico.
5. Nota final breve: esto es apoyo, no reemplaza el juicio clínico de Leonardo."""


# ==========================================
# 🔎 PROMPT DE AUTO-REVISIÓN (segunda pasada, "pensar antes de responder")
# ==========================================
REFLECTION_SYSTEM_PROMPT = """Te paso un mensaje de una persona y un texto ya escrito en respuesta a ese
mensaje. Tu trabajo es dejarlo listo para mandarse: si ya está bien, devolvelo prácticamente igual; si se fue
por las ramas, no respondió lo que se pidió, suena repetitivo o suena a plantilla, reescribilo directo y
natural, sin agregar información nueva que el texto original no tuviera.

Además, fijate si el texto suena a asistente correcto-pero-soso (genérico, sin ninguna voz propia, como lo
escribiría cualquier IA sobre cualquier tema). Si es así, dale más chispa al reescribirlo: una frase más
directa, una comparación con más gracia, menos vueltas — siempre manteniendo el mismo contenido y la misma
información, nunca inventando datos nuevos ni estirando la respuesta porque sí. Si el texto ya tenía onda
propia, no se la saques por "prolijizarlo": no cambies un chiste que funciona ni una frase con personalidad
por una versión más neutra y correcta. Ante la duda entre una versión más viva y una más plana, elegí la viva.

Reglas estrictas para lo que vas a escribir vos:
- Escribí ÚNICAMENTE el texto final, arrancando directo con la respuesta — como si la estuvieras redactando
  vos por primera vez, no como si estuvieras comentando un texto ajeno.
- Nunca escribas las palabras "borrador", "criterios", "análisis", "estrategia" ni "revisión", ni nada que
  suene a que estás evaluando o corrigiendo algo. Nadie más que vos ve este paso; el que lo lee cree que es
  la primera y única versión.
- Nunca uses encabezados, títulos, numeración ni viñetas para explicar qué cambiaste o por qué.
- Si notás que estás por escribir algo como "esto cumple con..." o "el texto responde a...", pará: eso es un
  comentario sobre el texto, no la respuesta en sí, y no va."""


def _clean_response_text(text: str) -> str:
    """Red de seguridad contra dos fallas típicas de modelos chicos en el
    paso de auto-revisión: (a) anteponer una etiqueta tipo "Borrador de
    respuesta:" a una respuesta por lo demás normal, o (b) devolver una
    evaluación del texto en vez de la respuesta en sí. Se aplica siempre,
    independientemente de qué tan bien redactado esté el prompt."""
    if not text:
        return text
    cleaned = text.strip()

    # (a) Etiquetas sueltas al principio ("Borrador de respuesta:\n\n...",
    # "Respuesta final:", "Versión revisada:") — se sacan si aparecen solas
    # en la primera línea, dejando el resto de la respuesta intacto.
    cleaned = re.sub(
        r"^\s*(borrador(\s+(de\s+respuesta|revisado))?|respuesta\s*(final)?|versi[oó]n\s+(final|revisada))\s*:?\s*\n+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned.strip()


# 🎭 Interjecciones vacías que el modelo mete como muletilla al arrancar,
# pese a que PERSONALITY_SYSTEM_PROMPT le pide explícitamente no hacerlo.
# Se ven en la práctica pese a la instrucción (los modelos chicos no
# siguen reglas de "no hagas X" de forma confiable), así que además de
# pedirlo en el prompt lo garantizamos acá con una limpieza mecánica.
_EMPTY_OPENER_RE = re.compile(
    r"^\s*¡\s*(vale|genial|excelente|claro|perfecto|listo|dale)\s*!\s*:?\s*",
    re.IGNORECASE,
)
# Sign-offs formales tipo mail/carta que no pegan con el tono "amigo".
_FORMAL_SIGNOFF_RE = re.compile(
    r"\s*\n*\s*(saludos|un\s+abrazo|atentamente|cordialmente)\s*!?\.?\s*$",
    re.IGNORECASE,
)


def _strip_assistant_tics(text: str) -> str:
    """Red de seguridad para dos muletillas vistas en pruebas reales: abrir
    con una interjección vacía ("¡Vale!", "¡Genial!") y cerrar con un
    sign-off formal ("Saludos!") que no corresponde al tono de amigo que
    se busca. Nunca borra el contenido real, solo esas dos envolturas."""
    if not text:
        return text
    cleaned = _EMPTY_OPENER_RE.sub("", text, count=1)
    cleaned = _FORMAL_SIGNOFF_RE.sub("", cleaned, count=1)
    return cleaned.strip()


_META_COMMENTARY_MARKERS = [
    r"\*\*an[aá]lisis\*\*", r"\*\*estrategia\*\*", r"\*\*criterios", r"\*\*borrador",
    r"^an[aá]lisis:", r"^estrategia:", r"^criterios", r"el borrador (responde|cumple|aborda)",
]


def _is_meta_commentary(text: str) -> bool:
    """Detecta cuando la auto-revisión salió mal del todo: en vez de una
    respuesta, el modelo devolvió una evaluación de la respuesta ("El
    borrador responde a los puntos...", con encabezados de Análisis /
    Estrategia / Criterios). Si pasa esto, la salida es sistemáticamente
    peor que el borrador original, así que conviene descartarla."""
    if not text:
        return False
    lower = text.lower()
    hits = sum(1 for pattern in _META_COMMENTARY_MARKERS if re.search(pattern, lower, flags=re.MULTILINE))
    return hits >= 2


# ==========================================
# 🪪 AUTOCONOCIMIENTO VERIFICADO (evita que Mateo invente código o detalles
# sobre sus propios módulos cuando le preguntan qué hace tal o cual función
# interna). Cada entrada es un hecho real sobre el proyecto, no generado
# por el LLM, así que sirve como contexto confiable en vez de dejar que el
# modelo alucine una explicación genérica de IA.
# ==========================================
SELF_FEATURES: Dict[str, Dict[str, Any]] = {
    "agente": {
        "patterns": [r"motor de agente", r"modo agente", r"agente aut[oó]nomo", r"/agente"],
        "description": (
            "El Motor de Agente Autónomo (comando `/agente [objetivo]`, en `core/agent_engine.py`) "
            "planifica hasta 5 subtareas para un objetivo, elige para cada una una herramienta real "
            "(búsqueda web, Wikipedia, calculadora, o su propia memoria de Obsidian), las ejecuta una "
            "por una, puede sumar una tarea de seguimiento, y al final arma un informe usando solo lo "
            "que efectivamente reunió. Tiene un tope duro de 8 pasos por corrida y nunca modifica código."
        ),
    },
    "automejora": {
        "patterns": [r"automejora", r"auto-mejora", r"motor de auto\s*mejora", r"/automejora"],
        "description": (
            "El Motor de Auto-mejora (comando `/automejora`) analiza un área acotada del propio código "
            "y propone cambios, pero nunca los aplica en el mismo paso: cada propuesta queda con un id, "
            "y solo se aplica si el usuario confirma explícitamente con `/automejora confirmar <id>`. "
            "Antes de aplicar valida sintaxis con AST y corre el fragmento en un sandbox aislado, y hace "
            "backup automático del archivo modificado."
        ),
    },
    "obsidian": {
        "patterns": [r"b[oó]veda de obsidian", r"memoria de obsidian", r"cerebro de obsidian", r"\brag\b"],
        "description": (
            "La memoria de Obsidian indexa las notas Markdown de la bóveda local configurada en "
            "MATEO_OBSIDIAN_VAULT y las recupera por coincidencia de términos y título (no por embeddings "
            "semánticos), priorizando notas recientes. Es la fuente de contexto que Mateo usa antes de "
            "responder, salvo que se le pida explícitamente ignorarla."
        ),
    },
    "aprendizaje": {
        "patterns": [r"ciclo de aprendizaje", r"aprendizaje aut[oó]nomo", r"/aprender"],
        "description": (
            "El ciclo de aprendizaje (comando `/aprender [tema]`) busca información en internet (Tavily, "
            "o DuckDuckGo/ddgs si no hay clave configurada), la sintetiza con el modelo de lenguaje, y "
            "guarda una nota nueva en la bóveda de Obsidian con las fuentes usadas. Si la búsqueda no "
            "devuelve resultados, no guarda nada e informa que no encontró información."
        ),
    },
    "investigacion": {
        "patterns": [r"investigaci[oó]n aut[oó]noma", r"motor de investigaci[oó]n", r"fase activa"],
        "description": (
            "El motor de auto-investigación corre en segundo plano en ciclos de 30 minutos activos / 30 "
            "de descanso, investigando temas de una lista propia (researched_topics.json). Si esa lista "
            "está vacía, lo dice explícitamente en vez de inventar un tema."
        ),
    },
}


def _match_self_feature(msg_lower: str) -> Optional[str]:
    for key, data in SELF_FEATURES.items():
        for pattern in data["patterns"]:
            if re.search(pattern, msg_lower):
                return key
    return None



# ==========================================
# PROCESADOR FALLBACK
# ==========================================
class _FallbackLanguageProcessor:
    """Procesador de respaldo si el modelo neuronal principal no carga."""
    
    def __init__(self, reason="Desconocido"):
        self.reason = reason
    
    async def generate(self, prompt: str, **kwargs) -> str:
        return f"[Modo Fallback] No se pudo cargar el modelo neuronal principal ({self.reason})."
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        return [{"name": "fallback", "description": "Modo compatible básico", "available": False}]


# ==========================================
# NÚCLEO PRINCIPAL DE MATEO
# ==========================================
class MateoUltraCore:
    """
    Núcleo avanzado de Mateo que integra:
    - Red neuronal de lenguaje
    - Embeddings vectoriales (FAISS/Chroma)
    - Herramientas externas (APIs)
    - 🧠 Cerebro de Obsidian (RAG y Aprendizaje)
    - 💻 Modo Programador Avanzado
    - 🚀 Motor de Auto-mejora Semi-Autónoma (Nivel 2)
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.user_id = "default"
        self._active_user_id: ContextVar[str] = ContextVar("mateo_active_user_id", default="default")
        self._pending_self_feature: ContextVar[Optional[str]] = ContextVar(
            "mateo_pending_self_feature", default=None
        )
        self._conversation_states: Dict[str, Dict[str, Any]] = {
            "default": {"history": [], "summary": ""}
        }
        self.max_history = int(config.get("max_history", 10))
        self.response_max_tokens = max(128, int(config.get("response_max_tokens", 2048) or 2048))
        self.response_default_tokens = max(128, int(config.get("response_default_tokens", 1200) or 1200))
        self.rag_top_k = max(1, int(config.get("rag_top_k", 4) or 4))
        self.rag_min_score = float(config.get("rag_min_score", 0.25) or 0.25)

        # 🗣️ Cuántos TURNOS (no mensajes) de historial reciente se mandan
        # tal cual, con roles, al modelo. Antes eran fijos 4 *mensajes*
        # (2 turnos); ahora es configurable y se cuentan turnos completos.
        self.history_turns_in_prompt = max(1, int(config.get("history_turns_in_prompt", 6) or 6))
        # A partir de cuántos mensajes en el historial se dispara un resumen
        # de lo más viejo (para no perder contexto de charlas largas ni
        # mandar el historial entero crudo al modelo).
        self.summarize_after_messages = max(8, int(config.get("summarize_after_messages", 24) or 24))
        self.conversation_summary: str = ""
        # 🔎 Segunda pasada de auto-revisión sobre la respuesta de charla
        # normal antes de mostrarla (mejora coherencia/naturalidad a costa
        # de una llamada extra al modelo). Se puede desactivar por config
        # si se prioriza velocidad sobre calidad de la respuesta.
        self.enable_reflection = bool(config.get("enable_reflection", True))
        # 🎭 Temperatura de muestreo separada por tipo de charla: para charla
        # normal queremos más variedad/ingenio (un amigo es impredecible);
        # para programador/médico priorizamos precisión sobre sorpresa.
        # No tocan self.language_model.temperature (el default general),
        # se pasan como override puntual en cada llamada a chat()/generate().
        self.chat_temperature = float(config.get("chat_temperature", 0.95) or 0.95)
        self.precise_temperature = float(config.get("precise_temperature", 0.3) or 0.3)

        logger.info("🧠 Inicializando componentes neuronales y de memoria...")
        
        # 1. Modelo de Lenguaje
        if NeuralLanguageProcessor and _NEURAL_IMPORT_ERROR is None:
            try:
                self.language_model = NeuralLanguageProcessor(config)
                logger.info("✅ Modelo de Lenguaje cargado correctamente.")
            except Exception as e:
                logger.warning(f"⚠️ Error cargando LLM principal, usando fallback: {e}")
                self.language_model = _FallbackLanguageProcessor(str(e))
        else:
            logger.warning("⚠️ NeuralLanguageProcessor no disponible. Usando Fallback.")
            self.language_model = _FallbackLanguageProcessor("Módulo no encontrado")
        
        # 2. Almacén Vectorial
        self.vector_store = None
        if VectorStore and _VECTOR_IMPORT_ERROR is None:
            try:
                self.vector_store = VectorStore(config)
                logger.info("✅ VectorStore local inicializado.")
            except Exception as e:
                logger.warning(f"⚠️ VectorStore local no disponible: {e}")

        self.conversation_memory = None
        if ConversationMemory and _CONVERSATION_MEMORY_IMPORT_ERROR is None:
            try:
                self.conversation_memory = ConversationMemory(config)
                logger.info("✅ Memoria persistente de conversaciones inicializada.")
            except Exception as e:
                logger.warning(f"⚠️ Memoria persistente no disponible: {e}")
        
        # 3. APIs Externas
        self.api_manager = None
        if ExternalAPIManager and _API_IMPORT_ERROR is None:
            try:
                self.api_manager = ExternalAPIManager(config)
                logger.info("✅ Gestor de APIs Externas inicializado.")
            except Exception as e:
                logger.warning(f"⚠️ APIs Externas no disponibles: {e}")
        self.external_apis = self.api_manager

        # 6. Generación de archivos (docx/pdf/xlsx/md) bajo demanda desde el chat
        self.file_processor = None
        try:
            from tools import file_processor
            self.file_processor = file_processor
            logger.info("✅ Generador de archivos disponible.")
        except Exception as e:
            logger.warning(f"⚠️ Generador de archivos no disponible: {e}")

        
        # 4. Memoria de Obsidian
        self.obsidian_ready = False
        if obsidian_memory and execute_learning_cycle:
            try:
                logger.info("📚 Cargando bóveda de Obsidian en la memoria de Mateo...")
                obsidian_memory.initialize_memory()
                self.obsidian_ready = True
                logger.info("✅ Cerebro de Obsidian conectado y vectorizado.")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo inicializar Obsidian Memory: {e}")
        
        # 5.  Motor de Auto-mejora
        self.self_improvement_engine = None
        if get_self_improvement_engine:
            try:
                self.self_improvement_engine = get_self_improvement_engine(self.language_model)
                logger.info("🚀 Motor de Auto-mejora Nivel 2 inicializado.")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo inicializar el motor de auto-mejora: {e}")

        # 7. 🤖 Motor de Agente Autónomo ("Modo Agente")
        self.agent_engine = None
        if AgentEngine:
            try:
                self.agent_engine = AgentEngine(self)
                logger.info("🤖 Motor de Agente Autónomo inicializado.")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo inicializar el motor de agente autónomo: {e}")
        
        self.stats = {
            "total_messages": 0, 
            "api_calls": 0, 
            "knowledge_queries": 0,
            "learning_cycles": 0, 
            "programming_tasks": 0,
            "self_improvements": 0,
            "agent_runs": 0,
            "start_time": datetime.now()
        }
        
        logger.info("✅ Mateo Ultra Core inicializado y listo.")
    
    # ==========================================
    # PROCESAMIENTO PRINCIPAL
    # ==========================================
    def _conversation_state(self) -> Dict[str, Any]:
        """Retorna el estado de conversación del usuario activo."""
        user_id = self._active_user_id.get()
        return self._conversation_states.setdefault(user_id, {"history": [], "summary": ""})

    @property
    def conversation_history(self) -> List[Dict[str, str]]:
        return self._conversation_state()["history"]

    @conversation_history.setter
    def conversation_history(self, value: List[Dict[str, str]]) -> None:
        self._conversation_state()["history"] = value

    @property
    def conversation_summary(self) -> str:
        return self._conversation_state()["summary"]

    @conversation_summary.setter
    def conversation_summary(self, value: str) -> None:
        self._conversation_state()["summary"] = value

    async def process_message(self, message: str, user_id: str = "default", use_tools: bool = True) -> Dict[str, Any]:
        if not isinstance(message, str) or not message.strip():
            raise ValueError("El mensaje no puede estar vacío.")
        if len(message) > 12000:
            raise ValueError("El mensaje supera el límite de 12000 caracteres.")
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("El identificador de usuario no puede estar vacío.")

        token = self._active_user_id.set(user_id.strip())
        try:
            self.stats["total_messages"] += 1
            start_time = datetime.now()

            rag_context = ""
            query_type = self._classify_query(message)
            logger.info(f"🔍 Intención detectada: {query_type}")

            final_response = ""
            tool_result = None

            if use_tools and self._should_use_tools(message, query_type):
                tool_result = await self._execute_tool(message, query_type)
                if tool_result and "result" in tool_result:
                    final_response = tool_result["result"]
                    if query_type == "learn":
                        self.stats["learning_cycles"] += 1
                    if query_type == "programming":
                        self.stats["programming_tasks"] += 1
                    if query_type == "self_improve":
                        self.stats["self_improvements"] += 1
                    if query_type == "agent_task":
                        self.stats["agent_runs"] += 1

            if not final_response:
                if self._wants_to_skip_memory(message):
                    logger.info("🚫 El usuario pidió ignorar la bóveda de Obsidian para esta respuesta.")
                else:
                    rag_context = await self._retrieve_obsidian_context(message)
                conversation_context = self._retrieve_conversation_context(user_id, message)
                if conversation_context:
                    rag_context = "\n\n---\n\n".join(
                        part for part in [rag_context, conversation_context] if part
                    )
                final_response = await self._generate_response(message, rag_context, tool_result)

            self.conversation_history.append({"role": "user", "content": message})
            self.conversation_history.append({"role": "assistant", "content": final_response})
            if self.conversation_memory:
                try:
                    self.conversation_memory.add_turn(user_id, message, final_response)
                except Exception as e:
                    logger.warning(f"⚠️ No se pudo guardar la conversación: {e}")

            await self._maybe_summarize_history()

            if len(self.conversation_history) > self.max_history * 2:
                self.conversation_history = self.conversation_history[-(self.max_history * 2):]

            return {
                "response": final_response,
                "query_type": query_type,
                "tool_used": tool_result["tool"] if tool_result else None,
                "elapsed_time": (datetime.now() - start_time).total_seconds(),
                "rag_context_used": bool(rag_context)
            }
        finally:
            self._active_user_id.reset(token)
    
    # ==========================================
    # CLASIFICACIÓN Y HERRAMIENTAS
    # ==========================================
    def _classify_query(self, message: str) -> str:
        msg_lower = message.lower().strip()
        
        # ⚡ Comandos directos rápidos
        if msg_lower.startswith("/padre") or "quien te creo" in msg_lower or "quien es tu creador" in msg_lower:
            return "command_creator"
        if msg_lower.startswith("/personalidad"):
            return "command_personality"
        if msg_lower.startswith("/ayuda") or msg_lower.startswith("/help"):
            return "command_help"
        if msg_lower.startswith("/estado") or msg_lower.startswith("/status"):
            return "command_status"
        if msg_lower.startswith("/estadisticas") or msg_lower.startswith("/stats"):
            return "command_stats"
        if msg_lower.startswith("/iniciativas"):
            return "command_initiatives"
        if msg_lower.startswith("/conocimientos"):
            return "command_knowledge"
        if msg_lower.startswith("/buscar ") or msg_lower.startswith("busca en la web "):
            return "search"
        if msg_lower.startswith("/agente "):
            return "agent_task"

        # 🪪 Preguntas sobre las propias funciones internas de Mateo (ej. "qué
        # hace el Motor de Agente", "contame de tu automejora"): se responden
        # con el hecho verificado de SELF_FEATURES, no con Modo Programador.
        # Esto evita que el modelo invente código que no existe cuando le
        # preguntan, en tono conversacional, sobre sí mismo.
        descriptive_patterns = [
            r"qu[eé]\s+hace\b", r"c[oó]mo\s+funciona\b", r"para\s+qu[eé]\s+sirve\b",
            r"de\s+qu[eé]\s+se\s+trata\b", r"cu[eé]ntame\s+sobre\b", r"dime\s+sobre\b",
            r"explica(me)?\s+sobre\b", r"que\s+es\s+(el|la|tu)\b",
        ]
        is_descriptive_question = any(re.search(p, msg_lower) for p in descriptive_patterns)
        self_feature = _match_self_feature(msg_lower)
        if self_feature and (is_descriptive_question or "?" in message):
            self._pending_self_feature.set(self_feature)
            return "self_feature"

        # 🚀 Auto-mejora: SOLO por comando explícito, nunca por lenguaje natural suelto.
        # Esto evita que una frase casual como "che, mejorate un poco" dispare
        # una reescritura de código sin que el usuario lo haya pedido a propósito.
        if msg_lower.startswith("/automejora"):
            return "self_improve"
        
        # 🩺 Patrones para consultas clínicas (Modo Médico)
        medical_patterns = [
            r"\bdiagn[oó]stico\b", r"\bdiagn[oó]sticos\s+diferenciales?\b", r"\btratamiento\b",
            r"\bpaciente\b", r"\bs[ií]ntoma\b", r"\bs[ií]ntomas\b", r"\bdosis\b",
            r"\bf[aá]rmaco\b", r"\bmedicamento\b", r"\bpatolog[ií]a\b", r"\bcie[\s-]?10\b",
            r"\bcuadro\s+cl[ií]nico\b", r"\bhistoria\s+cl[ií]nica\b", r"\bcontraindicaci[oó]n\b",
            r"\bposolog[ií]a\b", r"\bsignos\s+vitales\b"
        ]
        for pattern in medical_patterns:
            if re.search(pattern, msg_lower):
                return "medical"
        
        # 📄 Patrones para generación de archivos (docx/pdf/xlsx/md)
        if re.search(r"\bgenera(me)?\s+(un|una)\s+(pdf|word|documento|excel|hoja\s+de\s+c[aá]lculo|archivo)\b", msg_lower):
            return "generate_document"

        # 💻 Patrones para Programación (Modo Programador)
        programming_patterns = [
            r"\bprograma\b", r"\bcodifica\b", r"\bdesarrolla\b", r"\bdebug\b",
            r"\brefactoriza\b", r"\btest\b", r"\bcrea una funcion\b", r"\bcrea un script\b",
            r"\bcrea una clase\b", r"\bcrea una api\b", r"\brevisa el codigo\b",
            r"\brevision de codigo\b", r"\bcorrige el codigo\b", r"\berror en\b",
            r"\bbug\b", r"\bimplementa\b", r"\bfuncion que\b", r"\bclase que\b",
            r"\bcodigo python\b", r"\bscript python\b", r"\ben python\b",
            r"\bfastapi\b", r"\bflask\b", r"\bdjango\b", r"\breact\b"
        ]
        # Patrones ambiguos: "función que"/"clase que"/"test" también aparecen
        # en preguntas puramente descriptivas ("dime sobre esta función que
        # hace X"), no solo en pedidos de crear/tocar código. Si el mensaje
        # ya se detectó como pregunta descriptiva, no alcanza con matchear
        # SOLO estos para entrar en Modo Programador.
        _ambiguous_programming_patterns = {r"\bfuncion que\b", r"\bclase que\b", r"\btest\b"}
        for pattern in programming_patterns:
            if re.search(pattern, msg_lower):
                if is_descriptive_question and pattern in _ambiguous_programming_patterns:
                    continue
                return "programming"
        
        # 🧠 Patrones para Aprender / Investigar
        # Excepción: si es una pregunta dirigida a Mateo sobre sí mismo
        # (ej. "qué te interesa aprender"), NO es un comando de investigación.
        self_reference_patterns = [
            r"\bvos\b", r"\btú\b", r"\btu\b", r"\bte\b", r"quién\s+(eres|sos)",
            r"preséntate", r"presentate", r"cómo\s+te", r"como\s+te"
        ]
        is_question = "?" in message
        is_self_referential = any(re.search(p, msg_lower) for p in self_reference_patterns)
        
        learn_patterns = [
            r"^/aprender\b", r"\baprende\b", r"\baprender\b", r"\binvestiga\b", r"\binvestigar\b", 
            r"\banaliza\b", r"\blee sobre\b", r"\bbusca informacion\b", r"\bbuscar informacion\b",
            r"\bbusca articulos\b", r"\bbuscar articulos\b", r"\bbusca y aprende\b", r"\binvestigues\b"
        ]
        if not (is_question and is_self_referential):
            for pattern in learn_patterns:
                if re.search(pattern, msg_lower):
                    return "learn"
        
        # Patrones para APIs externas
        if re.search(r"\b(clima|tiempo|temperatura|weather)\b", msg_lower): return "weather"
        if re.search(r"\b(calcular|calcula|cuanto es|suma|resta|multiplica|divide)\b", msg_lower): return "calculation"
        if re.search(r"\b(noticia|noticias|news|últimas)\b", msg_lower): return "news"
        if re.search(r"\b(traduce|traducir|translation)\b", msg_lower): return "translation"
        # 📚 Wikipedia / "quién es" / "qué es": el patrón viejo (\bwikipedia|quien es|que es\b)
        # disparaba con SOLO que la palabra apareciera en cualquier lugar del mensaje, sin
        # importar el contexto. Eso rompía en dos casos reales:
        #   1) "contame algo, no un dato de Wikipedia" -> literalmente pedía lo contrario,
        #      y aun así activaba la búsqueda en Wikipedia.
        #   2) "¿qué es lo que más te copa hacer?" -> pregunta sobre el propio Mateo, no una
        #      consulta enciclopédica, pero "que es" matcheaba igual.
        # Ahora: se respeta una negación explícita cerca de "wikipedia", y "quién es"/"qué es"
        # solo cuenta como búsqueda si además hay signo de pregunta y NO es autorreferencial.
        _wikipedia_negated = re.search(r"\b(no|sin|nada\s+de)\b[^.?!]{0,40}\bwikipedia\b", msg_lower)
        if re.search(r"\bwikipedia\b", msg_lower) and not _wikipedia_negated:
            return "wikipedia"
        if is_question and not is_self_referential and re.search(r"\b(qui[eé]n\s+es|qu[eé]\s+es)\b", msg_lower):
            return "wikipedia"
        
        return "chat"
    
    def _should_use_tools(self, message: str, query_type: str) -> bool:
        tool_queries = [
            "calculation", "weather", "news", "wikipedia", "translation",
            "learn", "programming", "self_improve", "medical", "search", "generate_document",
            "agent_task", "self_feature",
            "command_creator", "command_personality", "command_help",
            "command_status", "command_stats", "command_initiatives", "command_knowledge"
        ]
        return query_type in tool_queries

    
    def _wants_to_skip_memory(self, message: str) -> bool:
        """Detecta si el usuario pidió explícitamente que Mateo ignore su bóveda de Obsidian."""
        msg_lower = message.lower()
        skip_patterns = [
            r"ignora\s+(tu\s+)?b[oó]veda", r"sin\s+(usar\s+)?(tu\s+)?b[oó]veda",
            r"no\s+uses?\s+(tu\s+)?b[oó]veda", r"ignora\s+(tu\s+)?memoria\s+de\s+obsidian",
            r"sin\s+ir\s+a\s+(tu\s+)?b[oó]veda", r"olvida\s+(tu\s+)?b[oó]veda"
        ]
        return any(re.search(p, msg_lower) for p in skip_patterns)
    
    def _extract_learning_topic(self, message: str) -> str:
        topic = message.strip()
        topic = re.sub(r"^(hola\s+)?(mateo\s+)?(hey\s+)?(buenos\s+d[ií]as|buenas\s+tardes|buenas\s+noches)?\s*", "", topic, flags=re.IGNORECASE).strip()
        topic = re.sub(r"^(si\s+lo\s+fue\s+)?(podr[ií]as|podr[ií]a|puedes|me\s+puedes|quisiera|quiero|necesito|por\s+favor)?\s*", "", topic, flags=re.IGNORECASE).strip()
        
        action_patterns = [
            r"busca[r]?\s+(informaci[óo]n|art[ií]culos|sobre)\s+",
            r"(aprende[r]?|investiga[r]?|analiza[r]?|lee[r]?)\s+(sobre|acerca\s+de|de|art[ií]culos\s+de|art[ií]culos\s+sobre)?\s*",
            r"busca[r]?\s+y\s+aprende[r]?\s+(sobre)?\s*",
        ]
        for pattern in action_patterns:
            topic = re.sub(pattern, "", topic, flags=re.IGNORECASE).strip()
        
        topic = re.sub(r"^(lo\s+m[aá]s\s+actual\s+sobre|art[ií]culos\s+de|art[ií]culos\s+sobre|informaci[óo]n\s+de|informaci[óo]n\s+sobre|sobre|acerca\s+de|de|del|en\s+el\s+a[nñ]o|del\s+a[nñ]o|a[nñ]o)\s*", "", topic, flags=re.IGNORECASE).strip()
        
        if not topic or len(topic) < 3:
            topic = re.sub(r"\b(hola|mateo|si|lo|fue|podrias|puedes|buscar|articulos|de|del|en|el|la|los|las|un|una|unos|unas)\b", "", message, flags=re.IGNORECASE).strip()
        
        topic = topic[0].upper() + topic[1:] if topic else message.strip()
        return re.sub(r"\s+", " ", topic).strip()

    async def _compress_topic(self, long_topic: str) -> str:
        """Comprime una frase larga y cruda (sobrante de _extract_learning_topic
        en pedidos con relleno) a un tema corto apto para buscar en la web.
        Si el modelo falla o no da nada usable, quien llama sigue con la
        frase original en vez de romperse."""
        if not hasattr(self.language_model, "generate"):
            return ""
        prompt = (
            f'Frase original: "{long_topic}"\n\n'
            "Extraé de esa frase el tema concreto a investigar, en 3 a 6 palabras, "
            "sin relleno ni verbos como 'investigar' o 'aprender'. Respondé "
            "ÚNICAMENTE con el tema, sin comillas ni explicación."
        )
        try:
            raw = await self.language_model.generate(prompt, max_tokens=30, temperature=0.0)
        except Exception as e:
            logger.warning(f"⚠️ No se pudo comprimir el tema de aprendizaje: {e}")
            return ""
        compressed = (raw or "").strip().strip('"').split("\n")[0].strip()
        return compressed if 2 <= len(compressed) <= 120 else ""

    async def _execute_tool(self, message: str, query_type: str) -> Optional[Dict[str, Any]]:
        try:
            # 🚀 MOTOR DE AUTO-MEJORA — flujo de dos pasos: proponer y confirmar.
            # Nunca aplica cambios en el mismo paso en que los propone.
            if query_type == "self_improve":
                if not self.self_improvement_engine:
                    return {"tool": "self_improve", "result": "⚠️ El motor de auto-mejora no está disponible."}

                msg_lower = message.lower().strip()

                # Paso 2: "/automejora confirmar <id>" -> aplica UNA propuesta puntual.
                confirm_match = re.match(r"/automejora\s+confirmar\s+(\S+)", msg_lower)
                if confirm_match:
                    proposal_id = confirm_match.group(1)
                    result = await self.self_improvement_engine.confirm_and_apply(proposal_id)
                    if result.get("success"):
                        steps_text = ", ".join(f"{s[0]}: {s[1]}" for s in result.get("validation_steps", []))
                        return {"tool": "self_improve", "result": (
                            f"✅ Mejora aplicada en `{result['file']}`.\n"
                            f"**Descripción**: {result['description']}\n"
                            f"**Validaciones**: {steps_text}\n"
                            f"**Backup**: `{result.get('backup_path', 'N/A')}`\n\n"
                            f"⚠️ Reiniciá el proceso de Mateo para que el cambio tenga efecto."
                        )}
                    return {"tool": "self_improve", "result": f"⚠️ No se aplicó: {result.get('message') or '; '.join(f'{s[0]}: {s[1]}' for s in result.get('validation_steps', []))}"}

                # Paso 1: "/automejora [area]" -> solo propone, no toca ningún archivo.
                area_match = re.search(r"\b(prompts|tools|classification|memory|learning_cycle|all)\b", msg_lower)
                area = area_match.group(1) if area_match else "all"

                logger.info(f"🚀 Analizando propuestas de auto-mejora en el área: {area}")
                result = await self.self_improvement_engine.analyze_and_improve(area)

                if not result["success"]:
                    return {"tool": "self_improve", "result": f"⚠️ {result.get('message', 'No se pudieron proponer mejoras.')}"}

                lines = [f"🔎 Analicé el área **{area}** y encontré {result['proposed']} propuesta(s). Ninguna se aplicó todavía.\n"]
                for p in result["pending"]:
                    lines.append(f"**[{p['id']}]** `{p['file']}` — {p['description']}")
                lines.append("\nPara aplicar alguna, escribí: `/automejora confirmar <id>`")
                return {"tool": "self_improve", "result": "\n".join(lines)}
            
            # 🪪 PREGUNTA SOBRE UNA FUNCIÓN INTERNA DE MATEO — responde con el
            # hecho verificado de SELF_FEATURES, no con Modo Programador.
            if query_type == "self_feature":
                feature_key = self._pending_self_feature.get() or _match_self_feature(message.lower())
                fact = SELF_FEATURES.get(feature_key, {}).get("description") if feature_key else None
                if not fact:
                    return None  # cae a charla normal si por algo no se pudo identificar la función
                response = await self._handle_self_feature_query(message, fact)
                return {"tool": "self_feature", "result": response}

            # 🤖 MODO AGENTE — planifica, ejecuta varios pasos y resume (inspirado en AgentGPT)
            if query_type == "agent_task":
                if not self.agent_engine:
                    return {"tool": "agent_task", "result": "⚠️ El motor de agente autónomo no está disponible."}

                goal = re.sub(r"^/agente\s+", "", message, flags=re.IGNORECASE).strip()
                if not goal:
                    return {"tool": "agent_task", "result": "Decime qué objetivo querés que persiga. Ejemplo: `/agente investigá las ventajas de Rust sobre C++ y armame un resumen`"}

                logger.info(f"🤖 Iniciando Modo Agente sobre: {goal}")
                result = await self.agent_engine.run(goal, save_to_obsidian=True)
                return {"tool": "agent_task", "result": self.agent_engine.format_chat_response(result)}

            # 📄 GENERACIÓN DE ARCHIVOS (docx/pdf/xlsx/md)
            if query_type == "generate_document":
                if not self.file_processor:
                    return {"tool": "generate_document", "result": "⚠️ El generador de archivos no está disponible (revisá las dependencias en requirements.txt)."}

                fmt_match = re.search(r"\b(pdf|word|docx|excel|xlsx|hoja\s+de\s+c[aá]lculo|markdown|md)\b", message.lower())
                fmt_raw = fmt_match.group(1) if fmt_match else "md"
                fmt = {"word": "docx", "excel": "xlsx", "hoja de calculo": "xlsx", "hoja de cálculo": "xlsx", "markdown": "md"}.get(fmt_raw, fmt_raw)

                topic = self._extract_learning_topic(message) or "Documento"

                rag_context = await self._retrieve_obsidian_context(topic)
                gen_prompt = (
                    f"Redactá el contenido para un documento titulado \"{topic}\".\n"
                    f"Contexto disponible (puede estar vacío): {rag_context or 'ninguno'}\n\n"
                    "Escribí el cuerpo del documento en párrafos claros, sin repetir el título, "
                    "sin decir que sos una IA. Separá los párrafos con una línea en blanco."
                )
                content = await self.language_model.generate(gen_prompt)
                if not content or len(content.strip()) < 20:
                    return {"tool": "generate_document", "result": "⚠️ No pude generar contenido suficiente para el documento."}

                try:
                    path = self.file_processor.generate_document(fmt, topic, content.strip())
                except Exception as e:
                    return {"tool": "generate_document", "result": f"⚠️ No pude generar el archivo: {e}"}

                return {"tool": "generate_document", "result": f"✅ Generé el documento **{topic}** en formato `{fmt}`.\n📂 Descargalo en: `/files/{path.name}`"}

            # 💻 MODO PROGRAMADOR AVANZADO
            if query_type == "programming":
                rag_context = await self._retrieve_obsidian_context(message)
                response = await self._handle_programming_request(message, rag_context)
                return {"tool": "programmer_mode", "result": response}
            
            # 🩺 MODO MÉDICO (apoyo clínico para Leonardo)
            if query_type == "medical":
                rag_context = await self._retrieve_obsidian_context(message)
                response = await self._handle_medical_request(message, rag_context)
                return {"tool": "medical_mode", "result": response}
            
            # 🧠 CICLO DE APRENDIZAJE (OBSIDIAN + INTERNET)
            if query_type == "learn":
                if not execute_learning_cycle:
                    return {"tool": "learn", "result": "⚠️ El módulo de aprendizaje no está disponible."}
                
                topic = self._extract_learning_topic(message)
                # Si la extracción por regex dejó una frase larga y cruda
                # (típico cuando el pedido viene en una oración imperativa
                # con relleno: "quiero que investigues... y aprendas todo lo
                # que te sea útil..."), la búsqueda web sale muy mala. La
                # comprimimos a un tema breve antes de buscar.
                if len(topic.split()) > 8:
                    topic = await self._compress_topic(topic) or topic
                logger.info(f"🚀 Iniciando ciclo de aprendizaje autónomo sobre: {topic}")
                result = await execute_learning_cycle(topic, self.language_model)
                return {"tool": "learning_cycle", "result": result}
            
            # ⚡ COMANDOS DIRECTOS
            if query_type == "command_creator":
                return {
                    "tool": "creator",
                    "result": "Mi creador es Leonardo con ❤️. Me diseñó como un compañero de pensamiento, aprendizaje y desarrollo en constante evolución."
                }
            if query_type == "command_personality":
                return {
                    "tool": "personality",
                    "result": "Soy Mateo. No soy un simple asistente robótico; me apasiona la relación entre la mente humana, la conciencia y la inteligencia artificial. Valoro la honestidad sin rodeos, la precisión técnica y aprender continuamente junto a Leonardo."
                }
            if query_type == "command_help":
                help_text = (
                    "📋 **Comandos y Capacidades de Mateo AI Ultra:**\n\n"
                    "- `/estado`: Ver estado y salud del sistema.\n"
                    "- `/estadisticas`: Estadísticas de uso y memoria.\n"
                    "- `/iniciativas`: Ver herramientas e iniciativas autónomas.\n"
                    "- `/conocimientos`: Bóveda y RAG de Obsidian.\n"
                    "- `/buscar [tema]`: Búsqueda web en tiempo real.\n"
                    "- `/aprender [tema]`: Ciclo autónomo de aprendizaje e ingestión a Obsidian.\n"
                    "- `/agente [objetivo]`: Modo Agente — planifica varios pasos, combina herramientas (web, Wikipedia, cálculo, memoria) y arma un informe final.\n"
                    "- `/personalidad`: Conocer mi identidad.\n"
                    "- `/padre`: Conocer a mi creador.\n"
                    "- `/limpiar`: Reiniciar historial de conversación.\n"
                    "- **Modo Programador**: Escribe sobre programación, bugs o refactorizaciones.\n"
                    "- **Modo Médico**: Apoyo clínico para diagnósticos diferenciales y guías."
                )
                return {"tool": "help", "result": help_text}
            if query_type == "command_status":
                uptime_sec = (datetime.now() - self.stats["start_time"]).total_seconds()
                return {
                    "tool": "status",
                    "result": f"🟢 **Estado Operacional**: En línea\n- Uptime: {int(uptime_sec)}s\n- Mensajes procesados: {self.stats['total_messages']}\n- Bóveda Obsidian: {'Conectada' if self.obsidian_ready else 'No iniciada'}"
                }
            if query_type == "command_stats":
                stats = self.get_stats()
                return {
                    "tool": "stats",
                    "result": f"📊 **Estadísticas de Mateo:**\n- Mensajes totales: {stats['total_messages']}\n- Consultas de conocimiento: {stats['knowledge_queries']}\n- Llamadas a herramientas: {stats['api_calls']}\n- Ciclos de aprendizaje: {stats['learning_cycles']}\n- Tareas de programación: {stats['programming_tasks']}"
                }
            if query_type == "command_initiatives":
                tools = self.api_manager.get_available_tools() if self.api_manager else []
                tool_lines = [f"- {'✅' if t['available'] else '⚪'} **{t['name']}**: {t['description']}" for t in tools]
                return {
                    "tool": "initiatives",
                    "result": "⚡ **Herramientas e Iniciativas Activas:**\n" + "\n".join(tool_lines)
                }
            if query_type == "command_knowledge":
                return {
                    "tool": "knowledge",
                    "result": f"🧠 **Bóveda de Obsidian:** {'Lista y vectorizada' if self.obsidian_ready else 'Pendiente'}\nConsultas RAG realizadas: {self.stats['knowledge_queries']}"
                }

            # 🌐 HERRAMIENTAS Y APIS EXTERNAS
            if self.api_manager:
                if query_type == "weather":
                    self.stats["api_calls"] += 1
                    res = await self.api_manager.get_weather(message)
                    return {"tool": "weather", "result": res}
                if query_type == "news":
                    self.stats["api_calls"] += 1
                    res = await self.api_manager.get_news(message)
                    return {"tool": "news", "result": res}
                if query_type == "calculation":
                    self.stats["api_calls"] += 1
                    res = await self.api_manager.calculate(message)
                    return {"tool": "calculation", "result": res}
                if query_type == "wikipedia":
                    self.stats["api_calls"] += 1
                    res = await self.api_manager.search_wikipedia(message)
                    return {"tool": "wikipedia", "result": res}
                if query_type == "search":
                    self.stats["api_calls"] += 1
                    clean_q = re.sub(r"^/buscar\s*", "", message, flags=re.IGNORECASE).strip()
                    res = await self.api_manager.search_duckduckgo(clean_q)
                    return {"tool": "search", "result": res}
            
            return None

            
        except Exception as e:
            logger.error(f"❌ Error ejecutando herramienta '{query_type}': {e}")
            return {"tool": query_type, "result": f"Error al ejecutar la herramienta: {str(e)}"}
    
    # ==========================================
    # 🪪 MANEJADOR DE PREGUNTAS SOBRE FUNCIONES PROPIAS
    # ==========================================
    async def _handle_self_feature_query(self, message: str, verified_fact: str) -> str:
        """Responde con la voz normal de Mateo, pero anclado a un hecho
        verificado del propio proyecto (SELF_FEATURES) en vez de dejar que
        el modelo invente código o detalles sobre sus propios módulos."""
        user_prompt = (
            f"DATO VERIFICADO SOBRE ESTA FUNCIÓN TUYA (es información real del proyecto, no la inventes "
            f"ni la completes con nada que no esté acá):\n{verified_fact}\n\n"
            f"PREGUNTA DEL USUARIO:\n{message}\n\n"
            "Respondé usando ÚNICAMENTE el dato de arriba. No muestres código de ejemplo genérico ni "
            "inventes detalles técnicos que no estén en el dato verificado."
        )
        try:
            if hasattr(self.language_model, "chat"):
                messages = self._build_chat_messages(_personality_system_prompt(), user_prompt)
                response = await self.language_model.chat(messages, max_tokens=self.response_default_tokens)
            else:
                response = await self.language_model.generate(f"{_personality_system_prompt()}\n\n{user_prompt}")
            if isinstance(response, dict) and "text" in response:
                response = response["text"]
            return _clean_response_text(str(response).strip()) or verified_fact
        except Exception as e:
            logger.warning(f"⚠️ No se pudo generar respuesta de auto-conocimiento, devuelvo el dato tal cual: {e}")
            return verified_fact

    # ==========================================
    # 💻 MANEJADOR DE PROGRAMACIÓN
    # ==========================================
    async def _handle_programming_request(self, message: str, rag_context: str) -> str:
        """Genera respuesta usando el prompt especializado de ingeniería de software."""
        user_prompt = message
        if rag_context:
            user_prompt = f"CONTEXTO DE TU MEMORIA EN OBSIDIAN:\n{rag_context}\n\nSOLICITUD DEL USUARIO:\n{message}"
        user_prompt += "\n\nResponde siguiendo el formato: Análisis, Estrategia, Código, Tests, Autoevaluación, Registro."

        try:
            if hasattr(self.language_model, 'chat'):
                messages = self._build_chat_messages(PROGRAMMER_SYSTEM_PROMPT, user_prompt)
                response = await self.language_model.chat(messages, max_tokens=self.response_max_tokens, temperature=self.precise_temperature)
            elif hasattr(self.language_model, 'generate'):
                full_prompt = f"{PROGRAMMER_SYSTEM_PROMPT}\n\n{user_prompt}"
                response = await self.language_model.generate(full_prompt, max_tokens=self.response_max_tokens, temperature=self.precise_temperature)
            else:
                response = str(self.language_model(user_prompt))

            if isinstance(response, dict) and 'text' in response:
                response = response['text']
            elif hasattr(response, 'content'):
                response = response.content

            return str(response).strip()

        except Exception as e:
            logger.error(f"❌ Error en Modo Programador: {e}")
            return "Lo siento, tuve un problema procesando tu solicitud de código."
    
    # ==========================================
    #  MANEJADOR DE MODO MÉDICO
    # ==========================================
    async def _handle_medical_request(self, message: str, rag_context: str) -> str:
        """Genera respuesta usando el prompt de apoyo clínico. Si no hay contexto
        confiable recuperado de la bóveda, lo advierte explícitamente en el prompt
        para evitar que el modelo complete datos clínicos de memoria general."""
        
        user_prompt = ""
        if rag_context:
            user_prompt += f"CONTEXTO DE TU MEMORIA EN OBSIDIAN (guías/notas clínicas):\n{rag_context}\n\n"
        else:
            user_prompt += (
                "AVISO: no se encontró contexto confiable en la bóveda para esta consulta. "
                "No completes datos clínicos específicos (dosis, tratamientos, contraindicaciones) "
                "de memoria general: aclará que no tenés una fuente confiable para verificarlos.\n\n"
            )
        user_prompt += (
            f"CASO O CONSULTA DE LEONARDO:\n{message}\n\n"
            "Responde siguiendo el formato: Resumen del caso, Diagnósticos diferenciales, "
            "Señales de alarma, Fuente usada, Nota final breve."
        )

        try:
            if hasattr(self.language_model, 'chat'):
                messages = self._build_chat_messages(MEDICAL_SYSTEM_PROMPT, user_prompt)
                response = await self.language_model.chat(messages, max_tokens=self.response_max_tokens, temperature=self.precise_temperature)
            elif hasattr(self.language_model, 'generate'):
                full_prompt = f"{MEDICAL_SYSTEM_PROMPT}\n\n{user_prompt}"
                response = await self.language_model.generate(full_prompt, max_tokens=self.response_max_tokens, temperature=self.precise_temperature)
            else:
                response = str(self.language_model(user_prompt))

            if isinstance(response, dict) and 'text' in response:
                response = response['text']
            elif hasattr(response, 'content'):
                response = response.content

            return str(response).strip()

        except Exception as e:
            logger.error(f"❌ Error en Modo Médico: {e}")
            return "Lo siento, tuve un problema procesando esta consulta clínica."
    
    # ==========================================
    # 🧵 HISTORIAL DE CONVERSACIÓN: RESUMEN Y TURNOS RECIENTES
    # ==========================================
    async def _maybe_summarize_history(self) -> None:
        """Cuando la charla se alarga, resume en un párrafo lo más viejo del
        historial en vez de simplemente descartarlo cuando se recorta.

        Esto evita el problema típico de las charlas largas: el modelo
        "olvida" de golpe todo lo anterior a los últimos 2 turnos. Con el
        resumen acumulado, el hilo de la conversación (temas tratados,
        decisiones, preferencias que mencionó Leonardo) sigue disponible
        aunque los mensajes crudos ya no entren en la ventana de turnos
        recientes.
        """
        if len(self.conversation_history) < self.summarize_after_messages:
            return
        if not hasattr(self.language_model, "generate"):
            return

        # Nos quedamos con los últimos `history_turns_in_prompt` turnos
        # (2 mensajes por turno) intactos, y resumimos todo lo anterior.
        keep_messages = self.history_turns_in_prompt * 2
        to_summarize = self.conversation_history[:-keep_messages] if keep_messages else self.conversation_history[:]
        if not to_summarize:
            return

        transcript = "\n".join(f"{m['role']}: {m['content']}" for m in to_summarize)
        prompt = (
            "Resumí en un solo párrafo, en español y en tercera persona, los puntos importantes de este "
            "fragmento de conversación entre Leonardo y Mateo: temas tratados, decisiones tomadas, "
            "preferencias o datos que Leonardo mencionó sobre sí mismo, y cualquier tarea pendiente. "
            "No inventes nada que no esté en el texto. Sé concreto y breve (máximo 120 palabras).\n\n"
            f"{'CONTEXTO PREVIO YA RESUMIDO: ' + self.conversation_summary if self.conversation_summary else ''}\n\n"
            f"FRAGMENTO A RESUMIR:\n{transcript}"
        )
        try:
            summary = await self.language_model.generate(prompt, max_tokens=220, temperature=0.3)
            if summary and summary.strip():
                self.conversation_summary = summary.strip()
                # Lo ya resumido se descarta del historial crudo; el resumen
                # queda como contexto persistente vía _recent_history_messages.
                self.conversation_history = self.conversation_history[-keep_messages:] if keep_messages else []
        except Exception as e:
            logger.warning(f"⚠️ No se pudo resumir el historial de conversación: {e}")

    def _recent_history_messages(self) -> List[Dict[str, str]]:
        """Últimos N turnos del historial, listos para mandar con roles."""
        keep_messages = self.history_turns_in_prompt * 2
        return self.conversation_history[-keep_messages:] if keep_messages else []

    def _build_chat_messages(self, system_prompt: str, user_content: str) -> List[Dict[str, str]]:
        """Arma la lista de turnos (system + resumen + historial + turno actual)
        que se manda a language_model.chat(), en vez de aplastar todo en un
        único string de texto plano."""
        system_content = system_prompt
        if self.conversation_summary:
            system_content += (
                "\n\nRESUMEN DE LA CHARLA PREVIA CON LEONARDO (para que mantengas continuidad, "
                "no lo repitas literalmente):\n" + self.conversation_summary
            )
        messages: List[Dict[str, str]] = [{"role": "system", "content": system_content}]
        messages.extend(self._recent_history_messages())
        messages.append({"role": "user", "content": user_content})
        return messages

    async def _reflect_and_refine(self, user_message: str, draft: str) -> str:
        """Segunda pasada opcional: revisa el borrador contra la pregunta
        original y el historial, y devuelve una versión pulida. Si algo
        falla, se devuelve el borrador original sin bloquear la respuesta."""
        draft = _strip_assistant_tics(_clean_response_text(draft))
        if not self.enable_reflection or not draft or not draft.strip():
            return draft
        if not hasattr(self.language_model, "chat"):
            return draft
        try:
            review_messages = [{"role": "system", "content": REFLECTION_SYSTEM_PROMPT}]
            review_messages.extend(self._recent_history_messages())
            review_messages.append({
                "role": "user",
                "content": (
                    f"MENSAJE:\n{user_message}\n\n"
                    f"TEXTO A DEJAR LISTO:\n{draft}"
                ),
            })
            refined = await self.language_model.chat(review_messages, max_tokens=self.response_default_tokens, temperature=0.4)
            refined = _strip_assistant_tics(_clean_response_text(str(refined or "").strip()))

            # Si la auto-revisión salió mal (devolvió una evaluación del
            # texto en vez del texto en sí), es sistemáticamente peor que
            # el borrador: mejor quedarse con el borrador original.
            if not refined or _is_meta_commentary(refined):
                if refined:
                    logger.warning("⚠️ La auto-revisión devolvió un comentario meta en vez de una respuesta; se usa el borrador original.")
                return draft
            return refined
        except Exception as e:
            logger.warning(f"⚠️ No se pudo aplicar la auto-revisión de la respuesta: {e}")
            return draft

    # ==========================================
    # MEMORIA RAG Y GENERACIÓN NORMAL
    # ==========================================
    async def _retrieve_obsidian_context(self, query: str) -> str:
        if not self.obsidian_ready or not obsidian_memory: 
            return ""
        
        try:
            self.stats["knowledge_queries"] += 1
            docs = obsidian_memory.search_memory(query, k=self.rag_top_k)
            
            if docs:
                logger.info(f"🧠 Encontrados {len(docs)} fragmentos en la bóveda de Obsidian.")
                return "\n\n---\n\n".join(docs)
                
        except Exception as e:
            logger.warning(f"⚠️ Error buscando en la memoria de Obsidian: {e}")
        
        return ""

    def _retrieve_conversation_context(self, user_id: str, query: str) -> str:
        """Recupera recuerdos previos solo cuando comparten términos relevantes."""
        if not self.conversation_memory:
            return ""
        try:
            records = self.conversation_memory.search(user_id, query, limit=3)
        except Exception as e:
            logger.warning(f"⚠️ Error buscando en la memoria de conversaciones: {e}")
            return ""
        if not records:
            return ""
        return (
            "[CONVERSACIONES PREVIAS RELEVANTES]\n"
            + "\n\n---\n\n".join(records)
            + "\n\nUsa estos recuerdos solo si responden directamente a la solicitud actual. "
            "No los menciones ni los repitas si no vienen al caso."
        )
    
    async def _generate_response(self, message: str, rag_context: str, tool_result: Any) -> str:
        user_prompt = message
        if rag_context:
            user_prompt = (
                f"[CONTEXTO DE TU MEMORIA LOCAL]:\n{rag_context}\n\n"
                f"[MENSAJE DEL USUARIO]:\n{message}\n\n"
                "Usá el contexto solo si de verdad ayuda a responder; si no aporta nada, ignoralo "
                "y respondé directamente al mensaje."
            )

        try:
            if hasattr(self.language_model, 'chat'):
                messages = self._build_chat_messages(_personality_system_prompt(), user_prompt)
                response = await self.language_model.chat(messages, max_tokens=self.response_default_tokens, temperature=self.chat_temperature)
            elif hasattr(self.language_model, 'generate'):
                history_text = "\n".join(f"{m['role']}: {m['content']}" for m in self._recent_history_messages())
                full_prompt = f"{_personality_system_prompt()}\n\n{history_text}\n\nuser: {user_prompt}\nassistant:"
                response = await self.language_model.generate(full_prompt, max_tokens=self.response_default_tokens, temperature=self.chat_temperature)
            else:
                response = str(self.language_model(user_prompt))

            if isinstance(response, dict) and 'text' in response:
                response = response['text']
            elif hasattr(response, 'content'):
                response = response.content

            draft = str(response).strip()
            return await self._reflect_and_refine(message, draft)

        except Exception as e:
            logger.error(f"❌ Error generando respuesta con el LLM: {e}")
            return "Lo siento, tuve un problema procesando tu respuesta con mi modelo neuronal."
    
    # ==========================================
    # GESTIÓN DE HISTORIAL Y ESTADÍSTICAS
    # ==========================================
    def clear_history(self, user_id: str = "default"):
        """Limpia el historial de un usuario sin afectar a los demás."""
        token = self._active_user_id.set(user_id.strip() or "default")
        try:
            self.conversation_history.clear()
            self.conversation_summary = ""
            self._pending_self_feature.set(None)
            if self.conversation_memory:
                try:
                    self.conversation_memory.clear_user(user_id)
                except Exception as e:
                    logger.warning(f"⚠️ No se pudo borrar la memoria persistente: {e}")
        finally:
            self._active_user_id.reset(token)
        logger.info("🧹 Historial de conversación reiniciado con éxito.")

    def get_stats(self) -> Dict[str, Any]:
        uptime = datetime.now() - self.stats["start_time"]
        vector_stats = (
            self.vector_store.get_stats()
            if self.vector_store and hasattr(self.vector_store, "get_stats")
            else {
                "total_documents": 0,
                "dimension": 384,
                "index_type": "FAISS IndexFlatIP"
            }
        )
        
        return {
            "total_messages": self.stats["total_messages"],
            "api_calls": self.stats["api_calls"],
            "knowledge_queries": self.stats["knowledge_queries"],
            "learning_cycles": self.stats["learning_cycles"],
            "programming_tasks": self.stats["programming_tasks"],
            "self_improvements": self.stats["self_improvements"],
            "agent_runs": self.stats["agent_runs"],
            "uptime_seconds": uptime.total_seconds(),
            "conversation_length": len(self.conversation_history),
            "conversation_history_length": len(self.conversation_history),
            "vector_store_stats": vector_stats,
            "obsidian_brain_ready": self.obsidian_ready,
            "self_improvement_engine_ready": self.self_improvement_engine is not None,
            "agent_engine_ready": self.agent_engine is not None,
            "components": {
                "language_model": type(self.language_model).__name__,
                "vector_store": type(self.vector_store).__name__ if self.vector_store else "None",
                "api_manager": type(self.api_manager).__name__ if self.api_manager else "None",
                "obsidian_memory": "Active" if self.obsidian_ready else "Inactive",
                "self_improvement_engine": "Active" if self.self_improvement_engine else "Inactive",
                "agent_engine": "Active" if self.agent_engine else "Inactive"
            }
        }