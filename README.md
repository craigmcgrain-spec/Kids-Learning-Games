# Kids Learning Games

A native Qt desktop application for kindergarten and first-grade learners on
Fedora KDE. Children choose a profile, launch a reading game, hear phonics on
hover, and earn daily and lifetime points.

## Run

```bash
python3 -m kids_learning_app
```

For development without installation:

```bash
PYTHONPATH=src python3 -m kids_learning_app
```

Text-to-speech uses Qt TextToSpeech and prefers the system's `espeak-ng`
backend. Fedora packages it as `espeak-ng`. Use the **Voice** button on the
dashboard or reading screen to choose a speech engine, accent, and voice;
preview it; and save it as the app-wide default. The Flite `slt` voice is a
good natural-sounding choice for young learners. Whole words use that selected
voice. Individual sound buttons use eSpeak's phoneme mode so they pronounce
the sound itself instead of reading a letter name.

Use the **Fullscreen** button or press **F11** to toggle fullscreen mode.
Press **Esc** to leave fullscreen.

## Install

```bash
python3 -m pip install --user .
install -Dm644 packaging/io.github.kidslearning.Games.desktop \
  ~/.local/share/applications/io.github.kidslearning.Games.desktop
```

Progress is stored in
`~/.local/share/kids-learning-games/learning.db`.
