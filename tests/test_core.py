from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from kids_learning_app.phonics import parse_espeak_phonemes, phoneme_chunks
from kids_learning_app.storage import LearningStore
from kids_learning_app.ui import engine_label, load_words, voice_group, voice_variant


class StoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.store = LearningStore(Path(self.temp.name) / "test.db")

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_points_track_daily_and_overall(self) -> None:
        profile = self.store.add_profile("Ari", "🦊")
        self.store.add_point(profile.id, date(2026, 9, 3))
        self.store.add_point(profile.id, date(2026, 9, 4))
        current = self.store.profile(profile.id, date(2026, 9, 4))
        self.assertEqual(current.total_points, 2)
        self.assertEqual(current.daily_points, 1)

    def test_profile_names_are_unique_and_required(self) -> None:
        self.store.add_profile("Mia", "🐼")
        with self.assertRaises(ValueError):
            self.store.add_profile("mia", "🦁")
        with self.assertRaises(ValueError):
            self.store.add_profile(" ", "🦁")


class ContentTests(unittest.TestCase):
    def test_pdf_word_list_is_bundled(self) -> None:
        words = load_words()
        self.assertEqual(len(words), 300)
        self.assertEqual(words[:5], ["the", "of", "and", "a", "to"])
        self.assertEqual(words[-1], "want")

    def test_common_graphemes_stay_together(self) -> None:
        self.assertEqual(phoneme_chunks("through"), ["th", "r", "ough"])
        self.assertEqual(phoneme_chunks("chat"), ["ch", "a", "t"])
        self.assertEqual(phoneme_chunks("make"), ["m", "a", "ke"])

    def test_espeak_pronunciation_is_split_into_playable_sounds(self) -> None:
        sounds = parse_espeak_phonemes("tS'at")
        self.assertEqual([sound.code for sound in sounds], ["tS", "a", "t"])
        self.assertEqual([sound.label for sound in sounds], ["ch", "a", "t"])
        self.assertEqual(
            [sound.label for sound in parse_espeak_phonemes("D'@2")],
            ["th", "uh"],
        )

    def test_voice_names_are_presented_as_accent_and_variant(self) -> None:
        self.assertEqual(voice_group("English (America)+Annie"), "English (America)")
        self.assertEqual(voice_variant("English (America)+Annie"), "Annie")
        self.assertEqual(voice_variant("English (America)"), "System default")
        self.assertEqual(voice_group("slt", "flite"), "English (United States)")
        self.assertEqual(voice_variant("slt", "flite"), "slt")
        self.assertEqual(engine_label("flite"), "Flite — more natural")


if __name__ == "__main__":
    unittest.main()
