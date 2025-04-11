import cv2
from ultralytics import YOLO
import time
import datetime

model_path = "models/model.pt"
model = YOLO(model_path)

# Calibration: set the real-world size per pixel (cm per pixel)
cm_per_pixel = 0.05  # adjust based on your calibration
min_area_cm2 = 20.0  # minimum area threshold in cm^2

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Could not open webcam.")
    exit()

print("Starting live detection. Press 'q' to quit.")

face_last_seen_time = time.time()
alerted = False
count = 0

while True:
    ret, frame = cap.read()
    if not ret:
        print("Error: Failed to grab frame.")
        break

    results = model(frame, conf=0.4, verbose=False)
    current_time = time.time()
    detections = results[0].boxes
    face_found = False
    annotated_frame = frame.copy()

    if detections is not None:
        for box in detections:
            conf = float(box.conf[0])
            if conf >= 0.4:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                width_px = x2 - x1
                height_px = y2 - y1
                area_px = width_px * height_px
                area_cm2 = area_px * (cm_per_pixel ** 2)
                if area_cm2 > min_area_cm2:
                    face_found = True
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(
                        annotated_frame,
                        f"Area: {area_cm2:.2f} cm^2",
                        (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 255, 0),
                        2
                    )

    if face_found:
        face_last_seen_time = current_time
        count += 1
        print(f"Face detected {count} times... Its time is {datetime.datetime.now().strftime('%d-%m-%Y -- %H-%M-%S')}")
        alerted = False
    else:
        if (current_time - face_last_seen_time) >= 10 and not alerted:
            print("No face detected for 10 seconds!")
            alerted = True

    cv2.imshow("Live Face Detection", annotated_frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print("Live detection stopped.")
