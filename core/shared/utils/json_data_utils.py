import json
import os
from datetime import datetime


def save_log_to_json(
    log_data: str, filename: str = "./core/brevio_api/logs/logs.json"
) -> None:
    log_data = json.loads(log_data)

    if not isinstance(log_data, dict):
        raise ValueError("log_data must be a JSON object (dictionary).")

    log_data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = log_data

    log_dir = os.path.dirname(os.path.abspath(filename))
    os.makedirs(log_dir, exist_ok=True)

    existing_logs = []

    if os.path.exists(filename) and os.path.getsize(filename) > 0:
        try:
            with open(filename, "r", encoding="utf-8") as f:
                file_content = f.read().strip()
                if file_content:  # Verificar que no esté vacío
                    existing_logs = json.loads(file_content)
                    if not isinstance(existing_logs, list):
                        existing_logs = [existing_logs]
        except Exception as e:
            print(f"Error al leer {filename}: {str(e)}. Inicializando nuevo archivo.")

    existing_logs.append(log_entry)

    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(existing_logs, f, indent=4, ensure_ascii=False)
        print(
            f"Log añadido exitosamente a {filename}. Total logs: {len(existing_logs)}"
        )
    except Exception as e:
        print(f"Error al guardar en {filename}: {str(e)}")
