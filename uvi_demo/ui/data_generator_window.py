"""Standalone data generator simulator window."""

from __future__ import annotations

from PySide6.QtWidgets import QMainWindow

from uvi_demo.simulator.episode_data_generator import EpisodeDataGenerator
from uvi_demo.ui.cockpit_screen import SimulatorPanel


class DataGeneratorWindow(QMainWindow):
    """Top-level UI for selecting and playing episode scripts."""

    def __init__(self, generator: EpisodeDataGenerator) -> None:
        super().__init__()
        self.setWindowTitle("UVI Data Generator Simulator")
        self.setMinimumSize(460, 390)
        self.setStyleSheet(
            """
            QMainWindow {
                background: #05080c;
                color: #e7fbff;
                font-family: Segoe UI;
            }
            QFrame#simulatorPanel {
                background: rgba(3, 12, 18, 245);
                border: 1px solid rgba(71, 227, 245, 120);
                border-radius: 8px;
            }
            QLabel#panelTitle {
                color: #87f2ff;
                font-size: 13px;
                font-weight: 800;
            }
            QLabel#smallText {
                color: #b1d8dd;
                font-size: 12px;
            }
            QComboBox, QListWidget {
                background: #06131a;
                border: 1px solid #16444f;
                border-radius: 6px;
                color: #dffbff;
                font-size: 12px;
            }
            QPushButton#simButton {
                background: #0b2b34;
                border: 1px solid #38dceb;
                border-radius: 6px;
                color: #eafbff;
                font-size: 12px;
                font-weight: 800;
                padding: 7px 10px;
            }
            QPushButton#simButton:hover {
                background: #124250;
            }
            QProgressBar {
                background: #06131a;
                border: 1px solid #16444f;
                border-radius: 5px;
                color: #eafbff;
                text-align: center;
                height: 14px;
            }
            QProgressBar::chunk {
                background: #38dceb;
                border-radius: 4px;
            }
            """
        )
        panel = SimulatorPanel(generator)
        panel.setFixedSize(430, 350)
        self.setCentralWidget(panel)
