import streamlit as st
import requests
import json
import re
import base64
import time
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any

# Configuración de la página
st.set_page_config(
    page_title="Conversor de Ejercicios a Shortcodes",
    page_icon="📚",
    layout="wide"
)

# Configuración de EdiBlocks
EDIBLOCKS_BASE_URL = "https://ediblocks-test.edinumen.es"

# Tipologías definidas directamente como objeto Python para evitar problemas con JSON
TIPOLOGIAS = [
    {
        "name": "drag-words",
        "label": "Arrastrar palabras",
        "sample": "[drag-words words=\"gato|perro|elefante|mono|rata\" sentence=\"El [] es más grande que el [], pero el [] es el más [] pequeño.\" markers=\"elefante|perro|gato|mono\"][/drag-words]"
    },
    {
        "name": "multiple-choice",
        "label": "Selección múltiple",
        "sample": "[multiple-choice options=\"Lechuga|Manzana|Zanahoria|Plátano|Pera\" correctOptions=\"Manzana|Plátano|Pera\"][/multiple-choice]"
    },
    {
        "name": "single-choice",
        "label": "Selección única",
        "sample": "[single-choice options=\"Rojo|Verde|Azul|Amarillo\" correctOption=\"Azul\"][/single-choice]"
    },
    {
        "name": "abnone-choice",
        "label": "Elige A o B o Ninguno",
        "sample": "[abnone-choice titlea=\"Lorem\" texta=\"Lorem ipsum Lorem ipsum\" titleb=\"Ipsum\" textb=\"Lorem\" questions=\"a*¿Lorem ipsum?|b*¿Ipsum lorem?|c*¿Dolor sit?\"][/abnone-choice]"
    },
    {
        "name": "statement-option-match",
        "label": "Empareja opciones",
        "sample": "[statement-option-match statements=\"a*Lorem ipsum|b*Ipsum lorem|c*Dolor sit\" options=\"a*Persona 1*Lorem ipsum Lorem ipsum|b*Persona 2*Lorem ipsum Lorem ipsum|c*Persona 3*Lorem ipsum Lorem ipsum\"][/statement-option-match]"
    },
    {
        "name": "fill-in-the-blanks",
        "label": "Texto con espacios para rellenar (texto libre)",
        "sample": "[fill-in-the-blanks text=\"La capital de [text|España] es Madrid.\"][/fill-in-the-blanks]"
    },
    {
        "name": "fill-in-the-blanks",
        "label": "Textos con espacios para seleccionar entre opciones (menú desplegable)",
        "sample": "[fill-in-the-blanks text=\"El animal más rápido del mundo es el [select|leopardo#*guepardo#león#tigre].\"][/fill-in-the-blanks]"
    },
    {
        "name": "writing",
        "label": "Producción de texto",
        "sample": "[writing maxtime=\"0\"][/writing]"
    },
    {
        "name": "oral-expression",
        "label": "Expresión Oral",
        "sample": "[oral-expression autoplay=\"false\" maxtime=\"0\" maxplays=\"0\"][/oral-expression]"
    },
    {
        "name": "file-upload",
        "label": "Subir archivo",
        "sample": "[file-upload extensions=\"pdf|doc|docx\"][/file-upload]"
    },
    {
        "name": "image-choice",
        "label": "Selección de imagen",
        "sample": "[image-choice images=\"https://url-a-imagen-de-gato.com/gato.jpg*texto alternativo gato|https://url-a-imagen-de-perro.com/perro.jpg*texto alternativo perro\" correctOptionIndex=\"1\"][/image-choice]"
    },
    {
        "name": "multi-question",
        "label": "Multipregunta",
        "sample": "[multi-question questions=\"\"][/multi-question]"
    }
]

# Inicializar variables de sesión si no existen
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []
if 'shortcode_versions' not in st.session_state:
    st.session_state.shortcode_versions = {}
if 'current_image_url' not in st.session_state:
    st.session_state.current_image_url = None
if 'current_text_content' not in st.session_state:
    st.session_state.current_text_content = ""
if 'temp_text_content' not in st.session_state:
    st.session_state.temp_text_content = ""
if 'api_key_saved' not in st.session_state:
    st.session_state.api_key_saved = ""
if 'session_id' not in st.session_state:
    st.session_state.session_id = str(int(time.time()))
if 'prompt_personalizado' not in st.session_state:
    st.session_state.prompt_personalizado = ""
if 'input_type' not in st.session_state:
    st.session_state.input_type = "image_url"
if 'resultado' not in st.session_state:
    st.session_state.resultado = None

# ============================================================================
# NUEVAS VARIABLES DE SESIÓN PARA EDIBLOCKS (IMPLEMENTACIÓN BÁSICA)
# ============================================================================
if 'ediblocks_config' not in st.session_state:
    st.session_state.ediblocks_config = {
        'base_url': EDIBLOCKS_BASE_URL,
        'api_key': '',
        'organization_id': 1
    }
if 'available_tags' not in st.session_state:
    st.session_state.available_tags = []
if 'publication_history' not in st.session_state:
    st.session_state.publication_history = []
# ============================================================================
# CLASE EDIBLOCKS API (IMPLEMENTACIÓN BÁSICA)
# ============================================================================

class EdiBlocksAPI:
    """Clase básica para manejar las operaciones con la API de EdiBlocks"""
    
    def __init__(self, base_url: str, api_key: str = None):
        self.base_url = base_url
        self.api_key = api_key
    
    def get_headers(self, force_auth: bool = False) -> Dict[str, str]:
        """Obtener headers para las peticiones HTTP"""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # Para operaciones de escritura, siempre intentar autenticación si hay API key
        if force_auth or (self.api_key and self.api_key.strip()):
            api_key_clean = self.api_key.strip()
            headers['Authorization'] = f'Bearer {api_key_clean}'
        
        return headers
    
    def request(self, endpoint: str, method: str = 'GET', data: Dict = None) -> Optional[Dict]:
        """Realizar petición HTTP a la API"""
        url = f"{self.base_url}{endpoint}"
        
        # Para operaciones de escritura, forzar autenticación
        force_auth = method in ['POST', 'PUT', 'DELETE']
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=self.get_headers(), timeout=30)
            elif method == 'POST':
                response = requests.post(url, headers=self.get_headers(force_auth=True), 
                                       json=data, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, headers=self.get_headers(force_auth=True), 
                                      json=data, timeout=30)
            else:
                raise ValueError(f"Método HTTP no soportado: {method}")
            
            if response.status_code in [200, 201]:
                return response.json()
            else:
                st.error(f"❌ **Error en API EdiBlocks:** {response.status_code}")
                try:
                    error_detail = response.json()
                    st.error(f"📄 **Detalle:** {error_detail}")
                except:
                    st.error(f"📄 **Respuesta:** {response.text}")
                
                # Mensajes específicos para códigos de error comunes
                if response.status_code == 401:
                    st.warning("🔐 **Autenticación requerida**: Esta operación necesita una API Key válida.")
                elif response.status_code == 403:
                    st.warning("🚫 **Sin permisos**: Tu API Key no tiene permisos para esta operación.")
                elif response.status_code == 404:
                    st.warning("🔍 **No encontrado**: El endpoint o recurso no existe.")
                
                return None
                
        except requests.exceptions.Timeout:
            st.error("⏱️ **Timeout:** La API tardó demasiado en responder")
            return None
        except requests.exceptions.RequestException as e:
            st.error(f"🌐 **Error de conexión:** {str(e)}")
            return None
        except Exception as e:
            st.error(f"💥 **Error inesperado:** {str(e)}")
            return None

# ============================================================================
# FUNCIONES AUXILIARES PARA EDIBLOCKS
# ============================================================================

def format_multilang_text(text: str, lang: str = 'es') -> str:
    """Formatear texto en formato multiidioma JSON"""
    return json.dumps({
        'es': text if lang == 'es' else '',
        'en': text if lang == 'en' else '',
        'zh': text if lang == 'zh' else ''
    })

def generate_internal_name(name: str) -> str:
    """Generar nombre interno válido"""
    return re.sub(r'[^a-z0-9-]', '', name.lower().replace(' ', '-'))[:50]

