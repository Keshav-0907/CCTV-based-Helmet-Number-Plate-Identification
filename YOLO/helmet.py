import cv2
import numpy as np
import easyocr
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
import base64
from datetime import datetime

from ultralytics import YOLO

cred = credentials.Certificate('./number-plate-31b93-firebase-adminsdk-hrqbg-0b72e0925f.json')
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://number-plate-31b93-default-rtdb.firebaseio.com'
})

frameWidth = 640
frameHeight = 480

plateCascade = cv2.CascadeClassifier("./haarcascade_russian_plate_number.xml")
minArea = 500

cap = cv2.VideoCapture(0)
cap.set(3, frameWidth)
cap.set(4, frameHeight)
cap.set(10, 150)
count = 0

reader = easyocr.Reader(['en'])

detected_plates = []

ref = db.reference('/detected_things')

yolo = YOLO('helmet.pt') 

while True:
    success, img = cap.read()

    if not success:
        break

    imgGray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    numberPlates = plateCascade.detectMultiScale(imgGray, 1.1, 4)

    for (x, y, w, h) in numberPlates:
        area = w * h
        if area > minArea:
            cv2.rectangle(img, (x, y), (x + w, y + h), (255, 0, 0), 2)
            imgRoi = img[y:y + h, x:x + w]

            results = yolo(imgRoi)

            # Check for helmet detection
            helmet_detected = False
            for res in results.pred:
                if res['label'] == 0:  # Assuming 'helmet' class index is 0
                    helmet_detected = True
                    helmet_coords = res['box']  # Extract helmet bounding box coordinates
                    xmin, ymin, xmax, ymax = helmet_coords
                    # Draw rectangle around detected helmet
                    cv2.rectangle(imgRoi, (int(xmin), int(ymin)), (int(xmax), int(ymax)), (0, 255, 0), 2)
                    break

            # If no helmet is detected, proceed with number plate recognition
            if not helmet_detected:
                result = reader.readtext(cv2.cvtColor(imgRoi, cv2.COLOR_BGR2RGB))

                if result:
                    text = result[0][1]
                    print("Detected Plate Number:", text)

                    if text not in detected_plates:
                        _, img_encoded = cv2.imencode('.jpg', imgRoi)
                        img_base64 = base64.b64encode(img_encoded).decode('utf-8')

                        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                        detected_plates.append({
                            "Number Plate": text,
                            "Image": img_base64,
                            "Timestamp": current_time
                        })
                        ref.set(detected_plates)

                        cv2.putText(img, text, (x, y - 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    cv2.imshow("Result", img)
    key = cv2.waitKey(1)
    if key & 0xFF == ord('s'):
        cv2.imwrite("./" + str(count) + ".jpg", imgRoi)
        count += 1
    elif key & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
