#!/usr/bin/env python3
"""
German Language Learning Audio Generator
Uses Google Cloud TTS for high-quality German audio generation.

Setup:
1. Install: pip install google-cloud-texttospeech pydub anthropic
2. Set up Google Cloud TTS:
   - Create project at console.cloud.google.com
   - Enable Cloud Text-to-Speech API
   - Create service account and download JSON key
   - Set: export GOOGLE_APPLICATION_CREDENTIALS="path/to/key.json"
3. Set: export ANTHROPIC_API_KEY="your-key"
4. Ensure ffmpeg is installed for audio processing

Usage:
    python german_audio.py generate "give me sentences using dative case"
    python german_audio.py generate "everyday greetings" A1   # constrain to a CEFR level
    python german_audio.py import-wordlist                    # import all Goethe A1-B1 words
    python german_audio.py import-wordlist A1                 # import just one level
    python german_audio.py import-wordlist A1 100             # 100 most common A1 words
    python german_audio.py generate-words A1 20               # FRESH sentences for top 20 A1 words
    python german_audio.py generate-words B1 "Umwelt, Vertrag, sich beeilen"
    python german_audio.py list
    python german_audio.py list A1                            # list one level
    python german_audio.py list A1 20                         # top 20 A1 by frequency
    python german_audio.py create-audio "the_dog_is_big"
    python german_audio.py create-all
    python german_audio.py create-all A1                      # only A1-tagged sentences
    python german_audio.py test-voice
    python german_audio.py test-voice "Ich lerne jeden Tag Deutsch."

The import-wordlist command populates the sentence database from the leveled
Goethe A1-B1 vocabulary in wordlists/goethe_a1-b1.tsv (each word's official
example sentence + translation, tagged by CEFR level and corpus frequency).
Words are imported most-common-first, so a limit gives you the highest-priority
words. Then create-all turns those into audio. See wordlists/README.md for the
data's provenance.

import-wordlist reuses each word's official Goethe example sentence. If you want
freshly written, level-constrained sentences instead (for variety or extra
practice), use generate-words — it asks Claude for a new sentence per word.
"""

import os
import io
import json
import sys
import subprocess
from pathlib import Path
from google.cloud import texttospeech
from google.api_core import exceptions as google_exceptions
from pydub import AudioSegment
import anthropic

# Configuration
BASE_DIR = Path(__file__).resolve().parent
# Generated data lives inside the project (not $HOME). The sentence database is
# small and worth tracking in git; the audio is bulky and derived, so it lives in
# a separate gitignored dir. Both are overridable via environment variables.
DATA_DIR = Path(os.environ.get("GERMAN_TTS_DATA", BASE_DIR / "data"))
AUDIO_DIR = Path(os.environ.get("GERMAN_TTS_OUTPUT", BASE_DIR / "output"))
SENTENCES_FILE = DATA_DIR / "sentences.json"
# Leveled Goethe A1-B1 vocabulary (word + official example sentence + translation),
# built from the Goethe-Institut Wortlisten. See wordlists/README.md for provenance.
WORDLIST_FILE = BASE_DIR / "wordlists" / "goethe_a1-b1.tsv"
CEFR_LEVELS = ("A1", "A2", "B1")
# freq_rank value for words absent from the frequency corpus (they sort last).
NO_FREQ_RANK = 10 ** 7
# Claude model used for sentence generation.
MODEL = "claude-sonnet-5"
# Per-level guidance injected into the generation prompt so Claude stays within
# the vocabulary and grammar a learner at that level is expected to know.
LEVEL_GUIDANCE = {
    "A1": ("Use only the most basic, high-frequency words. Grammar: present tense, "
           "simple main clauses, common modal verbs (können, müssen, wollen). "
           "Avoid subordinate clauses and past tenses."),
    "A2": ("Everyday vocabulary. Grammar: present and perfect (Perfekt) tense, modal "
           "verbs, simple subordinate clauses with weil/dass/wenn, comparatives. "
           "Avoid Konjunktiv and complex nested clauses."),
    "B1": ("Broader everyday and some abstract vocabulary. Grammar: past tenses "
           "(Perfekt and Präteritum), Konjunktiv II for politeness/hypotheticals, "
           "passive voice, relative clauses, and multi-clause sentences."),
}
# Chirp3-HD are Google's newest (most natural) voices. Swap the trailing name
# for any other Chirp3-HD voice; see cloud.google.com/text-to-speech/docs/voices
GERMAN_VOICE = "de-DE-Chirp3-HD-Charon"   # Male; use a -Kore/-Aoede/etc. suffix for other timbres
ENGLISH_VOICE = "en-US-Chirp3-HD-Kore"    # Female