def detect_question_type(shortcode: str) -> str:
    """Detectar tipo de pregunta desde shortcode"""
    
    if not shortcode or not shortcode.strip():
        return 'text'
    
    detected_type = 'text'  # valor por defecto
    
    if '[multiple-choice' in shortcode:
        detected_type = 'multiple-choice'
    elif '[fill-in-the-blanks' in shortcode:
        detected_type = 'fill-in-the-blanks'
    elif '[single-choice' in shortcode:
        detected_type = 'single-choice'
    elif '[drag-words' in shortcode:
        detected_type = 'drag-words'
    elif '[statement-option-match' in shortcode:
        detected_type = 'statement-option-match'
    elif '[writing' in shortcode:
        detected_type = 'writing'
    elif '[oral-expression' in shortcode:
        detected_type = 'oral-expression'
    elif '[file-upload' in shortcode:
        detected_type = 'file-upload'
    elif '[image-choice' in shortcode:
        detected_type = 'image-choice'
    elif '[abnone-choice' in shortcode:
        detected_type = 'abnone-choice'
    elif '[multi-question' in shortcode:
        detected_type = 'multi-question'
    
    return detected_type

def test_connection_simple(base_url: str, api_key: str = None) -> bool:
    """Test de conexión simple basado en los archivos PHP"""
    
    # Test 1: GET tags
    try:
        headers = {'Accept': 'application/json'}
        response = requests.get(f"{base_url}/api/tags", headers=headers, timeout=10)
        
        if response.status_code == 200:
            try:
                data = response.json()
                return True
            except:
                pass
        elif response.status_code == 401:
            pass
        
    except Exception as e:
        return False
    
    # Test 2: GET questiongroups
    try:
        headers = {'Accept': 'application/json'}
        response = requests.get(f"{base_url}/api/questiongroups?limit=1", 
                              headers=headers, timeout=10)
        
        if response.status_code == 200:
            try:
                data = response.json()
                return True
            except:
                pass
        
    except Exception as e:
        pass
    
    return False

def get_available_tags(api: EdiBlocksAPI) -> List[Dict]:
    """Obtener lista de tags disponibles desde EdiBlocks API"""
    
    def extract_all_tags_recursively(tags_list):
        """Extraer todos los tags recursivamente, incluyendo children"""
        all_tags = []
        
        for tag in tags_list:
            if isinstance(tag, dict) and 'id' in tag and 'name' in tag:
                # Añadir el tag actual (sin el children para evitar problemas)
                clean_tag = {
                    'id': tag['id'],
                    'name': tag['name'],
                    'parent_id': tag.get('parent_id')
                }
                all_tags.append(clean_tag)
                
                # Si tiene children, procesarlos recursivamente
                if 'children' in tag and isinstance(tag['children'], list):
                    children_tags = extract_all_tags_recursively(tag['children'])
                    all_tags.extend(children_tags)
        
        return all_tags
    
    try:
        # Método simple: GET directo a /api/tags
        tags_result = api.request('/api/tags')
        
        if not tags_result:
            # Si no hay respuesta, devolver fallback
            return [
                {"id": 2, "name": "Comprensión Lectora y Uso de la Lengua", "parent_id": 1},
                {"id": 70, "name": "Intermedio Medio", "parent_id": 15}, 
                {"id": 111, "name": "Educativo", "parent_id": 108},
                {"id": 15, "name": "Nivel", "parent_id": None},
                {"id": 108, "name": "Contexto", "parent_id": None},
                {"id": 1, "name": "Habilidad", "parent_id": None}
            ]
        
        # Si es una lista directa, extraer todos los tags recursivamente
        if isinstance(tags_result, list):
            all_tags = extract_all_tags_recursively(tags_result)
            if all_tags:
                return all_tags
        
        # Si es un diccionario, buscar en keys comunes
        if isinstance(tags_result, dict):
            # Orden de prioridad para buscar tags
            search_keys = ['data', 'tags', 'results', 'items', 'content']
            
            for key in search_keys:
                if key in tags_result and isinstance(tags_result[key], list):
                    all_tags = extract_all_tags_recursively(tags_result[key])
                    if all_tags:
                        return all_tags
            
            # Si no se encontró en keys conocidas, buscar en todas
            for key, value in tags_result.items():
                if isinstance(value, list) and len(value) > 0:
                    all_tags = extract_all_tags_recursively(value)
                    if all_tags:
                        return all_tags
        
        # Si llegamos aquí, no se encontraron tags válidos
        return [
            {"id": 2, "name": "Comprensión Lectora y Uso de la Lengua", "parent_id": 1},
            {"id": 70, "name": "Intermedio Medio", "parent_id": 15}, 
            {"id": 111, "name": "Educativo", "parent_id": 108},
            {"id": 15, "name": "Nivel", "parent_id": None},
            {"id": 108, "name": "Contexto", "parent_id": None},
            {"id": 1, "name": "Habilidad", "parent_id": None}
        ]
        
    except Exception as e:
        return [
            {"id": 2, "name": "Comprensión Lectora y Uso de la Lengua", "parent_id": 1},
            {"id": 70, "name": "Intermedio Medio", "parent_id": 15}, 
            {"id": 111, "name": "Educativo", "parent_id": 108},
            {"id": 15, "name": "Nivel", "parent_id": None},
            {"id": 108, "name": "Contexto", "parent_id": None},
            {"id": 1, "name": "Habilidad", "parent_id": None}
        ]
# ============================================================================
# FUNCIONES DE PUBLICACIÓN EN EDIBLOCKS
# ============================================================================

def create_question_group(api: EdiBlocksAPI, task_data: Dict) -> Optional[Dict]:
    """Crear un nuevo grupo de preguntas en EdiBlocks"""
    payload = {
        "id": None,
        "name": format_multilang_text(task_data['name']),
        "questions": [],
        "type": task_data.get('type', 'sequence'),
        "status": "active",
        "instructions": format_multilang_text(task_data.get('instructions', '')),
        "projects": [],
        "item_grades": "",
        "internal_name": generate_internal_name(task_data['name']),
        "tags": task_data.get('tags', [])
    }
    
    return api.request('/api/questiongroups', 'POST', payload)

def add_questions_to_group(api: EdiBlocksAPI, group_id: int, questions: List[Dict]) -> Optional[Dict]:
    """Añadir preguntas a un grupo existente"""
    
    # Primero obtener el grupo actual
    current_group_response = api.request(f'/api/questiongroups/{group_id}')
    if not current_group_response:
        return None
    
    # EXTRAER EL OBJETO QUESTIONGROUP SI ESTÁ ANIDADO
    if 'questiongroup' in current_group_response:
        current_group = current_group_response['questiongroup']
    else:
        current_group = current_group_response
    
    # Formatear las preguntas nuevas
    formatted_questions = []
    for i, q in enumerate(questions):
        formatted_question = {
            "id": None,
            "name": q.get('name', f'Pregunta {i+1}'),
            "internal_name": q.get('internal_name', f'pregunta-{i+1}'),
            "statement": q.get('statement', ''),
            "type": q.get('type', 'text'),
            "status": "active",
            "shortcode": q.get('shortcode', ''),
            "tags": q.get('tags', []),
            "questions": q.get('subQuestions', [])
        }
        formatted_questions.append(formatted_question)
    
    # COMBINAR con preguntas existentes
    existing_questions = current_group.get('questions', [])
    all_questions = existing_questions + formatted_questions
    
    # CREAR PAYLOAD LIMPIO
    clean_payload = {
        "id": current_group.get('id'),
        "name": current_group.get('name'),
        "internal_name": current_group.get('internal_name'),
        "organization_id": current_group.get('organization_id'),
        "type": current_group.get('type', 'sequence'),
        "select_time": current_group.get('select_time', 0),
        "instructions": current_group.get('instructions'),
        "status": current_group.get('status', 'active'),
        "difficulty": current_group.get('difficulty'),
        "item_grades": current_group.get('item_grades'),
        "not_graded": current_group.get('not_graded', 0),
        "time_limit": current_group.get('time_limit'),
        "audio_num_loops": current_group.get('audio_num_loops', 0),
        "audio_between_time": current_group.get('audio_between_time', 0),
        "audio_end_time": current_group.get('audio_end_time', 0),
        "audio_start_time": current_group.get('audio_start_time', 0),
        "prepare_time": current_group.get('prepare_time'),
        "elementor_state": current_group.get('elementor_state'),
        "questions": all_questions,
        "tags": current_group.get('tags', [])
    }
    
    # Eliminar campos None para limpiar el payload
    clean_payload = {k: v for k, v in clean_payload.items() if v is not None}
    
    # Realizar el UPDATE con payload limpio
    result = api.request(f'/api/questiongroups/{group_id}', 'PUT', clean_payload)
    
    return result

