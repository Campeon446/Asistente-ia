import os
import streamlit as st
from google import genai
from google.genai import types
from streamlit_mic_recorder import mic_recorder

# Configuración de la página
st.set_page_config(
    page_title="Mi Asistente IA con Voz",
    page_icon="🎙️",
    layout="wide"
)

# Inicializar cliente de GenAI
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
    st.subheader("🎙️ Entrada de Voz")
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
st.title("Asistente IA Interactivo con Voz")
st.caption("Escribe, adjunta documentos o utiliza tu voz para interactuar.")

# Mostrar historial de chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Variable para capturar el texto de entrada (sea por teclado o por voz)
prompt_to_process = None

# 1. Verificar si el usuario habló mediante el grabador de voz
if audio_data:
    # El grabador devuelve un diccionario con los bytes del audio
    audio_bytes = audio_data['bytes']
    
    # Guardamos temporalmente el audio grabado
    audio_path = "temp_audio.wav"
    with open(audio_path, "wb") as f:
        f.write(audio_bytes)
        
    with st.spinner("Procesando tu voz..."):
        try:
            # Subimos el archivo de audio a la API de Gemini para que lo escuche y transcriba/responda
            audio_file_ref = client.files.upload(file=audio_path)
            
            # Pedimos a Gemini que transcriba y actúe sobre la instrucción de voz
            voice_response = client.models.generate_content(
                model=MODEL_ID,
                contents=[audio_file_ref, "Transcribe este audio brevemente y responde a la solicitud planteada en él con un tono técnico y profesional."]
            )
            prompt_to_process = voice_response.text
            os.remove(audio_path)
        except Exception as e:
            st.error(f"Error procesando el audio: {e}")

# 2. Verificar si el usuario escribió en el cuadro de texto tradicional
if chat_input := st.chat_input("Escribe tu mensaje o consulta..."):
    prompt_to_process = chat_input

# --- PROCESAR MENSAJE (Sea de texto o de voz) ---
if prompt_to_process:
    # Agregar mensaje al historial
    st.session_state.messages.append({"role": "user", "content": prompt_to_process})
    with st.chat_message("user"):
        st.markdown(prompt_to_process)

    # Preparar contenidos y archivos
    contents = []
    gemini_files = []
    if uploaded_files:
        for file in uploaded_files:
            temp_path = f"temp_{file.name}"
            with open(temp_path, "wb") as f:
                f.write(file.getbuffer())
            g_file = client.files.upload(file=temp_path)
            gemini_files.append(g_file)
            os.remove(temp_path)
        contents.extend(gemini_files)

    contents.append(prompt_to_process)

    # Generar respuesta del modelo
    with st.chat_message("assistant"):
        with st.spinner("Pensando respuesta..."):
            try:
                response = client.models.generate_content(
                    model=MODEL_ID,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction="Te comportas como un asistente técnico experto, preciso y profesional."
                    )
                )
                assistant_response = response.text
                st.markdown(assistant_response)
                
                # --- SINTETIZADOR DE VOZ (Texto a Voz nativo en el navegador) ---
                # Usamos JavaScript para que el navegador lea en voz alta la respuesta del asistente
                js_speech = f"""
                <script>
                    const text = {repr(assistant_response)};
                    const utterance = new SpeechSynthesisUtterance(text);
                    utterance.lang = 'es-ES'; // Configurado en español
                    window.speechSynthesis.speak(utterance);
                </script>
                """
                st.components.v1.html(js_speech, height=0)
                
                # Guardar respuesta en historial
                st.session_state.messages.append({"role": "assistant", "content": assistant_response})
                
            except Exception as e:
                st.error(f"Ocurrió un error: {e}")