import os

import requests
import json
import csv

API_URL = "https://openrouter.ai/api/v1/models"
API_KEY = os.getenv("OPEN_ROUTER_API_KEY")  # Si tienes una clave, reemplaza por tu API key como string

def fetch_all_models():
    headers = {}
    if API_KEY:
        headers["Authorization"] = API_KEY

    try:
        response = requests.get(API_URL, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("data", [])
    except requests.exceptions.RequestException as e:
        print(f"Error al conectar con OpenRouter: {e}")
        return []

def is_model_free(model):
    if model.get("id", "").endswith(":free"):
        return True
    pricing = model.get("pricing", {})
    # Consideramos "gratis" si el precio es 0 o no está definido
    for key in ["prompt", "completion", "request", "image", "web_search", "internal_reasoning"]:
        value = pricing.get(key)
        if value not in (0, "0", None):
            return False
    return True

def list_free_models(min_context_length=0):
    models = fetch_all_models()
    free_models = []
    for model in models:
        context_len = model.get("context_length", 0)
        if is_model_free(model) and context_len >= min_context_length:
            free_models.append({
                "id": model.get("id"),
                "name": model.get("name", "n/a"),
                "context_length": context_len,
                "description": model.get("description", ""),
                "inputs":model.get("architecture", {}).get("input_modalities",[]),
                "output":model.get("architecture", {}).get("output_modalities",[]),
                "tokenizer":model.get("architecture", {}).get("tokenizer", ""),
                "supported_parameters":model.get("supported_parameters", [])
            })
    return free_models

def export_to_json(models, filename="modelos_free.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(models, f, indent=2, ensure_ascii=False)

def export_to_csv(models, filename="modelos_free.csv"):
    with open(filename, "w", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=models[0].keys())
        writer.writeheader()
        writer.writerows(models)

def main():
    min_ctx = 32000  # ← Puedes ajustar este valor
    free_models = list_free_models(min_context_length=min_ctx)

    print(f"\n🔎 Se encontraron {len(free_models)} modelos gratuitos con al menos {min_ctx} tokens de contexto:\n")
    for model in free_models:
        print(f"- {model['id']} ({model['context_length']} tokens)")

    # Exportar si quieres
    export_to_json(free_models)
    export_to_csv(free_models)
    print("\n📁 Modelos exportados a 'modelos_free.json' y 'modelos_free.csv'.")

if __name__ == "__main__":
    main()