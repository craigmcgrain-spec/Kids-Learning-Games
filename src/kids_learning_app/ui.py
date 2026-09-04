from __future__ import annotations

import math
import random
from importlib.resources import files

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QEvent,
    QPointF,
    QPropertyAnimation,
    QProcess,
    QSettings,
    QStandardPaths,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QKeySequence, QPainter, QPen, QShortcut
from PySide6.QtTextToSpeech import QTextToSpeech, QVoice
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .phonics import phonemes_for_word
from .storage import LearningStore, Profile

COLORS = ["#ef4444", "#f59e0b", "#22c55e", "#3b82f6", "#8b5cf6", "#ec4899"]
ICONS = ["🦊", "🐼", "🦁", "🐸", "🐙", "🦄", "🚀", "🌈", "⭐", "🐝", "🐳", "🦖"]

APP_STYLE = """
QWidget { background: #fff9e8; color: #24324a; font-family: "Noto Sans"; }
QLabel#title { font-size: 34px; font-weight: 800; color: #2563eb; }
QLabel#subtitle { font-size: 17px; color: #52647f; }
QLabel#score { padding: 8px 15px; border-radius: 16px; background: #dbeafe;
               color: #1d4ed8; font-size: 16px; font-weight: 700; }
QPushButton { border: 0; border-radius: 16px; padding: 13px 20px; min-height: 28px;
              background: #2563eb; color: white; font-size: 17px; font-weight: 700; }
QPushButton:hover { background: #1d4ed8; }
QPushButton:pressed { background: #1e40af; }
QPushButton#secondary { background: #e0e7ff; color: #3730a3; }
QPushButton#correct { background: #16a34a; font-size: 22px; padding: 17px 30px; }
QPushButton#correct:hover { background: #15803d; }
QPushButton#profile { background: white; color: #24324a; border: 3px solid #93c5fd;
                      min-width: 150px; min-height: 130px; font-size: 18px; }
QPushButton#profile:hover { border-color: #2563eb; background: #eff6ff; }
QPushButton#game { text-align: left; padding: 24px; min-width: 260px; min-height: 90px;
                   background: #ef4444; font-size: 21px; }
QPushButton#coming { text-align: left; padding: 24px; min-width: 260px; min-height: 90px;
                     background: #cbd5e1; color: #64748b; font-size: 18px; }
QPushButton#phoneme { background: #fef3c7; color: #92400e; border: 3px solid #fbbf24;
                      font-size: 30px; min-width: 52px; min-height: 52px; padding: 9px; }
QPushButton#phoneme:hover { background: #fde68a; border-color: #f59e0b; }
QLineEdit { background: white; border: 3px solid #93c5fd; border-radius: 12px;
            padding: 12px; font-size: 19px; }
QFrame#card { background: white; border: 3px solid #bfdbfe; border-radius: 24px; }
"""


def load_words() -> list[str]:
    path = files("kids_learning_app").joinpath("data/high_frequency_words.txt")
    return [word.strip() for word in path.read_text(encoding="utf-8").splitlines() if word.strip()]


def voice_group(name: str, engine: str = "") -> str:
    if engine == "flite":
        return "English (United States)"
    return name.split("+", 1)[0]


def voice_variant(name: str, engine: str = "") -> str:
    if engine == "flite":
        return name
    return name.split("+", 1)[1] if "+" in name else "System default"


def engine_label(engine: str) -> str:
    return {
        "flite": "Flite — more natural",
        "speechd": "Speech Dispatcher — more voice choices",
    }.get(engine, engine.title())


class HoverButton(QPushButton):
    hovered = Signal(str)

    def enterEvent(self, event: QEvent) -> None:
        self.hovered.emit(self.text())
        super().enterEvent(event)


class HoverLabel(QLabel):
    hovered = Signal()

    def enterEvent(self, event: QEvent) -> None:
        self.hovered.emit()
        super().enterEvent(event)


