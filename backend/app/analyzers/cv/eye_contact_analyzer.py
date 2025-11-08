import cv2
import numpy as np
import mediapipe as mp
from typing import List, Tuple
from app.models import EyeContactMetrics


class EyeContactAnalyzer:
    """Analyzes eye contact using MediaPipe face detection and gaze estimation"""
    
    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils
    
    def estimate_gaze_direction(self, landmarks, frame_shape: Tuple[int, int]) -> Tuple[float, float]:
        """Estimate gaze direction based on eye landmarks"""
        # Key eye landmarks
        left_eye_left = landmarks[33]
        left_eye_right = landmarks[133]
        left_eye_top = landmarks[159]
        left_eye_bottom = landmarks[145]
        
        right_eye_left = landmarks[362]
        right_eye_right = landmarks[263]
        right_eye_top = landmarks[386]
        right_eye_bottom = landmarks[374]
        
        # Calculate eye centers
        left_eye_center_x = (left_eye_left.x + left_eye_right.x) / 2
        left_eye_center_y = (left_eye_top.y + left_eye_bottom.y) / 2
        
        right_eye_center_x = (right_eye_left.x + right_eye_right.x) / 2
        right_eye_center_y = (right_eye_top.y + right_eye_bottom.y) / 2
        
        # Calculate iris position (simplified - using inner eye corners)
        left_iris = landmarks[468]  # Left iris center
        right_iris = landmarks[473]  # Right iris center
        
        # Calculate gaze direction relative to eye center
        # If iris is centered, looking forward
        left_gaze_x = left_iris.x - left_eye_center_x
        left_gaze_y = left_iris.y - left_eye_center_y
        
        right_gaze_x = right_iris.x - right_eye_center_x
        right_gaze_y = right_iris.y - right_eye_center_y
        
        # Average gaze direction
        avg_gaze_x = (left_gaze_x + right_gaze_x) / 2
        avg_gaze_y = (left_gaze_y + right_gaze_y) / 2
        
        return avg_gaze_x, avg_gaze_y
    
    def is_looking_at_camera(self, gaze_x: float, gaze_y: float, threshold: float = 0.05) -> bool:
        """Determine if person is looking at camera based on gaze direction"""
        # If gaze is close to center (0, 0), looking at camera
        return abs(gaze_x) < threshold and abs(gaze_y) < threshold
    
    def analyze(self, video_path: str) -> EyeContactMetrics:
        """Analyze eye contact from video"""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise Exception("Could not open video file")
        
        eye_contact_frames = 0
        total_frames = 0
        eye_contact_durations = []
        current_duration = 0
        gaze_shifts = 0
        prev_looking = None
        
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        frame_interval = max(1, int(fps / 10))  # Sample ~10 times per second
        
        frame_count = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_count % frame_interval == 0:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = self.face_mesh.process(rgb_frame)
                
                if results.multi_face_landmarks:
                    landmarks = results.multi_face_landmarks[0].landmark
                    gaze_x, gaze_y = self.estimate_gaze_direction(landmarks, frame.shape)
                    is_looking = self.is_looking_at_camera(gaze_x, gaze_y)
                    
                    total_frames += 1
                    
                    if is_looking:
                        eye_contact_frames += 1
                        current_duration += 1
                    else:
                        if current_duration > 0:
                            eye_contact_durations.append(current_duration / (fps / frame_interval))
                            current_duration = 0
                    
                    # Track gaze shifts
                    if prev_looking is not None and prev_looking != is_looking:
                        gaze_shifts += 1
                    prev_looking = is_looking
            
            frame_count += 1
        
        cap.release()
        
        # Calculate metrics
        eye_contact_percentage = (eye_contact_frames / total_frames * 100) if total_frames > 0 else 0
        avg_eye_contact_duration = np.mean(eye_contact_durations) if eye_contact_durations else 0
        
        # Calculate gaze shifts per minute
        duration_seconds = frame_count / fps if fps > 0 else 1
        duration_minutes = duration_seconds / 60
        gaze_shifts_per_min = gaze_shifts / duration_minutes if duration_minutes > 0 else 0
        
        # Direct eye contact score (0-1)
        direct_eye_contact_score = min(eye_contact_percentage / 100, 1.0)
        
        # Generate feedback
        feedback = []
        if eye_contact_percentage < 60:
            feedback.append(f"Your eye contact is {eye_contact_percentage:.1f}%. Aim for 70-80% for better engagement.")
        if gaze_shifts_per_min > 20:
            feedback.append(f"You shift your gaze {gaze_shifts_per_min:.1f} times per minute. Try to maintain eye contact for 3-5 seconds.")
        if avg_eye_contact_duration < 2:
            feedback.append("Your eye contact durations are brief. Practice holding eye contact longer.")
        
        if not feedback:
            feedback.append("Excellent eye contact! You're engaging well with your audience.")
        
        return EyeContactMetrics(
            eye_contact_percentage=float(eye_contact_percentage),
            average_eye_contact_duration=float(avg_eye_contact_duration),
            gaze_shifts_per_minute=float(gaze_shifts_per_min),
            direct_eye_contact_score=float(direct_eye_contact_score),
            feedback=feedback
        )
    
    def __del__(self):
        if hasattr(self, 'face_mesh'):
            self.face_mesh.close()

