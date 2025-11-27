"""
LabelSense Annotator
Developed by Rahim Biswas

YouTube Channel GISsense
©LabelSense Annotator 2025
"""

import sys
import os
import random
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QLabel, QListWidget, QTextEdit,
                             QFileDialog, QMessageBox, QInputDialog, QSpinBox,
                             QSplitter, QGroupBox, QDialog, QStyle, QAction, QMenuBar)
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor, QPalette, QScreen, QIcon
from image_canvas import ImageCanvas
import json
import yaml
from pathlib import Path
import shutil

def find_project_root(start_path: Path) -> Path:
    current_path = start_path.resolve()
    markers = [
        "requirements.txt",
        ".env",
        ".venv",
        "venv"
    ]
    
    for parent in [current_path] + list(current_path.parents):
        for marker in markers:
            marker_path = parent / marker
            if marker_path.exists():
                if marker_path.is_dir() and marker in [".env", ".venv", "venv"]:
                    return parent
                else:
                    return parent
                
    print("Warning: No common project root marker found. Defaulting to script's directory.")
    return start_path.resolve()

script_directory = Path(__file__).resolve().parent
BASE_DIR = find_project_root(script_directory)
print(f"Determined project root (BASE_DIR): {BASE_DIR}")

# Icon paths
selectAll = BASE_DIR / "src" / "utlis" / "icons" / "selectAll.png"
deSelectAll = BASE_DIR / "src" / "utlis" / "icons" / "deSelectAll.png" 
deleteSelected = BASE_DIR / "src" / "utlis" / "icons" / "deleteSelected.png"
fileicon = BASE_DIR / "src" / "utlis" / "icons" / "menu.png"
exportImages = BASE_DIR / "src" / "utlis" / "icons" / "export.png"
selectFolder = BASE_DIR / "src" / "utlis" / "icons" / "file.png"
previousImage = BASE_DIR / "src" / "utlis" / "icons" / "previous.png"
nextImage = BASE_DIR / "src" / "utlis" / "icons" / "next.png"
drawingMode = BASE_DIR / "src" / "utlis" / "icons" / "drawingMode.png" 
editingMode = BASE_DIR / "src" / "utlis" / "icons" / "editingMode.png"
panningMode = BASE_DIR / "src" / "utlis" / "icons" / "panningMode.png"

