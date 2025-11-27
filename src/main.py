import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QPushButton, QMessageBox
from PyQt5.QtCore import QProcess, Qt, QSize
from PyQt5.QtGui import QIcon, QFont, QScreen
from utlis.LabelSense import YOLOAnnotator
# from utlis.yoloTraining import YOLOTrainingUI
from pathlib import Path


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


labelImgPath = BASE_DIR / "src" / "utlis" / "labelimg" / "labelImg.exe"

# Icon paths
icon_path = BASE_DIR / "src" / "utlis" / "icons" / "app_icon.png"
annotator_icon = BASE_DIR / "src" / "utlis" / "icons" / "labelSense.png"
labelimg_icon = BASE_DIR / "src" / "utlis" / "icons" / "labelimg.png"
training_icon = BASE_DIR / "src" / "utlis" / "icons" / "training.png"


class MainLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()

    
    def init_ui(self):
        self.setWindowTitle("Deep Learning Lab")
        
        window_width, window_height = 360, 165
        
        screen = QScreen.availableGeometry(self.screen())
        screen_width = screen.width()
        screen_height = screen.height()
        
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2

        self.setGeometry(x, y, window_width, window_height)

        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)
        layout.setContentsMargins(20, 40, 20, 20)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignCenter)

        layout.addStretch()

        self.annotator_btn = QPushButton()
        # self.annotator_btn.setFont(QFont("Arial", 14, QFont.Bold))  # Commented as in your code
        if annotator_icon.exists():
            self.annotator_btn.setIcon(QIcon(str(annotator_icon)))
        self.annotator_btn.setIconSize(QSize(30, 30))
        self.annotator_btn.setToolTip("LabelSense Annotator")
        self.annotator_btn.clicked.connect(self.open_annotator)
        layout.addWidget(self.annotator_btn)

        self.labelimg_btn = QPushButton()
        # self.labelimg_btn.setFont(QFont("Arial", 14, QFont.Bold))  # Commented as in your code
        if labelimg_icon.exists():
            self.labelimg_btn.setIcon(QIcon(str(labelimg_icon)))
        self.labelimg_btn.setIconSize(QSize(30, 30))
        self.labelimg_btn.setToolTip("LabelImg Annotator")
        self.labelimg_btn.clicked.connect(self.open_exe)
        layout.addWidget(self.labelimg_btn)

        # self.training_btn = QPushButton()
        # self.training_btn.setFont(QFont("Arial", 14, QFont.Bold))  # Commented as in your code
        # if training_icon.exists():
        #     self.training_btn.setIcon(QIcon(str(training_icon)))
        # self.training_btn.setIconSize(QSize(30, 30))
        # self.training_btn.setToolTip("YOLO Model Training")
        # self.training_btn.clicked.connect(self.open_training)
        # layout.addWidget(self.training_btn)

        layout.addStretch()

        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #ecf0f1,
                    stop: 1 #bdc3c7
                );
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border-radius: 10px;
                padding: 12px;
                font-size: 16px;
                font-weight: bold;
                min-height: 60px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #2980b9;
                transform: scale(1.05);
            }
            QPushButton:pressed {
                background-color: #1f618d;
            }
            QToolTip {
                background-color: #2c3e50;
                color: white;
                border: 1px solid #34495e;
                padding: 5px;
                font-size: 14px;
                font-weight: bold;
            }
        """)

        self.annotator_window = None
        self.training_window = None


    def open_annotator(self):
        try:
            if self.annotator_window is None:
                self.annotator_window = YOLOAnnotator()
            self.annotator_window.show()
            self.annotator_window.raise_()
            self.annotator_window.activateWindow()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open Image Annotator: {str(e)}")

    def open_exe(self):
        exe_path = str(labelImgPath)
        if not Path(exe_path).exists():
            QMessageBox.critical(self, "Error", f"Executable not found at {exe_path}")
            return
        success = QProcess.startDetached(exe_path)
        if not success:
            QMessageBox.critical(self, "Error", f"Failed to start LabelImg at {exe_path}")

def main():
    app = QApplication(sys.argv)
    window = MainLauncher()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()