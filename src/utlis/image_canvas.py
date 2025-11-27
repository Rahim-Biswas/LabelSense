"""
LabelSense Annotator
Developed by Rahim Biswas

YouTube Channel GISsense
©LabelSense Annotator 2025
"""

from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QScrollArea
from PyQt5.QtCore import Qt, QRect, pyqtSignal, QPoint, QPointF
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor, QFont, QBrush
import os


class ImageCanvas(QScrollArea):
    annotation_created = pyqtSignal(list, int)
    annotation_updated = pyqtSignal(int, list)

    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.image_label = ImageLabel()
        self.image_label.annotation_created.connect(self.annotation_created.emit)
        self.image_label.annotation_updated.connect(self.annotation_updated.emit)
        self.setWidget(self.image_label)

        self.current_class = 0
        self.image_label.current_class = 0

    def load_image(self, image_path):
        self.image_label.load_image(image_path)

    def set_annotations(self, annotations):
        self.image_label.set_annotations(annotations)

    def set_mode(self, mode):
        self.image_label.set_mode(mode)

    @property
    def current_class(self):
        return self.image_label.current_class

    @current_class.setter
    def current_class(self, value):
        self.image_label.current_class = value

    def set_dark_mode(self, enabled):
        """Apply or remove dark mode styles"""
        if enabled:
            self.setStyleSheet("""
                QScrollArea {
                    background-color: #2b2b2b;
                    border: 1px solid #555555;
                }
            """)
            self.image_label.setStyleSheet("border: 1px solid #555555;")
        else:
            self.setStyleSheet("")
            self.image_label.setStyleSheet("border: 1px solid gray;")