class RainbowBurst(QWidget):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._progress = 0.0
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.hide()
        self.animation = QPropertyAnimation(self, b"progress", self)
        self.animation.setDuration(850)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.finished.connect(self.hide)

    def get_progress(self) -> float:
        return self._progress

    def set_progress(self, value: float) -> None:
        self._progress = value
        self.update()

    progress = Property(float, get_progress, set_progress)

    def celebrate(self) -> None:
        self.setGeometry(self.parentWidget().rect())
        self.show()
        self.raise_()
        self.animation.stop()
        self.animation.start()

    def paintEvent(self, event: QEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        center = QPointF(self.width() / 2, self.height() / 2)
        fade = max(0, int(255 * (1 - self._progress)))
        for index in range(30):
            angle = index * math.tau / 30
            distance = 30 + self._progress * min(self.width(), self.height()) * 0.42
            point = center + QPointF(math.cos(angle) * distance, math.sin(angle) * distance)
            color = QColor(COLORS[index % len(COLORS)])
            color.setAlpha(fade)
            painter.setPen(QPen(color, 7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawPoint(point)


class ProfileDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Create a learner")
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        title = QLabel("Who is ready to learn?")
        title.setObjectName("title")
        layout.addWidget(title)
        layout.addWidget(QLabel("Enter a name"))
        self.name = QLineEdit()
        self.name.setMaxLength(24)
        self.name.setPlaceholderText("Learner's name")
        layout.addWidget(self.name)
        layout.addWidget(QLabel("Pick a picture"))
        icon_grid = QGridLayout()
        self.icons = QButtonGroup(self)
        self.icons.setExclusive(True)
        for index, icon in enumerate(ICONS):
            button = QPushButton(icon)
            button.setCheckable(True)
            button.setStyleSheet(
                "QPushButton { font-size: 30px; background: white; color: #24324a; "
                "border: 3px solid #bfdbfe; } QPushButton:checked { border-color: #2563eb; "
                "background: #dbeafe; }"
            )
            self.icons.addButton(button, index)
            icon_grid.addWidget(button, index // 6, index % 6)
        self.icons.button(0).setChecked(True)
        layout.addLayout(icon_grid)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @property
    def selection(self) -> tuple[str, str]:
        return self.name.text(), ICONS[self.icons.checkedId()]


class VoiceSettingsDialog(QDialog):
    def __init__(
        self,
        engines: list[str],
        current_engine: str,
        current_voice_name: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.engines = [engine for engine in engines if engine != "mock"]
        self.voices_by_engine: dict[str, dict[str, QVoice]] = {}
        self.preview_speech: QTextToSpeech | None = None
        self.setWindowTitle("Voice settings")
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        title = QLabel("Choose a reading voice")
        title.setObjectName("title")
        layout.addWidget(title)
        help_text = QLabel("Pick an English accent and voice, then listen to a sample.")
        help_text.setObjectName("subtitle")
        help_text.setWordWrap(True)
        layout.addWidget(help_text)

        layout.addWidget(QLabel("Speech engine"))
        self.engine = QComboBox()
        for engine in self.engines:
            self.engine.addItem(engine_label(engine), engine)
        layout.addWidget(self.engine)
        layout.addWidget(QLabel("Accent"))
        self.accent = QComboBox()
        layout.addWidget(self.accent)
        layout.addWidget(QLabel("Voice"))
        self.voice = QComboBox()
        layout.addWidget(self.voice)

        preview = QPushButton("🔊  Preview this voice")
        preview.setObjectName("secondary")
        preview.clicked.connect(self.preview)
        layout.addWidget(preview)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.engine.currentIndexChanged.connect(self._populate_accents)
        self.accent.currentTextChanged.connect(self._populate_voices)
        engine_index = self.engine.findData(current_engine)
        self.engine.setCurrentIndex(max(0, engine_index))
        self._populate_accents(selected_voice_name=current_voice_name)

    @property
    def selected_engine(self) -> str:
        return str(self.engine.currentData() or "")

    def _voices(self, engine: str) -> dict[str, QVoice]:
        if engine not in self.voices_by_engine:
            speech = QTextToSpeech(engine)
            self.voices_by_engine[engine] = {
                voice.name(): voice for voice in speech.availableVoices()
            }
        return self.voices_by_engine[engine]

    def _populate_accents(
        self,
        _index: int = -1,
        selected_voice_name: str = "",
    ) -> None:
        names = self._voices(self.selected_engine)
        self.accent.blockSignals(True)
        self.accent.clear()
        self.accent.addItems(
            sorted({voice_group(name, self.selected_engine) for name in names})
        )
        self.accent.blockSignals(False)
        initial_group = voice_group(selected_voice_name, self.selected_engine)
        accent_index = self.accent.findText(initial_group)
        self.accent.setCurrentIndex(max(0, accent_index))
        self._populate_voices(self.accent.currentText(), selected_voice_name)

    def _populate_voices(self, group: str, selected_name: str = "") -> None:
        self.voice.clear()
        voices = self._voices(self.selected_engine)
        names = sorted(
            name
            for name in voices
            if voice_group(name, self.selected_engine) == group
        )
        for name in names:
            self.voice.addItem(voice_variant(name, self.selected_engine), name)
        selected_index = self.voice.findData(selected_name)
        self.voice.setCurrentIndex(max(0, selected_index))

    @property
    def selected_voice_name(self) -> str:
        return str(self.voice.currentData() or "")

    def preview(self) -> None:
        voice = self._voices(self.selected_engine).get(self.selected_voice_name)
        if voice is None:
            return
        if self.preview_speech is not None:
            self.preview_speech.stop()
            self.preview_speech.deleteLater()
        self.preview_speech = QTextToSpeech(self.selected_engine, self)
        self.preview_speech.stop()
        self.preview_speech.setVoice(voice)
        self.preview_speech.setRate(-0.25)
        self.preview_speech.say("Hello! Let's read and learn together.")


class MainWindow(QMainWindow):
    def __init__(self, store: LearningStore | None = None) -> None:
        super().__init__()
        self.store = store or LearningStore()
        self.current_profile: Profile | None = None
        self.words = load_words()
        self.word_order: list[str] = []
        self.word_index = 0
        self.phoneme_process = QProcess(self)
        self.fullscreen_buttons: list[QPushButton] = []
        self.previous_window_state = self.windowState()
        self.settings = QSettings("KidsLearning", "Kids Learning Games")
        saved_engine = str(self.settings.value("speech/engine", "speechd"))
        available_engines = QTextToSpeech.availableEngines()
        engine = saved_engine if saved_engine in available_engines else available_engines[0]
        self.speech = QTextToSpeech(engine, self)
        self.speech.setRate(-0.25)
        self._apply_saved_voice()
        self.setWindowTitle("Kids Learning Games")
        self.setMinimumSize(900, 650)
        self.resize(1100, 760)
        self.setStyleSheet(APP_STYLE)
        self.pages = QStackedWidget()
        self.setCentralWidget(self.pages)
        self.profile_page = self._build_profile_page()
        self.dashboard_page = self._build_dashboard_page()
        self.reading_page = self._build_reading_page()
        self.pages.addWidget(self.profile_page)
        self.pages.addWidget(self.dashboard_page)
        self.pages.addWidget(self.reading_page)
        self.burst = RainbowBurst(self)
        QShortcut(QKeySequence("F11"), self, activated=self.toggle_fullscreen)
        QShortcut(QKeySequence("Escape"), self, activated=self.exit_fullscreen)
        self.refresh_profiles()

    def _page_shell(self, title: str, subtitle: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(48, 38, 48, 38)
        layout.setSpacing(18)
        heading = QLabel(title)
        heading.setObjectName("title")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        caption = QLabel(subtitle)
        caption.setObjectName("subtitle")
        caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        caption.setWordWrap(True)
        layout.addWidget(heading)
        layout.addWidget(caption)
        return page, layout

    def _build_profile_page(self) -> QWidget:
        page, layout = self._page_shell("Kids Learning Games", "Choose your learner to begin!")
        top = QHBoxLayout()
        top.addStretch()
        top.addWidget(self._fullscreen_button())
        layout.insertLayout(0, top)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        holder = QWidget()
        self.profile_grid = QGridLayout(holder)
        self.profile_grid.setSpacing(18)
        scroll.setWidget(holder)
        layout.addWidget(scroll, 1)
        add = QPushButton("＋  Create a new learner")
        add.clicked.connect(self.create_profile)
        layout.addWidget(add, alignment=Qt.AlignmentFlag.AlignCenter)
        return page

    def _build_dashboard_page(self) -> QWidget:
        page, layout = self._page_shell("Ready to play?", "Pick a learning game.")
        top = QHBoxLayout()
        switch = QPushButton("← Switch learner")
        switch.setObjectName("secondary")
        switch.clicked.connect(lambda: self.pages.setCurrentWidget(self.profile_page))
        settings = QPushButton("⚙ Voice")
        settings.setObjectName("secondary")
        settings.clicked.connect(self.open_voice_settings)
        fullscreen = self._fullscreen_button()
        self.dashboard_name = QLabel()
        self.dashboard_name.setStyleSheet("font-size: 22px; font-weight: 800;")
        self.dashboard_score = QLabel()
        self.dashboard_score.setObjectName("score")
        top.addWidget(switch)
        top.addWidget(settings)
        top.addStretch()
        top.addWidget(self.dashboard_name)
        top.addWidget(self.dashboard_score)
        top.addWidget(fullscreen)
        layout.insertLayout(0, top)
        games = QGridLayout()
        games.setSpacing(22)
        reading = QPushButton("📚  Reading Adventure\nPractice sight words and sounds")
        reading.setObjectName("game")
        reading.clicked.connect(self.start_reading)
        games.addWidget(reading, 0, 0)
        for index, text in enumerate(
            ["🔢  Number Game\nComing soon", "🎨  Shape Game\nComing soon", "🎵  Rhyme Game\nComing soon"]
        ):
            button = QPushButton(text)
            button.setObjectName("coming")
            button.setEnabled(False)
            games.addWidget(button, (index + 1) // 2, (index + 1) % 2)
        layout.addStretch()
        layout.addLayout(games)
        layout.addStretch()
        return page

    def _build_reading_page(self) -> QWidget:
        page, layout = self._page_shell("Reading Adventure", "Hover over a sound to hear it.")
        top = QHBoxLayout()
        home = QPushButton("← Games")
        home.setObjectName("secondary")
        home.clicked.connect(self.show_dashboard)
        settings = QPushButton("⚙ Voice")
        settings.setObjectName("secondary")
        settings.clicked.connect(self.open_voice_settings)
        fullscreen = self._fullscreen_button()
        self.reading_score = QLabel()
        self.reading_score.setObjectName("score")
        top.addWidget(home)
        top.addWidget(settings)
        top.addStretch()
        top.addWidget(self.reading_score)
        top.addWidget(fullscreen)
        layout.insertLayout(0, top)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(42, 42, 42, 42)
        card_layout.setSpacing(24)
        self.word_label = HoverLabel()
        self.word_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.word_label.setStyleSheet("font-size: 72px; font-weight: 900; color: #7c3aed;")
        self.word_label.setToolTip("Hover to hear the whole word")
        self.word_label.hovered.connect(self.speak_current_word)
        card_layout.addWidget(self.word_label)
        self.phoneme_row = QHBoxLayout()
        self.phoneme_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addLayout(self.phoneme_row)
        hear_word = QPushButton("🔊  Hear the whole word")
        hear_word.setObjectName("secondary")
        hear_word.clicked.connect(self.speak_current_word)
        card_layout.addWidget(hear_word, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(card, 1)
        correct = QPushButton("✓  I read it correctly!")
        correct.setObjectName("correct")
        correct.clicked.connect(self.mark_correct)
        layout.addWidget(correct, alignment=Qt.AlignmentFlag.AlignCenter)
        return page

    def refresh_profiles(self) -> None:
        while self.profile_grid.count():
            item = self.profile_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        profiles = self.store.profiles()
        if not profiles:
            message = QLabel("Create a learner profile to save points and progress.")
            message.setObjectName("subtitle")
            message.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.profile_grid.addWidget(message, 0, 0)
            return
        for index, profile in enumerate(profiles):
            button = QPushButton(
                f"{profile.icon}\n{profile.name}\n⭐ {profile.total_points} points"
            )
            button.setObjectName("profile")
            button.clicked.connect(lambda checked=False, value=profile: self.select_profile(value))
            self.profile_grid.addWidget(button, index // 4, index % 4)

    def create_profile(self) -> None:
        dialog = ProfileDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            profile = self.store.add_profile(*dialog.selection)
        except ValueError as error:
            QMessageBox.warning(self, "Try another name", str(error))
            return
        self.refresh_profiles()
        self.select_profile(profile)

    def _fullscreen_button(self) -> QPushButton:
        button = QPushButton("⛶ Fullscreen")
        button.setObjectName("secondary")
        button.setToolTip("Toggle fullscreen (F11)")
        button.clicked.connect(self.toggle_fullscreen)
        self.fullscreen_buttons.append(button)
        return button

    def toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.exit_fullscreen()
            return
        self.previous_window_state = self.windowState()
        self.showFullScreen()
        self._update_fullscreen_buttons()

    def exit_fullscreen(self) -> None:
        if not self.isFullScreen():
            return
        self.setWindowState(self.previous_window_state)
        self._update_fullscreen_buttons()

    def _update_fullscreen_buttons(self) -> None:
        text = "⛶ Exit fullscreen" if self.isFullScreen() else "⛶ Fullscreen"
        for button in self.fullscreen_buttons:
            button.setText(text)

    def _apply_saved_voice(self) -> None:
        saved_name = str(self.settings.value("speech/voiceName", ""))
        if not saved_name:
            return
        for voice in self.speech.availableVoices():
            if voice.name() == saved_name:
                self.speech.setVoice(voice)
                return

    def open_voice_settings(self) -> None:
        engines = QTextToSpeech.availableEngines()
        selectable_engines = [engine for engine in engines if engine != "mock"]
        if not selectable_engines:
            QMessageBox.warning(
                self,
                "No voices found",
                "No text-to-speech engines are installed on this computer.",
            )
            return
        dialog = VoiceSettingsDialog(
            selectable_engines,
            self.speech.engine(),
            self.speech.voice().name(),
            self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        selected_engine = dialog.selected_engine
        selected_name = dialog.selected_voice_name
        replacement = QTextToSpeech(selected_engine, self)
        voices = replacement.availableVoices()
        selected_voice = next(
            (voice for voice in voices if voice.name() == selected_name),
            None,
        )
        if selected_voice is None:
            replacement.deleteLater()
            QMessageBox.warning(self, "Voice unavailable", "That voice is no longer available.")
            return
        self.speech.stop()
        self.speech.deleteLater()
        self.speech = replacement
        self.speech.setRate(-0.25)
        self.speech.setVoice(selected_voice)
        self.settings.setValue("speech/engine", selected_engine)
        self.settings.setValue("speech/voiceName", selected_name)
        self.settings.sync()
        self.speak("Voice saved!")

    def select_profile(self, profile: Profile) -> None:
        self.current_profile = self.store.profile(profile.id)
        self.show_dashboard()

    def show_dashboard(self) -> None:
        if self.current_profile is None:
            self.pages.setCurrentWidget(self.profile_page)
            return
        self.current_profile = self.store.profile(self.current_profile.id)
        self.dashboard_name.setText(f"{self.current_profile.icon} {self.current_profile.name}")
        self.dashboard_score.setText(
            f"⭐ Today: {self.current_profile.daily_points}   🏆 Total: {self.current_profile.total_points}"
        )
        self.pages.setCurrentWidget(self.dashboard_page)

    def start_reading(self) -> None:
        self.word_order = self.words.copy()
        random.shuffle(self.word_order)
        self.word_index = 0
        self.show_word()
        self.pages.setCurrentWidget(self.reading_page)

    def show_word(self) -> None:
        word = self.word_order[self.word_index]
        self.word_label.setText(word)
        while self.phoneme_row.count():
            item = self.phoneme_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for phoneme in phonemes_for_word(word):
            button = HoverButton(phoneme.label)
            button.setObjectName("phoneme")
            button.setToolTip(f"Hover or click to hear the /{phoneme.label}/ sound")
            button.hovered.connect(
                lambda _label, code=phoneme.code, label=phoneme.label: self.speak_phoneme(
                    code, label
                )
            )
            button.clicked.connect(
                lambda checked=False, code=phoneme.code, label=phoneme.label: self.speak_phoneme(
                    code, label
                )
            )
            self.phoneme_row.addWidget(button)
        self.update_reading_score()

    def speak(self, text: str) -> None:
        if self.phoneme_process.state() != QProcess.ProcessState.NotRunning:
            self.phoneme_process.kill()
            self.phoneme_process.waitForFinished(100)
        self.speech.stop()
        self.speech.say(text)

    def speak_phoneme(self, code: str, fallback_label: str) -> None:
        executable = QStandardPaths.findExecutable("espeak-ng")
        if not code or not executable:
            self.speak(fallback_label)
            return
        self.speech.stop()
        if self.phoneme_process.state() != QProcess.ProcessState.NotRunning:
            self.phoneme_process.kill()
            self.phoneme_process.waitForFinished(100)
        self.phoneme_process.start(
            executable,
            ["-v", "en-us", f"[[{code}]]"],
        )

    def speak_current_word(self) -> None:
        if self.word_order:
            self.speak(self.word_order[self.word_index])

    def mark_correct(self) -> None:
        if self.current_profile is None:
            return
        self.store.add_point(self.current_profile.id)
        self.current_profile = self.store.profile(self.current_profile.id)
        self.burst.celebrate()
        self.word_index = (self.word_index + 1) % len(self.word_order)
        self.show_word()

    def update_reading_score(self) -> None:
        if self.current_profile:
            self.reading_score.setText(
                f"⭐ Today: {self.current_profile.daily_points}   "
                f"🏆 Total: {self.current_profile.total_points}"
            )

    def resizeEvent(self, event: QEvent) -> None:
        super().resizeEvent(event)
        self.burst.setGeometry(self.rect())

    def closeEvent(self, event: QEvent) -> None:
        self.store.close()
        super().closeEvent(event)
