"""Application entry point for the UVI demo."""

from PySide6.QtWidgets import QApplication

from uvi_demo.ui.boot_screen import BootScreen


def main() -> None:
    """Start the Phase 1 demo application."""
    app = QApplication([])
    window = BootScreen()
    window.showFullScreen()
    app.exec()


if __name__ == "__main__":
    main()
