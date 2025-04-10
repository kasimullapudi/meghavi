import cv2
from ultralytics import YOLO
import time
import datetime

model_path = "models/model.pt"
model = YOLO(model_path)

# Open a connection to the webcam.
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Could not open webcam.")
    exit()

print("Starting live detection. Press 'q' to quit.")

# Initialize timing variables.
face_last_seen_time = time.time()
alerted = False
count = 0

while True:
    ret, frame = cap.read()
    if not ret:
        print("Error: Failed to grab frame.")
        break

    # Run inference with a confidence threshold of 0.4 and suppress verbose output.
    results = model(frame, conf=0.4, verbose=False)
    current_time = time.time()

    # Process detections from the first (and only) result.
    detections = results[0].boxes
    face_found = False

    if detections is not None:
        for box in detections:
            conf = float(box.conf[0])
            if conf >= 0.4:
                face_found = True
                break

    # Update the timestamp if a face is detected.
    if face_found:
        face_last_seen_time = current_time
        count += 1
        print(f"Face detected {count} times... Its time is {datetime.datetime.now().strftime('%d-%m-%Y -- %H-%M-%S')}")
        alerted = False  # reset the alert flag for new absence
    else:
        # Check if no face has been seen for at least 10 seconds.
        if (current_time - face_last_seen_time) >= 10 and not alerted:
            print("No face detected for 10 seconds!")
            
            alerted = True  # Prevent further printing until a new face is found

    # Annotate and show the frame.
    annotated_frame = results[0].plot()
    cv2.imshow("Live Face Detection", annotated_frame)

    # Exit if 'q' is pressed.
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

print("Live detection stopped.")
