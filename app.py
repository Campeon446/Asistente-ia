import os
import streamlit as st
import unicodedata
import re
from google import genai
from google.genai import types
from streamlit_mic_recorder import mic_recorder

# Configuración de la página
st.set_page_config(
    page_title="Asistente Tecnico en Construccion",
    page_icon="🏗️",
    layout="wide"
)

# Inicializar cliente de Gemini
client = genai.Client()

MODEL_ID = "gemini-3.5-flash-lite"

# Inicializar historial en sesión
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("💬 Conversaciones")
    if st.button("➕ Nueva conversación", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
        
    st.markdown("---")
    st.subheader("🎙️ Entrada de Voz (Transcripción)")
    st.markdown("Presiona el botón para hablarle al asistente:")
    
    # Componente para grabar audio desde el micrófono
    audio_data = mic_recorder(
        start_prompt="🔴 Iniciar Grabación",
        stop_prompt="⏹️ Detener Grabación",
        just_once=False,
        key='mic'
    )
    
    st.markdown("---")
    st.subheader("📁 Adjuntar Archivos")
    uploaded_files = st.file_uploader(
        "Planos, Excel, Word, etc.", 
        type=["pdf", "png", "jpg", "jpeg", "txt", "docx", "xlsx", "csv"],
        accept_multiple_files=True
    )

# --- CUERPO PRINCIPAL ---
st.title("Asistente Técnico en Construcción")
st.caption("Escribe, adjunta tus planos o utiliza tu voz para obtener cómputos métricos y asesoramiento.")

# Mostrar historial de chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Variable para capturar el texto de entrada
prompt_to_process = None

# 1. Verificar si el usuario habló mediante el grabador de voz
if audio_data:
    audio_bytes = audio_data['bytes']
    audio_path = "temp_audio.wav"
    with open(audio_path, "wb") as f:
        f.write(audio_bytes)
        
    with st.spinner("Procesando tu voz..."):
        try:
            audio_file_ref = client.files.upload(file=audio_path)
            voice_response = client.models.generate_content(
                model=MODEL_ID,
                contents=[audio_file_ref, "Transcribe este audio brevemente y responde a la solicitud planteada en él con un tono técnico y profesional en construcción."]
            )
            prompt_to_process = voice_response.text
            os.remove(audio_path)
        except Exception as e:
            st.error(f"Error procesando el audio: {e}")

# 2. Verificar si el usuario escribió en el cuadro de texto tradicional
if chat_input := st.chat_input("Escribe tu consulta o los detalles de la obra..."):
    prompt_to_process = chat_input

# --- PROCESAR MENSAJE ---
if prompt_to_process:
    st.session_state.messages.append({"role": "user", "content": prompt_to_process})
    with st.chat_message("user"):
        st.markdown(prompt_to_process)

    contents = []
    gemini_files = []
    
    if uploaded_files:
        for archivo in uploaded_files:
            # Limpiamos el nombre para evitar errores con tildes o espacios
            nombre_original = archivo.name
            nombre_limpio = unicodedata.normalize('NFKD', nombre_original).encode('ASCII', 'ignore').decode('ASCII')
            nombre_limpio = re.sub(r'[^a-zA-Z0-9_.-]', '_', nombre_limpio)
            
            temp_path = f"temp_{nombre_limpio}"
            with open(temp_path, "wb") as f:
                f.write(archivo.getbuffer())
            
            g_file = client.files.upload(file=temp_path)
            gemini_files.append(g_file)
            os.remove(temp_path)
            
        contents.extend(gemini_files)
        
    contents.append(prompt_to_process)

    # Generar respuesta del modelo
    with st.chat_message("assistant"):
        with st.spinner("Analizando plano y calculando materiales..."):
            try:
                response = client.models.generate_content(
                    model=MODEL_ID,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction="Te comportas como un asistente técnico experto en construcción en seco, cómputos métricos de perfilería, yeso, aislamientos y tabiquería. Da respuestas estructuradas, profesionales y claras."
                    )
                )
                assistant_response = response.text
                st.markdown(assistant_response)
                
                # Guardar respuesta en historial
                st.session_state.messages.append({"role": "assistant", "content": assistant_response})
                
            except Exception as e:
                st.error(f"Ocurrió un error en la ejecución: {e}")