def publish_to_ediblocks(task_name: str, instructions: str, resultado: Dict, 
                        selected_tags: List[Dict], api_key: str) -> Dict:
    """Función principal para publicar en EdiBlocks (implementación básica)"""
    try:
        # Crear instancia de API
        api = EdiBlocksAPI(EDIBLOCKS_BASE_URL, api_key)
        
        # Preparar datos de la tarea
        task_data = {
            'name': task_name,
            'instructions': instructions,
            'type': 'sequence',
            'tags': selected_tags
        }
        
        # Crear el grupo de preguntas
        group_result = create_question_group(api, task_data)
        if not group_result:
            return {'success': False, 'error': 'No se pudo crear el grupo de preguntas'}
        
        group_id = group_result['id']
        
        # Preparar las preguntas desde el resultado
        questions = []
        for actividad in resultado.get('actividades', []):
            # Obtener la versión más reciente del shortcode
            shortcode = actividad.get('shortcode', '')
            actividad_key = f"actividad_{actividad.get('numero')}"
            
            if (actividad_key in st.session_state.shortcode_versions and 
                st.session_state.shortcode_versions[actividad_key]):
                versiones = st.session_state.shortcode_versions[actividad_key]
                if versiones:
                    shortcode = versiones[-1]["shortcode"]
            
            questions.append({
                'name': f"Actividad {actividad.get('numero')}",
                'statement': actividad.get('texto_original', ''),
                'type': detect_question_type(shortcode),
                'shortcode': shortcode,
                'tags': []
            })
        
        # Añadir preguntas al grupo
        if questions:
            final_result = add_questions_to_group(api, group_id, questions)
            if final_result:
                return {
                    'success': True,
                    'group_id': group_id,
                    'group': final_result,
                    'questions_count': len(questions)
                }
            else:
                return {'success': False, 'error': 'No se pudieron añadir las preguntas al grupo'}
        else:
            return {'success': False, 'error': 'No hay preguntas para publicar'}
            
    except Exception as e:
        return {'success': False, 'error': f'Error inesperado: {str(e)}'}

# ============================================================================
# FUNCIONES DE INTERFAZ BÁSICA PARA EDIBLOCKS
# ============================================================================

def mostrar_selector_tags_basico() -> List[str]:
    """Selector básico de tags sin funcionalidades avanzadas"""
    
    if not st.session_state.available_tags:
        st.warning("No hay tags cargados. Usa el botón 'Cargar tags' primero.")
        return []
    
    # Crear opciones simples
    tag_options = []
    for tag in st.session_state.available_tags:
        parent_info = ""
        if tag.get('parent_id'):
            # Buscar el nombre del padre
            parent_tag = next(
                (t for t in st.session_state.available_tags if t['id'] == tag['parent_id']), 
                None
            )
            if parent_tag:
                parent_info = f" (de: {parent_tag['name']})"
        
        option_text = f"{tag['name']} (ID: {tag['id']}){parent_info}"
        tag_options.append(option_text)
    
    # Selector múltiple simple
    selected_options = st.multiselect(
        "Selecciona las etiquetas:",
        options=tag_options,
        help="Selecciona las etiquetas apropiadas para esta tarea"
    )
    
    return selected_options

def mostrar_configuracion_ediblocks_basica():
    """Configuración básica de EdiBlocks"""
    
    st.subheader("⚙️ Configuración de EdiBlocks")
    
    # URL de la API
    new_base_url = st.text_input(
        "URL base de EdiBlocks",
        value=st.session_state.ediblocks_config['base_url'],
        help="URL base de la API de EdiBlocks"
    )
    
    # API Key
    new_api_key = st.text_input(
        "API Key de EdiBlocks",
        value=st.session_state.ediblocks_config['api_key'],
        type="password",
        help="API Key para autenticación (opcional para solo lectura)"
    )
    
    # Organization ID
    new_org_id = st.number_input(
        "ID de Organización",
        value=st.session_state.ediblocks_config['organization_id'],
        min_value=1,
        help="ID de tu organización en EdiBlocks"
    )
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💾 Guardar configuración"):
            st.session_state.ediblocks_config.update({
                'base_url': new_base_url,
                'api_key': new_api_key,
                'organization_id': new_org_id
            })
            st.success("✅ Configuración guardada")
    
    with col2:
        if st.button("🔗 Probar conexión"):
            with st.spinner("Probando conexión..."):
                success = test_connection_simple(new_base_url, new_api_key)
                if success:
                    st.success("✅ ¡Conexión exitosa!")
                else:
                    st.error("❌ No se pudo conectar")
    
    with col3:
        if st.button("🏷️ Cargar tags"):
            api = EdiBlocksAPI(new_base_url, new_api_key)
            with st.spinner("Cargando tags..."):
                st.session_state.available_tags = get_available_tags(api)
                if st.session_state.available_tags:
                    st.success(f"✅ {len(st.session_state.available_tags)} tags cargados")
                else:
                    st.error("❌ No se pudieron cargar los tags")

def mostrar_seccion_publicacion_basica():
    """Sección básica de publicación en EdiBlocks"""
    
    if not st.session_state.resultado:
        st.info("ℹ️ Primero procesa una imagen o texto para poder publicar en EdiBlocks.")
        return
    
    st.subheader("📤 Publicar en EdiBlocks")
    
    # Mostrar configuración
    mostrar_configuracion_ediblocks_basica()
    
    st.markdown("---")
    
    # Formulario de publicación
    with st.form("publish_form"):
        st.subheader("Configurar publicación")
        
        # Nombre de la tarea
        task_name = st.text_input(
            "Nombre de la tarea",
            value="Tarea generada desde Streamlit",
            help="Nombre que aparecerá en EdiBlocks"
        )
        
        # Instrucciones
        task_instructions = st.text_area(
            "Instrucciones de la tarea",
            value=st.session_state.resultado.get('enunciado', ''),
            help="Instrucciones generales para los estudiantes"
        )
        
        # Selección de tags
        st.subheader("🏷️ Etiquetas")
        selected_tag_names = mostrar_selector_tags_basico()
        
        # Botón de publicación
        submitted = st.form_submit_button("🚀 Publicar en EdiBlocks", type="primary")
        
        if submitted:
            if not task_name.strip():
                st.error("❌ El nombre de la tarea es obligatorio")
            elif not st.session_state.ediblocks_config['api_key']:
                st.error("❌ Se requiere una API Key para publicar")
            else:
                # Preparar tags seleccionados
                selected_tags = []
                for tag_option in selected_tag_names:
                    # Extraer ID del tag
                    match = re.search(r'ID: (\d+)', tag_option)
                    if match:
                        tag_id = int(match.group(1))
                        # Buscar el tag completo
                        for tag in st.session_state.available_tags:
                            if tag['id'] == tag_id:
                                selected_tags.append(tag)
                                break
                
                # Publicar
                with st.spinner("Publicando en EdiBlocks..."):
                    result = publish_to_ediblocks(
                        task_name,
                        task_instructions,
                        st.session_state.resultado,
                        selected_tags,
                        st.session_state.ediblocks_config['api_key']
                    )
                    
                    if result['success']:
                        st.success(f"🎉 ¡Tarea publicada exitosamente!")
                        st.info(f"🆔 ID del grupo creado: {result['group_id']}")
                        st.info(f"📝 Preguntas publicadas: {result['questions_count']}")
                        
                        # Agregar al historial
                        st.session_state.publication_history.append({
                            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'task_name': task_name,
                            'group_id': result['group_id'],
                            'questions_count': result['questions_count'],
                            'tags': [tag['name'] for tag in selected_tags]
                        })
                        
                        # Agregar al historial general
                        agregar_a_historial(
                            "Tarea publicada en EdiBlocks",
                            f"Nombre: {task_name}\nID: {result['group_id']}\nPreguntas: {result['questions_count']}"
                        )
                        
                    else:
                        st.error(f"❌ Error al publicar: {result['error']}")
    
    # Mostrar historial si existe
    if st.session_state.publication_history:
        st.markdown("---")
        st.subheader("📋 Historial de publicaciones")
        
        for pub in reversed(st.session_state.publication_history):
            with st.expander(f"📅 {pub['timestamp']} - {pub['task_name']}"):
                st.write(f"**🆔 ID del grupo:** {pub['group_id']}")
                st.write(f"**📝 Preguntas publicadas:** {pub['questions_count']}")
                if pub['tags']:
                    st.write(f"**🏷️ Tags:** {', '.join(pub['tags'])}")
                
                # Enlace directo
                ediblocks_url = f"{st.session_state.ediblocks_config['base_url']}/questiongroups/{pub['group_id']}"
                st.markdown(f"[🔗 Ver en EdiBlocks]({ediblocks_url})")
