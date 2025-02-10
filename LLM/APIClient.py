import logging
import time
from collections import deque
from datetime import datetime, timedelta


class APIClient:
    def __init__(self, tokens_per_minute=6000, calls_per_minute: int = 30,
                 daily_calls: int = 1000):
        # Límites
        self.MAX_TOKENS_PER_MINUTE = tokens_per_minute
        self.MAX_CALLS_PER_MINUTE = calls_per_minute
        self.MAX_DAILY_CALLS = daily_calls

        # Trackers
        self.daily_calls = 0
        self.last_daily_reset = datetime.now()
        self.call_history = deque()  # (timestamp, tokens_usados)

        # Tokenizador
        # self.tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-32B")

    def _reset_daily_counter(self) -> None:
        """Reinicia el contador diario a medianoche"""
        now = datetime.now()
        if now.date() != self.last_daily_reset.date():
            self.daily_calls = 0
            self.last_daily_reset = now

    def _check_limits(self, required_tokens: int) -> list[str]:
        """Verifica todos los límites y devuelve los problemas detectados"""
        self._reset_daily_counter()
        now = time.time()

        # Limpiar llamadas antiguas
        while self.call_history and now - self.call_history[0][0] > 60:
            self.call_history.popleft()

        # Calcular métricas actuales
        current_minute_tokens = sum(t[1] for t in self.call_history)
        current_minute_calls = len(self.call_history)

        issues = []

        # Verificar límite diario
        if self.daily_calls >= self.MAX_DAILY_CALLS:
            next_reset = datetime.combine(
                datetime.now() + timedelta(days=1),
                datetime.min.time()
            )
            wait_seconds = (next_reset - datetime.now()).total_seconds()
            issues.append(f"Límite diario alcanzado. Esperar {wait_seconds:.1f}")

        # Verificar límite de llamadas/minuto
        if current_minute_calls >= self.MAX_CALLS_PER_MINUTE:
            oldest_call = self.call_history[0][0]
            wait_seconds = 60 - (now - oldest_call)
            issues.append(f"Límite de llamadas/min. Esperar {wait_seconds:.1f}")

        # Verificar límite de tokens/minuto
        # Solo verificar si la llamada actual requiere tokens y si excede el límite
        if required_tokens > 0 and (current_minute_tokens + required_tokens) > self.MAX_TOKENS_PER_MINUTE:
            # Si la llamada actual por sí sola excede el límite, esperar no ayuda
            if required_tokens > self.MAX_TOKENS_PER_MINUTE:
                 error_msg = f"Límite de tokens/min excedido por la llamada actual ({required_tokens} > {self.MAX_TOKENS_PER_MINUTE})."
                 # Marcar como problema irresoluble esperando. El manejo se hará en wait_if_needed
                 issues.append(error_msg)
            elif self.call_history: # Si hay historial y la suma excede, calcular espera
                 # Esperar hasta que la llamada más antigua salga de la ventana de 60s
                 # (Asume que liberar esa llamada podría liberar suficientes tokens)
                 oldest_call_time = self.call_history[0][0]
                 # Calcular tiempo hasta que la llamada más antigua cumpla 60s + pequeño margen
                 wait_seconds = max(0, 60.1 - (now - oldest_call_time))
                 issues.append(f"Límite de tokens/min. Esperar {wait_seconds:.1f}s")
            # else: No hay historial, pero la suma excede (y req_tokens <= MAX).
            # Esto implica current_minute_tokens > 0 sin historial, lo cual es imposible.
            # O req_tokens > MAX, cubierto arriba. No se necesita acción aquí.

        return issues

    def wait_if_needed(
            self,
            required_tokens: int = 0
    ) -> bool:
        """
        Verifica si la llamada API puede proceder según los límites de tasa.
        Espera si es necesario y registra la llamada si procede.

        Args:
            required_tokens: El número estimado de tokens que consumirá la llamada.

        Returns:
            bool: True si la llamada puede proceder (después de esperar si fue necesario),
                  False si la llamada no puede proceder (p.ej., requiere demasiados tokens
                  y excede el límite por sí sola).
        """
        # Verificar y esperar si es necesario para cumplir con los límites de la API
        while True:
            issues = self._check_limits(required_tokens)

            if not issues:
                break # Límites OK, salir del bucle de espera

            # Procesar problemas y calcular tiempo de espera
            wait_times = []
            can_proceed = True
            issue_messages = [] # Para logging

            for issue in issues:
                issue_messages.append(issue) # Guardar mensaje original
                # Comprobar si es el error irrecuperable de tokens
                if "excedido por la llamada actual" in issue:
                     logging.error(issue)
                     can_proceed = False # Marcar que no se puede proceder
                     # No necesitamos 'break' aquí, procesaremos todos los issues para logging
                     continue # No intentar extraer tiempo de este mensaje

                # Intentar extraer tiempo de espera del mensaje
                try:
                    # Busca el último token, quita 's' si existe, convierte a float
                    parts = issue.split()
                    time_str = parts[-1]
                    if time_str.endswith('s'):
                        time_str = time_str[:-1]
                    wait_times.append(float(time_str))
                except (ValueError, IndexError):
                    # Si falla la extracción, registrar advertencia pero continuar
                    logging.warning(f"No se pudo extraer tiempo de espera del mensaje: '{issue}'")

            if not can_proceed:
                # Si se detectó el error irrecuperable en cualquier issue
                return False # Devolver False inmediatamente

            # Si podemos proceder pero hubo issues, calcular tiempo de espera
            if not wait_times:
                 # Si hubo 'issues' pero no se extrajo ningún tiempo válido
                 logging.warning("Problema de límite detectado pero no se pudo calcular tiempo de espera. Esperando 1s por defecto.")
                 sleep_time = 1.0
            else:
                 # Esperar el máximo tiempo calculado
                 sleep_time = max(wait_times)

            # Asegurar espera mínima para evitar busy-waiting y problemas de precisión
            sleep_time = max(0.1, sleep_time)

            logging.info(f"Límite API alcanzado. Esperando {sleep_time:.1f}s. Motivos: {'; '.join(issue_messages)}")
            time.sleep(sleep_time)
            # Al final del bucle, se volverá a llamar a _check_limits() para re-evaluar


        # Si salimos del bucle while, significa que los límites se cumplen
        # Registrar la llamada como exitosa
        self.daily_calls += 1
        self.call_history.append((time.time(), required_tokens))
        return True # Indicar que la llamada puede proceder
