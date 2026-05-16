from pathlib import Path
import sys

from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from .qml_controller import KairosController
from .storage import create_store


def main() -> None:
    data_dir = Path(__file__).resolve().parents[2] / "data"
    app = QGuiApplication(sys.argv)
    controller = KairosController(create_store(data_dir))
    sync_timer = QTimer()
    sync_timer.setInterval(30000)
    sync_timer.timeout.connect(controller.refresh)
    sync_timer.start()
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("kairos", controller)
    engine.load(Path(__file__).resolve().parent / "qml" / "Main.qml")
    if not engine.rootObjects():
        raise SystemExit(1)
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
