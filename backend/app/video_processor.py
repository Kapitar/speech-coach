import cv2
import os
from moviepy.editor import VideoFileClip
import tempfile


class VideoProcessor:
    """Handles video and audio extraction"""
    
    def __init__(self, video_path: str):
        self.video_path = video_path
        self.cap = None
        
    def extract_audio(self):
        """Extract audio from video file"""
        try:
            video = VideoFileClip(self.video_path)
            audio_path = tempfile.mktemp(suffix='.wav')
            video.audio.write_audiofile(audio_path, verbose=False, logger=None)
            video.close()
            return self.video_path, audio_path
        except Exception as e:
            raise Exception(f"Failed to extract audio: {str(e)}")
    
    def get_video_properties(self):
        """Get video properties like fps, duration, resolution"""
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            raise Exception("Could not open video file")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = frame_count / fps if fps > 0 else 0
        
        cap.release()
        
        return {
            'fps': fps,
            'frame_count': frame_count,
            'width': width,
            'height': height,
            'duration': duration
        }
    
    def get_frames(self, sample_rate: int = 1):
        """Get frames from video at specified sample rate (every Nth frame)"""
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            raise Exception("Could not open video file")
        
        frames = []
        frame_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_count % sample_rate == 0:
                frames.append(frame)
            
            frame_count += 1
        
        cap.release()
        return frames
    
    def __del__(self):
        if self.cap is not None:
            self.cap.release()

