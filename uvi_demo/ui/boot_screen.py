"""Boot sequence UI for KL15 ignition and HPC startup."""

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from uvi_demo.ui.cockpit_screen import CockpitScreen


BOOT_STEPS = [
    "KL15 ON",
    "Booting Linux HPC...",
    "Starting Execution Manager...",
    "Reading Service Manifest...",
    "Starting Mock CAN Gateway...",
    "Starting KUKSA Data Broker...",
    "Starting Producer Services...",
    "Starting Dashboard Application...",
    "Starting UVI Companion...",
]


class BootScreen(QMainWindow):
    """Fullscreen ignition and boot shell."""

    def __init__(self, cockpit_screen: QWidget | None = None) -> None:
        super().__init__()
        self.setWindowTitle("Unified Vehicle Intelligence")
        self._step_index = 0

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.boot_page = QWidget()
        self.boot_page.setObjectName("bootPage")
        self.boot_page.setStyleSheet(
            """
            #bootPage {
                background: #05080c;
                color: #e7fbff;
                font-family: Segoe UI;
            }
            QLabel#title {
                font-size: 38px;
                font-weight: 700;
            }
            QLabel#subtitle {
                color: #7dcbd3;
                font-size: 16px;
            }
            QFrame#panel {
                background: rgba(10, 20, 28, 210);
                border: 1px solid #123844;
                border-radius: 8px;
            }
            QListWidget {
                background: transparent;
                border: none;
                color: #83aeb7;
                font-size: 16px;
                outline: none;
            }
            QListWidget::item {
                padding: 8px 0;
            }
            QListWidget::item:selected {
                color: #7ff4ff;
                background: transparent;
            }
            QPushButton#keyButton {
                background: #06151c;
                border: 2px solid #26d9e8;
                border-radius: 46px;
                color: #bdfaff;
                font-size: 18px;
                font-weight: 700;
            }
            QPushButton#keyButton:hover {
                background: #0b2530;
            }
            """
        )

        root = QVBoxLayout(self.boot_page)
        root.setContentsMargins(64, 54, 64, 42)
        root.setSpacing(28)

        header = QVBoxLayout()
        title = QLabel("Unified Vehicle Intelligence")
        title.setObjectName("title")
        subtitle = QLabel("Linux HPC cockpit boot environment")
        subtitle.setObjectName("subtitle")
        header.addWidget(title)
        header.addWidget(subtitle)
        root.addLayout(header)

        panel = QFrame()
        panel.setObjectName("panel")
        panel_shadow = QGraphicsDropShadowEffect()
        panel_shadow.setBlurRadius(40)
        panel_shadow.setColor(QColor(0, 210, 230, 70))
        panel_shadow.setOffset(0, 0)
        panel.setGraphicsEffect(panel_shadow)

        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(28, 24, 28, 24)
        panel_title = QLabel("Execution Manager")
        panel_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self.steps_list = QListWidget()
        for step in BOOT_STEPS:
            self.steps_list.addItem(QListWidgetItem(f"○ {step}"))
        panel_layout.addWidget(panel_title)
        panel_layout.addWidget(self.steps_list)
        root.addWidget(panel, stretch=1)

        footer = QHBoxLayout()
        footer.addStretch(1)
        self.key_button = QPushButton("KL15")
        self.key_button.setObjectName("keyButton")
        self.key_button.setFixedSize(96, 96)
        self.key_button.clicked.connect(self.start_boot)
        footer.addWidget(self.key_button, alignment=Qt.AlignmentFlag.AlignRight)
        root.addLayout(footer)

        self.stack.addWidget(self.boot_page)
        self.stack.addWidget(cockpit_screen or CockpitScreen())

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.advance_boot)

    def start_boot(self) -> None:
        """Begin the mock KL15 boot sequence."""
        self.key_button.setEnabled(False)
        self.key_button.setText("ON")
        self._step_index = 0
        self.timer.start(520)

    def advance_boot(self) -> None:
        """Advance one boot step and switch to cockpit when complete."""
        if self._step_index >= len(BOOT_STEPS):
            self.timer.stop()
            self.stack.setCurrentIndex(1)
            return

        item = self.steps_list.item(self._step_index)
        item.setText(f"● {BOOT_STEPS[self._step_index]}")
        self.steps_list.setCurrentRow(self._step_index)
        self._step_index += 1
