import logging
import time
from collections import deque
from datetime import datetime, timedelta
from enum import Enum, auto
from dataclasses import dataclass

# --- Constants for better readability ---
SECONDS_IN_MINUTE = 60
MIN_API_SLEEP_INTERVAL_SECONDS = 0.1  # Minimum sleep time to prevent busy-waiting
DEFAULT_API_RETRY_SLEEP_SECONDS = 1.0  # Default sleep if no specific time is calculated


# --- Structured data for limit issues ---
class APILimitType(Enum):
    DAILY_CALLS = auto()
    CALLS_PER_MINUTE = auto()
    TOKENS_PER_MINUTE = auto()
    TOKENS_PER_CALL_EXCEEDED = auto()  # Specific fatal token issue where a single call is too large


@dataclass
class APIRateLimitIssue:
    issue_type: APILimitType
    message: str
    wait_seconds: float = 0.0
    is_fatal: bool = False


class APIClient:
    def __init__(self, tokens_per_minute: int = 6000, calls_per_minute: int = 30,
                 daily_calls: int = 1000):
        # Límites
        self.MAX_TOKENS_PER_MINUTE = tokens_per_minute
        self.MAX_CALLS_PER_MINUTE = calls_per_minute
        self.MAX_DAILY_CALLS = daily_calls

        # Trackers
        self.daily_calls_count = 0
        self.last_daily_reset = datetime.now()
        self.call_history = deque()  # Stores (timestamp: float, tokens_used: int)

        # Tokenizer (Removed as it was commented out and not used)
        # If you plan to use a tokenizer, you can re-add it here.
        # self.tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-32B")

    def _reset_daily_counter(self) -> None:
        """Reinicia el contador diario de llamadas si ha pasado la medianoche."""
        now = datetime.now()
        if now.date() != self.last_daily_reset.date():
            self.daily_calls_count = 0
            self.last_daily_reset = now
            logging.info("Contador diario de llamadas API reiniciado.")

    def _check_limits(self, required_tokens: int) -> list[APIRateLimitIssue]:
        """
        Verifica todos los límites de la API y devuelve una lista de los problemas detectados.
        """
        self._reset_daily_counter()
        now_timestamp = time.time()
        issues: list[APIRateLimitIssue] = []

        # 1. Limpiar llamadas antiguas del historial (más de SECONDS_IN_MINUTE)
        while self.call_history and (now_timestamp - self.call_history[0][0] > SECONDS_IN_MINUTE):
            self.call_history.popleft()

        # 2. Calcular métricas actuales para la última ventana de un minuto
        current_minute_tokens = sum(call_data[1] for call_data in self.call_history)
        current_minute_calls = len(self.call_history)

        # 3. Verificar límite diario de llamadas
        if self.daily_calls_count >= self.MAX_DAILY_CALLS:
            # Calculate time until next day's midnight
            tomorrow = datetime.now() + timedelta(days=1)
            next_reset_time = datetime.combine(tomorrow.date(), datetime.min.time())
            wait_seconds = (next_reset_time - datetime.now()).total_seconds()
            issues.append(APIRateLimitIssue(
                issue_type=APILimitType.DAILY_CALLS,
                message=(f"Límite diario de {self.MAX_DAILY_CALLS} llamadas alcanzado. "
                         f"Esperar {wait_seconds:.1f}s para el reseteo a medianoche."),
                wait_seconds=wait_seconds
            ))

        # 4. Verificar límite de llamadas por minuto
        if current_minute_calls >= self.MAX_CALLS_PER_MINUTE:
            if self.call_history:  # Should be true if current_minute_calls > 0
                oldest_call_timestamp = self.call_history[0][0]
                # Wait until the oldest call is older than SECONDS_IN_MINUTE
                wait_seconds = max(0, (
                            oldest_call_timestamp + SECONDS_IN_MINUTE) - now_timestamp + MIN_API_SLEEP_INTERVAL_SECONDS)
                issues.append(APIRateLimitIssue(
                    issue_type=APILimitType.CALLS_PER_MINUTE,
                    message=(
                        f"Límite de {self.MAX_CALLS_PER_MINUTE} llamadas/minuto alcanzado ({current_minute_calls} llamadas). "
                        f"Esperar {wait_seconds:.1f}s."),
                    wait_seconds=wait_seconds
                ))
            # else: If MAX_CALLS_PER_MINUTE is 0, this might trigger with no history.
            # However, MAX_CALLS_PER_MINUTE is expected to be > 0.

        # 5. Verificar límite de tokens por minuto
        potential_total_tokens = current_minute_tokens + required_tokens
        if required_tokens > 0 and potential_total_tokens > self.MAX_TOKENS_PER_MINUTE:
            if required_tokens > self.MAX_TOKENS_PER_MINUTE:
                # This single call exceeds the total per-minute token limit
                message = (f"La llamada actual requiere {required_tokens} tokens, lo cual excede el límite "
                           f"de {self.MAX_TOKENS_PER_MINUTE} tokens/minuto. Esta llamada no puede procesarse.")
                issues.append(APIRateLimitIssue(
                    issue_type=APILimitType.TOKENS_PER_CALL_EXCEEDED,
                    message=message,
                    is_fatal=True
                ))
            elif self.call_history:  # Not fatal, but over limit due to existing calls
                oldest_call_timestamp = self.call_history[0][0]
                # Wait until the oldest call (and its tokens) expires from the window
                wait_seconds = max(0, (
                            oldest_call_timestamp + SECONDS_IN_MINUTE) - now_timestamp + MIN_API_SLEEP_INTERVAL_SECONDS)
                message = (f"Límite de {self.MAX_TOKENS_PER_MINUTE} tokens/minuto sería excedido "
                           f"({potential_total_tokens} tokens con la llamada actual). "
                           f"Esperar {wait_seconds:.1f}s para liberar tokens.")
                issues.append(APIRateLimitIssue(
                    issue_type=APILimitType.TOKENS_PER_MINUTE,
                    message=message,
                    wait_seconds=wait_seconds
                ))
            # else: No call history, current_minute_tokens is 0.
            # So, (0 + required_tokens) > MAX_TOKENS_PER_MINUTE means required_tokens > MAX_TOKENS_PER_MINUTE.
            # This case is covered by the `required_tokens > self.MAX_TOKENS_PER_MINUTE` fatal error check above.

        return issues

    def wait_if_needed(self, required_tokens: int = 0) -> bool:
        """
        Verifica si la llamada API puede proceder según los límites de tasa.
        Espera si es necesario y registra la llamada si procede.

        Args:
            required_tokens: El número estimado de tokens que consumirá la llamada.

        Returns:
            bool: True si la llamada puede proceder (después de esperar si fue necesario),
                  False si la llamada no puede proceder (p.ej., requiere demasiados tokens
                  que exceden el límite por sí sola, u otro error fatal).
        """
        while True:
            issues = self._check_limits(required_tokens)

            if not issues:
                break  # No issues, limits are OK. Proceed.

            # Check for any fatal issues
            fatal_issues = [issue for issue in issues if issue.is_fatal]
            if fatal_issues:
                for issue in fatal_issues:
                    logging.error(f"Error fatal de límite API: {issue.message}")
                return False  # Cannot proceed

            # If here, all issues are non-fatal and require waiting.
            # Calculate the maximum wait time suggested by the issues.
            wait_times = [issue.wait_seconds for issue in issues if issue.wait_seconds > 0]

            sleep_time: float
            if not wait_times:
                # This might happen if issues were reported but with 0 wait_seconds (e.g., limit just cleared).
                # Or if an issue type was missed in wait_seconds population (bug).
                # Default to a small retry sleep to avoid busy loop if state hasn't quite updated.
                logging.warning(
                    "Problema de límite API detectado sin tiempo de espera específico o tiempo de espera cero. "
                    f"Esperando {DEFAULT_API_RETRY_SLEEP_SECONDS:.1f}s por defecto."
                )
                sleep_time = DEFAULT_API_RETRY_SLEEP_SECONDS
            else:
                sleep_time = max(wait_times)

            # Ensure a minimum sleep duration to prevent rapid, no-op loops and handle precision.
            sleep_time = max(MIN_API_SLEEP_INTERVAL_SECONDS, sleep_time)

            issue_messages = [issue.message for issue in issues]
            logging.info(
                f"Límite(s) API alcanzado(s). Esperando {sleep_time:.1f}s. "
                f"Motivos: {'; '.join(issue_messages)}"
            )
            time.sleep(sleep_time)
            # Loop will continue and _check_limits() will be called again to re-evaluate.

        # If loop exited, limits are met. Record the call.
        self.daily_calls_count += 1
        self.call_history.append((time.time(), required_tokens))
        # logging.debug(f"API call permitted. Daily calls: {self.daily_calls_count}, History size: {len(self.call_history)}")
        return True  # Indicate that the call can proceed