class ImageLabel(QLabel):
    annotation_created = pyqtSignal(list, int)
    annotation_updated = pyqtSignal(int, list)

    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(400, 300)
        self.setStyleSheet("border: 1px solid gray;")
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.cursor_pos = None

        self.original_pixmap = None
        self.scaled_pixmap = None
        self.zoom_factor = 1.0
        self.offset = QPointF(0, 0)
        self.is_panning = False
        self.last_pan_pos = QPointF()
        self.mode = 'draw'  # 'draw', 'edit', or 'pan'

        self.annotations = []
        self.current_class = 0

        self.drawing = False
        self.resizing = False
        self.moving = False
        self.selected_annotation_idx = -1
        self.resize_corner = None  # 'top-left', 'top-right', 'bottom-left', 'bottom-right'
        self.start_point = QPoint()
        self.end_point = QPoint()
        self.last_move_pos = QPoint()
        self.original_annotation_rect = None

        self.colors = [
            QColor(255, 0, 0),  # Red
            QColor(0, 255, 0),  # Green
            QColor(0, 0, 255),  # Blue
            QColor(255, 255, 0),  # Yellow
            QColor(255, 0, 255),  # Magenta
            QColor(0, 255, 255),  # Cyan
            QColor(255, 165, 0),  # Orange
            QColor(128, 0, 128),  # Purple
            QColor(255, 192, 203),  # Pink
            QColor(165, 42, 42),  # Brown
        ]

    def set_mode(self, mode):
        self.mode = mode
        self.drawing = False
        self.resizing = False
        self.moving = False
        self.selected_annotation_idx = -1
        self.resize_corner = None
        self.is_panning = False

        if mode == 'pan':
            self.setCursor(Qt.OpenHandCursor)
        else:
            self.setCursor(Qt.CrossCursor)

        self.update()

    def load_image(self, image_path):
        if os.path.exists(image_path):
            self.original_pixmap = QPixmap(image_path)
            if self.original_pixmap.isNull():
                return
            self.zoom_factor = 0.5
            self.offset = QPointF(0, 0)
            self.scale_and_display()
            self.annotations = []

    def scale_and_display(self):
        if self.original_pixmap:
            self.scaled_pixmap = self.original_pixmap.scaled(
                int(self.original_pixmap.width() * self.zoom_factor),
                int(self.original_pixmap.height() * self.zoom_factor),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.update()

    def set_annotations(self, annotations):
        self.annotations = annotations
        self.update()

    def updateZoom(self, new_zoom_factor, fixed_point):
        if not self.original_pixmap:
            return

        i_x = (fixed_point.x() - self.offset.x()) / self.zoom_factor
        i_y = (fixed_point.y() - self.offset.y()) / self.zoom_factor

        self.zoom_factor = new_zoom_factor

        self.scaled_pixmap = self.original_pixmap.scaled(
            int(self.original_pixmap.width() * self.zoom_factor),
            int(self.original_pixmap.height() * self.zoom_factor),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        self.offset = QPointF(
            fixed_point.x() - i_x * self.zoom_factor,
            fixed_point.y() - i_y * self.zoom_factor
        )

        self.update()

        scroll_area = self.parent()
        if isinstance(scroll_area, QScrollArea):
            h_bar = scroll_area.horizontalScrollBar()
            v_bar = scroll_area.verticalScrollBar()
            h_bar.setValue(int(-self.offset.x()))
            v_bar.setValue(int(-self.offset.y()))

    def wheelEvent(self, event):
        if not self.original_pixmap:
            event.ignore()
            return

        zoom_delta = 1.1
        if event.angleDelta().y() > 0:
            new_zoom = self.zoom_factor * zoom_delta
        else:
            new_zoom = self.zoom_factor / zoom_delta
        new_zoom = max(0.1, min(5.0, new_zoom))

        self.updateZoom(new_zoom, event.pos())
        event.accept()

    def get_corner_points(self, rect):
        return {
            'top-left': rect.topLeft(),
            'top-right': rect.topRight(),
            'bottom-left': rect.bottomLeft(),
            'bottom-right': rect.bottomRight()
        }

    def is_near_corner(self, pos, rect):
        corners = self.get_corner_points(rect)
        threshold = 8  # Fixed threshold in screen pixels
        for corner_name, corner_point in corners.items():
            distance = ((pos.x() - corner_point.x()) ** 2 + (pos.y() - corner_point.y()) ** 2) ** 0.5
            if distance <= threshold:
                return corner_name
        return None

    def is_inside_bbox(self, pos, rect):
        return rect.contains(pos.toPoint())

    def mousePressEvent(self, event):
        pos = QPointF(
            (event.pos().x() - self.offset.x()),
            (event.pos().y() - self.offset.y())
        )

        scaled_pos = QPointF(pos.x() / self.zoom_factor, pos.y() / self.zoom_factor)

        if event.button() == Qt.LeftButton and self.scaled_pixmap:
            if self.mode == 'pan':
                self.is_panning = True
                self.last_pan_pos = event.pos()
                self.setCursor(Qt.ClosedHandCursor)
            elif self.mode == 'edit':
                for idx, annotation in enumerate(self.annotations):
                    rect = self.yolo_to_rect(annotation['bbox'])
                    screen_rect = rect.translated(self.offset.toPoint())
                    corner = self.is_near_corner(event.pos(), screen_rect)
                    if corner:
                        self.resizing = True
                        self.selected_annotation_idx = idx
                        self.resize_corner = corner
                        self.start_point = scaled_pos.toPoint()
                        self.end_point = scaled_pos.toPoint()
                        self.original_annotation_rect = rect
                        self.update()
                        return

                for idx, annotation in enumerate(self.annotations):
                    rect = self.yolo_to_rect(annotation['bbox'])
                    if self.is_inside_bbox(scaled_pos, rect):
                        self.selected_annotation_idx = idx
                        self.moving = True
                        self.start_point = event.pos()
                        self.last_move_pos = event.pos()
                        self.original_annotation_rect = rect
                        self.update()
                        return

                # Clicked outside any box, deselect
                self.selected_annotation_idx = -1
                self.update()
            elif self.mode == 'draw':
                self.drawing = True
                self.selected_annotation_idx = -1
                self.resize_corner = None
                self.start_point = pos.toPoint()
                self.end_point = pos.toPoint()
                self.update()
        elif event.button() == Qt.MidButton and self.scaled_pixmap:
            self.is_panning = True
            self.last_pan_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)

    def draw_crosshair(self, painter):
        if self.cursor_pos is None:
            return
        pen = QPen(QColor(64, 255, 0), 1, Qt.DashLine)
        painter.setPen(pen)
        x = self.cursor_pos.x()
        y = self.cursor_pos.y()
        painter.drawLine(x, 0, x, self.height())
        painter.drawLine(0, y, self.width(), y)

    def mouseMoveEvent(self, event):
        pos = QPointF(
            (event.pos().x() - self.offset.x()),
            (event.pos().y() - self.offset.y())
        )

        scaled_pos = QPointF(pos.x() / self.zoom_factor, pos.y() / self.zoom_factor)

        self.cursor_pos = event.pos()  # Track cursor position
        self.update()  # Trigger repaint

        if self.drawing and event.buttons() & Qt.LeftButton:
            self.end_point = pos.toPoint()
            self.update()
        elif self.resizing and event.buttons() & Qt.LeftButton:
            self.end_point = scaled_pos.toPoint()
            self.update()
        elif self.moving and event.buttons() & Qt.LeftButton:
            # Calculate movement delta in original image coordinates
            delta = (event.pos() - self.last_move_pos) / self.zoom_factor
            self.last_move_pos = event.pos()

            # Update annotation position
            if self.selected_annotation_idx >= 0:
                current_bbox = self.annotations[self.selected_annotation_idx]['bbox']
                orig_width = self.original_pixmap.width()
                orig_height = self.original_pixmap.height()

                # Convert delta to normalized coordinates
                delta_x = delta.x() / orig_width
                delta_y = delta.y() / orig_height

                # Update center position
                new_bbox = [
                    current_bbox[0] + delta_x,  # center_x
                    current_bbox[1] + delta_y,  # center_y
                    current_bbox[2],  # width
                    current_bbox[3]  # height
                ]

                # Clamp to image boundaries
                half_w = new_bbox[2] / 2
                half_h = new_bbox[3] / 2
                new_bbox[0] = max(half_w, min(1 - half_w, new_bbox[0]))
                new_bbox[1] = max(half_h, min(1 - half_h, new_bbox[1]))

                self.annotations[self.selected_annotation_idx]['bbox'] = new_bbox
            self.update()
        elif self.is_panning and (event.buttons() & Qt.LeftButton or event.buttons() & Qt.MidButton):
            delta = event.pos() - self.last_pan_pos
            self.offset += delta
            self.last_pan_pos = event.pos()
            scroll_area = self.parent()
            if isinstance(scroll_area, QScrollArea):
                h_bar = scroll_area.horizontalScrollBar()
                v_bar = scroll_area.verticalScrollBar()
                h_bar.setValue(int(-self.offset.x()))
                v_bar.setValue(int(-self.offset.y()))
            self.update()
        else:
            # Handle cursor changes when hovering
            cursor_set = False
            if self.mode == 'edit':
                # Check if hovering over any annotation
                for idx, annotation in enumerate(self.annotations):
                    rect = self.yolo_to_rect(annotation['bbox'])
                    screen_rect = rect.translated(self.offset.toPoint())
                    corner = self.is_near_corner(event.pos(), screen_rect)
                    if corner:
                        # Set different cursors for different corners
                        if corner in ['top-left', 'bottom-right']:
                            self.setCursor(Qt.SizeFDiagCursor)
                        elif corner in ['top-right', 'bottom-left']:
                            self.setCursor(Qt.SizeBDiagCursor)
                        cursor_set = True
                        break
                    elif self.is_inside_bbox(scaled_pos, rect):
                        self.setCursor(Qt.SizeAllCursor)  # Move cursor
                        cursor_set = True
                        break

            if self.mode == 'pan' and not cursor_set:
                self.setCursor(Qt.OpenHandCursor)
                cursor_set = True

            if not cursor_set:
                self.setCursor(Qt.CrossCursor)

    def mouseReleaseEvent(self, event):
        pos = QPointF(
            (event.pos().x() - self.offset.x()),
            (event.pos().y() - self.offset.y())
        )

        scaled_pos = QPointF(pos.x() / self.zoom_factor, pos.y() / self.zoom_factor)

        if event.button() == Qt.LeftButton:
            if self.drawing:
                self.drawing = False
                self.end_point = pos.toPoint()
                rect = QRect(self.start_point, self.end_point).normalized()

                if rect.width() > 5 and rect.height() > 5:
                    yolo_bbox = self.rect_to_yolo(rect)
                    self.annotation_created.emit(yolo_bbox, self.current_class)
                    self.annotations.append({
                        'class': self.current_class,
                        'bbox': yolo_bbox
                    })
                self.update()
            elif self.resizing:
                self.resizing = False
                if self.selected_annotation_idx >= 0:
                    rect = QRect(self.start_point, self.end_point).normalized()
                    new_rect = self.adjust_rect_for_resize(rect)
                    yolo_bbox = self.rect_to_yolo(new_rect)
                    self.annotation_updated.emit(self.selected_annotation_idx, yolo_bbox)
                    self.annotations[self.selected_annotation_idx]['bbox'] = yolo_bbox
                self.resize_corner = None
                self.original_annotation_rect = None
                self.update()
            elif self.moving:
                self.moving = False
                if self.selected_annotation_idx >= 0:
                    # Emit updated annotation
                    self.annotation_updated.emit(
                        self.selected_annotation_idx,
                        self.annotations[self.selected_annotation_idx]['bbox']
                    )
                self.original_annotation_rect = None
                self.update()
            elif self.is_panning and self.mode == 'pan':
                self.is_panning = False
                self.setCursor(Qt.OpenHandCursor)
        elif event.button() == Qt.RightButton and self.mode == 'edit' and self.selected_annotation_idx >= 0:
            # Save edits on right-click or deselect
            if self.resizing:
                rect = QRect(self.start_point, self.end_point).normalized()
                new_rect = self.adjust_rect_for_resize(rect)
                yolo_bbox = self.rect_to_yolo(new_rect)
                self.annotation_updated.emit(self.selected_annotation_idx, yolo_bbox)
                self.annotations[self.selected_annotation_idx]['bbox'] = yolo_bbox
                self.resizing = False
                self.resize_corner = None
            elif self.moving:
                # Finalize move
                if self.selected_annotation_idx >= 0:
                    self.annotation_updated.emit(
                        self.selected_annotation_idx,
                        self.annotations[self.selected_annotation_idx]['bbox']
                    )
                self.moving = False
            self.selected_annotation_idx = -1  # Deselect after saving
            self.original_annotation_rect = None
            self.update()
        elif (event.button() == Qt.MidButton or event.button() == Qt.LeftButton) and self.is_panning:
            self.is_panning = False
            if self.mode == 'pan':
                self.setCursor(Qt.OpenHandCursor)
            else:
                self.setCursor(Qt.CrossCursor)

    def adjust_rect_for_resize(self, new_rect):
        if self.selected_annotation_idx < 0 or not self.resize_corner or not self.original_annotation_rect:
            return new_rect

        original_rect = self.original_annotation_rect
        corners = self.get_corner_points(original_rect)

        if self.resize_corner == 'top-left':
            return QRect(new_rect.topLeft(), original_rect.bottomRight()).normalized()
        elif self.resize_corner == 'top-right':
            return QRect(QPoint(original_rect.left(), new_rect.top()),
                         QPoint(new_rect.right(), original_rect.bottom())).normalized()
        elif self.resize_corner == 'bottom-left':
            return QRect(QPoint(new_rect.left(), original_rect.top()),
                         QPoint(original_rect.right(), new_rect.bottom())).normalized()
        elif self.resize_corner == 'bottom-right':
            return QRect(original_rect.topLeft(), new_rect.bottomRight()).normalized()
        return new_rect

    def rect_to_yolo(self, rect):
        if not self.original_pixmap:
            return [0, 0, 0, 0]

        orig_width = self.original_pixmap.width()
        orig_height = self.original_pixmap.height()

        x = rect.x() / self.zoom_factor
        y = rect.y() / self.zoom_factor
        w = rect.width() / self.zoom_factor
        h = rect.height() / self.zoom_factor

        center_x = (x + w / 2) / orig_width
        center_y = (y + h / 2) / orig_height
        norm_width = w / orig_width
        norm_height = h / orig_height

        return [center_x, center_y, norm_width, norm_height]

    def yolo_to_rect(self, yolo_bbox):
        if not self.scaled_pixmap:
            return QRect()

        center_x, center_y, width, height = yolo_bbox

        scaled_width = self.scaled_pixmap.width()
        scaled_height = self.scaled_pixmap.height()

        x = (center_x - width / 2) * scaled_width
        y = (center_y - height / 2) * scaled_height
        w = width * scaled_width
        h = height * scaled_height

        return QRect(int(x), int(y), int(w), int(h))

    def draw_rulers(self, painter):
        """Draw rulers on the top and left sides of the canvas."""
        ruler_thickness = 24
        tick_interval = 50  # pixels between major ticks
        minor_tick = 10  # pixels between minor ticks

        # Draw top ruler
        painter.save()
        painter.setPen(QPen(QColor(180, 180, 180), 1))
        painter.setBrush(QColor(240, 240, 240, 220))
        painter.drawRect(0, 0, self.width(), ruler_thickness)

        for x in range(0, self.width(), minor_tick):
            if x % tick_interval == 0:
                painter.drawLine(x, 0, x, ruler_thickness)
                painter.setFont(QFont("Arial", 8))
                painter.drawText(x + 2, ruler_thickness - 8, str(x))
            else:
                painter.drawLine(x, ruler_thickness - 8, x, ruler_thickness)
        painter.restore()

        # Draw left ruler
        painter.save()
        painter.setPen(QPen(QColor(180, 180, 180), 1))
        painter.setBrush(QColor(240, 240, 240, 220))
        painter.drawRect(0, 0, ruler_thickness, self.height())

        for y in range(0, self.height(), minor_tick):
            if y % tick_interval == 0:
                painter.drawLine(0, y, ruler_thickness, y)
                painter.setFont(QFont("Arial", 8))
                painter.drawText(2, y + 12, str(y))
            else:
                painter.drawLine(ruler_thickness - 8, y, ruler_thickness, y)
        painter.restore()

    def leaveEvent(self, event):
        self.cursor_pos = None
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self.scaled_pixmap:
            painter.drawPixmap(self.offset, self.scaled_pixmap)

            for idx, annotation in enumerate(self.annotations):
                class_id = annotation['class']
                bbox = annotation['bbox']

                color = self.colors[class_id % len(self.colors)]

                # Use thicker border and different color for selected annotation
                if idx == self.selected_annotation_idx:
                    pen = QPen(QColor(255, 255, 0), 3)  # Yellow, thick border
                else:
                    pen = QPen(color, 2)

                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)
                rect = self.yolo_to_rect(bbox)
                painter.drawRect(rect.translated(self.offset.toPoint()))

                # Draw class label
                painter.setPen(QPen(QColor(255, 255, 255), 1))
                painter.setBrush(QBrush(color))
                font = QFont()
                font.setPixelSize(12)
                painter.setFont(font)

                label_rect = QRect(rect.x(), rect.y() - 20, 50, 20).translated(self.offset.toPoint())
                painter.fillRect(label_rect, color)
                painter.drawText(label_rect, Qt.AlignCenter, str(class_id))

                # Draw resize handles for selected box only
                if idx == self.selected_annotation_idx:
                    corners = self.get_corner_points(rect)
                    painter.setBrush(QBrush(QColor(255, 255, 255)))
                    painter.setPen(QPen(QColor(0, 0, 0), 1))
                    for corner_point in corners.values():
                        corner_point = corner_point + self.offset.toPoint()
                        painter.drawEllipse(corner_point.x() - 4, corner_point.y() - 4, 8, 8)

            # Draw current drawing/resizing rectangle
            if self.drawing or self.resizing:
                color = self.colors[self.current_class % len(self.colors)]
                pen = QPen(color, 2, Qt.DashLine)
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)
                current_rect = QRect(self.start_point, self.end_point).normalized()
                if self.resizing and self.selected_annotation_idx >= 0:
                    current_rect = self.adjust_rect_for_resize(current_rect)
                painter.drawRect(current_rect.translated(self.offset.toPoint()))

        self.draw_crosshair(painter)
        self.draw_rulers(painter)
        painter.end()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.original_pixmap:
            self.scale_and_display()