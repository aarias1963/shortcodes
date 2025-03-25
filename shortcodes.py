import streamlit as st
import requests
import json
import re
import base64
import time
from datetime import datetime

# Configuración de la página
st.set_page_config(
    page_title="Conversor de Ejercicios a Shortcodes",
    page_icon="📚",
    layout="wide"
)

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
if 'api_key_saved' not in st.session_state:
    st.session_state.api_key_saved = ""
if 'session_id' not in st.session_state:
    # Crear un ID de sesión único para los widgets
    st.session_state.session_id = str(int(time.time()))
if 'prompt_personalizado' not in st.session_state:
    st.session_state.prompt_personalizado = ""
if 'input_type' not in st.session_state:
    st.session_state.input_type = "image_url"  # "image_url" o "text_upload"
# Inicializar resultado si no existe
if 'resultado' not in st.session_state:
    st.session_state.resultado = None

# Esta sección contenía funciones para procesar PDFs que han sido eliminadas

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

### 5. fill-in-the-blanks
- Usar para: Elegir entre dos opciones
- Formato: [fill-in-the-blanks text="Texto: [radio|Verdadero#Falso*]" casesensitive="false" specialcharssensitive="false"][/fill-in-the-blanks]
- Ejemplo: [fill-in-the-blanks text="La leche es: [radio|Blanca*#Negra]" casesensitive="false" specialcharssensitive="false"][/fill-in-the-blanks]
- MUY IMPORTANTE: El asterisco (*) indica la opción correcta. El símbolo | separa las opciones.

### 6. fill-in-the-blanks
- Usar para: Textos con espacios para seleccionar entre opciones (menú desplegable)
- Formato: [fill-in-the-blanks text="Texto con [select|Incorrecta1#*Correcta#Incorrecta2] para seleccionar." casesensitive="false" specialcharssensitive="false"][/fill-in-the-blanks]
- Ejemplo: [fill-in-the-blanks text="El animal más rápido es el [select|leopardo#*guepardo#león#tigre]." casesensitive="false" specialcharssensitive="false"][/fill-in-the-blanks]
- MUY IMPORTANTE: El asterisco (*) indica la opción correcta. Debe haber solo una opción correcta por cada hueco. El símbolo # separa las opciones.

### 7. fill-in-the-blanks
- Usar para: Introducir letras letras para completar una única palabra
- Formato: [fill-in-the-blanks text="Texto [short-text|letra1][short-text|letra2][short-text|letra3]" casesensitive="false" specialcharssensitive="false"][/fill-in-the-blanks]
- Ejemplo: [fill-in-the-blanks text="El caballo [text|blanco] de Santiago es de [short-text|c][short-text|o][short-text|l][short-text|o][short-text|r] blanco." casesensitive="false" specialcharssensitive="false"][/fill-in-the-blanks]

