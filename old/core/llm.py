import json
from pathlib import Path
from litellm import completion
from core.file_io import FilesystemFileReader, FilesystemFileWriter


CONFIG_DIR = Path.home() / ".sential"
CONFIG_FILE = CONFIG_DIR / "settings.json"


def get_config_file():
    if not CONFIG_FILE.exists():
        return {}
    file_content = FilesystemFileReader().read_file(CONFIG_FILE)
    return json.loads(file_content)


def save_config(model: str, api_key: str):
    CONFIG_DIR.mkdir(exist_ok=True)
    fw = FilesystemFileWriter(CONFIG_FILE)
    data = json.dumps({"model": model, "api_key": api_key})
    fw.write_file(data)


def ask_llm(model_name: str, api_key: str, prompt: str) -> str:
    # Pass the key directly here
    response = completion(
        model=model_name,
        messages=[{"role": "system", "content": prompt}],
        api_key=api_key,
        num_retries=3,
    )
    return response.choices[0].message.content
