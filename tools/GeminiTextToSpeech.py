import os
import wave
from dotenv import load_dotenv
from google import genai
from pydub import AudioSegment
from google.genai import types
from typing import List, Dict, Union

class GeminiTextToSpeech:
    def __init__(self, api_key: str = None, model: str = "gemini-2.5-flash-preview-tts",
                 voice: str = "Kore", sample_rate: int = 24000, channels: int = 1, sample_width: int = 2):
        """
        Inicializa el cliente de Gemini Text-to-Speech.

        Nota: Para guardar en formato MP3, se requiere la biblioteca `pydub` y `ffmpeg`.
        Puedes instalarlos con: `pip install pydub` y asegurándote de que `ffmpeg` esté en el PATH de tu sistema.

        :param api_key: Clave de API de Google Generative AI. Si None, busca en GOOGLE_API_KEY.
        :param model: Identificador del modelo TTS a usar.
        :param voice: Nombre de la voz pre-definida a usar.
        :param sample_rate: Frecuencia de muestreo para el WAV.
        :param channels: Número de canales de audio.
        :param sample_width: Bytes por muestra (normalmente 2 para PCM16).
        """
        load_dotenv()
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("API key for Google Generative AI must be provided in parameter or via GOOGLE_API_KEY env var.")
        # genai.api_key = self.api_key

        self.client = genai.Client()
        self.model = model
        self.voice = voice
        self.sample_rate = sample_rate
        self.channels = channels
        self.sample_width = sample_width

    def _save_audio(self, pcm_bytes: bytes, output_path: str):
        """
        Guarda los bytes de audio PCM16 en un archivo, soportando WAV y MP3.
        El formato se determina por la extensión del archivo en `output_path`.
        """
        _, extension = os.path.splitext(output_path)
        extension = extension.lower()

        if extension == '.wav':
            with wave.open(output_path, "wb") as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.sample_width)
                wf.setframerate(self.sample_rate)
                wf.writeframes(pcm_bytes)
        elif extension == '.mp3':
            audio_segment = AudioSegment(
                data=pcm_bytes,
                sample_width=self.sample_width,
                frame_rate=self.sample_rate,
                channels=self.channels
            )
            audio_segment.export(output_path, format="mp3")
        else:
            raise ValueError(f"Formato de archivo no soportado: '{extension}'. Use '.wav' o '.mp3'.")

    def text_to_speech(self, text: str, output_path: str = "output.wav"):
        """
        Genera audio desde el texto y lo guarda en un archivo (WAV o MP3).
        :param text: Texto a convertir en voz.
        :param output_path: Ruta del archivo de salida. La extensión (.wav o .mp3) determina el formato.
        :return: Ruta del archivo generado.
        """
        response = self.client.models.generate_content(
            model=self.model,
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=self.voice
                        )
                    )
                )
            )
        )

        # Extraer los datos del primer candidato
        candidate = response.candidates[0]
        part = candidate.content.parts[0]
        inline_data = part.inline_data.data

        # Si viene como URL o base64, necesitarás lógica adicional
        if isinstance(inline_data, (bytes, bytearray)):
            pcm_bytes = inline_data
        elif isinstance(inline_data, str):
            raise RuntimeError("Audio data is a string (URL or base64). Additional download or decode logic required.")
        else:
            raise RuntimeError(f"Unexpected audio data type: {type(inline_data)}")

        # Guardar como WAV
        self._save_audio(pcm_bytes, output_path)
        print(f"✅ Saved audio to {output_path}")
        return output_path

