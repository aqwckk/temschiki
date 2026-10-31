import sys

from app.config import settings

# модули эмуляторов импортируют друг друга как top-level (from core import ...),
# sys.path учитывает только строки
_emulators_path = str(settings.emulators_dir)
if _emulators_path not in sys.path:
    sys.path.insert(0, _emulators_path)
