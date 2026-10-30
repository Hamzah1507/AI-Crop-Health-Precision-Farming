"""
Phase 2: PlantVillage Crop Disease Classification Model Training & Evaluation

Downloads a verified subset of the open PlantVillage dataset (CC BY-SA 3.0 / CC BY 4.0),
performs deterministic train/val/test splits with SHA-256 deduplication,
fine-tunes a PyTorch ResNet18 model using transfer learning,
and evaluates performance on held-out test images.
"""

import os
import sys
import json
import time
import random
import hashlib
import urllib.request
import urllib.parse
from typing import List, Dict, Tuple

import cv2
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.metrics import classification_report, confusion_matrix

# Set deterministic seeds
RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)
torch.manual_seed(RANDOM_SEED)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "ml", "data", "plantvillage_subset")
MODELS_DIR = os.path.join(BASE_DIR, "ml", "models")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

# 18 Target classes: 6 crops, all with both diseased conditions and explicit healthy classes
TARGET_CLASSES = [
    "Apple___Apple_scab",
    "Apple___Black_rot",
    "Apple___healthy",
    "Corn_(maize)___Common_rust_",
    "Corn_(maize)___Northern_Leaf_Blight",
    "Corn_(maize)___healthy",
    "Grape___Black_rot",
    "Grape___healthy",
    "Pepper,_bell___Bacterial_spot",
    "Pepper,_bell___healthy",
    "Potato___Early_blight",
    "Potato___Late_blight",
    "Potato___healthy",
    "Tomato___Bacterial_spot",
    "Tomato___Early_blight",
    "Tomato___Late_blight",
    "Tomato___Leaf_Mold",
    "Tomato___healthy",
]

SAMPLES_PER_CLASS = 50
BATCH_SIZE = 16
NUM_EPOCHS = 5
LEARNING_RATE = 0.001

# Standard ImageNet normalization parameters
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


# --- 1. ResNet18 Architecture in Pure PyTorch ---
def conv3x3(in_planes, out_planes, stride=1):
    return nn.Conv2d(in_planes, out_planes, kernel_size=3, stride=stride, padding=1, bias=False)

def conv1x1(in_planes, out_planes, stride=1):
    return nn.Conv2d(in_planes, out_planes, kernel_size=1, stride=stride, bias=False)

class BasicBlock(nn.Module):
    expansion = 1
    def __init__(self, inplanes, planes, stride=1, downsample=None):
        super().__init__()
        self.conv1 = conv3x3(inplanes, planes, stride)
        self.bn1 = nn.BatchNorm2d(planes)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = conv3x3(planes, planes)
        self.bn2 = nn.BatchNorm2d(planes)
        self.downsample = downsample
    def forward(self, x):
        identity = x
        out = self.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        if self.downsample is not None:
            identity = self.downsample(x)
        out += identity
        return self.relu(out)

class ResNet18(nn.Module):
    def __init__(self, num_classes=18):
        super().__init__()
        self.inplanes = 64
        self.conv1 = nn.Conv2d(3, 64, kernel_size=7, stride=2, padding=3, bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.relu = nn.ReLU(inplace=True)
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        self.layer1 = self._make_layer(64, 2)
        self.layer2 = self._make_layer(128, 2, stride=2)
        self.layer3 = self._make_layer(256, 2, stride=2)
        self.layer4 = self._make_layer(512, 2, stride=2)
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(512, num_classes)
    def _make_layer(self, planes, blocks, stride=1):
        downsample = None
        if stride != 1 or self.inplanes != planes:
            downsample = nn.Sequential(conv1x1(self.inplanes, planes, stride), nn.BatchNorm2d(planes))
        layers = [BasicBlock(self.inplanes, planes, stride, downsample)]
        self.inplanes = planes
        for _ in range(1, blocks):
            layers.append(BasicBlock(self.inplanes, planes))
        return nn.Sequential(*layers)
    def forward(self, x):
        x = self.maxpool(self.relu(self.bn1(self.conv1(x))))
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)
        x = self.avgpool(x)
        return self.fc(torch.flatten(x, 1))


