from ultralytics import YOLO

model = YOLO(r"yolo11n.pt")
model.predict(
    source=4,
    save=True,
    show=True,

)