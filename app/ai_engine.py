import cv2
import torch
import torch.nn as nn
from torchvision import transforms
from PIL import Image
from ultralytics import YOLO
import numpy as np
import os
import timm

class MobileNetV4Classifier(nn.Module):
    def __init__(self, model_name, num_classes, dropout=0.1):
        super().__init__()
        # Using timm to create MobileNetV4. 
        # Common names: mobilenetv4_conv_small, mobilenetv4_conv_medium, etc.
        self.backbone = timm.create_model(model_name, pretrained=False, num_classes=0)
        
        # Get the number of features from the backbone
        # Set to eval to avoid BatchNorm errors with batch size 1
        self.backbone.eval()
        dummy_input = torch.zeros(1, 3, 224, 224)
        with torch.no_grad():
            features = self.backbone(dummy_input)
            dim = features.shape[1]
            
        self.head = nn.Sequential(
            nn.LayerNorm(dim),
            nn.Dropout(dropout),
            nn.Linear(dim, 512),
            nn.GELU(),
            nn.Dropout(dropout / 2),
            nn.Linear(512, num_classes),
        )

    def forward(self, x):
        return self.head(self.backbone(x))

class AIInspectionEngine:
    def __init__(self, detection_model_path="models/engine_best (2).pt", classification_model_path="models/saddle_best.pth"):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Using device: {self.device} for Inference")
        
        # Load Detection Model
        try:
            self.yolo_model = YOLO(detection_model_path)
            print(f"YOLO detection model loaded: {detection_model_path}")
        except Exception as e:
            print(f"Error loading YOLO model: {e}")
            self.yolo_model = None

        # Load Classification Model
        try:
            self.cls_model, self.class_names, self.img_size = self._load_classification_model(classification_model_path, self.device)
            print(f"MobileNetV4 classification model loaded from {classification_model_path}")
        except Exception as e:
            print(f"Error loading classification model: {e}")
            self.cls_model = None
            
        self.transform = transforms.Compose([
            transforms.Resize((self.img_size, self.img_size) if hasattr(self, 'img_size') else (224, 224)),
            transforms.ToTensor(),
        ])

    def _load_classification_model(self, path, device):
        ckpt = torch.load(path, map_location=device, weights_only=False)
        # Default to a mobilenetv4 variant if not specified
        model_name = ckpt.get("model_name", "mobilenetv4_conv_small")
        num_classes = ckpt.get("num_classes", 3)
        
        model = MobileNetV4Classifier(
            model_name,
            num_classes,
        ).to(device)
        
        model.load_state_dict(ckpt["model_state"])
        model.eval()
        class_names = ckpt.get("class_names", [f"class_{i}" for i in range(num_classes)])
        img_size = ckpt.get("img_size", 224)
        return model, class_names, img_size

    def classify_saddles_batch(self, saddle_images):
        if not self.cls_model or not saddle_images:
            return []
        
        batch_tensors = [] 
        for img_rgb in saddle_images: # expects rgb
            pil_img = Image.fromarray(img_rgb)
            input_tensor = self.transform(pil_img)
            batch_tensors.append(input_tensor)

        batch_tensor = torch.stack(batch_tensors).to(self.device)
        with torch.no_grad():
            logits = self.cls_model(batch_tensor)
            probs = torch.softmax(logits, dim=1)
            _, predicted_indices = torch.max(probs, 1)

        predictions = [self.class_names[idx.item()] for idx in predicted_indices]
        return predictions

    def process_frame(self, frame_bgr):
        """
        Processes a single frame.
        Returns: 
           annotated_frame (numpy array BGR)
           verdict (dict containing stats and overall PASS/FAIL)
        """
        if self.yolo_model is None:
            return frame_bgr, {"status": "UNKNOWN", "message": "Models not loaded"}
            
        results = self.yolo_model.track(frame_bgr, persist=True, conf=0.5, verbose=False)
        
        engines = []
        saddles = []
        
        if results and results[0].boxes:
            boxes = results[0].boxes
            for box in boxes:
                cls_id = int(box.cls[0])
                label = self.yolo_model.names[cls_id]
                x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
                
                if label.lower() == "engine":
                    engines.append((x1, y1, x2, y2))
                elif label.lower() == "saddle":
                    saddles.append((x1, y1, x2, y2))

        annotated_frame = results[0].plot() if results else frame_bgr.copy()
        final_verdict = "UNKNOWN"
        engines_processed = 0
        total_pass = 0
        total_fail = 0

        for (ex1, ey1, ex2, ey2) in engines:
            saddles_in_engine = []
            
            for (sx1, sy1, sx2, sy2) in saddles:
                cx = (sx1 + sx2) // 2
                cy = (sy1 + sy2) // 2
                if ex1 <= cx <= ex2 and ey1 <= cy <= ey2:
                    saddles_in_engine.append((sx1, sy1, sx2, sy2))

            if len(saddles_in_engine) == 4:
                cropped_images_rgb = []
                frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                
                for (sx1, sy1, sx2, sy2) in saddles_in_engine:
                    crop_rgb = frame_rgb[sy1:sy2, sx1:sx2]
                    if crop_rgb.size > 0:
                        cropped_images_rgb.append(crop_rgb)

                if len(cropped_images_rgb) == 4:
                    engines_processed += 1
                    preds = self.classify_saddles_batch(cropped_images_rgb)
                    
                    is_pass = all(p.lower() == "perfect" for p in preds)
                    if is_pass:
                        status_color = (0, 255, 0)
                        status_text = "PASS"
                        total_pass += 1
                    else:
                        status_color = (0, 0, 255)
                        status_text = "FAIL"
                        total_fail += 1
                        
                    final_verdict = status_text # Updates to the last engine's verdict in the frame
                    
                    cv2.rectangle(annotated_frame, (ex1, ey1), (ex2, ey2), status_color, 4)
                    (text_w, text_h), _ = cv2.getTextSize(f"ENGINE: {status_text}", cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)
                    cv2.rectangle(annotated_frame, (ex1, ey1 - text_h - 10), (ex1 + text_w, ey1), status_color, -1)
                    cv2.putText(annotated_frame, f"ENGINE: {status_text}", (ex1, ey1 - 5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
                    
                    for (sx1, sy1, sx2, sy2), pred in zip(saddles_in_engine, preds):
                        scol = (0, 255, 0) if pred.lower() == "perfect" else (0, 0, 255)
                        cv2.rectangle(annotated_frame, (sx1, sy1), (sx2, sy2), scol, 2)
                        cv2.putText(annotated_frame, pred.upper(), (sx1, sy1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, scol, 2)

            elif len(saddles_in_engine) > 0:
                cv2.putText(annotated_frame, f"Saddles: {len(saddles_in_engine)}/4", 
                            (ex1, ey2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                            
        return annotated_frame, {
            "status": final_verdict if engines_processed > 0 else "UNKNOWN",
            "engines_processed": engines_processed,
            "pass_count": total_pass,
            "fail_count": total_fail
        }
