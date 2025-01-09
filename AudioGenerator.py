import shutil
import subprocess
import tempfile
from pathlib import Path

from tqdm import tqdm


class AudioGenerator:
    def __init__(self, voice="Paulina", output_dir=Path(tempfile.mkdtemp(prefix="audio_")),
                 final_output="final_audio.m4a"):
        """
        Initialize the AudioGenerator class.

        Parameters:
        - voice (str): The voice to use for macOS 'say' command.
        - output_dir (str): Directory to store intermediate audio files.
        - final_output (str): File name for the final merged audio file.
        """
        self.voice = voice
        self.output_dir = Path(output_dir)
        self.final_output = final_output
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def text_to_audio(self, text, output_file):
        """
        Converts the given text to audio using macOS's 'say' command and saves as .m4a.

        Parameters:
        - text (str): The text to convert to audio.
        - output_file (str): The name of the output file.
        """

        try:
            temp_file = self.output_dir / "chunk_temp.txt"
            with open(temp_file, "w") as f:
                f.write(text)
            subprocess.run(["say", "-v", self.voice, "-o", output_file, "-f", str(temp_file)], check=True)
            print(f"Audio saved: {output_file}")
        except subprocess.CalledProcessError as e:
            print(f"Error during text-to-audio conversion: {e}")
            raise

    def merge_audio_files(self, audio_files):
        """
        Merges multiple .m4a audio files into one using ffmpeg.

        Parameters:
        - audio_files (list): List of audio file paths to merge.
        """
        try:
            # Create a text file listing all input audio files
            file_list = self.output_dir / "file_list.txt"
            with open(file_list, "w") as f:
                for audio in audio_files:
                    f.write(f"file '{audio}'\n")

            # Use ffmpeg to concatenate the audio files
            subprocess.run(
                ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(file_list), "-c:a", "libfdk_aac", "-b:a", "64k",
                 self.final_output],
                check=True
            )
            print(f"All audio files merged into: {self.final_output}")
        except subprocess.CalledProcessError as e:
            print(f"Error during audio merging: {e}")
            raise
        finally:
            # Clean up the temporary file list
            if file_list.exists():
                file_list.unlink()

    def process_texts(self, texts):
        """
        Converts a list of texts to individual .m4a audio files and merges them into one final .m4a file.

        Parameters:
        - texts (list): List of strings to convert to audio.
        """
        audio_files = []

        try:
            # Convert each text to an individual .m4a audio file
            for i, text in tqdm(enumerate(texts, start=1), desc="Processing Texts", unit="Text"):
                if "text" in text:
                    audio_file = self.output_dir / f"chunk_{i:04d}.m4a"
                    self.text_to_audio(text["text"]
                                       .replace("”", "\"")
                                       .replace("“", "\"")
                                       .replace("’", "'")
                                       .replace("‘", "'")
                                       .replace("—", "-")
                                       , audio_file)
                    audio_files.append(audio_file)

            # Merge all .m4a audio files into one
            self.merge_audio_files(audio_files)
        finally:
            # Clean up intermediate audio files
            if self.output_dir.exists():
                shutil.rmtree(self.output_dir)
                print(f"Intermediate audio files deleted: {self.output_dir}")