# --- 2. Dataset Fetching & Caching ---
def fetch_plantvillage_subset() -> List[Dict]:
    """Download images for target classes from GitHub with SHA-256 deduplication."""
    print("=" * 70)
    print("Step 1: Fetching PlantVillage repository tree...")
    tree_url = "https://api.github.com/repos/spMohanty/PlantVillage-Dataset/git/trees/master?recursive=1"
    req = urllib.request.Request(tree_url, headers={"User-Agent": "CropHealthAI-Research/1.0"})
    res = urllib.request.urlopen(req, timeout=20)
    tree_data = json.loads(res.read().decode())
    tree = tree_data.get("tree", [])

    # Group color images by class
    class_files = {c: [] for c in TARGET_CLASSES}
    for item in tree:
        path = item.get("path", "")
        if item.get("type") == "blob" and path.startswith("raw/color/"):
            parts = path.split("/")
            if len(parts) >= 4:
                cls_name = parts[2]
                if cls_name in class_files:
                    class_files[cls_name].append(path)

    # For classes truncated by git tree (e.g. Tomato classes), fetch contents directly
    for cls_name in TARGET_CLASSES:
        if len(class_files[cls_name]) < SAMPLES_PER_CLASS:
            try:
                c_url = f"https://api.github.com/repos/spMohanty/PlantVillage-Dataset/contents/raw/color/{urllib.parse.quote(cls_name)}"
                req = urllib.request.Request(c_url, headers={"User-Agent": "CropHealthAI-Research/1.0"})
                res = urllib.request.urlopen(req, timeout=12)
                f_list = json.loads(res.read().decode())
                class_files[cls_name] = [f"raw/color/{cls_name}/{f['name']}" for f in f_list if f.get("type") == "file"]
            except Exception as e:
                print(f"Warning: Failed listing contents for {cls_name}: {e}")

    samples = []
    seen_hashes = set()
    total_downloaded = 0

    print(f"Targeting {len(TARGET_CLASSES)} classes ({SAMPLES_PER_CLASS} images/class)...")
    download_tasks = []
    class_assignments = []

    for cls_idx, cls_name in enumerate(TARGET_CLASSES):
        cls_dir = os.path.join(DATA_DIR, cls_name)
        os.makedirs(cls_dir, exist_ok=True)
        available = class_files[cls_name]
        random.seed(RANDOM_SEED + cls_idx)
        selected = random.sample(available, min(len(available), SAMPLES_PER_CLASS))

        for rel_path in selected:
            fname = os.path.basename(rel_path)
            local_path = os.path.join(cls_dir, fname)
            download_tasks.append((rel_path, local_path))
            class_assignments.append((cls_name, cls_idx, local_path))

    def _fetch_one(item):
        rel_path, local_path = item
        if not os.path.exists(local_path):
            raw_url = f"https://raw.githubusercontent.com/spMohanty/PlantVillage-Dataset/master/{urllib.parse.quote(rel_path)}"
            for _ in range(3):
                try:
                    req = urllib.request.Request(raw_url, headers={"User-Agent": "CropHealthAI-Research/1.0"})
                    data = urllib.request.urlopen(req, timeout=15).read()
                    with open(local_path, "wb") as f:
                        f.write(data)
                    return 1
                except Exception:
                    time.sleep(0.3)
            return 0
        return 0

    from concurrent.futures import ThreadPoolExecutor
    print(f"Downloading dataset images using 10 worker threads...")
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(_fetch_one, download_tasks))
    total_downloaded = sum(results)

    cls_counts = {c: 0 for c in TARGET_CLASSES}
    for cls_name, cls_idx, local_path in class_assignments:
        if not os.path.exists(local_path) or os.path.getsize(local_path) == 0:
            continue
        with open(local_path, "rb") as f:
            h = hashlib.sha256(f.read()).hexdigest()

        if h in seen_hashes:
            continue
        seen_hashes.add(h)

        samples.append({
            "path": local_path,
            "class_name": cls_name,
            "label": cls_idx,
            "sha256": h
        })
        cls_counts[cls_name] += 1

    for i, c in enumerate(TARGET_CLASSES):
        print(f"  [{i+1:02d}/{len(TARGET_CLASSES)}] {c:<38} -> {cls_counts[c]} unique images")

    print(f"Total unique images collected: {len(samples)} (new downloads: {total_downloaded})")
    return samples


