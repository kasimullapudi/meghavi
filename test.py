import os
import cv2
import math
import numpy as np
import mediapipe as mp
from ultralytics import YOLO
import requests
# --- Configuration ---
MODEL_PATH        = "models/model.pt"
OUTPUT_DIR        = "captured_faces"
NUM_FRAMES        = 1        # capture only one frame
MAX_DISTANCE_CM   = 100.0    # only capture if under 1 meter

# quality thresholds
AREA_THRESHOLD       = 5000     # px²
SHARPNESS_THRESHOLD  = 100.0    # laplacian var
YAW_THRESHOLD        = 10       # degrees
PITCH_THRESHOLD      = 10       # degrees

# power-law coefficients from calibration
a = 9703.20
b = -0.4911842338691967

# head-pose model points
MODEL_POINTS = np.array([
    (0.0,   0.0,    0.0),      # nose tip
    (0.0,  -330.0, -65.0),     # chin
    (-165.0,170.0, -135.0),    # left eye corner
    (165.0, 170.0, -135.0),    # right eye corner
    (-150.0,-150.0,-125.0),    # left mouth corner
    (150.0, -150.0,-125.0)     # right mouth corner
], dtype=np.float64)

LANDMARK_IDS = {
    "nose_tip":    1,
    "chin":        199,
    "left_eye":    33,
    "right_eye":   263,
    "left_mouth":  61,
    "right_mouth": 291
}

# initialize models
model      = YOLO(MODEL_PATH)
mp_face    = mp.solutions.face_mesh
face_mesh  = mp_face.FaceMesh(static_image_mode=False)

os.makedirs(OUTPUT_DIR, exist_ok=True)

def estimate_head_pose(landmarks, img_size):
    image_points = np.array([
        (landmarks[LANDMARK_IDS["nose_tip"]][0]  * img_size[1],
         landmarks[LANDMARK_IDS["nose_tip"]][1]  * img_size[0]),
        (landmarks[LANDMARK_IDS["chin"]][0]      * img_size[1],
         landmarks[LANDMARK_IDS["chin"]][1]      * img_size[0]),
        (landmarks[LANDMARK_IDS["left_eye"]][0]  * img_size[1],
         landmarks[LANDMARK_IDS["left_eye"]][1]  * img_size[0]),
        (landmarks[LANDMARK_IDS["right_eye"]][0] * img_size[1],
         landmarks[LANDMARK_IDS["right_eye"]][1] * img_size[0]),
        (landmarks[LANDMARK_IDS["left_mouth"]][0]* img_size[1],
         landmarks[LANDMARK_IDS["left_mouth"]][1]* img_size[0]),
        (landmarks[LANDMARK_IDS["right_mouth"]][0]*img_size[1],
         landmarks[LANDMARK_IDS["right_mouth"]][1]*img_size[0])
    ], dtype=np.float64)

    focal_length = img_size[1]
    center       = (img_size[1]/2, img_size[0]/2)
    cam_matrix   = np.array([[focal_length, 0, center[0]],
                             [0, focal_length, center[1]],
                             [0, 0, 1]], dtype=np.float64)
    dist_coeffs = np.zeros((4,1))

    success, rvec, _ = cv2.solvePnP(
        MODEL_POINTS, image_points, cam_matrix, dist_coeffs,
        flags=cv2.SOLVEPNP_ITERATIVE
    )
    if not success:
        return None, None

    R, _ = cv2.Rodrigues(rvec)
    sy = math.sqrt(R[0,0]**2 + R[1,0]**2)
    pitch = math.degrees(math.atan2(-R[2,0], sy))
    yaw   = math.degrees(math.atan2(R[1,0], R[0,0]))
    return yaw, pitch

def variance_of_laplacian(img):
    return cv2.Laplacian(img, cv2.CV_64F).var()

cap = cv2.VideoCapture("http://192.168.31.116:5000/video")
selected = []

print("Looking for a single clear, frontal face under 1 m...")

while len(selected) < NUM_FRAMES:
    ret, frame = cap.read()
    if not ret:
        break

    results     = model(frame, conf=0.4, verbose=False)
    detections  = results[0].boxes
    if detections is None:
        continue

    # Try to get landmarks
    rgb         = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mesh_result = face_mesh.process(rgb)
    if not mesh_result.multi_face_landmarks:
        print("Face detected but all landmarks not found.")
        continue
    landmarks = [(lm.x, lm.y) for lm in mesh_result.multi_face_landmarks[0].landmark]

    face_detected = False

    for box in detections:
        conf = float(box.conf[0])
        if conf < 0.4:
            continue

        x1, y1, x2, y2 = map(int, box.xyxy[0])
        area_px       = (x2-x1)*(y2-y1)
        if area_px < AREA_THRESHOLD:
            continue

        face_detected = True
        distance_cm   = a * (area_px ** b)

        if distance_cm > MAX_DISTANCE_CM:
            print(f"Face detected but not under distance. Distance: {distance_cm:.2f} cm")
            continue

        yaw, pitch = estimate_head_pose(landmarks, frame.shape[:2])
        if yaw is None or abs(yaw) > YAW_THRESHOLD or abs(pitch) > PITCH_THRESHOLD:
            continue

        roi       = frame[y1:y2, x1:x2]
        gray      = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        sharpness = variance_of_laplacian(gray)
        if sharpness < SHARPNESS_THRESHOLD:
            continue
        # Passed all checks: capture this frame
        print(f"Captured! distance={distance_cm:.1f} cm, area={area_px}, yaw={yaw:.1f}°")
        selected.append(frame.copy())
        break  # exit for-loop once captured

# Save the one captured face
if selected:
    cv2.imwrite(os.path.join(OUTPUT_DIR, "face.jpg"), selected[0])
    print(f"Saved to {OUTPUT_DIR}/face.jpg")
    url = "https://meghavi-kiosk-api.onrender.com/api/faces/upload"
    file_path = "captured_faces/face.jpg"

    with open(file_path, "rb") as image_file:
        files = {"image": image_file}
        response = requests.post(url, files=files)
    print(type(response.status_code))
    if response.status_code == 201:
        print("success",response.status_code)
    else:
        print("failed",response.status_code)

cap.release()
cv2.destroyAllWindows()
