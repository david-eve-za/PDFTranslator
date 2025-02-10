import os
import logging
from typing import Literal, Optional

from together import Together
from transformers import AutoTokenizer
from huggingface_hub import login

from LLM.APIClient import APIClient
from PDFv2 import CommonPrompts


class TogetherAI(APIClient, CommonPrompts):
    def __init__(self, model_type: Literal["text", "image", "audio"], width: int = 512, height: int = 512):
        APIClient.__init__(self=self, tokens_per_minute=131072, calls_per_minute=60, daily_calls=200000)
        CommonPrompts.__init__(self)
        api_key = os.getenv("TOGETHER_API_KEY")
        hf_token = os.getenv("HF_TOKEN")

        if not api_key:
            logging.error("La variable de entorno TOGETHER_API_KEY no está configurada.")
            raise ValueError("TOGETHER_API_KEY no configurada")
        if not hf_token:
            # Podría ser un warning si el login no es estrictamente necesario siempre
            logging.warning("La variable de entorno HF_TOKEN no está configurada. El login a Hugging Face fallará.")
            # Considerar si lanzar un error o continuar dependiendo de la necesidad del login

        try:
            self._client = Together(api_key=api_key)
            # Considerar mover el login solo si es estrictamente necesario para el tokenizer
            login(token=hf_token)
        except Exception as e:
            logging.error(f"Error al inicializar el cliente Together o al hacer login en Hugging Face: {e}")
            raise
        self._text_generation_model = "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"
        try:
            # Asegurarse que el tokenizer coincide con el modelo base si es necesario
            # Por ejemplo, Llama-3.3-70B-Instruct-Turbo-Free usa el tokenizer de Llama-3.3-70B-Instruct
            tokenizer_name = "meta-llama/Llama-3.3-70B-Instruct"
            self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
        except Exception as e:
            logging.error(f"Error al cargar el tokenizer '{tokenizer_name}': {e}")
            raise
        self._image_generation_model = "black-forest-labs/FLUX.1-schnell-Free"
        self._model_type = model_type
        if model_type == "text":
            self._system_prompt = self.get_text_prompt()
        else:
            self._system_prompt = self.get_audio_prompt()
        self._width = width
        self._height = height
        self._system_prompt_size = self.count_tokens(self._system_prompt)

    def get_system_prompt_size(self):
        return self._system_prompt_size

    def call_model(self, prompt: str, temperature: float = 0.1) -> Optional[str]:
        """
        Llama al modelo apropiado (texto/audio o imagen) después de verificar los límites de tasa.

        Args:
            prompt: El prompt para el modelo.
            temperature: La temperatura para la generación de texto (si aplica).

        Returns:
            La respuesta del modelo (texto o URL de imagen) o None si ocurre un error.
        """
        if self._model_type == "text" or self._model_type == "audio":
            # Calcular tokens requeridos = prompt sistema + prompt usuario
            # Nota: Verificar si count_tokens debe usar add_special_tokens=True/False según la API
            required_tokens = self.get_system_prompt_size() + self.count_tokens(prompt)

            # Esperar si es necesario
            can_proceed = self.wait_if_needed(required_tokens)
            if not can_proceed:
                logging.error(f"No se puede proceder con la llamada debido a límites de tasa irrecuperables (tokens requeridos: {required_tokens}).")
                return None # O lanzar una excepción específica

            # Llamar al modelo de texto
            return self._call_text_model(prompt=prompt, system=self._system_prompt, temperature=temperature)
        elif self._model_type == "image":
            # Nota: Aquí no se verifican límites de tasa para imágenes. Implementar si es necesario.
            return self._call_image_model(prompt)
        else:
            logging.error(f"Tipo de modelo desconocido: {self._model_type}")
            return None

    def count_tokens(self, text):
        return len(self.tokenizer.encode(text, add_special_tokens=False))

    def _call_text_model(self, prompt: str, system: str, temperature: float = 0.1) -> Optional[str]:
        """Llama al modelo de texto/chat de TogetherAI."""
        message = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
        try:
            response = self._client.chat.completions.create(
                model=self._text_generation_model,
                messages=message,
                temperature=temperature,
                max_tokens=4000 # Considerar hacerlo configurable
            )
            # Podría ser útil loggear response.usage.total_tokens si se necesita el conteo exacto
            # logging.info(f"Tokens usados (API): {response.usage.total_tokens}")
            if response.choices:
                return response.choices[0].message.content
            else:
                logging.warning("La respuesta de la API no contiene 'choices'.")
                return None
        except Exception as e:
            logging.error(f"Error durante la llamada a la API de texto TogetherAI: {e}")
            # Podría mapear a excepciones más específicas si se importa together.errors
            return None

    def _call_image_model(self, prompt: str) -> Optional[str]:
        """Llama al modelo de generación de imágenes de TogetherAI."""
        try:
            response = self._client.images.generate(
                model=self._image_generation_model,
                prompt=prompt,
                width=self._width,
                height=self._height,
                steps=4, # Considerar hacerlo configurable
                n=1      # Considerar hacerlo configurable
            )
            if response.data:
                return response.data[0].url
            else:
                logging.warning("La respuesta de la API de imagen no contiene 'data'.")
                return None
        except Exception as e:
            logging.error(f"Error durante la llamada a la API de imagen TogetherAI: {e}")
            # Podría mapear a excepciones más específicas
            return None
