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
    python german_audio.py list
    python german_audio.py create-audio "the_dog_is_big"
    python german_audio.py create-all
"""

import os
import json
import sys
from pathlib import Path
from google.cloud import texttospeech
from pydub import AudioSegment
import anthropic

# Configuration
HOME = Path.home()
OUTPUT_DIR = HOME / "German"
SENTENCES_FILE = OUTPUT_DIR / "sentences.json"
GERMAN_VOICE = "de-DE-Neural2-B"  # Male voice, change to Neural2-A for female
ENGLISH_VOICE = "en-US-Neural2-J"  # Female voice

class GermanAudioGenerator:
    def __init__(self):
        self.output_dir = OUTPUT_DIR
        self.sentences_file = SENTENCES_FILE
        self.tts_client = texttospeech.TextToSpeechClient()
        self.output_dir.mkdir(exist_ok=True)
        
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
    
    def _synthesize_speech(self, text, language_code, voice_name):
        """Generate speech using Google Cloud TTS"""
        synthesis_input = texttospeech.SynthesisInput(text=text)
        
        voice = texttospeech.VoiceSelectionParams(
            language_code=language_code,
            name=voice_name
        )
        
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=0.85  # Slightly slower for learning
        )
        
        response = self.tts_client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        return response.audio_content
    
    def generate_sentences(self, instruction):
        """Use Claude to generate German-English sentence pairs"""
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        
        prompt = f"""Generate 8-10 German-English sentence pairs based on this instruction: "{instruction}"

Requirements:
- Each sentence should demonstrate the requested grammar concept
- Keep sentences practical and conversational
- Provide the German sentence and its English translation
- Format as a JSON array of objects with "german" and "english" keys
- Use natural, spoken German appropriate for learners

Return ONLY the JSON array, no other text."""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Parse the JSON response
        response_text = message.content[0].text.strip()
        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        
        sentence_pairs = json.loads(response_text.strip())
        
        # Load existing sentences and add new ones
        sentences = self._load_sentences()
        
        for pair in sentence_pairs:
            # Create filename from English sentence
            filename = pair['english'].lower()
            filename = ''.join(c if c.isalnum() or c.isspace() else '' for c in filename)
            filename = '_'.join(filename.split())[:60]  # Limit length
            
            sentences[filename] = {
                "german": pair['german'],
                "english": pair['english'],
                "audio_generated": False
            }
        
        self._save_sentences(sentences)
        print(f"✓ Generated {len(sentence_pairs)} new sentence pairs")
        print(f"✓ Total sentences in database: {len(sentences)}")
        return sentence_pairs
    
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
        temp_german = self.output_dir / "temp_german.mp3"
        temp_english = self.output_dir / "temp_english.mp3"
        
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
        output_file = self.output_dir / f"{filename_key}.m4a"
        combined.export(output_file, format="ipod", codec="aac", bitrate="128k")
        
        # Clean up temp files
        temp_german.unlink()
        temp_english.unlink()
        
        # Update database
        sentences[filename_key]['audio_generated'] = True
        self._save_sentences(sentences)
        
        print(f"✓ Created: {output_file}")
        return True
    
    def create_all_audio(self):
        """Generate audio for all sentences that don't have it yet"""
        sentences = self._load_sentences()
        pending = [k for k, v in sentences.items() if not v.get('audio_generated', False)]
        
        print(f"Generating audio for {len(pending)} sentences...")
        
        for i, filename_key in enumerate(pending, 1):
            print(f"\n[{i}/{len(pending)}]", end=" ")
            self.create_audio(filename_key)
        
        print(f"\n✓ Complete! All audio files generated.")
    
    def list_sentences(self):
        """List all sentences in the database"""
        sentences = self._load_sentences()
        
        if not sentences:
            print("No sentences in database yet.")
            return
        
        print(f"\n{'='*80}")
        print(f"SENTENCE DATABASE ({len(sentences)} total)")
        print(f"{'='*80}\n")
        
        for filename, pair in sentences.items():
            status = "✓" if pair.get('audio_generated', False) else "○"
            print(f"{status} {filename}")
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
            print("Usage: python german_audio.py generate \"your instruction\"")
            sys.exit(1)
        instruction = sys.argv[2]
        generator.generate_sentences(instruction)
    
    elif command == "list":
        generator.list_sentences()
    
    elif command == "create-audio":
        if len(sys.argv) < 3:
            print("Usage: python german_audio.py create-audio \"filename_key\"")
            sys.exit(1)
        filename_key = sys.argv[2]
        generator.create_audio(filename_key)
    
    elif command == "create-all":
        generator.create_all_audio()
    
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)

if __name__ == "__main__":
    main()