# ============================================================================
# FUNCIONES ORIGINALES DE IMGTOSH (CONSERVADAS)
# ============================================================================

# Función para analizar texto con prompt adaptado
def analizar_texto_con_prompt(api_key, texto, prompt_personalizado=""):
    url = "https://api.anthropic.com/v1/messages"
    
    # Usar exactamente los encabezados que funcionaron
    headers = {
        "x-api-key": api_key.strip(),  # Eliminar espacios al inicio/final
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    # Prompt base detallado para Claude
    instrucciones_base = """
# Tarea: Extraer ejercicios educativos y convertirlos en shortcodes

Analiza detalladamente este texto de ejercicios educativos y extrae:

1. El enunciado principal que explica el objetivo general de los ejercicios
2. Cada actividad o pregunta individual presente en el texto

"""

    # Combinar prompt base con el prompt personalizado si existe
    if prompt_personalizado and prompt_personalizado.strip():
        instrucciones_completas = instrucciones_base + "\n\n## Instrucciones personalizadas adicionales\n\n" + prompt_personalizado
    else:
        instrucciones_completas = instrucciones_base
    
    # Añadir el texto de instrucciones sobre shortcodes y formato
    instrucciones_completas += """
## Tipos de shortcodes disponibles

Debes convertir cada actividad al formato de shortcode más apropiado según los siguientes tipos:

### 1. drag-words
- Usar para: Ejercicios donde hay que completar frases arrastrando palabras a huecos
- Formato: [drag-words words="palabra1|palabra2|palabra3" sentence="Texto con [] para rellenar" markers="palabra_correcta1|palabra_correcta2"][/drag-words]
- Ejemplo: [drag-words words="gato|perro|elefante|mono|rata" sentence="El [] es más grande que el [], pero el [] es el más [] pequeño." markers="elefante|perro|gato|mono"][/drag-words]

### 2. multiple-choice
- Usar para: Preguntas con MÚLTIPLES respuestas correctas posibles
- Formato: [multiple-choice options="opción1|opción2|opción3" correctOptions="opciónCorrecta1|opciónCorrecta2"][/multiple-choice]
- Ejemplo: [multiple-choice options="Lechuga|Manzana|Zanahoria|Plátano|Pera" correctOptions="Manzana|Plátano|Pera"][/multiple-choice]

### 3. single-choice
- Usar para: Preguntas con UNA SOLA respuesta correcta
- Formato: [single-choice options="opción1|opción2|opción3" correctOption="opciónCorrecta"][/single-choice]
- Ejemplo: [single-choice options="Rojo|Verde|Azul|Amarillo" correctOption="Azul"][/single-choice]

### 4. fill-in-the-blanks
- Usar para: Textos con espacios para rellenar (texto libre)
- Formato: [fill-in-the-blanks text="Texto con [text|respuesta] para completar." casesensitive="false" specialcharssensitive="false"][/fill-in-the-blanks]
- Ejemplo: [fill-in-the-blanks text="La capital de [text|España] es Madrid." casesensitive="false" specialcharssensitive="false"][/fill-in-the-blanks]
- MUY IMPORTANTE: Si hay varias respuestas válidas se deben separar con el símbolo almohadilla (#).

### 5. fill-in-the-blanks
- Usar para: Elegir entre dos opciones
- Formato: [fill-in-the-blanks text="Texto: [radio|Verdadero#*Falso]" casesensitive="false" specialcharssensitive="false"][/fill-in-the-blanks]
- Ejemplo: [fill-in-the-blanks text="La leche es: [radio|*Blanca#Negra]" casesensitive="false" specialcharssensitive="false"][/fill-in-the-blanks]
- MUY IMPORTANTE: El asterisco (*) indica la opción correcta. El símbolo | separa las opciones.

### 6. fill-in-the-blanks
- Usar para: Textos con espacios para seleccionar entre opciones (menú desplegable)
- Formato: [fill-in-the-blanks text="Texto con [select|Incorrecta1#*Correcta#Incorrecta2] para seleccionar." casesensitive="false" specialcharssensitive="false"][/fill-in-the-blanks]
- Ejemplo: [fill-in-the-blanks text="El animal más rápido es el [select|leopardo#*guepardo#león#tigre]." casesensitive="false" specialcharssensitive="false"][/fill-in-the-blanks]
- MUY IMPORTANTE: El asterisco (*) indica la opción correcta. Debe haber solo una opción correcta por cada hueco. El símbolo # separa las opciones. SIEMPRE hay que poner la oción correcta.

### 7. fill-in-the-blanks
- Usar para: Introducir letras para completar una única palabra
- Formato: [fill-in-the-blanks text="Texto [short-text|letra1][short-text|letra2][short-text|letra3]" casesensitive="false" specialcharssensitive="false"][/fill-in-the-blanks]
- Ejemplo: [fill-in-the-blanks text="El caballo [text|blanco] de Santiago es de [short-text|c][short-text|o][short-text|l][short-text|o][short-text|r] blanco." casesensitive="false" specialcharssensitive="false"][/fill-in-the-blanks]

### 8. statement-option-match
- Usar para: Emparejar conceptos o frases con sus correspondientes opciones
- Formato: [statement-option-match statements="a*afirmación1|b*afirmación2" options="b*respuesta correcta para la afirmación2*descripción1 (puede no existir, si no existe no poner nada)|a*respuesta correcta para la afirmación2*descripción2 (puede no existir, si no existe no poner nada)"][/statement-option-match]
- Ejemplo: [statement-option-match statements="a*La leche es|b*El cielo es|c*La hierba es" options="b*azul*El  mismo color que el mar|b*verde*|a*blanca*"][/statement-option-match]
- MUY IMPORTANTE: Poner la misma etiqueta (números o letras) tanto en los statments como en las options. En las options las etiquetas indican la respuesta correcta para la opción. En las options, si no hay descripción mantener los dos asteríscos.

### 9. writing
- Usar para: Producción libre de texto escrito
- Formato: [writing maxtime="0"][/writing]
- Ejemplo: [writing maxtime="0"][/writing]

### 10. oral-expression
- Usar para: Producción oral de respuestas
- Formato: [oral-expression autoplay="false" maxtime="0" maxplays="0"][/oral-expression]
- Ejemplo: [oral-expression autoplay="false" maxtime="0" maxplays="0"][/oral-expression]

### 11. file-upload
- Usar para: Subir archivos como respuesta
- Formato: [file-upload extensions="pdf|doc|docx"][/file-upload]
- Ejemplo: [file-upload extensions="pdf|doc|docx"][/file-upload]

### 12. image-choice
- Usar para: Preguntas con opciones de selección de imágenes
- Formato: [image-choice images="url_imagen1*texto_alternativo1|url_imagen2*texto_alternativo2" correctOptionIndex="índice_opción_correcta"][/image-choice]
- Ejemplo: [image-choice images="https://url-a-imagen-de-gato.com/gato.jpg*texto alternativo gato|https://url-a-imagen-de-perro.com/perro.jpg*texto alternativo perro" correctOptionIndex="1"][/image-choice]

### 13. multi-question
- Usar para: Agrupar varias preguntas en un solo bloque
- Formato: [multi-question questions=""][/multi-question]
- Ejemplo: [multi-question questions=""][/multi-question]

### 14. abnone-choice
- Usar para: Preguntas con opciones A, B, Ninguna de las anteriores
- Formato: [abnone-choice titlea="Título A" texta="Texto A" titleb="Título B" textb="Texto B" questions="a*Pregunta A|b*Pregunta B|c*Pregunta C"][/abnone-choice]
- Ejemplo: [abnone-choice titlea="Lorem" texta="Lorem ipsum Lorem ipsum" titleb="Ipsum" textb="Lorem" questions="a*¿Lorem ipsum?|b*¿Ipsum lorem?|c*¿Dolor sit?"]

## Instrucciones IMPORTANTES

1. Analiza cuidadosamente el tipo de ejercicio antes de elegir el shortcode
2. Usa EXACTAMENTE la misma estructura y símbolos separadores (|, *, #, etc.) que se muestran en los ejemplos
3. Respeta el formato exacto de las comillas y corchetes
4. Si un ejercicio no encaja exactamente en un tipo, elige el más cercano y adáptalo
5. Si un ejercicio tiene múltiples partes que requieren diferentes tipos, trátalas como actividades separadas
6. Si un ejercicio tiene múltiples partes intenta que vaya en un ÚNICO shortcode
7. Los shortcodes tipo fill-the-blanks pueden usarse para agrupar en un único shortcode varios apartados distintos. Pueden ser del mismo tipo o de diferente tipo:
   – Ejemplo: [fill-in-the-blanks text="La capital de [text|España] es Madrid. El caballo [text|blanco] de Santiago es de [short-text|c][short-text|o][short-text|l][short-text|o][short-text|r] blanco. El animal más rápido del mundo es el [select|leopardo#*guepardo#león#tigre]. Las afirmaciones anteriores son: [radio|Verdaderas#*Falsas]" casesensitive="false" specialcharssensitive="false"][/fill-in-the-blanks]

## Formato de tu respuesta

Responde usando exactamente este formato:

ENUNCIADO: (escribe aquí el enunciado principal identificado en el texto)

ACTIVIDAD 1:
- Texto original: (transcribe aquí el texto completo de la actividad como aparece en el texto)
- Tipo de shortcode: (nombre exacto del tipo de shortcode más adecuado)
- Shortcode generado: (escribe el shortcode completo siguiendo exactamente el formato del ejemplo)

ACTIVIDAD 2:
- Texto original: (texto de la segunda actividad)
- Tipo de shortcode: (tipo elegido)
- Shortcode generado: (shortcode completo)

Y así sucesivamente para cada actividad identificada.

NO uses formato JSON ni otro formato. Usa SOLO el formato de texto indicado.
"""
    
    # Estructura de la solicitud
    data = {
        "model": "claude-sonnet-4-20250514",  # MANTENER CLAUDE 4
        "max_tokens": 4000,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": instrucciones_completas + "\n\nAquí está el texto a analizar:\n\n" + texto
                    }
                ]
            }
        ]
    }
    
    try:
        # Realizar la solicitud a la API
        response = requests.post(url, headers=headers, json=data, timeout=60)
        
        # Verificar si la respuesta fue exitosa
        if response.status_code == 200:
            try:
                resultado = response.json()
                
                # Extraer la respuesta de texto
                if 'content' in resultado and len(resultado['content']) > 0:
                    respuesta_texto = resultado['content'][0]['text']
                    return respuesta_texto
                else:
                    st.error("La respuesta de Claude no contiene contenido de texto")
                    return None
            except Exception as e:
                st.error(f"Error al procesar la respuesta: {str(e)}")
                return None
        else:
            # Mostrar información sobre el error
            st.error(f"Error en la API: Código {response.status_code}")
            try:
                error_detail = response.json()
            except:
                error_detail = response.text
            st.error(f"Detalle del error: {error_detail}")
            return None
    
    except Exception as e:
        st.error(f"Error al comunicarse con la API: {str(e)}")
        return None