class YOLOAnnotator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LabelSense")
        
        screen = QScreen.availableGeometry(self.screen())
        self.setGeometry(screen)
        self.setWindowState(Qt.WindowState.WindowMaximized)
        
        self.image_folder = ""
        self.current_image_path = ""
        self.image_files = []
        self.current_image_index = 0
        self.classes = ["Playground", "Brick Kiln", "Metro Shed", "Pond-1","Pond-2","Sheds","Solar Panel","STP"]
        self.annotations = {}
        self.project_file_path = None
        
        self.init_ui()
        self.init_menu()
        self.apply_os_theme()
    
    def init_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        
        save_action = QAction("Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_project)
        file_menu.addAction(save_action)
        file_menu.setIcon(QIcon(str(fileicon)))

        save_as_action = QAction("Save As", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_project_as)
        file_menu.addAction(save_as_action)
        
        load_action = QAction("Load Project", self)
        load_action.setShortcut("Ctrl+O")
        load_action.triggered.connect(self.load_project)
        file_menu.addAction(load_action)
        
        export_menu = menubar.addMenu("Export")
        export_action = QAction("Export YOLO Dataset", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self.export_dataset)
        export_menu.addAction(export_action)
        export_menu.setIcon(QIcon(str(exportImages)))

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        self.canvas = ImageCanvas()
        self.canvas.annotation_created.connect(self.add_annotation)
        self.canvas.annotation_updated.connect(self.update_annotation)
        splitter.addWidget(self.canvas)
        
        splitter.setSizes([300, 900])
    
    def toggle_draw_mode(self):
        if not self.draw_mode_btn.isChecked():
            self.draw_mode_btn.setChecked(True)
            return
        # self.edit_mode_btn.setChecked(False)
        self.pan_mode_btn.setChecked(False)
        self.canvas.set_mode('draw')

    def toggle_edit_mode(self):
        self.draw_mode_btn.setChecked(False)
        self.pan_mode_btn.setChecked(False)
        self.canvas.set_mode('edit')

    def toggle_pan_mode(self):
        if not self.pan_mode_btn.isChecked():
            self.pan_mode_btn.setChecked(True)
            return
        self.draw_mode_btn.setChecked(False)
        self.canvas.set_mode('pan')

    def create_left_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        folder_group = QGroupBox("Dataset Folder")
        folder_layout = QVBoxLayout(folder_group)
        
        self.folder_btn = QPushButton("Browse Folder")
        self.folder_btn.clicked.connect(self.select_folder)
        self.folder_btn.setIcon(QIcon(str(selectFolder)))
        folder_layout.addWidget(self.folder_btn)
             
        self.folder_label = QLabel("No folder selected")
        self.folder_label.setWordWrap(True)
        folder_layout.addWidget(self.folder_label)
        
        layout.addWidget(folder_group)
        
        mode_group = QGroupBox("Mode Control")
        mode_layout = QVBoxLayout(mode_group)

        mode_btn_layout = QHBoxLayout()
        self.draw_mode_btn = QPushButton("Draw")
        self.draw_mode_btn.setIcon(QIcon(str(drawingMode)))
        self.draw_mode_btn.setCheckable(True)
        self.draw_mode_btn.setChecked(True)
        self.draw_mode_btn.clicked.connect(self.toggle_draw_mode)

        self.pan_mode_btn = QPushButton("Pan")
        self.pan_mode_btn.setIcon(QIcon(str(panningMode)))
        self.pan_mode_btn.setCheckable(True)
        self.pan_mode_btn.clicked.connect(self.toggle_pan_mode)

        mode_btn_layout.addWidget(self.draw_mode_btn)
        mode_btn_layout.addWidget(self.pan_mode_btn)
        mode_layout.addLayout(mode_btn_layout)

        layout.addWidget(mode_group)

        image_group = QGroupBox("Images")
        image_layout = QVBoxLayout(image_group)
        
        self.image_list = QListWidget()
        self.image_list.itemClicked.connect(self.load_image)
        image_layout.addWidget(self.image_list)
        
        self.image_counter = QLabel("0/0")
        image_layout.addWidget(self.image_counter)
        
        nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton()
        self.prev_btn.clicked.connect(self.prev_image)
        self.prev_btn.setIcon(QIcon(str(previousImage)))
        self.next_btn = QPushButton()
        self.next_btn.clicked.connect(self.next_image)
        self.next_btn.setIcon(QIcon(str(nextImage)))
        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(self.next_btn)
        image_layout.addLayout(nav_layout)
        
        layout.addWidget(image_group)
        
        class_group = QGroupBox("Classes")
        class_layout = QVBoxLayout(class_group)
        
        class_btn_layout = QHBoxLayout()
        self.add_class_btn = QPushButton("Add Class")
        self.add_class_btn.clicked.connect(self.add_class)
        self.remove_class_btn = QPushButton("Remove Class")
        self.remove_class_btn.clicked.connect(self.remove_class)
        class_btn_layout.addWidget(self.add_class_btn)
        class_btn_layout.addWidget(self.remove_class_btn)
        class_layout.addLayout(class_btn_layout)
        
        self.class_list = QListWidget()
        self.class_list.itemClicked.connect(self.select_class)
        self.update_class_list()
        class_layout.addWidget(self.class_list)
        
        current_class_layout = QHBoxLayout()
        current_class_layout.addWidget(QLabel("Current Class:"))
        self.class_spinbox = QSpinBox()
        self.class_spinbox.setMinimum(0)
        self.class_spinbox.setMaximum(len(self.classes) - 1)
        self.class_spinbox.valueChanged.connect(self.class_changed)
        current_class_layout.addWidget(self.class_spinbox)
        class_layout.addLayout(current_class_layout)
        
        layout.addWidget(class_group)
        
        ann_group = QGroupBox("Current Image Annotations")
        ann_layout = QVBoxLayout(ann_group)
        
        self.annotation_list = QListWidget()
        self.annotation_list.setSelectionMode(QListWidget.MultiSelection)
        self.annotation_list.itemClicked.connect(self.handle_item_clicked)
        ann_layout.addWidget(self.annotation_list)
        
        selection_btn_layout = QHBoxLayout()
        self.select_all_btn = QPushButton()
        self.select_all_btn.setIcon(QIcon(str(selectAll)))
        self.select_all_btn.setToolTip("Select All Annotations")
        self.select_all_btn.clicked.connect(self.select_all_annotations)
        selection_btn_layout.addWidget(self.select_all_btn)
        
        self.deselect_all_btn = QPushButton()
        self.deselect_all_btn.setIcon(QIcon(str(deSelectAll)))
        self.deselect_all_btn.setToolTip("Deselect All Annotations")
        self.deselect_all_btn.clicked.connect(self.deselect_all_annotations)
        selection_btn_layout.addWidget(self.deselect_all_btn)
        
        self.delete_ann_btn = QPushButton()
        self.delete_ann_btn.setIcon(QIcon(str(deleteSelected)))
        self.delete_ann_btn.setToolTip("Delete Selected Annotations")
        self.delete_ann_btn.clicked.connect(self.delete_annotation)
        selection_btn_layout.addWidget(self.delete_ann_btn)
        
        ann_layout.addLayout(selection_btn_layout)
        
        layout.addWidget(ann_group)
        
        self.setStyleSheet(self.styleSheet() + """
            QPushButton#select_all_btn, QPushButton#deselect_all_btn, QPushButton#delete_ann_btn {
                min-width: 30px;
                max-width: 30px;
                min-height: 30px;
                max-height: 30px;
                padding: 2px;
            }
            QPushButton#delete_ann_btn {
                max-width: 60px;
                font-size: 12px;
            }
        """)
        
        return panel
    
    def apply_os_theme(self):
        palette = QApplication.palette()
        bg_color = palette.color(QPalette.Window).value()
        is_dark = bg_color < 128
        
        if is_dark:
            self.setStyleSheet("""
                QMainWindow, QWidget {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QPushButton {
                    background-color: #3c3f41;
                    color: #ffffff;
                    border: 1px solid #555555;
                    padding: 5px;
                }
                QPushButton:hover {
                    background-color: #4b4e4f;
                }
                QGroupBox {
                    background-color: #353535;
                    color: #ffffff;
                    border: 1px solid #555555;
                    margin-top: 10px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    subcontrol-position: top left;
                    padding: 0 3px;
                    color: #ffffff;
                }
                QListWidget {
                    background-color: #353535;
                    color: #ffffff;
                    border: 1px solid #555555;
                }
                QListWidget::item:selected {
                    background-color: #4b4e4f;
                }
                QSpinBox {
                    background-color: #353535;
                    color: #ffffff;
                    border: 1px solid #555555;
                }
                QLabel {
                    color: #ffffff;
                }
            """)
            self.canvas.set_dark_mode(True)
        else:
            self.setStyleSheet("")
            self.canvas.set_dark_mode(False)
    
    def handle_item_clicked(self, item):
        modifiers = QApplication.keyboardModifiers()
        if not (modifiers & Qt.ControlModifier or modifiers & Qt.ShiftModifier):
            self.annotation_list.clearSelection()
            item.setSelected(True)
    
    def select_all_annotations(self):
        for index in range(self.annotation_list.count()):
            self.annotation_list.item(index).setSelected(True)
    
    def deselect_all_annotations(self):
        self.annotation_list.clearSelection()
    
    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder")
        if folder:
            self.image_folder = folder
            self.folder_label.setText(f"Folder: {folder}")
            self.load_images()
    
    def load_images(self):
        if not self.image_folder:
            return
            
        extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
        self.image_files = []
        
        for file in os.listdir(self.image_folder):
            if any(file.lower().endswith(ext) for ext in extensions):
                self.image_files.append(file)
        
        self.image_files.sort()
        self.image_list.clear()
        self.image_list.addItems(self.image_files)
        self.update_image_counter()
        
        if self.image_files:
            self.current_image_index = 0
            self.load_current_image()
    
    def load_image(self, item):
        self.current_image_index = self.image_files.index(item.text())
        self.load_current_image()
    
    def load_current_image(self):
        if not self.image_files:
            return
            
        self.current_image_path = os.path.join(self.image_folder, self.image_files[self.current_image_index])
        self.canvas.load_image(self.current_image_path)
        
        image_name = self.image_files[self.current_image_index]
        if image_name in self.annotations:
            self.canvas.set_annotations(self.annotations[image_name])
        else:
            self.canvas.set_annotations([])
        
        self.update_annotation_list()
        self.image_list.setCurrentRow(self.current_image_index)
        self.setWindowTitle(f"YOLO Annotator - {image_name}")
        self.update_image_counter()
    
    def update_image_counter(self):
        total = len(self.image_files)
        current = self.current_image_index + 1 if self.image_files else 0
        self.image_counter.setText(f"{current}/{total}")
    
    def prev_image(self):
        if self.current_image_index > 0:
            self.current_image_index -= 1
            self.load_current_image()
    
    def next_image(self):
        if self.current_image_index < len(self.image_files) - 1:
            self.current_image_index += 1
            self.load_current_image()
    
    def add_class(self):
        text, ok = QInputDialog.getText(self, 'Add Class', 'Enter class name:')
        if ok and text:
            self.classes.append(text)
            self.update_class_list()
            self.class_spinbox.setMaximum(len(self.classes) - 1)
    
    def remove_class(self):
        current_row = self.class_list.currentRow()
        if current_row >= 0 and len(self.classes) > 1:
            self.classes.pop(current_row)
            self.update_class_list()
            self.class_spinbox.setMaximum(len(self.classes) - 1)
            if self.class_spinbox.value() >= len(self.classes):
                self.class_spinbox.setValue(len(self.classes) - 1)
    
    def update_class_list(self):
        self.class_list.clear()
        for i, class_name in enumerate(self.classes):
            self.class_list.addItem(f"{i}: {class_name}")
    
    def select_class(self, item):
        class_id = int(item.text().split(':')[0])
        self.class_spinbox.setValue(class_id)
    
    def class_changed(self, value):
        self.canvas.current_class = value
    
    def add_annotation(self, bbox, class_id):
        image_name = self.image_files[self.current_image_index]
        if image_name not in self.annotations:
            self.annotations[image_name] = []
        
        self.annotations[image_name].append({
            'class': class_id,
            'bbox': bbox
        })
        
        self.update_annotation_list()
    
    def update_annotation(self, index, bbox):
        image_name = self.image_files[self.current_image_index]
        if image_name in self.annotations and 0 <= index < len(self.annotations[image_name]):
            self.annotations[image_name][index]['bbox'] = bbox
            self.update_annotation_list()
            self.canvas.set_annotations(self.annotations[image_name])  # Refresh canvas
    
    def update_annotation_list(self):
        self.annotation_list.clear()
        image_name = self.image_files[self.current_image_index] if self.image_files else ""
        
        if image_name in self.annotations:
            for i, ann in enumerate(self.annotations[image_name]):
                class_name = self.classes[ann['class']]
                bbox_str = f"[{ann['bbox'][0]:.3f}, {ann['bbox'][1]:.3f}, {ann['bbox'][2]:.3f}, {ann['bbox'][3]:.3f}]"
                self.annotation_list.addItem(f"{i}: {class_name} {bbox_str}")
    
    def delete_annotation(self):
        selected_items = self.annotation_list.selectedItems()
        if not selected_items:
            return

        image_name = self.image_files[self.current_image_index]
        if image_name not in self.annotations:
            return

        selected_indices = sorted([self.annotation_list.row(item) for item in selected_items], reverse=True)
        for index in selected_indices:
            if 0 <= index < len(self.annotations[image_name]):
                self.annotations[image_name].pop(index)

        self.canvas.set_annotations(self.annotations[image_name])
        self.update_annotation_list()
    
    def save_project(self):
        if not self.image_folder:
            QMessageBox.warning(self, "Warning", "No project data to save!")
            return
        
        if self.project_file_path:
            self._save_to_file(self.project_file_path)
        else:
            self.save_project_as()
    
    def save_project_as(self):
        save_path, _ = QFileDialog.getSaveFileName(self, "Save Project As", "", "JSON Files (*.json)")
        if save_path:
            self._save_to_file(save_path)
            self.project_file_path = save_path
    
    def _save_to_file(self, save_path):
        project_data = {
            'image_folder': self.image_folder,
            'current_image_index': self.current_image_index,
            'classes': self.classes,
            'annotations': self.annotations
        }
        try:
            with open(save_path, 'w') as f:
                json.dump(project_data, f, indent=4)
            QMessageBox.information(self, "Success", f"Project saved to:\n{save_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save project:\n{str(e)}")
    
    def load_project(self):
        load_path, _ = QFileDialog.getOpenFileName(self, "Load Project", "", "JSON Files (*.json)")
        if load_path:
            try:
                with open(load_path, 'r') as f:
                    project_data = json.load(f)
                
                self.image_folder = project_data.get('image_folder', '')
                self.current_image_index = project_data.get('current_image_index', 0)
                self.classes = project_data.get('classes', ["Military Helicopter", "Helicopter", "Passenger Airplane", "SAM Site"])
                self.annotations = project_data.get('annotations', {})
                
                if self.image_folder and os.path.exists(self.image_folder):
                    self.folder_label.setText(f"Folder: {self.image_folder}")
                    self.load_images()
                    if self.image_files:
                        self.current_image_index = min(self.current_image_index, len(self.image_files) - 1)
                        self.load_current_image()
                    self.update_class_list()
                    self.class_spinbox.setMaximum(len(self.classes) - 1)
                    self.project_file_path = load_path
                    QMessageBox.information(self, "Success", f"Project loaded from:\n{load_path}")
                else:
                    QMessageBox.warning(self, "Warning", "Image folder not found. Please select a new folder.")
                    self.select_folder()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load project:\n{str(e)}")
    
    def export_dataset(self):
        if not self.image_folder or not self.annotations:
            QMessageBox.warning(self, "Warning", "No images or annotations to export!")
            return
        
        train_ratio, ok = QInputDialog.getDouble(
            self, 
            "Train/Val Split", 
            "Enter training data percentage (0-100):", 
            80.0, 
            0.0, 
            100.0, 
            1
        )
        if not ok:
            return
        
        export_folder = QFileDialog.getExistingDirectory(self, "Select Export Folder")
        if not export_folder:
            return
        
        try:
            dataset_name = os.path.basename(self.image_folder)
            dataset_path = os.path.join(export_folder, dataset_name)
            
            os.makedirs(os.path.join(dataset_path, "images", "train"), exist_ok=True)
            os.makedirs(os.path.join(dataset_path, "images", "val"), exist_ok=True)
            os.makedirs(os.path.join(dataset_path, "labels", "train"), exist_ok=True)
            os.makedirs(os.path.join(dataset_path, "labels", "val"), exist_ok=True)
            
            annotated_images = list(self.annotations.keys())
            random.shuffle(annotated_images)
            split_idx = int(len(annotated_images) * (train_ratio / 100.0))
            train_images = annotated_images[:split_idx]
            val_images = annotated_images[split_idx:]
            

            
            for img_list, split in [(train_images, "train"), (val_images, "val")]:
                for img_name in img_list:
                    src_img = os.path.join(self.image_folder, img_name)
                    dst_img = os.path.join(dataset_path, "images", split, img_name)
                    shutil.copy2(src_img, dst_img)
                    
                    label_name = os.path.splitext(img_name)[0] + ".txt"
                    label_path = os.path.join(dataset_path, "labels", split, label_name)
                    
                    with open(label_path, 'w') as f:
                        for ann in self.annotations[img_name]:
                            bbox = ann['bbox']
                            f.write(f"{ann['class']} {bbox[0]} {bbox[1]} {bbox[2]} {bbox[3]}\n")
            
            yaml_data = {
                'path': os.path.abspath(dataset_path),
                'train': 'images/train',
                'val': 'images/val',
                'nc': len(self.classes),
                'names': self.classes,
            }
            
            yaml_path = os.path.join(dataset_path, f"{dataset_name}.yaml")
            with open(yaml_path, 'w') as f:
                yaml.dump(yaml_data, f, default_flow_style=False)
            
            QMessageBox.information(
                self, 
                "Success", 
                f"Dataset exported successfully to:\n{dataset_path}\n"
                f"Train: {len(train_images)} images, Val: {len(val_images)} images"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export dataset:\n{str(e)}")

def main():
    app = QApplication(sys.argv)
    
    window = YOLOAnnotator()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