# Lista de voces
def get_gemini_tts_voices() -> List[Dict[str, Union[str, List[str]]]]:
    """
    Proporciona una lista de las voces preconstruidas (Prebuilt Voices)
    disponibles para los modelos Gemini TTS (Flash/Pro Preview TTS),
    basadas en la documentación oficial de Google.

    La API de Gemini (google-genai) actualmente no tiene un método client.list_voices(),
    por lo que se utiliza una lista estática.

    Returns:
        List[Dict]: Lista de diccionarios, cada uno con el nombre de la voz
                    y sus características sugeridas.
    """
    voices_data = [
        # Voces Femeninas (Female)
        {"name": "Zephyr", "gender": "Female", "style_suggestion": "Bright"},
        {"name": "Kore", "gender": "Female", "style_suggestion": "Firm"},
        {"name": "Leda", "gender": "Female", "style_suggestion": "Youthful"},
        {"name": "Aoede", "gender": "Female", "style_suggestion": "Breezy"},
        {"name": "Autonoe", "gender": "Female", "style_suggestion": "Bright"},
        {"name": "Callirrhoe", "gender": "Female", "style_suggestion": "Easy-going"},
        {"name": "Despina", "gender": "Female", "style_suggestion": "Smooth"},
        {"name": "Erinome", "gender": "Female", "style_suggestion": "Clear"},
        {"name": "Gacrux", "gender": "Female", "style_suggestion": "Mature"},
        {"name": "Laomedeia", "gender": "Female", "style_suggestion": "Upbeat"},
        {"name": "Pulcherrima", "gender": "Female", "style_suggestion": "Forward"},
        {"name": "Sulafat", "gender": "Female", "style_suggestion": "Warm"},
        {"name": "Vindemiatrix", "gender": "Female", "style_suggestion": "Gentle"},
        {"name": "Achernar", "gender": "Female", "style_suggestion": "Soft"},

        # Voces Masculinas (Male)
        {"name": "Puck", "gender": "Male", "style_suggestion": "Upbeat"},
        {"name": "Charon", "gender": "Male", "style_suggestion": "Informative"},
        {"name": "Fenrir", "gender": "Male", "style_suggestion": "Excitable"},
        {"name": "Orus", "gender": "Male", "style_suggestion": "Firm"},
        {"name": "Enceladus", "gender": "Male", "style_suggestion": "Breathy"},
        {"name": "Iapetus", "gender": "Male", "style_suggestion": "Clear"},
        {"name": "Umbriel", "gender": "Male", "style_suggestion": "Easy-going"},
        {"name": "Algieba", "gender": "Male", "style_suggestion": "Smooth"},
        {"name": "Algenib", "gender": "Male", "style_suggestion": "Gravelly"},
        {"name": "Rasalgethi", "gender": "Male", "style_suggestion": "Informative"},
        {"name": "Alnilam", "gender": "Male", "style_suggestion": "Firm"},
        {"name": "Schedar", "gender": "Male", "style_suggestion": "Even"},
        {"name": "Achird", "gender": "Male", "style_suggestion": "Friendly"},
        {"name": "Zubenelgenubi", "gender": "Male", "style_suggestion": "Casual"},
        {"name": "Sadachbia", "gender": "Male", "style_suggestion": "Lively"},
        {"name": "Sadaltager", "gender": "Male", "style_suggestion": "Knowledgeable"},
    ]
    return voices_data

# Ejemplo de uso
if __name__ == "__main__":
    voices = get_gemini_tts_voices()

    for voice in voices:

        print(f"Nombre: {voice['name']}, Género: {voice['gender']}, Sugerencia de Estilo: {voice['style_suggestion']}")

        tts = GeminiTextToSpeech(voice=voice['name'])
        text_to_say = "Hola mundo! Esta es una prueba del modelo de texto a voz de Gemini. Ahora puedo guardar en WAV y también en MP3."

        # TODO: Get full current path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # output_wav_path = os.path.join(current_dir, f"gemini_tts_test_{voice['name']}.wav")
        output_mp3_path = os.path.join(f"{current_dir}/audiobooks", f"gemini_tts_test_{voice['name']}.mp3")

        # tts.text_to_speech(text_to_say, output_path=output_wav_path)
        tts.text_to_speech(text_to_say, output_path=output_mp3_path)