# Función para analizar la imagen con prompt mejorado y personalizado
def analizar_imagen_con_prompt(api_key, image_url, prompt_personalizado=""):
    url = "https://api.anthropic.com/v1/messages"
    
    # Usar exactamente los encabezados que funcionaron
    headers = {
        "x-api-key": api_key.strip(),  # Eliminar espacios al inicio/final
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    # Prompt base detallado para Claude (mismo que para texto pero adaptado para imágenes)
    instrucciones_base = """
# Tarea: Extraer ejercicios educativos y convertirlos en shortcodes

Analiza detalladamente esta imagen de un libro de ejercicios educativos y extrae:

1. El enunciado principal que explica el objetivo general de los ejercicios
2. Cada actividad o pregunta individual presente en la imagen

## Tipos de shortcodes disponibles

[AQUÍ VA EL MISMO CONTENIDO QUE EN LA FUNCIÓN DE TEXTO - omitido por brevedad]

## Formato de tu respuesta

Responde usando exactamente este formato:

ENUNCIADO: (escribe aquí el enunciado principal identificado en la imagen)

ACTIVIDAD 1:
- Texto original: (transcribe aquí el texto completo de la actividad como aparece en la imagen)
- Tipo de shortcode: (nombre exacto del tipo de shortcode más adecuado)
- Shortcode generado: (escribe el shortcode completo siguiendo exactamente el formato del ejemplo)

[resto del formato...]

NO uses formato JSON ni otro formato. Usa SOLO el formato de texto indicado.
"""

    # Combinar prompt base con el prompt personalizado si existe
    if prompt_personalizado and prompt_personalizado.strip():
        instrucciones_completas = instrucciones_base + "\n\n## Instrucciones personalizadas adicionales\n\n" + prompt_personalizado
    else:
        instrucciones_completas = instrucciones_base
    
    # Estructura de la solicitud 
    data = {
        "model": "claude-sonnet-4-20250514",  # MANTENER CLAUDE 4
        "max_tokens": 4000,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "url",
                            "url": image_url
                        }
                    },
                    {
                        "type": "text",
                        "text": instrucciones_completas
                    }
                ]
            }
        ]
    }
    
    try:
        # Realizar la solicitud a la API
        response = requests.post(url, headers=headers, json=data, timeout=60)
        
        # Verificar si la respuesta fue exitosa
        if response.status_code == 200:
            try:
                resultado = response.json()
                
                # Extraer la respuesta de texto
                if 'content' in resultado and len(resultado['content']) > 0:
                    respuesta_texto = resultado['content'][0]['text']
                    return respuesta_texto
                else:
                    st.error("La respuesta de Claude no contiene contenido de texto")
                    return None
            except Exception as e:
                st.error(f"Error al procesar la respuesta: {str(e)}")
                return None
        else:
            # Mostrar información sobre el error
            st.error(f"Error en la API: Código {response.status_code}")
            try:
                error_detail = response.json()
            except:
                error_detail = response.text
            st.error(f"Detalle del error: {error_detail}")
            return None
    
    except Exception as e:
        st.error(f"Error al comunicarse con la API: {str(e)}")
        return None