# --- 3. PyTorch Dataset & Preprocessing ---
class LeafDataset(Dataset):
    def __init__(self, items: List[Dict], is_train: bool = False):
        self.items = items
        self.is_train = is_train

    def __len__(self):
        return len(self.items)

    def __getitem__(self, idx):
        item = self.items[idx]
        img = cv2.imread(item["path"])
        if img is None:
            # Fallback black canvas
            img = np.zeros((224, 224, 3), dtype=np.uint8)
        else:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img = cv2.resize(img, (224, 224), interpolation=cv2.INTER_LINEAR)

        # Basic data augmentation on training set
        if self.is_train:
            if random.random() > 0.5:
                img = cv2.flip(img, 1)  # horizontal flip
            if random.random() > 0.5:
                img = cv2.flip(img, 0)  # vertical flip

        # Normalize with ImageNet mean and std
        norm_img = (img.astype(np.float32) / 255.0 - IMAGENET_MEAN) / IMAGENET_STD
        # Transpose from (H, W, C) to (C, H, W)
        tensor_img = torch.from_numpy(norm_img.transpose(2, 0, 1))
        label = item["label"]
        return tensor_img, label


# --- 4. Training & Evaluation Pipeline ---
def train_and_evaluate():
    samples = fetch_plantvillage_subset()

    # Stratified 70 / 15 / 15 Split
    train_items, val_items, test_items = [], [], []
    by_class = {}
    for s in samples:
        by_class.setdefault(s["label"], []).append(s)

    for cls_idx, items in by_class.items():
        random.seed(RANDOM_SEED + cls_idx)
        random.shuffle(items)
        n = len(items)
        n_train = int(n * 0.70)
        n_val = int(n * 0.15)
        train_items.extend(items[:n_train])
        val_items.extend(items[n_train:n_train + n_val])
        test_items.extend(items[n_train + n_val:])

    print(f"\nDataset Splits: Train = {len(train_items)}, Val = {len(val_items)}, Test = {len(test_items)}")

    train_loader = DataLoader(LeafDataset(train_items, is_train=True), batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(LeafDataset(val_items, is_train=False), batch_size=BATCH_SIZE, shuffle=False)
    test_loader = DataLoader(LeafDataset(test_items, is_train=False), batch_size=BATCH_SIZE, shuffle=False)

    print("\n" + "=" * 70)
    print("Step 2: Initializing ResNet18 Transfer Learning Model...")
    model = ResNet18(num_classes=1000)
    # Load official ImageNet weights
    weights_path = os.path.expanduser("~/.cache/torch/hub/checkpoints/resnet18-f37072fd.pth")
    if os.path.exists(weights_path):
        state = torch.load(weights_path, weights_only=True)
        model.load_state_dict(state)
        print("Loaded ImageNet weights from local PyTorch cache.")
    else:
        from torch.hub import load_state_dict_from_url
        state = load_state_dict_from_url("https://download.pytorch.org/models/resnet18-f37072fd.pth", progress=False)
        model.load_state_dict(state)
        print("Downloaded and loaded ImageNet weights.")

    # Freeze feature extractor layers 1-3 to prevent catastrophic forgetting and accelerate training
    for param in model.conv1.parameters(): param.requires_grad = False
    for param in model.bn1.parameters(): param.requires_grad = False
    for param in model.layer1.parameters(): param.requires_grad = False
    for param in model.layer2.parameters(): param.requires_grad = False
    for param in model.layer3.parameters(): param.requires_grad = False

    # Replace classifier head with target classes
    model.fc = nn.Linear(512, len(TARGET_CLASSES))

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(filter(lambda p: p.requires_grad, model.parameters()), lr=LEARNING_RATE)

    print("\n" + "=" * 70)
    print(f"Step 3: Training model for {NUM_EPOCHS} epochs on CPU...")
    best_val_acc = 0.0
    best_checkpoint_path = os.path.join(MODELS_DIR, "resnet18_plantvillage_best.pt")

    for epoch in range(1, NUM_EPOCHS + 1):
        t0 = time.time()
        model.train()
        train_loss = 0.0
        train_correct = 0
        total_train = 0

        for images, labels in train_loader:
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            train_loss += loss.item() * images.size(0)
            preds = outputs.argmax(dim=1)
            train_correct += (preds == labels).sum().item()
            total_train += images.size(0)

        train_loss = train_loss / total_train
        train_acc = (train_correct / total_train) * 100.0

        # Validation
        model.eval()
        val_correct = 0
        total_val = 0
        with torch.no_grad():
            for images, labels in val_loader:
                outputs = model(images)
                preds = outputs.argmax(dim=1)
                val_correct += (preds == labels).sum().item()
                total_val += images.size(0)

        val_acc = (val_correct / total_val) * 100.0
        elapsed = time.time() - t0

        print(f"Epoch {epoch}/{NUM_EPOCHS} [{elapsed:.1f}s]: Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.1f}%, Val Acc: {val_acc:.1f}%")

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), best_checkpoint_path)
            print(f"  --> Saved new best checkpoint to {best_checkpoint_path} (Val Acc: {val_acc:.1f}%)")

    # Save class mapping
    class_mapping = {
        "classes": TARGET_CLASSES,
        "class_to_idx": {c: i for i, c in enumerate(TARGET_CLASSES)},
        "idx_to_class": {i: c for i, c in enumerate(TARGET_CLASSES)},
        "num_classes": len(TARGET_CLASSES),
        "architecture": "ResNet18",
        "input_size": [224, 224],
        "normalization": {
            "mean": IMAGENET_MEAN.tolist(),
            "std": IMAGENET_STD.tolist()
        },
        "dataset_source": "PlantVillage (Hughes & Salathe, 2015; Mohanty et al., 2016)",
        "license": "Creative Commons Attribution-ShareAlike 3.0 (CC BY-SA 3.0)",
        "random_seed": RANDOM_SEED
    }
    mapping_path = os.path.join(MODELS_DIR, "class_mapping.json")
    with open(mapping_path, "w") as f:
        json.dump(class_mapping, f, indent=2)
    print(f"\nSaved class mapping to: {mapping_path}")

    # --- 5. Evaluation on Held-Out Test Set ---
    print("\n" + "=" * 70)
    print("Step 4: Evaluating on Held-Out Test Set...")
    model.load_state_dict(torch.load(best_checkpoint_path, weights_only=True))
    model.eval()

    all_preds = []
    all_labels = []
    latencies = []

    with torch.no_grad():
        for images, labels in test_loader:
            for i in range(images.size(0)):
                single = images[i:i+1]
                t_start = time.perf_counter()
                out = model(single)
                latencies.append((time.perf_counter() - t_start) * 1000.0)

            outputs = model(images)
            preds = outputs.argmax(dim=1)
            all_preds.extend(preds.cpu().numpy().tolist())
            all_labels.extend(labels.cpu().numpy().tolist())

    all_preds = np.array(all_preds)
    all_labels = np.array(all_labels)

    test_acc = (all_preds == all_labels).mean() * 100.0
    avg_latency = np.mean(latencies)
    p95_latency = np.percentile(latencies, 95)

    print(f"\nFinal Test Accuracy: {test_acc:.2f}% ({np.sum(all_preds == all_labels)}/{len(all_labels)})")
    print(f"Average CPU Inference Latency: {avg_latency:.1f} ms (p95: {p95_latency:.1f} ms)")

    report_str = classification_report(
        all_labels,
        all_preds,
        labels=list(range(len(TARGET_CLASSES))),
        target_names=TARGET_CLASSES,
        digits=3,
        zero_division=0
    )
    print("\nDetailed Classification Report:")
    print(report_str)

    cm = confusion_matrix(all_labels, all_preds, labels=list(range(len(TARGET_CLASSES))))
    cm_summary = {
        "test_accuracy_pct": round(float(test_acc), 2),
        "avg_latency_ms": round(float(avg_latency), 2),
        "p95_latency_ms": round(float(p95_latency), 2),
        "confusion_matrix": cm.tolist(),
        "total_test_samples": int(len(all_labels)),
        "correct_test_samples": int(np.sum(all_preds == all_labels))
    }

    results_path = os.path.join(MODELS_DIR, "evaluation_metrics.json")
    with open(results_path, "w") as f:
        json.dump(cm_summary, f, indent=2)
    print(f"Saved test evaluation metrics to: {results_path}")

    # Check file sizes
    model_size_mb = os.path.getsize(best_checkpoint_path) / (1024 * 1024)
    print(f"Checkpoint size: {model_size_mb:.2f} MB ({best_checkpoint_path})")
    print("=" * 70)


if __name__ == "__main__":
    train_and_evaluate()

