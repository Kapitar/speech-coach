import cv2
import numpy as np
import mediapipe as mp
from typing import List
from app.models import PostureMetrics


class PostureAnalyzer:
    """Analyzes posture using MediaPipe pose detection"""
    
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils
    
    def analyze(self, video_path: str) -> PostureMetrics:
        """Analyze posture from video"""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise Exception("Could not open video file")
        
        shoulder_alignments = []
        back_straightness_scores = []
        stability_scores = []
        confidence_scores = []
        
        prev_shoulder_center = None
        frame_count = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # Process every 5th frame for efficiency
            if frame_count % 5 == 0:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = self.pose.process(rgb_frame)
                
                if results.pose_landmarks:
                    landmarks = results.pose_landmarks.landmark
                    
                    # Get key points
                    left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
                    right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
                    left_hip = landmarks[self.mp_pose.PoseLandmark.LEFT_HIP]
                    right_hip = landmarks[self.mp_pose.PoseLandmark.RIGHT_HIP]
                    nose = landmarks[self.mp_pose.PoseLandmark.NOSE]
                    
                    # Only calculate if key landmarks are visible
                    if not (left_shoulder.visibility > 0.5 and right_shoulder.visibility > 0.5 and
                           left_hip.visibility > 0.5 and right_hip.visibility > 0.5):
                        continue  # Skip this frame if landmarks not visible
                    
                    # Calculate shoulder alignment (should be level)
                    shoulder_height_diff = abs(left_shoulder.y - right_shoulder.y)
                    shoulder_alignment = 1.0 - min(shoulder_height_diff * 10, 1.0)
                    shoulder_alignments.append(shoulder_alignment)
                    
                    # Calculate back straightness (shoulders and hips should be aligned)
                    # For a person standing straight, shoulders should be above hips
                    # Normal difference in MediaPipe coordinates is about 0.15-0.25
                    shoulder_center_y = (left_shoulder.y + right_shoulder.y) / 2
                    hip_center_y = (left_hip.y + right_hip.y) / 2
                    vertical_alignment = abs(shoulder_center_y - hip_center_y)
                    
                    # Expected difference for good posture (shoulders above hips)
                    expected_diff = 0.2
                    
                    # Score is high when alignment is close to expected difference
                    # Allow some tolerance (0.1 to 0.3 is reasonable)
                    if 0.1 <= vertical_alignment <= 0.3:
                        # Good alignment - score based on how close to expected
                        back_straightness = 1.0 - abs(vertical_alignment - expected_diff) * 2
                    elif vertical_alignment < 0.1:
                        # Too close (might be slouching or bad detection)
                        back_straightness = vertical_alignment * 5
                    else:
                        # Too far apart (bad posture or detection issue)
                        back_straightness = max(0.0, 1.0 - (vertical_alignment - 0.3) * 2)
                    
                    back_straightness_scores.append(back_straightness)
                    
                    # Calculate stability (how much the person moves)
                    current_shoulder_center = (left_shoulder.x + right_shoulder.x) / 2
                    if prev_shoulder_center is not None:
                        movement = abs(current_shoulder_center - prev_shoulder_center)
                        stability = 1.0 - min(movement * 20, 1.0)
                        stability_scores.append(stability)
                    prev_shoulder_center = current_shoulder_center
                    
                    # Calculate confidence score (open posture, shoulders back)
                    # Distance between shoulders indicates openness
                    shoulder_width = abs(left_shoulder.x - right_shoulder.x)
                    # Normalize based on typical shoulder width
                    confidence = min(shoulder_width * 3, 1.0)
                    confidence_scores.append(confidence)
            
            frame_count += 1
        
        cap.release()
        
        # Calculate averages
        avg_shoulder_alignment = np.mean(shoulder_alignments) if shoulder_alignments else 0.7
        avg_back_straightness = np.mean(back_straightness_scores) if back_straightness_scores else 0.7
        avg_stability = np.mean(stability_scores) if stability_scores else 0.7
        avg_confidence = np.mean(confidence_scores) if confidence_scores else 0.7
        
        # Generate feedback
        feedback = []
        if avg_shoulder_alignment < 0.7:
            feedback.append("Keep your shoulders level and aligned.")
        if avg_back_straightness < 0.7:
            feedback.append("Maintain a straight back with shoulders over hips.")
        if avg_stability < 0.6:
            feedback.append("Try to maintain a more stable, grounded posture.")
        if avg_confidence < 0.6:
            feedback.append("Open up your posture - keep your shoulders back and chest open.")
        
        if not feedback:
            feedback.append("Your posture is good! Maintain this confident stance.")
        
        return PostureMetrics(
            average_shoulder_alignment=float(avg_shoulder_alignment),
            average_back_straightness=float(avg_back_straightness),
            stability_score=float(avg_stability),
            confidence_score=float(avg_confidence),
            feedback=feedback
        )
    
    def __del__(self):
        if hasattr(self, 'pose'):
            self.pose.close()