# Función para refinar un shortcode específico
def refinar_shortcode(api_key, shortcode_original, texto_original, tipo_actividad, instruccion_refinamiento):
    url = "https://api.anthropic.com/v1/messages"
    
    headers = {
        "x-api-key": api_key.strip(),
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    # Prompt para refinar el shortcode
    prompt = f"""
# Tarea: Refinar un shortcode educativo existente

Necesito que refines el siguiente shortcode según las instrucciones proporcionadas:

## Texto original del ejercicio
{texto_original}

## Tipo de shortcode actual
{tipo_actividad}

## Shortcode actual
{shortcode_original}

## Instrucciones de refinamiento
{instruccion_refinamiento}

## Tipos de shortcodes disponibles
El shortcode debe seguir alguno de estos formatos:
- drag-words: [drag-words words="palabra1|palabra2|palabra3" sentence="Texto con [] para rellenar" markers="palabra_correcta1|palabra_correcta2"][/drag-words]
- multiple-choice: [multiple-choice options="opción1|opción2|opción3" correctOptions="opciónCorrecta1|opciónCorrecta2"][/multiple-choice]
- single-choice: [single-choice options="opción1|opción2|opción3" correctOption="opciónCorrecta"][/single-choice]
- fill-in-the-blanks: [fill-in-the-blanks text="Texto con [text|respuesta] para completar." casesensitive="false" specialcharssensitive="false"][/fill-in-the-blanks]
- [otros tipos...]

## Instrucciones importantes
1. Mantén el mismo tipo de shortcode a menos que la instrucción de refinamiento indique explícitamente cambiarlo
2. Sigue EXACTAMENTE la misma estructura y símbolos separadores (|, *, #, etc.)
3. Respeta el formato exacto de las comillas y corchetes
4. Incorpora las mejoras solicitadas en la instrucción de refinamiento

## Formato de tu respuesta
Proporciona tu respuesta usando exactamente este formato:

SHORTCODE REFINADO: (escribe aquí solo el shortcode refinado completo, sin comentarios adicionales)

EXPLICACIÓN: (explica brevemente los cambios realizados)
"""
    
    data = {
        "model": "claude-sonnet-4-20250514",  # MANTENER CLAUDE 4
        "max_tokens": 1000,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)
        
        if response.status_code == 200:
            try:
                resultado = response.json()
                
                if 'content' in resultado and len(resultado['content']) > 0:
                    respuesta_texto = resultado['content'][0]['text']
                    
                    # Extraer el shortcode refinado y la explicación
                    shortcode_match = re.search(r'SHORTCODE REFINADO:\s*(.*?)(?=EXPLICACIÓN:|$)', respuesta_texto, re.DOTALL)
                    explicacion_match = re.search(r'EXPLICACIÓN:\s*(.*?)$', respuesta_texto, re.DOTALL)
                    
                    shortcode_refinado = shortcode_match.group(1).strip() if shortcode_match else None
                    explicacion = explicacion_match.group(1).strip() if explicacion_match else None
                    
                    return {
                        "shortcode": shortcode_refinado,
                        "explicacion": explicacion
                    }
                else:
                    st.error("La respuesta de Claude no contiene contenido de texto")
                    return None
            except Exception as e:
                st.error(f"Error al procesar la respuesta: {str(e)}")
                return None
        else:
            st.error(f"Error en la API: Código {response.status_code}")
            return None
    
    except Exception as e:
        st.error(f"Error al comunicarse con la API: {str(e)}")
        return None
# Función para extraer información de la respuesta de texto
def extraer_informacion_texto(texto_completo):
    resultado = {}
    
    # Extraer el enunciado - más robusto ahora
    match_enunciado = re.search(r'ENUNCIADO:[\s\r\n]*(.*?)(?=ACTIVIDAD|\Z)', texto_completo, re.DOTALL | re.IGNORECASE)
    if match_enunciado:
        resultado["enunciado"] = match_enunciado.group(1).strip()
    else:
        # Buscar alternativas como "Enunciado principal:" o similar
        alt_matches = re.search(r'(?:ENUNCIADO|ENUNCIADO PRINCIPAL|INSTRUCCIÓN):[\s\r\n]*(.*?)(?=ACTIVIDAD|\Z)', texto_completo, re.DOTALL | re.IGNORECASE)
        if alt_matches:
            resultado["enunciado"] = alt_matches.group(1).strip()
        else:
            resultado["enunciado"] = "No se encontró un enunciado claro"
    
    # Extraer actividades - patrón más robusto
    actividades = []
    
    # Patrón mejorado para capturar más variaciones en el formato
    pattern = r'ACTIVIDAD\s+(\d+):\s*[\r\n]*(?:-\s*)?Texto original:[\s\r\n]*(.*?)[\r\n]*(?:-\s*)?Tipo de shortcode:[\s\r\n]*(.*?)[\r\n]*(?:-\s*)?Shortcode generado:[\s\r\n]*(.*?)(?=ACTIVIDAD\s+\d+:|\Z)'
    
    matches_actividades = re.finditer(pattern, texto_completo, re.DOTALL | re.IGNORECASE)
    
    for match in matches_actividades:
        num_actividad = match.group(1)
        texto_original = match.group(2).strip()
        tipo = match.group(3).strip()
        shortcode = match.group(4).strip()
        
        actividades.append({
            "numero": num_actividad,
            "texto_original": texto_original,
            "tipo": tipo,
            "shortcode": shortcode
        })
    
    # Si no encontramos actividades con el patrón anterior, intentar un patrón alternativo
    if not actividades:
        alt_pattern = r'(?:ACTIVIDAD|EJERCICIO|PREGUNTA)\s*(?:\d+)?:?\s*(.*?)[\r\n]+(?:TIPO|SHORTCODE):?\s*(.*?)[\r\n]+(?:SHORTCODE|CÓDIGO):?\s*(.*?)(?=(?:ACTIVIDAD|EJERCICIO|PREGUNTA)|\Z)'
        alt_matches = re.finditer(alt_pattern, texto_completo, re.DOTALL | re.IGNORECASE)
        
        for i, match in enumerate(alt_matches):
            texto_original = match.group(1).strip()
            tipo = match.group(2).strip()
            shortcode = match.group(3).strip()
            
            actividades.append({
                "numero": str(i+1),
                "texto_original": texto_original,
                "tipo": tipo,
                "shortcode": shortcode
            })
    
    resultado["actividades"] = actividades
    
    return resultado

# Función para generar el archivo de texto descargable
def generate_download_text(resultado):
    if not resultado or "enunciado" not in resultado or "actividades" not in resultado:
        return None
    
    # Iniciar con el enunciado principal
    texto = f"ENUNCIADO Principal\n{resultado['enunciado']}\n\n"
    
    # Añadir cada actividad
    for actividad in resultado["actividades"]:
        numero = actividad.get("numero", "")
        
        # Obtener la versión más reciente del shortcode si existe en el historial
        shortcode = actividad.get("shortcode", "")
        actividad_key = f"actividad_{numero}"
        if actividad_key in st.session_state.shortcode_versions and st.session_state.shortcode_versions[actividad_key]:
            # Usar la versión más reciente
            versiones = st.session_state.shortcode_versions[actividad_key]
            if versiones:
                shortcode = versiones[-1]["shortcode"]
        
        texto += f"ENUNCIADO Pregunta {numero}\n{actividad.get('texto_original', '')}\n\n"
        texto += f"SHORTCODE Pregunta {numero}\n{shortcode}\n\n"
    
    return texto

# Función para crear datos de descarga
def get_download_data(text, filename="resultados_analisis.txt"):
    b64 = base64.b64encode(text.encode()).decode()
    return b64, filename

# Función para agregar entrada al historial
def agregar_a_historial(evento, detalles=None):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entrada = {
        "timestamp": timestamp,
        "evento": evento,
        "detalles": detalles
    }
    st.session_state.conversation_history.append(entrada)

# Función para guardar una nueva versión de un shortcode
def guardar_version_shortcode(actividad_num, shortcode, explicacion=None):
    # Asegurarse de que shortcode_versions existe en la sesión
    if 'shortcode_versions' not in st.session_state:
        st.session_state.shortcode_versions = {}
    
    actividad_key = f"actividad_{actividad_num}"
    
    if actividad_key not in st.session_state.shortcode_versions:
        st.session_state.shortcode_versions[actividad_key] = []
    
    # Guardar la nueva versión con timestamp
    st.session_state.shortcode_versions[actividad_key].append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "shortcode": shortcode,
        "explicacion": explicacion
    })

# ============================================================================
# INTERFAZ PRINCIPAL ACTUALIZADA
# ============================================================================

# Configuración de la app
st.title("🔄 Conversor de Ejercicios a Shortcodes + EdiBlocks")
st.markdown("### Extracción automática de ejercicios desde imágenes y texto plano + Publicación en EdiBlocks")

# Sidebar para configuración y historial
with st.sidebar:
    st.header("Configuración")
    
    # API key con formato textarea para evitar problemas de copiar/pegar
    api_key = st.text_area(
        "Clave API de Anthropic", 
        value=st.session_state.api_key_saved,
        help="Copia y pega tu clave API completa (comienza con sk-ant-)"
    )
    
    # Guardar la API key en la sesión para conservarla en reinicios
    if api_key != st.session_state.api_key_saved:
        st.session_state.api_key_saved = api_key
    
    # Opciones avanzadas - minimizadas por defecto
    with st.expander("Opciones avanzadas"):
        mostrar_respuesta_completa = st.checkbox("Mostrar respuesta completa", value=False)
        mostrar_tipologias = st.checkbox("Mostrar ejemplos de tipologías", value=False)
        nombre_archivo = st.text_input("Nombre del archivo de descarga", value="resultados_analisis.txt")
        
        # Botón para reiniciar todo el estado de la aplicación
        if st.button("🔄 Reiniciar toda la aplicación"):
            # Limpiar todas las variables de estado
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            # Inicializar las variables necesarias
            st.session_state.conversation_history = []
            st.session_state.shortcode_versions = {}
            st.session_state.current_image_url = None
            st.session_state.current_text_content = ""
            st.session_state.temp_text_content = ""
            st.session_state.input_type = "image_url"
            st.session_state.prompt_personalizado = ""
            st.session_state.api_key_saved = ""
            st.session_state.session_id = str(int(time.time()))
            st.session_state.resultado = None
            # Variables EdiBlocks
            st.session_state.ediblocks_config = {
                'base_url': EDIBLOCKS_BASE_URL,
                'api_key': '',
                'organization_id': 1
            }
            st.session_state.available_tags = []
            st.session_state.publication_history = []
            # Agregar registro al historial
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            entrada = {
                "timestamp": timestamp,
                "evento": "Reinicio completo de la aplicación",
                "detalles": "Se ha reiniciado el estado completo de la aplicación"
            }
            st.session_state.conversation_history = [entrada]
            # Recargar la página
            st.rerun()
    
    # Historial de acciones
    st.header("Historial")
    with st.expander("Ver historial de acciones", expanded=True):
        if st.session_state.conversation_history:
            for entrada in reversed(st.session_state.conversation_history):
                with st.container():
                    st.write(f"**{entrada['timestamp']}**: {entrada['evento']}")
                    if entrada['detalles']:
                        st.caption(entrada['detalles'])
                    st.divider()
        else:
            st.info("No hay historial de acciones aún.")

