"""Interactive voice companion card for the cockpit."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout


class CompanionCard(QFrame):
    """Shows conversation state and exposes voice/text input."""

    listen_requested = Signal()
    text_submitted = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("companionCard")
        self.setFixedSize(500, 300)
        self.setStyleSheet(
            """
            QFrame#companionCard { background: rgba(2, 14, 20, 235); border: 1px solid #2addec;
                border-radius: 8px; color: #eaffff; }
            QLabel#companionTitle { color: #78f4ff; font-size: 14px; font-weight: 800; }
            QFrame#voiceBox { background: rgba(5, 27, 34, 210); border: 1px solid rgba(57, 231, 245, 90);
                border-radius: 8px; }
            QLabel#boxTitle { color: #78f4ff; font-size: 11px; font-weight: 800; }
            QLabel#voiceInputText { color: #d7fbff; font-size: 14px; }
            QLabel#audioTranscriptText { color: #effeff; font-size: 14px; }
            QLabel#companionStatus { color: #87b9c0; font-size: 11px; }
            QPushButton { background: #0b3d48; border: 1px solid #39e7f5; border-radius: 20px;
                color: white; font-size: 13px; font-weight: 700; min-width: 52px; min-height: 40px; }
            QPushButton:checked { background: #d64f68; border-color: #ff8c9c; }
            QPushButton:disabled { color: #607c81; border-color: #315158; }
            QLineEdit { background: #061e26; border: 1px solid #285d66; border-radius: 8px;
                color: white; padding: 8px; }
            """
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 13, 16, 13)
        root.setSpacing(7)

        title = QLabel("UVI AUDIO COMPANION")
        title.setObjectName("companionTitle")
        root.addWidget(title)
        self.text_audio_text = self._build_voice_box(
            root,
            "TEXT TO AUDIO",
            "Typed text will play as audio.",
            "voiceInputText",
        )
        self.audio_text = self._build_voice_box(
            root,
            "AUDIO TO TEXT",
            "Tap MIC and speak to see text here.",
            "audioTranscriptText",
        )
        self.status = QLabel("Ready - type text for audio output")
        self.status.setObjectName("companionStatus")

        controls = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Type here if the cabin is noisy...")
        self.input.returnPressed.connect(self._send_text)
        self.mic = QPushButton("MIC")
        self.mic.setToolTip("Talk to UVI")
        self.mic.setCheckable(True)
        self.mic.clicked.connect(self.listen_requested.emit)
        controls.addWidget(self.input, 1)
        controls.addWidget(self.mic)

        root.addWidget(self.status)
        root.addLayout(controls)

    def _build_voice_box(self, root: QVBoxLayout, title: str, text: str, text_object_name: str) -> QLabel:
        box = QFrame()
        box.setObjectName("voiceBox")
        box_layout = QVBoxLayout(box)
        box_layout.setContentsMargins(10, 8, 10, 8)
        box_layout.setSpacing(4)

        heading = QLabel(title)
        heading.setObjectName("boxTitle")

        body = QLabel(text)
        body.setObjectName(text_object_name)
        body.setWordWrap(True)
        body.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        body.setMinimumHeight(44)

        box_layout.addWidget(heading)
        box_layout.addWidget(body, 1)
        root.addWidget(box, 1)
        return body

    def _send_text(self) -> None:
        text = self.input.text().strip()
        if text:
            print(f"[UVI UI] textbox submitted -> {text}", flush=True)
            self.input.clear()
            self.text_submitted.emit(text)

    def show_user_text(self, text: str) -> None:
        self.audio_text.setText(text)

    def show_text_audio_input(self, text: str) -> None:
        self.text_audio_text.setText("Input sent to audio interface")

    def show_companion_text(self, text: str) -> None:
        self.status.setText("LLM output received for voice playback")

    def set_status(self, text: str) -> None:
        self.status.setText(text)

    def set_listening(self, active: bool) -> None:
        self.mic.setChecked(active)
        self.mic.setText("STOP" if active else "MIC")
        self.mic.setEnabled(not active)
