# VideoGenerator.py
import logging
import os
from pathlib import Path
from typing import List

from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip

logger = logging.getLogger(__name__)


class VideoGenerator:
    def __init__(self, default_output_fps: int = 24, default_image_resolution: tuple = (1280, 720)):
        """
        Initializes the VideoGenerator.

        Parameters:
        - default_output_fps (int): Default frames per second for the output video.
        - default_image_resolution (tuple): Default (width, height) to resize images to.
                                            Set to None to keep original image sizes (may result in varied aspect ratios).
        """
        self.default_output_fps = default_output_fps
        self.default_image_resolution = default_image_resolution

    def create_video_from_images_and_audio(
            self,
            image_paths: List[str],
            audio_path: str,
            output_video_path: str,
            fps: int = None,
            image_resolution: tuple = None
    ) -> bool:
        """
        Creates a video by sequencing images and setting an audio track.
        Each image will be displayed for an equal fraction of the total audio duration.

        Parameters:
        - image_paths (List[str]): A list of paths to image files.
        - audio_path (str): Path to the audio file.
        - output_video_path (str): Path where the final video will be saved.
        - fps (int, optional): Frames per second for the output video. Defaults to self.default_output_fps.
        - image_resolution (tuple, optional): (width, height) to resize images. Defaults to self.default_image_resolution.

        Returns:
        - bool: True if video creation was successful, False otherwise.
        """
        if not image_paths:
            logger.error("No image paths provided. Cannot create video.")
            return False

        if not os.path.exists(audio_path):
            logger.error(f"Audio file not found: {audio_path}")
            return False

        output_fps = fps if fps is not None else self.default_output_fps
        target_resolution = image_resolution if image_resolution is not None else self.default_image_resolution

        try:
            logger.info(f"Loading audio from: {audio_path}")
            audio_clip = AudioFileClip(audio_path)
            audio_duration = audio_clip.duration

            if audio_duration <= 0:
                logger.error("Audio duration is zero or negative. Cannot determine image display times.")
                return False

            num_images = len(image_paths)
            duration_per_image = audio_duration / num_images
            logger.info(
                f"Audio duration: {audio_duration:.2f}s. Number of images: {num_images}. Duration per image: {duration_per_image:.2f}s.")

            video_clips = []
            for i, img_path in enumerate(image_paths):
                if not os.path.exists(img_path):
                    logger.warning(f"Image file not found: {img_path}. Skipping.")
                    continue

                try:
                    img_clip = ImageClip(img_path)
                    if target_resolution:
                        # Resize while maintaining aspect ratio, fitting within target_resolution
                        # and adding black bars if necessary (or cropping, depending on strategy)
                        # For simplicity, let's resize and let moviepy handle aspect.
                        # A more robust solution might involve padding.
                        img_clip = img_clip.resize(height=target_resolution[1])  # Resize based on height
                        if img_clip.w > target_resolution[0]:  # If too wide, resize based on width
                            img_clip = img_clip.resize(width=target_resolution[0])

                        # To center and pad to target_resolution:
                        if target_resolution:
                            img_clip = CompositeVideoClip([img_clip.set_position('center')],
                                                          size=target_resolution,
                                                          bg_color=(0, 0, 0))  # Black background

                    img_clip = img_clip.set_duration(duration_per_image)
                    video_clips.append(img_clip)
                    logger.debug(f"Processed image {i + 1}/{num_images}: {img_path}")
                except Exception as e:
                    logger.error(f"Error processing image {img_path}: {e}. Skipping.")
                    continue

            if not video_clips:
                logger.error("No valid images could be processed to create video clips.")
                audio_clip.close()
                return False

            final_video_clip = concatenate_videoclips(video_clips, method="compose")
            final_video_clip = final_video_clip.set_audio(audio_clip)

            # Ensure the video duration exactly matches the audio duration
            # This can be important if concatenate_videoclips has minor precision issues
            final_video_clip = final_video_clip.set_duration(audio_duration)

            logger.info(f"Writing final video to: {output_video_path} with FPS: {output_fps}")
            # Use libx264 for H.264 video (common) and aac for audio.
            # threads can be used to speed up encoding if ffmpeg supports it.
            # preset can be 'ultrafast', 'fast', 'medium', 'slow', 'slower' (tradeoff speed vs compression)
            final_video_clip.write_videofile(
                output_video_path,
                fps=output_fps,
                codec="libx264",
                audio_codec="aac",
                temp_audiofile=f"{Path(output_video_path).stem}_temp_audio.m4a",  # moviepy recommendation
                remove_temp=True,
                threads=os.cpu_count()  # Use available CPU cores
                # preset="medium" # Good balance
            )

            logger.info("Video creation successful.")
            return True

        except Exception as e:
            logger.error(f"An error occurred during video creation: {e}", exc_info=True)
            return False
        finally:
            # Close clips if they were opened
            if 'audio_clip' in locals() and audio_clip:
                audio_clip.close()
            if 'video_clips' in locals():
                for clip in video_clips:
                    clip.close()
            if 'final_video_clip' in locals() and final_video_clip:
                final_video_clip.close()