# Mostrar ejemplos de tipologías si está activado
if 'mostrar_tipologias' in locals() and mostrar_tipologias:
    with st.expander("Ejemplos de tipologías de ejercicios"):
        for tipo in TIPOLOGIAS:
            st.markdown(f"**{tipo['label']} ({tipo['name']})**")
            st.code(tipo['sample'], language="html")

# Selector de tipo de entrada
input_type_options = ["URL de imagen", "Texto plano"]
input_type_mapping = {
    "URL de imagen": "image_url", 
    "Texto plano": "text_upload"
}
reverse_mapping = {v: k for k, v in input_type_mapping.items()}

selected_input_type = st.radio(
    "Selecciona el tipo de entrada:",
    input_type_options,
    index=input_type_options.index(reverse_mapping.get(st.session_state.input_type, "URL de imagen"))
)

# Actualizar el tipo de entrada en la sesión
st.session_state.input_type = input_type_mapping[selected_input_type]

# Área principal
col1, col2 = st.columns([1, 1])

with col1:
    # Interfaz diferente según el tipo de entrada seleccionado
    if st.session_state.input_type == "image_url":
        st.header("Proporciona la URL de la imagen")
        url_imagen = st.text_input(
            "URL de la imagen", 
            "",
            help="URL pública de la imagen de ejercicios"
        )
        
        # Previsualizar la imagen (con manejo simple)
        if url_imagen:
            try:
                # Verificar si la URL es accesible antes de mostrarla
                response = requests.head(url_imagen, timeout=5)
                if response.status_code == 200:
                    st.image(url_imagen, caption="Imagen actual", use_container_width=True)
                else:
                    st.warning(f"⚠️ No se puede acceder a la imagen en la URL proporcionada. Código de estado: {response.status_code}")
            except Exception as e:
                st.warning(f"⚠️ No se ha podido acceder a la imagen en la URL proporcionada. Error: {str(e)}")
        elif 'current_image_url' in st.session_state and st.session_state.current_image_url:
            try:
                # Verificar si la URL guardada es accesible
                response = requests.head(st.session_state.current_image_url, timeout=5)
                if response.status_code == 200:
                    st.image(st.session_state.current_image_url, caption="Imagen procesada", use_container_width=True)
                else:
                    st.warning(f"⚠️ No se puede acceder a la imagen guardada. Código de estado: {response.status_code}")
            except Exception as e:
                st.warning(f"⚠️ No se ha podido acceder a la imagen guardada. Error: {str(e)}")
    
    else:  # text_upload
        st.header("Texto de los ejercicios")
        # Opción para subir un archivo de texto
        uploaded_text_file = st.file_uploader("Sube un archivo de texto (opcional)", type=["txt"])
        
        # Si se subió un archivo de texto, leerlo
        if uploaded_text_file is not None:
            # Verificar si es un nuevo archivo de texto
            text_contents = uploaded_text_file.getvalue().decode("utf-8")
            text_hash = hash(text_contents)
            
            is_new_text = ('current_text_hash' not in st.session_state or 
                           st.session_state.get('current_text_hash') != text_hash)
            
            if is_new_text:
                # Es un nuevo archivo de texto
                st.session_state.current_text_hash = text_hash
                st.session_state.current_text_content = text_contents
                st.session_state.temp_text_content = text_contents
                
                # Registrar en el historial
                agregar_a_historial(
                    "Nuevo archivo de texto subido", 
                    f"Nombre: {uploaded_text_file.name}\nTamaño: {len(text_contents)} caracteres"
                )
        
        # Callback para cuando cambia el texto
        def on_text_change():
            st.session_state.temp_text_content = st.session_state.text_input_area
            st.session_state.current_text_content = st.session_state.text_input_area
        
        # Área de texto para editar o pegar directamente
        st.text_area(
            "O introduce el texto directamente aquí",
            value=st.session_state.temp_text_content,
            height=300,
            help="Pega el texto de los ejercicios o edita el contenido del archivo subido",
            key="text_input_area",
            on_change=on_text_change
        )
        
        # Botón dedicado para actualizar explícitamente el texto
        if st.button("Actualizar texto", key="update_text_btn"):
            st.session_state.current_text_content = st.session_state.temp_text_content
            st.success("Texto actualizado correctamente.")
            time.sleep(0.5)
            st.rerun()
    
    # Campo para prompt personalizado (común para ambos tipos)
    st.header("Instrucciones personalizadas (opcional)")
    prompt_personalizado = st.text_area(
        "Añade instrucciones adicionales para Claude",
        value=st.session_state.prompt_personalizado,
        key=f"prompt_personal_{st.session_state.session_id}",
        help="Por ejemplo: 'Divida las preguntas complejas en ejercicios más simples' o 'Para los ejercicios de matemáticas, añade ejemplos resueltos'"
    )
    
    # Guardar el prompt personalizado en la sesión
    if prompt_personalizado != st.session_state.prompt_personalizado:
        st.session_state.prompt_personalizado = prompt_personalizado
    
    # Botón de procesamiento
    if st.button("Procesar", type="primary"):
        if not api_key:
            st.error("Por favor, ingresa tu clave API de Anthropic en la barra lateral.")
        elif st.session_state.input_type == "image_url" and not url_imagen:
            st.error("Por favor, proporciona una URL de imagen válida.")
        elif st.session_state.input_type == "text_upload" and (not st.session_state.current_text_content.strip() and not st.session_state.temp_text_content.strip()):
            st.error("Por favor, introduce o sube un texto para procesar.")
        else:
            # Limpiar variables específicas para un nuevo procesamiento
            for key in ['texto_respuesta', 'resultado', 'shortcode_versions']:
                if key in st.session_state:
                    del st.session_state[key]
            
            # Procesar según el tipo de entrada
            if st.session_state.input_type == "image_url":
                # Verificar si es una nueva imagen o la misma
                is_new_image = 'current_image_url' not in st.session_state or st.session_state.current_image_url != url_imagen
                
                if is_new_image:
                    # Guardar mensaje para el historial
                    old_url = st.session_state.get('current_image_url', 'Ninguna')
                    mensaje_cambio = f"URL anterior: {old_url}\nNueva URL: {url_imagen}"
                    
                    # Actualizar la URL actual
                    st.session_state.current_image_url = url_imagen
                    
                    # Registrar el cambio en el historial
                    agregar_a_historial("Cambio de imagen", mensaje_cambio)
                
                # Procesar la imagen desde la URL
                with st.spinner("Analizando la imagen con Claude 4..."):
                    texto_respuesta = analizar_imagen_con_prompt(api_key, url_imagen, prompt_personalizado)
                    
                    if texto_respuesta:
                        evento = "Imagen procesada con Claude 4"
                        detalles = f"URL: {url_imagen}"
                        if prompt_personalizado:
                            detalles += f"\nPrompt personalizado: {prompt_personalizado}"
                        
                        agregar_a_historial(evento, detalles)
            
            elif st.session_state.input_type == "text_upload":
                # Procesar el texto directamente
                with st.spinner("Analizando el texto con Claude 4..."):
                    # Asegurarse de usar el texto más actualizado
                    texto_a_procesar = st.session_state.temp_text_content
                    if not texto_a_procesar.strip():
                        texto_a_procesar = st.session_state.current_text_content
                    
                    texto_respuesta = analizar_texto_con_prompt(api_key, texto_a_procesar, prompt_personalizado)
                    
                    if texto_respuesta:
                        evento = "Texto procesado con Claude 4"
                        detalles = f"Longitud: {len(texto_a_procesar)} caracteres"
                        if prompt_personalizado:
                            detalles += f"\nPrompt personalizado: {prompt_personalizado}"
                        
                        agregar_a_historial(evento, detalles)
            
            # Procesar el resultado (común para todos los tipos de entrada)
            if 'texto_respuesta' in locals() and texto_respuesta:
                # Guardar el texto completo
                st.session_state.texto_respuesta = texto_respuesta
                
                # Extraer información estructurada
                info_estructurada = extraer_informacion_texto(texto_respuesta)
                st.session_state.resultado = info_estructurada
                
                # Asegurarse de que shortcode_versions existe
                if 'shortcode_versions' not in st.session_state:
                    st.session_state.shortcode_versions = {}
                
                # Guardar la versión inicial de cada shortcode
                for actividad in info_estructurada.get("actividades", []):
                    guardar_version_shortcode(
                        actividad.get("numero"), 
                        actividad.get("shortcode")
                    )
                
                # Mostrar mensaje de éxito
                st.success("¡Análisis completado!")
                st.rerun()  # Recargar para actualizar la interfaz