# Playback speed for learners (< 1.0 is slower). Applied to all synthesis.
SPEAKING_RATE = 0.85
# Some Chirp3-HD voices silently ignore the API's speaking_rate parameter.
# When they do, we can't detect it from the response, so set this True to skip
# the API rate entirely and slow the audio in post-processing (pitch-preserving
# via ffmpeg's atempo filter) instead. Leave False to try the API rate first.
FORCE_POST_SLOWDOWN = False


def _slugify(text, maxlen=60):
    """Turn arbitrary text into a filesystem-safe key (letters/digits + underscores)."""
    text = text.lower()
    text = ''.join(c if c.isalnum() or c.isspace() else '' for c in text)
    return '_'.join(text.split())[:maxlen]


def _parse_level_and_limit(args):
    """Split CLI args into (level, limit): numeric arg -> limit, other -> level."""
    level, limit = None, None
    for a in args:
        if a.isdigit():
            limit = int(a)
        else:
            level = a
    return level, limit


class GermanAudioGenerator:
    def __init__(self):
        self.audio_dir = AUDIO_DIR
        self.data_dir = DATA_DIR
        self.sentences_file = SENTENCES_FILE
        self.tts_client = texttospeech.TextToSpeechClient()
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize sentence database
        if not self.sentences_file.exists():
            self._save_sentences({})
    
    def _load_sentences(self):
        """Load sentences from JSON database"""
        with open(self.sentences_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_sentences(self, sentences):
        """Save sentences to JSON database"""
        with open(self.sentences_file, 'w', encoding='utf-8') as f:
            json.dump(sentences, f, indent=2, ensure_ascii=False)
    
    def _slow_audio(self, mp3_bytes, tempo):
        """Slow MP3 audio using ffmpeg's atempo filter (preserves pitch).

        atempo accepts 0.5-2.0; SPEAKING_RATE is expected to be within that.
        Returns the processed MP3 bytes, or the original bytes on failure.
        """
        if tempo == 1.0:
            return mp3_bytes
        try:
            result = subprocess.run(
                ["ffmpeg", "-hide_banner", "-loglevel", "error",
                 "-i", "pipe:0", "-filter:a", f"atempo={tempo}",
                 "-f", "mp3", "pipe:1"],
                input=mp3_bytes,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            return result.stdout
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"  ⚠ Post-processing slowdown failed ({e}); using original speed")
            return mp3_bytes

    def _synthesize_speech(self, text, language_code, voice_name):
        """Generate speech using Google Cloud TTS.

        Tries to apply SPEAKING_RATE at the API level. If the chosen voice
        rejects the parameter (some Chirp3-HD voices do), it falls back to
        synthesizing at normal speed and slowing the audio in post-processing.
        Set FORCE_POST_SLOWDOWN=True to always slow in post (for voices that
        silently ignore the API rate rather than rejecting it).
        """
        synthesis_input = texttospeech.SynthesisInput(text=text)

        voice = texttospeech.VoiceSelectionParams(
            language_code=language_code,
            name=voice_name
        )

        # Decide whether the API applies the rate or we do it afterwards.
        api_rate = 1.0 if FORCE_POST_SLOWDOWN else SPEAKING_RATE
        post_tempo = SPEAKING_RATE if FORCE_POST_SLOWDOWN else 1.0

        def _synthesize(rate):
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=rate  # Slightly slower for learning
            )
            return self.tts_client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            ).audio_content

        try:
            audio = _synthesize(api_rate)
        except google_exceptions.InvalidArgument:
            # Voice rejected speaking_rate — retry at normal speed and slow in post.
            print(f"  ⚠ '{voice_name}' rejected speaking_rate; slowing in post-processing")
            audio = _synthesize(1.0)
            post_tempo = SPEAKING_RATE

        return self._slow_audio(audio, post_tempo)
    
    def _level_guidance(self, level):
        """Validate a CEFR level and return (level_upper, guidance_text) or (None, None)."""
        level = level.upper()
        if level not in LEVEL_GUIDANCE:
            print(f"✗ Unknown level '{level}'. Use one of: {', '.join(CEFR_LEVELS)}")
            return None, None
        return level, LEVEL_GUIDANCE[level]

    def _ask_claude_json(self, prompt, max_tokens=2000):
        """Send a prompt to Claude and parse its reply as a JSON array."""
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        message = client.messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        # Skip any non-text blocks (e.g. extended-thinking blocks) and join the text.
        response_text = "".join(
            block.text for block in message.content
            if getattr(block, "type", None) == "text"
        ).strip()
        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        return json.loads(response_text.strip())

    def generate_sentences(self, instruction, level=None):
        """Use Claude to generate German-English sentence pairs.

        If level is one of A1/A2/B1, the sentences are constrained to the
        vocabulary and grammar appropriate for that CEFR level.
        """
        level_block = ""
        if level:
            level, guidance = self._level_guidance(level)
            if level is None:
                return []
            level_block = (
                f"\n- Target CEFR level: {level}. {guidance} "
                f"Stay strictly within what a {level} learner would understand."
            )

        prompt = f"""Generate 8-10 German-English sentence pairs based on this instruction: "{instruction}"

Requirements:
- Each sentence should demonstrate the requested grammar concept
- Keep sentences practical and conversational
- Provide the German sentence and its English translation
- Format as a JSON array of objects with "german" and "english" keys
- Use natural, spoken German appropriate for learners{level_block}

Return ONLY the JSON array, no other text."""

        sentence_pairs = self._ask_claude_json(prompt)

        # Load existing sentences and add new ones
        sentences = self._load_sentences()

        for pair in sentence_pairs:
            # Create filename from English sentence
            filename = _slugify(pair['english'])

            entry = {
                "german": pair['german'],
                "english": pair['english'],
                "audio_generated": False
            }
            if level:
                entry["level"] = level
            sentences[filename] = entry
        
        self._save_sentences(sentences)
        print(f"✓ Generated {len(sentence_pairs)} new sentence pairs")
        print(f"✓ Total sentences in database: {len(sentences)}")
        return sentence_pairs

    def _load_wordlist(self, level=None):
        """Load the Goethe A1-B1 wordlist (word/example/translation, tagged by level).

        Pass a CEFR level (A1/A2/B1) to return only that level's words. Entries are
        returned most-common-first (by corpus frequency rank), so callers can take a
        prefix to prioritize the most important words.
        """
        if not WORDLIST_FILE.exists():
            print(f"✗ Wordlist not found: {WORDLIST_FILE}")
            return []
        want = level.upper() if level else None
        if want and want not in CEFR_LEVELS:
            print(f"✗ Unknown level '{want}'. Use one of: {', '.join(CEFR_LEVELS)}")
            return []
        entries = []
        with open(WORDLIST_FILE, encoding="utf-8") as f:
            next(f, None)  # skip the header row
            for line in f:
                line = line.rstrip("\n")
                if not line.strip():
                    continue
                parts = line.split("\t")
                if len(parts) < 4:
                    continue
                lvl, word, german, english = parts[0], parts[1], parts[2], parts[3]
                try:
                    freq_rank = int(parts[4]) if len(parts) > 4 else NO_FREQ_RANK
                except ValueError:
                    freq_rank = NO_FREQ_RANK
                if want and lvl != want:
                    continue
                entries.append({"level": lvl, "word": word, "german": german,
                                "english": english, "freq_rank": freq_rank})
        # Most common first; ties (and unranked words) keep file/alphabetical order.
        entries.sort(key=lambda e: e["freq_rank"])
        return entries

    def import_wordlist(self, level=None, limit=None):
        """Import Goethe wordlist example sentences into the sentence database.

        Each word's official example sentence becomes a to-be-spoken entry tagged
        with its CEFR level. Words are taken most-common-first, so passing a limit
        imports the highest-frequency (most important) words for the scope. Existing
        entries with the same key are left untouched, so this is safe to re-run.
        """
        entries = self._load_wordlist(level)
        if not entries:
            print("No wordlist entries to import.")
            return

        if limit is not None:
            entries = entries[:limit]

        sentences = self._load_sentences()
        added = 0
        for e in entries:
            base = f"{e['level'].lower()}_{_slugify(e['word'])}"
            key, i = base, 2
            # Give distinct senses of the same word distinct keys.
            while key in sentences and sentences[key].get("german") != e["german"]:
                key = f"{base}_{i}"
                i += 1
            if key in sentences:
                continue  # already imported this exact sentence
            sentences[key] = {
                "german": e["german"],
                "english": e["english"],
                "word": e["word"],
                "level": e["level"],
                "freq_rank": e["freq_rank"],
                "source": "goethe-wortliste",
                "audio_generated": False,
            }
            added += 1

        self._save_sentences(sentences)
        scope = level.upper() if level else "A1-B1"
        limit_msg = f", top {limit} by frequency" if limit is not None else ""
        print(f"✓ Imported {added} new sentences from Goethe wordlist ({scope}{limit_msg})")
        print(f"✓ Total sentences in database: {len(sentences)}")
        return added

    def generate_for_words(self, level, words=None, count=None, batch_size=15):
        """Generate a fresh, level-appropriate example sentence for each target word.

        Unlike import-wordlist (which reuses Goethe's canned example), this asks
        Claude for a NEW sentence per word, constrained to the given CEFR level.
        Provide an explicit `words` list, or a `count` to pull that many of the most
        common words for the level from the Goethe wordlist. Generated entries use a
        distinct key prefix so they never overwrite imported ones.
        """
        level, guidance = self._level_guidance(level)
        if level is None:
            return []

        # Resolve target words; remember frequency rank when we know it.
        rank_of = {}
        if words is None:
            entries = self._load_wordlist(level)[:(count or 10)]
            words = [e["word"] for e in entries]
            rank_of = {e["word"]: e["freq_rank"] for e in entries}
        words = [w for w in words if w.strip()]
        if not words:
            print("No target words to generate for.")
            return []

        print(f"Generating fresh {level} sentences for {len(words)} words...")
        sentences = self._load_sentences()
        generated = []
        for start in range(0, len(words), batch_size):
            batch = words[start:start + batch_size]
            word_lines = "\n".join(f"- {w}" for w in batch)
            prompt = f"""Write ONE natural, spoken German example sentence for EACH German word below, suitable for a CEFR {level} learner.

{guidance}
Every other word in each sentence must also be {level}-appropriate — stay strictly within what a {level} learner understands.

Words:
{word_lines}

For each word return an object with:
- "word": the target word exactly as given
- "german": the example sentence (it must actually use the word)
- "english": an English translation of the sentence

Return ONLY a JSON array of these objects, one per word, no other text."""

            try:
                pairs = self._ask_claude_json(prompt, max_tokens=4000)
            except Exception as e:
                print(f"  ⚠ Batch {start // batch_size + 1} failed ({e}); skipping")
                continue

            for pair in pairs:
                word = (pair.get("word") or "").strip()
                german = (pair.get("german") or "").strip()
                english = (pair.get("english") or "").strip()
                if not (word and german and english):
                    continue
                key_base = f"{level.lower()}_gen_{_slugify(word)}"
                key, i = key_base, 2
                # Distinct sentences for the same word coexist (accumulate variants).
                while key in sentences and sentences[key].get("german") != german:
                    key = f"{key_base}_{i}"
                    i += 1
                entry = {
                    "german": german,
                    "english": english,
                    "word": word,
                    "level": level,
                    "source": "generated",
                    "audio_generated": False,
                }
                if rank_of.get(word) is not None:
                    entry["freq_rank"] = rank_of[word]
                sentences[key] = entry
                generated.append(word)
            print(f"  ✓ {len(generated)}/{len(words)} done...")

        self._save_sentences(sentences)
        print(f"✓ Generated {len(generated)} fresh {level} sentences")
        print(f"✓ Total sentences in database: {len(sentences)}")
        return generated

    def create_audio(self, filename_key):
        """Create audio file for a specific sentence pair"""
        sentences = self._load_sentences()
        
        if filename_key not in sentences:
            print(f"✗ Sentence '{filename_key}' not found in database")
            return False
        
        pair = sentences[filename_key]
        german_text = pair['german']
        english_text = pair['english']
        
        print(f"Creating audio for: {english_text}")
        
        # Generate German audio
        german_audio = self._synthesize_speech(german_text, "de-DE", GERMAN_VOICE)
        
        # Generate English audio
        english_audio = self._synthesize_speech(english_text, "en-US", ENGLISH_VOICE)
        
        # Save temporary files
        temp_german = self.audio_dir / "temp_german.mp3"
        temp_english = self.audio_dir / "temp_english.mp3"
        
        with open(temp_german, 'wb') as f:
            f.write(german_audio)
        with open(temp_english, 'wb') as f:
            f.write(english_audio)
        
        # Combine with 1 second pause between
        german_segment = AudioSegment.from_mp3(temp_german)
        english_segment = AudioSegment.from_mp3(temp_english)
        silence = AudioSegment.silent(duration=1000)  # 1 second
        
        combined = german_segment + silence + english_segment
        
        # Export final file using AAC (mp3 encoder not available in your ffmpeg)
        output_file = self.audio_dir / f"{filename_key}.m4a"
        combined.export(output_file, format="ipod", codec="aac", bitrate="128k")
        
        # Clean up temp files
        temp_german.unlink()
        temp_english.unlink()
        
        # Update database
        sentences[filename_key]['audio_generated'] = True
        self._save_sentences(sentences)
        
        print(f"✓ Created: {output_file}")
        return True
    
    def create_all_audio(self, level=None):
        """Generate audio for all sentences that don't have it yet.

        Pass a CEFR level (A1/A2/B1) to only process sentences tagged with it —
        useful for working through the imported wordlist one level at a time.
        """
        sentences = self._load_sentences()
        want = level.upper() if level else None
        pending = [k for k, v in sentences.items()
                   if not v.get('audio_generated', False)
                   and (want is None or v.get('level') == want)]

        scope = f" ({want})" if want else ""
        print(f"Generating audio for {len(pending)} sentences{scope}...")
        
        for i, filename_key in enumerate(pending, 1):
            print(f"\n[{i}/{len(pending)}]", end=" ")
            self.create_audio(filename_key)
        
        print(f"\n✓ Complete! All audio files generated.")
    
    def test_voice(self, german_text=None):
        """Synthesize one sample sentence to A/B voices without touching the DB.

        Writes voice_test.m4a to the output dir using the currently configured
        GERMAN_VOICE / ENGLISH_VOICE / SPEAKING_RATE / FORCE_POST_SLOWDOWN.
        """
        german_text = german_text or "Der schnelle braune Fuchs springt über den faulen Hund."
        english_text = "The quick brown fox jumps over the lazy dog."

        print(f"German voice : {GERMAN_VOICE}")
        print(f"English voice: {ENGLISH_VOICE}")
        print(f"Speaking rate: {SPEAKING_RATE} (force post-slowdown: {FORCE_POST_SLOWDOWN})")
        print(f"DE: {german_text}")
        print(f"EN: {english_text}")

        german_audio = self._synthesize_speech(german_text, "de-DE", GERMAN_VOICE)
        english_audio = self._synthesize_speech(english_text, "en-US", ENGLISH_VOICE)

        german_segment = AudioSegment.from_mp3(io.BytesIO(german_audio))
        english_segment = AudioSegment.from_mp3(io.BytesIO(english_audio))
        silence = AudioSegment.silent(duration=1000)  # 1 second

        combined = german_segment + silence + english_segment

        output_file = self.audio_dir / "voice_test.m4a"
        combined.export(output_file, format="ipod", codec="aac", bitrate="128k")

        print(f"✓ Wrote sample: {output_file}")
        return True

    def list_sentences(self, level=None, limit=None):
        """List sentences in the database, optionally filtered by CEFR level.

        Pass a limit to show only the first N (imported entries are ordered
        most-common-first, so this shows the highest-frequency words).
        """
        sentences = self._load_sentences()

        if not sentences:
            print("No sentences in database yet.")
            return

        want = level.upper() if level else None
        items = [(k, v) for k, v in sentences.items()
                 if want is None or v.get('level') == want]
        total_matched = len(items)
        if limit is not None:
            items = items[:limit]

        scope = f", {want}" if want else ""
        print(f"\n{'='*80}")
        print(f"SENTENCE DATABASE ({len(items)} shown{scope}, {total_matched} matched, "
              f"{len(sentences)} total)")
        print(f"{'='*80}\n")

        for filename, pair in items:
            status = "✓" if pair.get('audio_generated', False) else "○"
            tag = f"[{pair['level']}] " if pair.get('level') else ""
            rank = pair.get('freq_rank')
            rank_msg = f" (freq #{rank})" if rank and rank < NO_FREQ_RANK else ""
            print(f"{status} {tag}{filename}{rank_msg}")
            print(f"  DE: {pair['german']}")
            print(f"  EN: {pair['english']}")
            print()

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    generator = GermanAudioGenerator()
    command = sys.argv[1]
    
    if command == "generate":
        if len(sys.argv) < 3:
            print("Usage: python german_audio.py generate \"your instruction\" [A1|A2|B1]")
            sys.exit(1)
        instruction = sys.argv[2]
        level = sys.argv[3] if len(sys.argv) > 3 else None
        generator.generate_sentences(instruction, level)

    elif command == "import-wordlist":
        # Optional level filter and/or top-N limit, in any order:
        #   import-wordlist          -> all A1-B1
        #   import-wordlist A1       -> all A1
        #   import-wordlist A1 100   -> 100 most common A1 words
        #   import-wordlist 200      -> 200 most common words across A1-B1
        level, limit = _parse_level_and_limit(sys.argv[2:])
        generator.import_wordlist(level, limit)

    elif command == "generate-words":
        # Fresh Claude sentences for specific words, constrained to a level:
        #   generate-words A1 20                     -> top 20 A1 words by frequency
        #   generate-words B1 "Umwelt, sich beeilen" -> these exact words
        #   generate-words A2                        -> top 10 A2 words (default)
        if len(sys.argv) < 3:
            print('Usage: python german_audio.py generate-words <A1|A2|B1> '
                  '[count | "wort1, wort2, ..."]')
            sys.exit(1)
        level = sys.argv[2]
        arg = sys.argv[3] if len(sys.argv) > 3 else None
        if arg is None:
            generator.generate_for_words(level, count=10)
        elif arg.isdigit():
            generator.generate_for_words(level, count=int(arg))
        else:
            words = [w.strip() for w in arg.split(",") if w.strip()]
            generator.generate_for_words(level, words=words)

    elif command == "list":
        level, limit = _parse_level_and_limit(sys.argv[2:])
        generator.list_sentences(level, limit)

    elif command == "create-audio":
        if len(sys.argv) < 3:
            print("Usage: python german_audio.py create-audio \"filename_key\"")
            sys.exit(1)
        filename_key = sys.argv[2]
        generator.create_audio(filename_key)

    elif command == "create-all":
        # Optional level filter: create-all A1
        level = sys.argv[2] if len(sys.argv) > 2 else None
        generator.create_all_audio(level)

    elif command == "test-voice":
        # Optional custom German sentence: test-voice "Ich lerne Deutsch."
        german_text = sys.argv[2] if len(sys.argv) > 2 else None
        generator.test_voice(german_text)
    
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)

if __name__ == "__main__":
    main()
