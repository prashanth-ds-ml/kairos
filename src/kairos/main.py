from pathlib import Path

from PySide6.QtWidgets import QApplication

from .storage import JsonStore
from .ui import MainWindow


def main() -> None:
    data_dir = Path(__file__).resolve().parents[2] / "data"
    app = QApplication([])
    window = MainWindow(JsonStore(data_dir))
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
