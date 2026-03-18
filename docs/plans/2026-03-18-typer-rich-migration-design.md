# Design: Migrar argparse a Typer + Rich

## Objetivo
Convertir el CLI basado en argparse a Typer con Rich para una mejor experiencia de usuario.

## Decisión de Configuración
- **Solo CLI**: Eliminar dependencia de config.json, todos los valores se pasan por CLI con valores por defecto
- **Rich completo**: Barra de progreso, colores, tablas de resumen

## Cambios

### 1. Dependencias
Agregar a requirements.txt:
```
typer[all]>=0.9.0
```

### 2. GlobalConfig.py
- Eliminar método `update_from_args()`
- Simplificar para solo manejar valores por defecto
- Mantener como singleton para compatibilidad con otros módulos

### 3. PDFAgent.py
Reemplazar argparse con Typer:

```python
import typer
from rich.console import Console
from rich.progress import Progress
from rich.table import Table

app = typer.Typer()
console = Console()

@app.command()
def main(
    input_path: Path = typer.Argument(..., help="Path to directory or file"),
    source_lang: str = typer.Option("en-US", "--source-lang", "-sl"),
    target_lang: str = typer.Option("es-MX", "--target-lang", "-tl"),
    output_format: str = typer.Option("m4a", "--format", "-f"),
    voice: str = typer.Option("Paulina", "--voice"),
    gen_video: bool = typer.Option(False, "--gen-video"),
    agent: str = typer.Option("nvidia", "--agent", "-a"),
):
```

### 4. Features de Rich
- **Consola**: `console.print()` con colores para mensajes
- **Progreso**: `rich.progress.Progress` para iterar sobre archivos
- **Tabla resumen**: `rich.table.Table` para mostrar estadísticas finales
- **Logging**: `rich.logging.RichHandler` para logs en archivo

## Argumentos CLI Finales
| Argumento | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| input_path | Path | (requerido) | Archivo o directorio a procesar |
| --source-lang, -sl | str | en-US | Idioma origen |
| --target-lang, -tl | str | es-MX | Idioma destino |
| --format, -f | str | m4a | Formato de salida (m4a, mp3, aiff, wav) |
| --voice | str | Paulina | Voz macOS para el idioma destino |
| --gen-video | bool | False | Generar video |
| --agent, -a | str | nvidia | Agente de traducción (nvidia, gemini, ollama) |

## Archivos a Modificar
1. `requirements.txt` - agregar typer[all]
2. `GlobalConfig.py` - eliminar update_from_args, simplificar
3. `PDFAgent.py` - migrar argparse a typer + rich