### 8. statement-option-match
- Usar para: Emparejar conceptos o frases con sus correspondientes opciones
- Formato: [statement-option-match statements="a*afirmación1|b*afirmación2" options="a*título1*descripción1|b*título2*descripción2"][/statement-option-match]
- Ejemplo: [statement-option-match statements="a*Lorem ipsum|b*Ipsum lorem|c*Dolor sit" options="a*Persona 1*Lorem ipsum Lorem ipsum|b*Persona 2*Lorem ipsum Lorem ipsum|c*Persona 3*Lorem ipsum Lorem ipsum"][/statement-option-match]

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
   – Ejemplo: [fill-in-the-blanks text="La capital de [text|España] es Madrid. El caballo [text|blanco] de Santiago es de [short-text|c][short-text|o][short-text|l][short-text|o][short-text|r] blanco. El animal más rápido del mundo es el [select|leopardo#*guepardo#león#tigre]. Las afirmaciones anteriores son: [radio|Verdaderas#Falsas*]" casesensitive="false" specialcharssensitive="false"][/fill-in-the-blanks]

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
        "model": "claude-3-7-sonnet-20250219",
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
    
    # Prompt base detallado para Claude
    instrucciones_base = """
# Tarea: Extraer ejercicios educativos y convertirlos en shortcodes

Analiza detalladamente esta imagen de un libro de ejercicios educativos y extrae:

1. El enunciado principal que explica el objetivo general de los ejercicios
2. Cada actividad o pregunta individual presente en la imagen

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

### 5. fill-in-the-blanks
- Usar para: Elegir entre dos opciones
- Formato: [fill-in-the-blanks text="Texto: [radio|Verdadero#Falso*]" casesensitive="false" specialcharssensitive="false"][/fill-in-the-blanks]
- Ejemplo: [fill-in-the-blanks text="La leche es: [radio|Blanca*#Negra]" casesensitive="false" specialcharssensitive="false"][/fill-in-the-blanks]
- MUY IMPORTANTE: El asterisco (*) indica la opción correcta. El símbolo | separa las opciones.

### 6. fill-in-the-blanks
- Usar para: Textos con espacios para seleccionar entre opciones (menú desplegable)
- Formato: [fill-in-the-blanks text="Texto con [select|Incorrecta1#*Correcta#Incorrecta2] para seleccionar." casesensitive="false" specialcharssensitive="false"][/fill-in-the-blanks]
- Ejemplo: [fill-in-the-blanks text="El animal más rápido es el [select|leopardo#*guepardo#león#tigre]." casesensitive="false" specialcharssensitive="false"][/fill-in-the-blanks]
- MUY IMPORTANTE: El asterisco (*) indica la opción correcta. Debe haber solo una opción correcta por cada hueco. El símbolo # separa las opciones.

### 7. fill-in-the-blanks
- Usar para: Introducir letras letras para completar una única palabra
- Formato: [fill-in-the-blanks text="Texto [short-text|letra1][short-text|letra2][short-text|letra3]" casesensitive="false" specialcharssensitive="false"][/fill-in-the-blanks]
- Ejemplo: [fill-in-the-blanks text="El caballo [text|blanco] de Santiago es de [short-text|c][short-text|o][short-text|l][short-text|o][short-text|r] blanco." casesensitive="false" specialcharssensitive="false"][/fill-in-the-blanks]

### 8. statement-option-match
- Usar para: Emparejar conceptos o frases con sus correspondientes opciones
- Formato: [statement-option-match statements="a*afirmación1|b*afirmación2" options="a*título1*descripción1|b*título2*descripción2"][/statement-option-match]
- Ejemplo: [statement-option-match statements="a*Lorem ipsum|b*Ipsum lorem|c*Dolor sit" options="a*Persona 1*Lorem ipsum Lorem ipsum|b*Persona 2*Lorem ipsum Lorem ipsum|c*Persona 3*Lorem ipsum Lorem ipsum"][/statement-option-match]

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
   – Ejemplo: [fill-in-the-blanks text="La capital de [text|España] es Madrid. El caballo [text|blanco] de Santiago es de [short-text|c][short-text|o][short-text|l][short-text|o][short-text|r] blanco. El animal más rápido del mundo es el [select|leopardo#*guepardo#león#tigre]. Las afirmaciones anteriores son: [radio|Verdaderas#Falsas*]" casesensitive="false" specialcharssensitive="false"][/fill-in-the-blanks]

## Formato de tu respuesta

Responde usando exactamente este formato:

ENUNCIADO: (escribe aquí el enunciado principal identificado en la imagen)

ACTIVIDAD 1:
- Texto original: (transcribe aquí el texto completo de la actividad como aparece en la imagen)
- Tipo de shortcode: (nombre exacto del tipo de shortcode más adecuado)
- Shortcode generado: (escribe el shortcode completo siguiendo exactamente el formato del ejemplo)

ACTIVIDAD 2:
- Texto original: (texto de la segunda actividad)
- Tipo de shortcode: (tipo elegido)
- Shortcode generado: (shortcode completo)

Y así sucesivamente para cada actividad identificada.

NO uses formato JSON ni otro formato. Usa SOLO el formato de texto indicado.
"""

    # Combinar prompt base con el prompt personalizado si existe
    if prompt_personalizado and prompt_personalizado.strip():
        instrucciones_completas = instrucciones_base + "\n\n## Instrucciones personalizadas adicionales\n\n" + prompt_personalizado
    else:
        instrucciones_completas = instrucciones_base
    
    # Estructura de la solicitud 
    data = {
        "model": "claude-3-7-sonnet-20250219",
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
- fill-in-the-blanks: [fill-in-the-blanks text="Texto con [select|Incorrecta1#*Correcta#Incorrecta2 casesensitive="false" specialcharssensitive="false"] para seleccionar."][/fill-in-the-blanks]
- fill-in-the-blanks: [fill-in-the-blanks text="Texto [short-text|letra1][short-text|letra2][short-text|letra3]" casesensitive="false" specialcharssensitive="false"][/fill-in-the-blanks]
- fill-in-the-blanks: [fill-in-the-blanks text="Texto: [radio|Verdadero#Falso*]" casesensitive="false" specialcharssensitive="false"][/fill-in-the-blanks]
- statement-option-match: [statement-option-match statements="a*afirmación1|b*afirmación2" options="a*título1*descripción1|b*título2*descripción2"][/statement-option-match]
- writing: [writing maxtime="0"][/writing]
- oral-expression: [oral-expression autoplay="false" maxtime="0" maxplays="0"][/oral-expression]
- file-upload: [file-upload extensions="pdf|doc|docx"][/file-upload]
- image-choice: [image-choice images="url_imagen1*texto_alternativo1|url_imagen2*texto_alternativo2" correctOptionIndex="índice_opción_correcta"][/image-choice]
- multi-question: [multi-question questions=""][/multi-question]
- abnone-choice: [abnone-choice titlea="Título A" texta="Texto A" titleb="Título B" textb="Texto B" questions="a*Pregunta A|b*Pregunta B|c*Pregunta C"][/abnone-choice]

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
        "model": "claude-3-7-sonnet-20250219",
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

# Configuración de la app
st.title("🔄 Conversor de Ejercicios a Shortcodes")
st.markdown("### Extracción automática de ejercicios desde imágenes y texto plano")

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
            st.session_state.current_pdf_page_images = []
            st.session_state.current_pdf_page_index = 0
            st.session_state.input_type = "image_url"
            st.session_state.prompt_personalizado = ""
            st.session_state.api_key_saved = ""
            st.session_state.session_id = str(int(time.time()))
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
            for i, entrada in enumerate(reversed(st.session_state.conversation_history)):
                with st.container():
                    st.write(f"**{entrada['timestamp']}**: {entrada['evento']}")
                    if entrada['detalles']:
                        # En lugar de usar un expander anidado, mostrar los detalles con formato
                        st.markdown("**Detalles:**")
                        st.markdown(f"```\n{entrada['detalles']}\n```")
                    st.divider()
        else:
            st.info("No hay historial de acciones aún.")

# Mostrar ejemplos de tipologías si está activado
if mostrar_tipologias:
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
                
                # Registrar en el historial
                agregar_a_historial(
                    "Nuevo archivo de texto subido", 
                    f"Nombre: {uploaded_text_file.name}\nTamaño: {len(text_contents)} caracteres"
                )
        
        # Área de texto para editar o pegar directamente
        text_content = st.text_area(
            "O introduce el texto directamente aquí",
            value=st.session_state.current_text_content,
            height=300,
            help="Pega el texto de los ejercicios o edita el contenido del archivo subido"
        )
        
        # Actualizar el texto en la sesión si cambió
        if text_content != st.session_state.current_text_content:
            st.session_state.current_text_content = text_content
    
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
        elif st.session_state.input_type == "text_upload" and not st.session_state.current_text_content.strip():
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
                with st.spinner("Analizando la imagen..."):
                    texto_respuesta = analizar_imagen_con_prompt(api_key, url_imagen, prompt_personalizado)
                    
                    if texto_respuesta:
                        evento = "Imagen procesada"
                        detalles = f"URL: {url_imagen}"
                        if prompt_personalizado:
                            detalles += f"\nPrompt personalizado: {prompt_personalizado}"
                        
                        agregar_a_historial(evento, detalles)
            
            else:  # text_upload
                # Procesar el texto directamente
                with st.spinner("Analizando el texto..."):
                    texto_respuesta = analizar_texto_con_prompt(api_key, st.session_state.current_text_content, prompt_personalizado)
                    
                    if texto_respuesta:
                        evento = "Texto procesado"
                        detalles = f"Longitud: {len(st.session_state.current_text_content)} caracteres"
                        if prompt_personalizado:
                            detalles += f"\nPrompt personalizado: {prompt_personalizado}"
                        
                        agregar_a_historial(evento, detalles)
            
            # Procesar el resultado (común para todos los tipos de entrada)
            if texto_respuesta:
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
    if 'resultado' in st.session_state:
        st.success("✅ ¡Análisis completado con éxito! Consulta los resultados a continuación.")
    
    if 'texto_respuesta' in st.session_state and mostrar_respuesta_completa:
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
                        with st.spinner("Refinando shortcode..."):
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
                                    f"Refinamiento de Actividad {num_actividad}", 
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
    else:
        st.info("Procesa una imagen o un fichero de texto para ver los resultados.")

# Footer
st.markdown("---")
st.markdown("<div style='text-align: center; padding: 10px;'>Desarrollado con ❤️ para convertir ejercicios educativos a formatos digitales.</div>", unsafe_allow_html=True)