with col2:
    st.header("Resultado")
    
    # Mostrar mensaje de éxito si hay un resultado
    if 'resultado' in st.session_state and st.session_state.resultado:
        st.success("✅ ¡Análisis completado con éxito! Consulta los resultados a continuación.")
    
    if ('texto_respuesta' in st.session_state and st.session_state.texto_respuesta and 
        'mostrar_respuesta_completa' in locals() and mostrar_respuesta_completa):
        # Mostrar el texto completo de la respuesta solo si está activada la opción
        with st.expander("Respuesta completa de Claude"):
            st.markdown(st.session_state.texto_respuesta)
    
    if 'resultado' in st.session_state and st.session_state.resultado:
        resultado = st.session_state.resultado
        
        # Mostrar enunciado en una caja tipo markdown similar a la de los shortcodes
        st.subheader("Enunciado original")
        st.code(resultado.get("enunciado", "No se encontró un enunciado"), language="markdown")
        
        st.subheader("Actividades convertidas")
        for i, actividad in enumerate(resultado.get("actividades", [])):
            num_actividad = actividad.get("numero", i+1)
            actividad_key = f"actividad_{num_actividad}"
            
            with st.expander(f"Actividad {num_actividad}", expanded=False):
                st.markdown("**Texto original:**")
                texto_original = actividad.get("texto_original", "")
                st.write(texto_original)
                
                st.markdown("**Tipo de shortcode:**")
                tipo_actual = actividad.get("tipo", "")
                st.code(tipo_actual)
                
                # Mostrar shortcode actual
                st.markdown("**Shortcode actual:**")
                
                # Obtener la versión más reciente del shortcode si existe
                shortcode_actual = actividad.get("shortcode", "")
                
                # Asegurarse de que shortcode_versions existe
                if 'shortcode_versions' not in st.session_state:
                    st.session_state.shortcode_versions = {}
                
                if actividad_key in st.session_state.shortcode_versions and st.session_state.shortcode_versions[actividad_key]:
                    versiones = st.session_state.shortcode_versions[actividad_key]
                    if versiones:
                        shortcode_actual = versiones[-1]["shortcode"]
                
                st.code(shortcode_actual, language="html")
                
                # Historial de versiones del shortcode
                if actividad_key in st.session_state.shortcode_versions and len(st.session_state.shortcode_versions[actividad_key]) > 1:
                    st.markdown("**Historial de versiones:**")
                    version_tabs = st.tabs([f"V{v_idx+1}" for v_idx in range(len(st.session_state.shortcode_versions[actividad_key]))])
                    for v_idx, (tab, version) in enumerate(zip(version_tabs, st.session_state.shortcode_versions[actividad_key])):
                        with tab:
                            st.write(f"**Versión {v_idx+1}** - {version['timestamp']}")
                            st.code(version['shortcode'], language="html")
                            if version.get('explicacion'):
                                st.write(f"*Explicación:* {version['explicacion']}")
                
                # Área para refinar el shortcode
                st.markdown("**Refinar este shortcode:**")
                instruccion_refinamiento = st.text_area(
                    "Instrucciones de refinamiento", 
                    key=f"refine_{num_actividad}_{st.session_state.session_id}",
                    help="Especifica cómo quieres mejorar o modificar este shortcode"
                )
                
                if st.button("Refinar", key=f"btn_refine_{num_actividad}_{st.session_state.session_id}"):
                    if not api_key:
                        st.error("Se requiere una clave API para refinar el shortcode.")
                    elif not instruccion_refinamiento:
                        st.warning("Por favor, proporciona instrucciones sobre cómo refinar el shortcode.")
                    else:
                        with st.spinner("Refinando shortcode con Claude 4..."):
                            # Obtener resultado de refinamiento
                            resultado_refinamiento = refinar_shortcode(
                                api_key, 
                                shortcode_actual, 
                                texto_original, 
                                tipo_actual, 
                                instruccion_refinamiento
                            )
                            
                            if resultado_refinamiento and resultado_refinamiento["shortcode"]:
                                # Guardar nueva versión
                                guardar_version_shortcode(
                                    num_actividad, 
                                    resultado_refinamiento["shortcode"],
                                    resultado_refinamiento.get("explicacion")
                                )
                                
                                # Agregar al historial
                                agregar_a_historial(
                                    f"Refinamiento de Actividad {num_actividad} con Claude 4", 
                                    f"Instrucción: {instruccion_refinamiento}\nExplicación: {resultado_refinamiento.get('explicacion', 'No proporcionada')}"
                                )
                                
                                # Recargar la página para mostrar el shortcode actualizado
                                st.rerun()
                            else:
                                st.error("No se pudo refinar el shortcode. Inténtalo de nuevo.")
        
        # Mostrar todos los shortcodes juntos (versiones más recientes)
        st.subheader("Todos los shortcodes generados (versión actual)")
        todos_shortcodes = []
        
        for actividad in resultado.get("actividades", []):
            num_actividad = actividad.get("numero")
            actividad_key = f"actividad_{num_actividad}"
            
            shortcode = actividad.get("shortcode", "")
            # Usar la versión más reciente si existe
            if 'shortcode_versions' in st.session_state and actividad_key in st.session_state.shortcode_versions and st.session_state.shortcode_versions[actividad_key]:
                versiones = st.session_state.shortcode_versions[actividad_key]
                if versiones:
                    shortcode = versiones[-1]["shortcode"]
            
            todos_shortcodes.append(shortcode)
        
        st.code("\n\n".join(todos_shortcodes), language="html")
            
        # Generar y preparar descarga
        texto_descargable = generate_download_text(resultado)
        if texto_descargable:
            st.subheader("Descargar resultados")
            nombre_archivo_final = nombre_archivo if 'nombre_archivo' in locals() else "resultados_analisis.txt"
            
            # Preparar datos para descarga
            b64_data, filename = get_download_data(texto_descargable, nombre_archivo_final)
            
            # Crear botón de descarga
            download_button_str = f'''
            <div style="margin-bottom: 20px;">
            <a href="data:file/txt;base64,{b64_data}" download="{filename}">
                <button style="
                    background-color: #4CAF50;
                    border: none;
                    color: white;
                    padding: 12px 24px;
                    text-align: center;
                    text-decoration: none;
                    display: inline-block;
                    font-size: 16px;
                    margin: 4px 2px;
                    cursor: pointer;
                    border-radius: 4px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.2);
                ">
                    📥 Descargar Resultados
                </button>
            </a>
            </div>
            '''
            st.markdown(download_button_str, unsafe_allow_html=True)
            
            # Mostrar vista previa del archivo de descarga
            with st.expander("Vista previa del archivo de descarga"):
                st.text(texto_descargable)
        
        # ============================================================================
        # NUEVA SECCIÓN: PUBLICACIÓN EN EDIBLOCKS
        # ============================================================================
        st.markdown("---")
        mostrar_seccion_publicacion_basica()
        
    else:
        st.info("Procesa una imagen o un texto para ver los resultados.")

# Footer
st.markdown("---")
st.markdown("<div style='text-align: center; padding: 10px;'>Conversor de Ejercicios a Shortcodes + EdiBlocks - Desarrollado con ❤️ usando Claude 4</div>", unsafe_allow_html=True)
