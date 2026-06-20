"""Premium EV cockpit screen with layered motion simulation."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QPolygonF, QRadialGradient
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget


ASSET_DIR = Path(__file__).resolve().parents[1] / "assets"
DRIVE_LOOP_CANDIDATES = (
    ASSET_DIR / "drive_loop.mp4",
    ASSET_DIR / "drive_loop.mp4.mp4",
)
DRIVE_LOOP = next((path for path in DRIVE_LOOP_CANDIDATES if path.exists()), DRIVE_LOOP_CANDIDATES[0])


@dataclass
class SimulationState:
    """Synthetic vehicle state driving the cockpit scene."""

    tick: int = 0
    speed: float = 0.0
    target_speed: float = 78.0
    battery: float = 82.0
    range_km: float = 314.0
    lane_phase: float = 0.0
    traffic_phase: float = 0.0
    steering: float = 0.0
    rain: float = 0.0
    wiper_phase: float = 0.0
    companion_message: str = "Route clear. Watching range, traffic, and road conditions."

    @property
    def speed_factor(self) -> float:
        return min(max(self.speed / 110.0, 0.0), 1.0)

    def advance(self) -> None:
        self.tick += 1
        t = self.tick / 24.0
        self.target_speed = 48.0 + 7.0 * math.sin(t / 6.8) + 2.5 * math.sin(t / 2.4)
        self.speed += (self.target_speed - self.speed) * 0.04
        self.steering = 4.5 * math.sin(t / 4.8) + 1.5 * math.sin(t / 1.9)
        self.lane_phase = (self.lane_phase + max(self.speed, 10.0) * 0.0022) % 1.0
        self.traffic_phase = (self.traffic_phase + max(self.speed, 10.0) * 0.00085) % 1.0
        self.rain = max(0.0, math.sin(t / 9.5) * 0.85)
        self.wiper_phase = (self.wiper_phase + 0.015 + self.rain * 0.055) % 1.0
        self.battery = max(0.0, self.battery - 0.001 - self.speed * 0.00001)
        self.range_km = max(0.0, self.range_km - self.speed * 0.000034)

        if self.rain > 0.48:
            self.companion_message = "Rain building. Visibility and traction are being monitored."
        elif self.speed > 86:
            self.companion_message = "Open stretch ahead. Holding a smooth energy profile."
        else:
            self.companion_message = "Traffic flow stable. Keeping lane assist and range in view."


class CockpitScreen(QWidget):
    """Layered cockpit: outside world, interior foreground, live HUD."""

    def __init__(self) -> None:
        super().__init__()
        self.state = SimulationState()
        self.setObjectName("cockpit")
        self.setStyleSheet(
            """
            #cockpit {
                background: #030507;
                color: #eafbff;
                font-family: Segoe UI;
            }
            QFrame#glassPanel {
                background: rgba(2, 12, 18, 155);
                border: 1px solid rgba(71, 227, 245, 120);
                border-radius: 8px;
            }
            QLabel#panelTitle {
                color: #87f2ff;
                font-size: 12px;
                font-weight: 800;
            }
            QLabel#panelValue {
                color: #f2feff;
                font-size: 19px;
                font-weight: 700;
            }
            QLabel#speedReadout {
                color: #7ff4ff;
                font-size: 56px;
                font-weight: 900;
            }
            QLabel#smallText {
                color: #b1d8dd;
                font-size: 12px;
            }
            """
        )

        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(0)
        layout.setVerticalSpacing(0)

        has_video = DRIVE_LOOP.exists()
        if has_video:
            self.video_backdrop = DriveVideoBackdrop(DRIVE_LOOP)
            layout.addWidget(self.video_backdrop, 0, 0, 2, 4)
            layout.setRowStretch(0, 5)
            layout.setRowStretch(1, 1)
            layout.setRowStretch(2, 4)
            self.canvas = LayeredCockpitCanvas(self.state, cockpit_foreground_only=True)
            layout.addWidget(self.canvas, 2, 0, 1, 4)
        else:
            self.canvas = LayeredCockpitCanvas(self.state)
            layout.addWidget(self.canvas, 0, 0, 3, 4)

        self.cluster = InstrumentCluster(self.state)
        layout.addWidget(self.cluster, 2, 0, 1, 2, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)

        self.display = PanoramicDisplay(self.state)
        layout.addWidget(self.display, 1, 2, 1, 2, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._advance_simulation)
        self.timer.start(33)

    def _advance_simulation(self) -> None:
        self.state.advance()
        self.canvas.update()
        self.cluster.refresh()
        self.display.refresh()


class DriveVideoBackdrop(QVideoWidget):
    """Native video playback layer for smooth windshield motion."""

    def __init__(self, drive_loop: Path) -> None:
        super().__init__()
        self.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatioByExpanding)
        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.audio.setVolume(0.0)
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self)
        self.player.setSource(QUrl.fromLocalFile(str(drive_loop)))
        self.player.setPlaybackRate(0.72)
        self.player.setLoops(QMediaPlayer.Loops.Infinite)
        self.player.mediaStatusChanged.connect(self._loop_video)
        self.player.play()

    def _loop_video(self, status) -> None:
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.player.setPosition(0)
            self.player.play()


class LayeredCockpitCanvas(QWidget):
    """Paints separate moving exterior and fixed cockpit foreground."""

    def __init__(self, state: SimulationState, cockpit_foreground_only: bool = False) -> None:
        super().__init__()
        self.state = state
        self.cockpit_foreground_only = cockpit_foreground_only
        self.setMinimumSize(1000, 620)
        if self.cockpit_foreground_only:
            self.setMinimumHeight(310)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.cockpit_foreground_only:
            self._paint_native_video_cockpit_foreground(painter)
        else:
            self._paint_exterior(painter)
            self._paint_backward_traffic(painter)
            self._paint_hud(painter)
            self._paint_weather(painter)
            self._paint_cockpit_foreground(painter)
            self._paint_vignette(painter)
        painter.end()

    def _paint_native_video_cockpit_foreground(self, painter: QPainter) -> None:
        width = self.width()
        height = self.height()
        gradient = QLinearGradient(0, 0, 0, height)
        gradient.setColorAt(0.0, QColor(18, 24, 27))
        gradient.setColorAt(0.2, QColor(8, 12, 15))
        gradient.setColorAt(0.58, QColor(3, 5, 7))
        gradient.setColorAt(1.0, QColor(1, 2, 3))
        painter.fillRect(self.rect(), gradient)

        top_edge = QPainterPath()
        top_edge.moveTo(0, height * 0.1)
        top_edge.cubicTo(width * 0.25, height * 0.0, width * 0.56, height * 0.07, width, height * 0.02)
        top_edge.lineTo(width, height * 0.26)
        top_edge.cubicTo(width * 0.72, height * 0.22, width * 0.36, height * 0.28, 0, height * 0.33)
        top_edge.closeSubpath()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(16, 20, 23, 245))
        painter.drawPath(top_edge)

        painter.setPen(QPen(QColor(230, 235, 236, 130), 4))
        painter.drawLine(QPointF(width * 0.05, height * 0.21), QPointF(width * 0.96, height * 0.12))
        painter.setPen(QPen(QColor(26, 220, 245, 150), 2))
        painter.drawLine(QPointF(width * 0.04, height * 0.28), QPointF(width * 0.96, height * 0.19))

        vent_path = QPainterPath()
        vent_path.moveTo(width * 0.36, height * 0.38)
        vent_path.lineTo(width * 0.94, height * 0.25)
        vent_path.lineTo(width * 0.92, height * 0.43)
        vent_path.lineTo(width * 0.34, height * 0.56)
        vent_path.closeSubpath()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(8, 12, 15, 230))
        painter.drawPath(vent_path)
        painter.setPen(QPen(QColor(55, 66, 70, 150), 1))
        for offset in range(8):
            y = height * (0.41 + offset * 0.015)
            painter.drawLine(QPointF(width * 0.39, y), QPointF(width * 0.9, y - height * 0.11))

        self._paint_embedded_cluster(painter, QRectF(width * 0.12, height * 0.14, width * 0.27, height * 0.34))
        self._paint_modern_ivi(painter, QRectF(width * 0.48, height * 0.22, width * 0.45, height * 0.38))

        painter.save()
        painter.translate(width * 0.26, height * 0.62)
        painter.rotate(self.state.steering * 0.42)
        scale = min(width / 1350.0, height / 300.0)
        painter.scale(scale, scale)
        rim = QRectF(-210, -170, 420, 330)
        painter.setPen(QPen(QColor(8, 11, 13), 34))
        painter.drawEllipse(rim)
        painter.setPen(QPen(QColor(42, 214, 245, 160), 9))
        painter.drawArc(rim, 25 * 16, 130 * 16)
        painter.setPen(QPen(QColor(22, 27, 31), 28))
        painter.drawLine(QPointF(0, 0), QPointF(-150, 92))
        painter.drawLine(QPointF(0, 0), QPointF(150, 92))
        painter.drawLine(QPointF(0, 0), QPointF(0, 126))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(10, 14, 17))
        painter.drawEllipse(QRectF(-76, -56, 152, 112))
        painter.setBrush(QColor(47, 220, 245, 190))
        painter.drawEllipse(QRectF(-31, -31, 62, 62))
        painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        painter.setPen(QColor(1, 12, 16))
        painter.drawText(QRectF(-31, -18, 62, 36), Qt.AlignmentFlag.AlignCenter, "UVI")
        painter.restore()

        glow = QRadialGradient(QPointF(width * 0.62, height * 0.1), width * 0.55)
        glow.setColorAt(0.0, QColor(45, 215, 245, 22))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillRect(self.rect(), glow)

    def _paint_embedded_cluster(self, painter: QPainter, rect: QRectF) -> None:
        painter.setPen(QPen(QColor(55, 226, 245, 110), 1.4))
        painter.setBrush(QColor(3, 16, 22, 230))
        painter.drawRoundedRect(rect, 10, 10)

        center = rect.center()
        radius = min(rect.width(), rect.height()) * 0.34
        base = QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2)
        painter.setPen(QPen(QColor(46, 70, 78, 175), 7))
        painter.drawArc(base, 210 * 16, -240 * 16)
        painter.setPen(QPen(QColor(75, 235, 255, 220), 7))
        speed_span = -240 * min(self.state.speed / 120.0, 1.0)
        painter.drawArc(base, 210 * 16, int(speed_span * 16))

        painter.setFont(QFont("Segoe UI", max(16, int(rect.height() * 0.26)), QFont.Weight.Bold))
        painter.setPen(QColor(235, 253, 255))
        painter.drawText(base, Qt.AlignmentFlag.AlignCenter, f"{self.state.speed:02.0f}")
        painter.setFont(QFont("Segoe UI", max(8, int(rect.height() * 0.06)), QFont.Weight.Bold))
        painter.setPen(QColor(135, 205, 212))
        painter.drawText(rect.adjusted(0, rect.height() * 0.28, 0, 0), Qt.AlignmentFlag.AlignHCenter, "km/h")

        battery = QRectF(rect.left() + rect.width() * 0.08, rect.bottom() - rect.height() * 0.22, rect.width() * 0.36, rect.height() * 0.055)
        painter.setPen(QPen(QColor(75, 105, 112), 1.2))
        painter.setBrush(QColor(4, 10, 13))
        painter.drawRoundedRect(battery, 3, 3)
        fill = QRectF(battery)
        fill.setWidth(battery.width() * self.state.battery / 100.0)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(83, 238, 184))
        painter.drawRoundedRect(fill, 3, 3)

        painter.setFont(QFont("Segoe UI", max(8, int(rect.height() * 0.08)), QFont.Weight.Bold))
        painter.setPen(QColor(198, 244, 248))
        painter.drawText(QRectF(rect.left() + rect.width() * 0.5, battery.top() - 4, rect.width() * 0.42, rect.height() * 0.1), Qt.AlignmentFlag.AlignRight, f"{self.state.range_km:03.0f} km")

    def _paint_modern_ivi(self, painter: QPainter, rect: QRectF) -> None:
        painter.setPen(QPen(QColor(58, 226, 245, 95), 1.5))
        painter.setBrush(QColor(4, 18, 24, 218))
        painter.drawRoundedRect(rect, 10, 10)

        painter.setFont(QFont("Segoe UI", max(10, int(rect.height() * 0.12)), QFont.Weight.Bold))
        painter.setPen(QColor(134, 245, 255, 220))
        painter.drawText(rect.adjusted(18, 10, -18, -10), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, "UVI Intelligent Drive")

        tile_gap = rect.width() * 0.025
        tile_top = rect.top() + rect.height() * 0.33
        tile_h = rect.height() * 0.42
        tile_w = (rect.width() - tile_gap * 5) / 4
        tiles = [
            ("ENERGY", f"{self.state.battery:02.0f}%"),
            ("RANGE", f"{self.state.range_km:03.0f} km"),
            ("ADAS", "Lane Active"),
            ("WEATHER", "Rain" if self.state.rain > 0.48 else "Clear"),
        ]
        for index, (title, value) in enumerate(tiles):
            tile = QRectF(rect.left() + tile_gap + index * (tile_w + tile_gap), tile_top, tile_w, tile_h)
            painter.setPen(QPen(QColor(60, 118, 128, 150), 1))
            painter.setBrush(QColor(6, 28, 35, 185))
            painter.drawRoundedRect(tile, 7, 7)
            painter.setFont(QFont("Segoe UI", max(7, int(rect.height() * 0.07)), QFont.Weight.Bold))
            painter.setPen(QColor(125, 203, 211))
            painter.drawText(tile.adjusted(10, 8, -10, -8), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, title)
            painter.setFont(QFont("Segoe UI", max(9, int(rect.height() * 0.1)), QFont.Weight.Bold))
            painter.setPen(QColor(240, 253, 255))
            painter.drawText(tile.adjusted(10, 0, -10, 10), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom, value)

        nav = QRectF(rect.left() + rect.width() * 0.05, rect.bottom() - rect.height() * 0.16, rect.width() * 0.9, rect.height() * 0.055)
        painter.setPen(QPen(QColor(45, 225, 245, 140), 2))
        painter.drawLine(nav.left(), nav.center().y(), nav.right(), nav.center().y())
        pulse_x = nav.left() + nav.width() * ((self.state.lane_phase * 0.5) % 1.0)
        painter.setBrush(QColor(80, 240, 255, 220))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(pulse_x, nav.center().y()), 4, 4)

    def _paint_video_glass_treatment(self, painter: QPainter) -> None:
        width = self.width()
        height = self.height()
        tint = QLinearGradient(0, 0, 0, height)
        tint.setColorAt(0.0, QColor(6, 18, 24, 36))
        tint.setColorAt(0.5, QColor(0, 0, 0, 0))
        tint.setColorAt(1.0, QColor(0, 0, 0, 95))
        painter.fillRect(self.rect(), tint)

        glow = QRadialGradient(QPointF(width * 0.7, height * 0.36), width * 0.4)
        glow.setColorAt(0.0, QColor(45, 215, 245, 28))
        glow.setColorAt(0.55, QColor(25, 140, 185, 10))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillRect(self.rect(), glow)

    def _vanishing(self) -> QPointF:
        return QPointF(self.width() * 0.5 + self.state.steering * 1.6, self.height() * 0.38)

    def _road_point(self, lane: float, depth: float) -> QPointF:
        vanishing = self._vanishing()
        bottom_y = self.height() * 0.9
        spread = self.width() * 0.72 * depth * depth
        return QPointF(vanishing.x() + lane * spread, vanishing.y() + (bottom_y - vanishing.y()) * depth)

    def _paint_exterior(self, painter: QPainter) -> None:
        width = self.width()
        height = self.height()
        speed = self.state.speed_factor
        shake_x = math.sin(self.state.tick * 0.23) * speed * 1.2
        shake_y = math.sin(self.state.tick * 0.17) * speed * 0.8

        sky = QLinearGradient(0, 0, 0, height * 0.62)
        sky.setColorAt(0.0, QColor(150, 173, 184))
        sky.setColorAt(0.45, QColor(220, 164, 101))
        sky.setColorAt(1.0, QColor(47, 58, 64))
        painter.fillRect(self.rect(), sky)

        sun = QRadialGradient(QPointF(width * 0.64, height * 0.18), width * 0.28)
        sun.setColorAt(0.0, QColor(255, 236, 185, 125))
        sun.setColorAt(0.5, QColor(242, 142, 89, 42))
        sun.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillRect(self.rect(), sun)

        painter.save()
        painter.translate(shake_x, shake_y)
        self._paint_city_parallax(painter)
        self._paint_road_surface(painter)
        self._paint_lane_markers(painter)
        painter.restore()

    def _paint_city_parallax(self, painter: QPainter) -> None:
        width = self.width()
        height = self.height()
        speed = self.state.speed_factor
        painter.setPen(Qt.PenStyle.NoPen)
        for row, scale in enumerate((0.25, 0.42, 0.64)):
            y = height * (0.13 + row * 0.055)
            offset = (self.state.lane_phase * width * scale * (0.16 + speed * 0.34)) % 110
            for index in range(-2, 22):
                x = index * 110 - offset
                building_h = height * (0.14 + 0.12 * ((index + row) % 4) / 3)
                painter.setBrush(QColor(30, 39, 44, 105 + row * 35))
                painter.drawRect(QRectF(x, y, 72, building_h))
                painter.setBrush(QColor(255, 206, 128, 40))
                painter.drawRect(QRectF(x + 16, y + 24, 12, 12))
                painter.drawRect(QRectF(x + 43, y + 52, 12, 12))

        painter.setBrush(QColor(44, 50, 53, 215))
        painter.drawRect(QRectF(0, height * 0.24, width, height * 0.035))
        painter.drawRect(QRectF(width * 0.16, 0, width * 0.05, height * 0.42))

    def _paint_road_surface(self, painter: QPainter) -> None:
        width = self.width()
        height = self.height()
        road = QPolygonF(
            [
                self._road_point(-0.16, 0.0),
                self._road_point(0.16, 0.0),
                self._road_point(0.9, 1.0),
                self._road_point(-0.9, 1.0),
            ]
        )
        road_gradient = QLinearGradient(0, height * 0.36, 0, height)
        road_gradient.setColorAt(0.0, QColor(72, 68, 64))
        road_gradient.setColorAt(1.0, QColor(28, 29, 30))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(road_gradient)
        painter.drawPolygon(road)

        painter.setPen(QPen(QColor(226, 230, 225, 130), 3))
        painter.drawLine(self._road_point(-0.9, 1.0), self._road_point(-0.16, 0.0))
        painter.drawLine(self._road_point(0.9, 1.0), self._road_point(0.16, 0.0))

    def _paint_lane_markers(self, painter: QPainter) -> None:
        speed = self.state.speed_factor
        for lane in (-0.34, 0.0, 0.34):
            for marker in range(10):
                depth = (self.state.lane_phase + marker / 10.0) % 1.0
                start = self._road_point(lane, depth)
                end = self._road_point(lane, min(depth + 0.045 + speed * 0.045, 1.0))
                alpha = int(45 + 145 * depth)
                thickness = 1.0 + depth * 5.5
                painter.setPen(QPen(QColor(245, 247, 240, alpha), thickness))
                painter.drawLine(start, end)

        painter.setPen(QPen(QColor(68, 226, 255, int(75 + speed * 65)), 1.5 + speed * 1.6))
        for marker in range(5):
            depth = (self.state.lane_phase * 1.15 + marker / 5.0) % 1.0
            painter.drawLine(self._road_point(-0.25, depth), self._road_point(0.25, depth))

    def _paint_backward_traffic(self, painter: QPainter) -> None:
        cars = [
            (-0.18, 0.04, QColor(25, 29, 33)),
            (0.2, 0.34, QColor(150, 48, 37)),
            (0.48, 0.59, QColor(43, 51, 56)),
            (-0.48, 0.79, QColor(62, 67, 70)),
        ]
        speed = self.state.speed_factor
        for lane, offset, color in cars:
            depth = (self.state.traffic_phase * (0.65 + speed * 0.35) + offset) % 1.0
            if depth < 0.07:
                continue
            center = self._road_point(lane, depth)
            car_w = self.width() * (0.024 + depth * depth * 0.09)
            car_h = self.height() * (0.017 + depth * depth * 0.058)
            rect = QRectF(center.x() - car_w / 2, center.y() - car_h / 2, car_w, car_h)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(color.red(), color.green(), color.blue(), int(120 + depth * 120)))
            painter.drawRoundedRect(rect, 5, 5)
            painter.setBrush(QColor(120, 170, 182, int(40 + depth * 85)))
            painter.drawRoundedRect(rect.adjusted(car_w * 0.22, car_h * 0.14, -car_w * 0.22, -car_h * 0.35), 3, 3)
            painter.setBrush(QColor(255, 55, 38, int(90 + depth * 140)))
            painter.drawRect(QRectF(rect.left() + car_w * 0.18, rect.bottom() - car_h * 0.2, car_w * 0.18, max(2, car_h * 0.08)))
            painter.drawRect(QRectF(rect.right() - car_w * 0.36, rect.bottom() - car_h * 0.2, car_w * 0.18, max(2, car_h * 0.08)))

    def _paint_hud(self, painter: QPainter) -> None:
        width = self.width()
        height = self.height()
        speed = self.state.speed_factor
        center = QPointF(width * 0.42 + self.state.steering * 1.3, height * 0.43)
        painter.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        painter.setPen(QColor(88, 236, 255, 215))
        painter.drawText(QRectF(width * 0.25, height * 0.395, 105, 44), Qt.AlignmentFlag.AlignCenter, f"{self.state.speed:02.0f}")
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        painter.drawText(QRectF(width * 0.36, height * 0.407, 110, 24), Qt.AlignmentFlag.AlignCenter, "22 min")
        painter.drawText(QRectF(width * 0.5, height * 0.407, 84, 24), Qt.AlignmentFlag.AlignCenter, "AUTO")

        for step in range(4):
            pulse = (self.state.lane_phase + step / 4.0) % 1.0
            alpha = int(65 + pulse * 95)
            painter.setPen(QPen(QColor(63, 224, 255, alpha), 2.4 + speed * 0.9))
            y = 18 + pulse * 76
            inset = step * 18
            painter.drawLine(center + QPointF(-104 + inset, y), center + QPointF(-26 + inset * 0.28, -24 + pulse * 24))
            painter.drawLine(center + QPointF(104 - inset, y), center + QPointF(26 - inset * 0.28, -24 + pulse * 24))

    def _paint_weather(self, painter: QPainter) -> None:
        if self.state.rain <= 0.05:
            return
        width = self.width()
        height = self.height()
        painter.setPen(QPen(QColor(205, 235, 245, int(55 + self.state.rain * 130)), 1))
        for index in range(140):
            x = (index * 43 + self.state.tick * 7) % max(width, 1)
            y = (index * 71 + self.state.tick * 14) % max(height, 1)
            painter.drawLine(QPointF(x, y), QPointF(x - 17, y + 40))

        angle = -44 + 88 * abs(math.sin(self.state.wiper_phase * math.pi))
        base = QPointF(width * 0.5, height * 0.73)
        length = height * 0.42
        end = QPointF(base.x() + math.sin(math.radians(angle)) * length, base.y() - math.cos(math.radians(angle)) * length)
        painter.setPen(QPen(QColor(4, 7, 9, 215), 10))
        painter.drawLine(base, end)
        painter.setPen(QPen(QColor(225, 245, 250, 95), 2))
        painter.drawLine(base + QPointF(4, 0), end + QPointF(4, 0))

    def _paint_cockpit_foreground(self, painter: QPainter) -> None:
        width = self.width()
        height = self.height()

        dash = QPainterPath()
        dash.moveTo(0, height * 0.69)
        dash.cubicTo(width * 0.18, height * 0.65, width * 0.34, height * 0.68, width * 0.5, height * 0.71)
        dash.cubicTo(width * 0.72, height * 0.75, width * 0.86, height * 0.69, width, height * 0.66)
        dash.lineTo(width, height)
        dash.lineTo(0, height)
        dash.closeSubpath()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(4, 6, 8, 248))
        painter.drawPath(dash)

        painter.setPen(QPen(QColor(25, 222, 245, 150), 2))
        painter.drawLine(QPointF(width * 0.09, height * 0.72), QPointF(width * 0.92, height * 0.69))
        painter.setPen(QPen(QColor(235, 239, 240, 150), 5))
        painter.drawLine(QPointF(width * 0.36, height * 0.79), QPointF(width * 0.94, height * 0.745))

        painter.setBrush(QColor(2, 4, 6, 238))
        painter.drawPolygon(QPolygonF([QPointF(0, 0), QPointF(width * 0.075, 0), QPointF(width * 0.15, height * 0.72), QPointF(0, height)]))
        painter.drawPolygon(QPolygonF([QPointF(width, 0), QPointF(width * 0.93, 0), QPointF(width * 0.85, height * 0.67), QPointF(width, height)]))

        self._paint_steering_wheel(painter)

    def _paint_steering_wheel(self, painter: QPainter) -> None:
        width = self.width()
        height = self.height()
        painter.save()
        painter.translate(width * 0.33, height * 0.84)
        painter.rotate(self.state.steering * 0.45)
        rim = QRectF(-190, -160, 380, 310)
        painter.setPen(QPen(QColor(7, 10, 12), 34))
        painter.drawEllipse(rim)
        painter.setPen(QPen(QColor(42, 214, 245, 160), 8))
        painter.drawArc(rim, 25 * 16, 130 * 16)
        painter.setPen(QPen(QColor(22, 27, 31), 26))
        painter.drawLine(QPointF(0, 0), QPointF(-136, 86))
        painter.drawLine(QPointF(0, 0), QPointF(136, 86))
        painter.drawLine(QPointF(0, 0), QPointF(0, 120))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(10, 14, 17))
        painter.drawEllipse(QRectF(-70, -52, 140, 104))
        painter.setBrush(QColor(47, 220, 245, 190))
        painter.drawEllipse(QRectF(-30, -30, 60, 60))
        painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        painter.setPen(QColor(1, 12, 16))
        painter.drawText(QRectF(-30, -17, 60, 34), Qt.AlignmentFlag.AlignCenter, "UVI")
        painter.restore()

    def _paint_vignette(self, painter: QPainter) -> None:
        edge = QRadialGradient(QPointF(self.width() * 0.5, self.height() * 0.44), self.width() * 0.72)
        edge.setColorAt(0.0, QColor(0, 0, 0, 0))
        edge.setColorAt(0.72, QColor(0, 0, 0, 0))
        edge.setColorAt(1.0, QColor(0, 0, 0, 150))
        painter.fillRect(self.rect(), edge)


class InstrumentCluster(QFrame):
    """Live driver instrument cluster overlay."""

    def __init__(self, state: SimulationState) -> None:
        super().__init__()
        self.state = state
        self.setObjectName("glassPanel")
        self.setFixedSize(300, 128)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 10, 18, 12)
        self.speed = QLabel("00")
        self.speed.setObjectName("speedReadout")
        self.speed.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status = QLabel("km/h | lane assist | traction normal")
        self.status.setObjectName("smallText")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.speed)
        layout.addWidget(self.status)

    def refresh(self) -> None:
        self.speed.setText(f"{self.state.speed:02.0f}")
        traction = "wet road" if self.state.rain > 0.48 else "traction normal"
        self.status.setText(f"km/h | lane assist | {traction}")


class PanoramicDisplay(QFrame):
    """Passenger-side live display overlay."""

    def __init__(self, state: SimulationState) -> None:
        super().__init__()
        self.state = state
        self.setObjectName("glassPanel")
        self.setFixedSize(600, 142)
        layout = QGridLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setHorizontalSpacing(18)

        self.energy_value = self._add_metric(layout, "ENERGY", 0, 0)
        self.route_value = self._add_metric(layout, "ROUTE", 0, 1)
        self.weather_value = self._add_metric(layout, "WEATHER", 0, 2)
        self.health_value = self._add_metric(layout, "HEALTH", 0, 3)
        self.companion_value = self._add_metric(layout, "UVI COMPANION", 1, 0, 1, 4)
        self.refresh()

    def _add_metric(
        self,
        layout: QGridLayout,
        title: str,
        row: int,
        column: int,
        row_span: int = 1,
        column_span: int = 1,
    ) -> QLabel:
        box = QVBoxLayout()
        title_label = QLabel(title)
        title_label.setObjectName("panelTitle")
        value_label = QLabel("")
        value_label.setObjectName("panelValue")
        value_label.setWordWrap(True)
        box.addWidget(title_label)
        box.addWidget(value_label)
        layout.addLayout(box, row, column, row_span, column_span)
        return value_label

    def refresh(self) -> None:
        self.energy_value.setText(f"{self.state.battery:02.0f}%  {self.state.range_km:03.0f} km")
        self.route_value.setText("NH48  22 min")
        self.weather_value.setText("Rain active" if self.state.rain > 0.48 else "Clear drive")
        self.health_value.setText("Nominal")
        self.companion_value.setText(self.state.companion_message)
