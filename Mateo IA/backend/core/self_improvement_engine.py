"""
Motor de Auto-mejora Semi-Autónoma de Mateo AI Ultra (Nivel 2)
Permite a Mateo analizar, proponer, validar y aplicar mejoras a su propio código.
"""
import ast
import os
import re
import json
import shutil
import logging
import asyncio
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# CORRECCIÓN: Usar __name__ correctamente
logger = logging.getLogger(__name__)

# Rutas normalizadas respecto a la raíz del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent.parent
BACKUP_DIR = BASE_DIR / "backend" / "backups" / "auto_improvement"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_FILES = [
    str(BASE_DIR / "backend" / "core" / "mateo_ultra_core.py"),
    str(BASE_DIR / "backend" / "core" / "learning_cycle.py"),
    str(BASE_DIR / "backend" / "tools" / "web_learner.py"),
    str(BASE_DIR / "backend" / "tools" / "obsidian_writer.py"),
    str(BASE_DIR / "backend" / "tools" / "obsidian_memory.py"),
    "backend/core/mateo_ultra_core.py",
    "backend/core/learning_cycle.py",
    "backend/tools/web_learner.py",
    "backend/tools/obsidian_writer.py",
    "backend/tools/obsidian_memory.py",
]


class SelfImprovementEngine:
    """
    Nivel 2 con confirmación humana obligatoria: el motor NUNCA aplica cambios
    de forma automática. `analyze_and_improve` solo propone; `confirm_and_apply`
    aplica una propuesta puntual que el usuario aprobó explícitamente por su id.
    Las propuestas pendientes viven en memoria y expiran solas al reiniciar el proceso.
    """

    # CORRECCIÓN 1: Constructor correcto con doble guion bajo
    def __init__(self, language_model):
        self.language_model = language_model
        self.improvement_history = []
        self._pending: Dict[str, Dict[str, Any]] = {}

    async def analyze_and_improve(self, area: str = "all") -> Dict[str, Any]:
        """Analiza el código y PROPONE mejoras. No modifica ningún archivo."""
        logger.info(f"Iniciando analisis de auto-mejora para el area: {area}")
        current_code = self._gather_code_for_area(area)

        if not current_code:
            return {"success": False, "message": "No se encontro codigo para analizar."}

        improvements = await self._propose_improvements(current_code, area)

        if not improvements:
            return {"success": False, "message": "No se propusieron mejoras."}

        proposals = []
        for improvement in improvements:
            check = self._validate_only(improvement)
            if not check["valid"]:
                continue
            proposal_id = f"si_{len(self._pending) + 1}_{datetime.now().strftime('%H%M%S')}"
            self._pending[proposal_id] = improvement
            proposals.append({
                "id": proposal_id,
                "file": improvement.get("archivo"),
                "description": improvement.get("descripcion"),
                "validation_steps": check["validation_steps"],
            })

        if not proposals:
            return {"success": False, "message": "Las mejoras propuestas no pasaron la validación previa (sintaxis o archivo no permitido)."}

        return {"success": True, "proposed": len(improvements), "pending": proposals}

    async def confirm_and_apply(self, proposal_id: str) -> Dict[str, Any]:
        """Aplica UNA propuesta previamente generada, identificada por su id, tras
        confirmación explícita del usuario. Corre el sandbox recién en este paso."""
        improvement = self._pending.pop(proposal_id, None)
        if improvement is None:
            return {"success": False, "message": f"No encontré la propuesta '{proposal_id}' (¿ya fue aplicada, o el proceso se reinició?)."}

        result = await self._validate_and_apply(improvement)
        if result["success"]:
            self._notify_improvement(result)
            self._log_to_obsidian(result)
        return result

    def _gather_code_for_area(self, area: str) -> Dict[str, str]:
        code_map = {}
        if area in ["all", "prompts"]:
            code_map["mateo_ultra_core.py"] = self._read_file("backend/core/mateo_ultra_core.py")
        if area in ["all", "learning_cycle"]:
            code_map["learning_cycle.py"] = self._read_file("backend/core/learning_cycle.py")
        if area in ["all", "tools"]:
            code_map["web_learner.py"] = self._read_file("backend/tools/web_learner.py")
            code_map["obsidian_writer.py"] = self._read_file("backend/tools/obsidian_writer.py")
        if area in ["all", "memory"]:
            code_map["obsidian_memory.py"] = self._read_file("backend/tools/obsidian_memory.py")
        return {k: v for k, v in code_map.items() if v}

    def _read_file(self, file_path: str) -> Optional[str]:
        try:
            path = Path(file_path)
            if not path.is_absolute():
                path = BASE_DIR / path
            with path.open("r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error leyendo {file_path}: {str(e)}")
            return None

    async def _propose_improvements(self, current_code: Dict[str, str], area: str) -> List[Dict[str, Any]]:
        code_parts = []
        for filename, content in current_code.items():
            code_parts.append(f"### {filename}")
            code_parts.append(content[:2000] + "...")
            code_parts.append("")
        code_summary = "\n".join(code_parts)

        prompt_lines = [
            "Eres Mateo, un ingeniero de software senior analizando tu propio codigo para mejorarlo.",
            "",
            f"AREA A ANALIZAR: {area}",
            "",
            "CODIGO ACTUAL:",
            code_summary,
            "",
            "TAREA: Propone hasta 3 mejoras concretas y seguras.",
            "Para cada mejora, devuelve un JSON con estos campos:",
            "- archivo: Nombre del archivo a modificar (debe estar en la lista permitida)",
            "- descripcion: Que vas a mejorar y por que",
            "- codigo_original: Fragmento exacto del codigo actual que vas a reemplazar",
            "- codigo_nuevo: El nuevo codigo mejorado",
            "",
            f"Archivos permitidos: {', '.join(ALLOWED_FILES)}",
            "",
            "Devuelve SOLO un array JSON valido, sin texto adicional antes o despues (no uses markdown ```json).",
            "Ejemplo de formato:",
            '[{"archivo": "backend/tools/web_learner.py", "descripcion": "Mejorar X", "codigo_original": "def old...", "codigo_nuevo": "def new..."}]',
            "",
            "Si no hay mejoras obvias, devuelve exactamente: []"
        ]
        prompt = "\n".join(prompt_lines)

        try:
            response = await self.language_model.generate(prompt)
            
            # CORRECCIÓN 3: Regex mejorado para capturar todo el array JSON correctamente
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                try:
                    improvements = json.loads(json_match.group(0))
                    if isinstance(improvements, list):
                        return improvements
                except json.JSONDecodeError:
                    logger.warning("El JSON extraído de la respuesta del LLM no es válido.")
            
            if "[]" in response:
                return []
                
            return []
        except Exception as e:
            logger.error(f"Error proponiendo mejoras: {str(e)}")
            return []

    def _validate_only(self, improvement: Dict[str, Any]) -> Dict[str, Any]:
        """Corre las validaciones que NO tocan disco (whitelist + sintaxis), para
        decidir si una propuesta merece mostrarse al usuario antes de aplicarla."""
        file_path = improvement.get("archivo")
        new_code = improvement.get("codigo_nuevo")
        steps: List[tuple] = []

        if not isinstance(file_path, str) or not isinstance(new_code, str) or not isinstance(improvement.get("codigo_original"), str):
            return {"valid": False, "validation_steps": [("Entrada", "RECHAZADO: propuesta incompleta")]}

        candidate = Path(file_path)
        if not candidate.is_absolute():
            candidate = BASE_DIR / candidate
        normalized_path = str(candidate.resolve())
        allowed_paths = {
            str((BASE_DIR / path).resolve()) if not Path(path).is_absolute() else str(Path(path).resolve())
            for path in ALLOWED_FILES
        }
        if normalized_path not in allowed_paths:
            return {"valid": False, "validation_steps": [("Lista blanca", "RECHAZADO: Archivo no permitido")]}
        steps.append(("Lista blanca", "APROBADO"))

        try:
            ast.parse(new_code)
            steps.append(("AST (Sintaxis)", "APROBADO"))
        except SyntaxError as e:
            return {"valid": False, "validation_steps": steps + [("AST (Sintaxis)", f"RECHAZADO: {e}")]}

        return {"valid": True, "validation_steps": steps}

    async def _validate_and_apply(self, improvement: Dict[str, Any]) -> Dict[str, Any]:
        file_path = improvement.get("archivo")
        original_code = improvement.get("codigo_original")
        new_code = improvement.get("codigo_nuevo")
        description = improvement.get("descripcion")
        
        result = {
            "file": file_path,
            "description": description,
            "success": False,
            "validation_steps": [],
            "rollback_performed": False
        }

        if not isinstance(file_path, str) or not isinstance(original_code, str) or not isinstance(new_code, str):
            result["validation_steps"].append(("Entrada", "RECHAZADO: propuesta incompleta"))
            return result

        candidate = Path(file_path)
        if not candidate.is_absolute():
            candidate = BASE_DIR / candidate
        normalized_path = str(candidate.resolve())
        allowed_paths = {
            str((BASE_DIR / path).resolve()) if not Path(path).is_absolute() else str(Path(path).resolve())
            for path in ALLOWED_FILES
        }
        if normalized_path not in allowed_paths:
            result["validation_steps"].append(("Lista blanca", "RECHAZADO: Archivo no permitido"))
            return result
        file_path = normalized_path
        result["validation_steps"].append(("Lista blanca", "APROBADO"))

        try:
            ast.parse(new_code)
            result["validation_steps"].append(("AST (Sintaxis)", "APROBADO"))
        except SyntaxError as e:
            result["validation_steps"].append(("AST (Sintaxis)", f"RECHAZADO: {str(e)}"))
            return result

        # CORRECCIÓN 4: Sandbox ahora es asíncrono para no bloquear el event loop
        sandbox_result = await self._run_sandbox_test(new_code)
        if not sandbox_result["success"]:
            result["validation_steps"].append(("Sandbox", f"RECHAZADO: {sandbox_result['error']}"))
            return result
        result["validation_steps"].append(("Sandbox", "APROBADO"))

        backup_path = None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                full_content = f.read()
                
            if original_code not in full_content:
                result["validation_steps"].append(("Aplicacion", "RECHAZADO: Codigo original no encontrado en el archivo"))
                return result

            backup_path = self._create_backup(file_path)
            result["backup_path"] = str(backup_path)
                
            new_content = full_content.replace(original_code, new_code, 1)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
                
            result["validation_steps"].append(("Aplicacion", "APROBADO"))
            result["success"] = True
        except Exception as e:
            if backup_path:
                self._rollback(file_path, backup_path)
            result["validation_steps"].append(("Aplicacion", f"RECHAZADO: {str(e)}"))
            result["rollback_performed"] = True
            
        return result

    # CORRECCIÓN 4: Subproceso asíncrono (Reemplaza subprocess.run)
    async def _run_sandbox_test(self, code: str) -> Dict[str, Any]:
        """Ejecuta (no solo parsea) el fragmento nuevo en un subproceso aislado,
        para detectar errores de import, de nombre o de sintaxis en tiempo de
        carga. IMPORTANTE: esto NO reemplaza una revisión humana ni prueba que
        el comportamiento sea correcto — solo descarta que el código explote al
        cargarse. `codigo_original` suele ser un fragmento (función/método), así
        que lo compilamos y ejecutamos como módulo independiente: si define
        funciones o clases, alcanza para detectar errores de sintaxis avanzados,
        de indentación o de referencias a nombres inexistentes en el propio
        fragmento; no llama a la función automáticamente porque no conocemos
        argumentos válidos para probarla seguro."""
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tmp:
                tmp.write("import sys\n")
                tmp.write("codigo = " + repr(code) + "\n")
                tmp.write("try:\n")
                tmp.write("    compilado = compile(codigo, '<propuesta>', 'exec')\n")
                tmp.write("    namespace = {'__name__': '__sandbox__'}\n")
                tmp.write("    exec(compilado, namespace)\n")
                tmp.write("except Exception as e:\n")
                tmp.write("    print(f'SANDBOX_ERROR: {type(e).__name__}: {e}', file=sys.stderr)\n")
                tmp.write("    sys.exit(1)\n")
                tmp.write("print('OK')\n")
                tmp_path = tmp.name

            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                tmp_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5.0)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return {"success": False, "error": "Timeout en el sandbox (5s)"}

            if proc.returncode == 0 and b"OK" in stdout:
                return {"success": True}
            else:
                error_msg = stderr.decode('utf-8', errors='ignore')[:200]
                return {"success": False, "error": error_msg}
        except Exception as e:
            return {"success": False, "error": str(e)[:200]}
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    def _create_backup(self, file_path: str) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup_name = Path(file_path).stem + f"_{timestamp}.py"
        backup_path = BACKUP_DIR / backup_name
        shutil.copy2(file_path, backup_path)
        logger.info(f"Backup creado: {str(backup_path)}")
        return backup_path

    def _rollback(self, file_path: str, backup_path: Path):
        try:
            shutil.copy2(backup_path, file_path)
            logger.warning(f"Rollback ejecutado para {file_path}")
        except Exception as e:
            logger.error(f"Error en rollback: {str(e)}")

    def _notify_improvement(self, result: Dict[str, Any]):
        print("\n" + "=" * 60)
        print("🚀 MATEO HA APLICADO UNA AUTO-MEJORA")
        print("=" * 60)
        print(f"📁 Archivo: {result['file']}")
        print(f"📝 Descripcion: {result['description']}")
        steps_text = ", ".join([f"{step[0]}: {step[1]}" for step in result['validation_steps']])
        print(f"✅ Validaciones: {steps_text}")
        if result.get("backup_path"):
            print(f"💾 Backup en: {result['backup_path']}")
        print("=" * 60 + "\n")

    def _log_to_obsidian(self, result: Dict[str, Any]):
        try:
            try:
                from tools.obsidian_writer import save_knowledge_to_obsidian
            except ImportError:
                from backend.tools.obsidian_writer import save_knowledge_to_obsidian

            
            validation_lines = [f"- **{step[0]}**: {step[1]}" for step in result['validation_steps']]
            validation_text = "\n".join(validation_lines)
            status_text = "Exito" if result['success'] else "Fallo"
            date_text = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            content_lines = [
                "## Descripcion",
                str(result['description']),
                "",
                "## Archivo Modificado",
                f"`{result['file']}`",
                "",
                "## Validaciones",
                validation_text,
                "",
                "## Backup",
                f"`{result.get('backup_path', 'N/A')}`",
                "",
                "## Estado",
                status_text,
                "",
                "---",
                f"*Auto-mejora aplicada por Mateo el {date_text}*"
            ]
            content = "\n".join(content_lines)
            topic = "AutoMejora_" + datetime.now().strftime('%Y%m%d_%H%M%S')
            
            save_knowledge_to_obsidian(
                topic=topic,
                synthesized_content=content,
                sources=["Motor de Auto-mejora de Mateo"]
            )
        except Exception as e:
            logger.error(f"Error registrando mejora en Obsidian: {str(e)}")

# ==========================================
# SINGLETON
# ==========================================
self_improvement_engine = None

# CORRECCIÓN 2: Indentación corregida para el Singleton
def get_self_improvement_engine(language_model):
    global self_improvement_engine
    if self_improvement_engine is None:
        self_improvement_engine = SelfImprovementEngine(language_model)
    return self_improvement_engine