import os
import streamlit as st
from google import genai
from google.genai import types
from streamlit_mic_recorder import mic_recorder
from elevenlabs.client import ElevenLabs

# Configuración de la página
st.set_page_config(
    page_title="Asistente Tecnico en Construccion",
    page_icon="🎙️",
    layout="wide"
)

# Inicializar clientes
client = genai.Client()
eleven_client = ElevenLabs(api_key=st.secrets.get("ELEVENLABS_API_KEY", os.getenv("ELEVENLABS_API_KEY")))

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
    audio_bytes = audio_data['bytes']
    audio_path = "temp_audio.wav"
    with open(audio_path, "wb") as f:
        f.write(audio_bytes)
        
    with st.spinner("Procesando tu voz..."):
        try:
            audio_file_ref = client.files.upload(file=audio_path)
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
    st.session_state.messages.append({"role": "user", "content": prompt_to_process})
    with st.chat_message("user"):
        st.markdown(prompt_to_process)

    contents = []
    gemini_files = []
   si uploaded_files:
          para archivo en uploaded_files:
              # Limpiamos el nombre para evitar errores de codificación con tildes o espacios
              nombre_original = archivo.Nombre
              nombre_limpio = unicodedata.normalize('NFKD', nombre_original).encode('ASCII', 'ignore').decode('ASCII')
              nombre_limpio = re.sub(r'[^a-zA-Z0-9_.-]', '_', nombre_limpio)
              
              temp_path = f"temp_{nombre_limpio}"
              con abierto(temp_path, "WB") como f:
                  f.escribe(archivo.getbuffer())
              g_file = cliente.Archivos.Subida(archivo=temp_path)
              gemini_files.Añadir(g_file)
              OS.eliminar(temp_path)
          Índice.Extender(gemini_files)
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
                
                # --- RESPUESTA DE AUDIO CON ELEVENLABS ---
                with st.spinner("Generando audio profesional..."):
                    audio_generator = eleven_client.text_to_speech.convert(
                        text=assistant_response,
                        voice_id="JBFqnCBsd6RMkjVDRZzb",  # Rachel (voz por defecto)
                        model_id="eleven_multilingual_v2",
                        output_format="mp3_44100_128",
                    )
                    
                    audio_file_path = "respuesta_audio.mp3"
                    with open(audio_file_path, "wb") as f:
                        for chunk in audio_generator:
                            if chunk:
                                f.write(chunk)
                    
                    # Reproductor de audio nativo con reproducción automática
                    st.audio(audio_file_path, format="audio/mp3", autoplay=True)
                
                # Guardar respuesta en historial
                st.session_state.messages.append({"role": "assistant", "content": assistant_response})
                
            except Exception as e:
                st.error(f"Ocurrió un error en la ejecución: {e}")
