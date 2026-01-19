from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QPainter, QPen, QBrush
from PySide6.QtWidgets import QLabel, QSizePolicy


class ImageViewer(QLabel):
    # 添加信号，用于通知区域变化
    region_changed = Signal(float, float, float, float)

    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setText("未加载图片")
        self._pixmap = None
        # 区域参数
        self.region_left = 0.2
        self.region_top = 0.2
        self.region_right = 0.8
        self.region_bottom = 0.8
        
        # 拖拽状态
        self.dragging = False
        self.resize_direction = None  # 'left', 'top', 'right', 'bottom', 'all'
        self.drag_start_pos = None
        
        # 启用鼠标追踪
        self.setMouseTracking(True)

    def load_image(self, image_path: str):
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            self.setText("图片加载失败")
            return

        self._pixmap = pixmap
        self._update_view()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_view()

    def _update_view(self):
        if not self._pixmap:
            return
        scaled = self._pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.setPixmap(scaled)

    def set_region(self, left, top, right, bottom):
        """设置区域参数"""
        self.region_left = left
        self.region_top = top
        self.region_right = right
        self.region_bottom = bottom
        self.update()  # 触发重绘

    def get_region(self):
        """获取区域参数"""
        return self.region_left, self.region_top, self.region_right, self.region_bottom

    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton and self._pixmap:
            pos = event.pos()
            scaled_rect = self.pixmap().rect()  # 获取缩放后的图片区域
            
            # 计算缩放比例
            if self._pixmap.width() > 0 and self._pixmap.height() > 0:
                scale_x = scaled_rect.width() / self._pixmap.width()
                scale_y = scaled_rect.height() / self._pixmap.height()
                
                # 计算偏移（居中显示时的偏移）
                offset_x = (self.width() - scaled_rect.width()) // 2
                offset_y = (self.height() - scaled_rect.height()) // 2
                
                # 将鼠标位置转换为相对于图片的比例
                rel_x = (pos.x() - offset_x) / scaled_rect.width() if scaled_rect.width() > 0 else 0
                rel_y = (pos.y() - offset_y) / scaled_rect.height() if scaled_rect.height() > 0 else 0
                
                # 检查点击是否在区域内
                tolerance = 0.02  # 容差比例
                
                # 检测点击是否在边框上
                if abs(rel_x - self.region_left) <= tolerance and self.region_top <= rel_y <= self.region_bottom:
                    self.resize_direction = 'left'
                    self.dragging = True
                elif abs(rel_x - self.region_right) <= tolerance and self.region_top <= rel_y <= self.region_bottom:
                    self.resize_direction = 'right'
                    self.dragging = True
                elif abs(rel_y - self.region_top) <= tolerance and self.region_left <= rel_x <= self.region_right:
                    self.resize_direction = 'top'
                    self.dragging = True
                elif abs(rel_y - self.region_bottom) <= tolerance and self.region_left <= rel_x <= self.region_right:
                    self.resize_direction = 'bottom'
                    self.dragging = True
                elif (self.region_left <= rel_x <= self.region_right and self.region_top <= rel_y <= self.region_bottom):
                    self.resize_direction = 'all'
                    self.drag_start_pos = (rel_x, rel_y)
                    self.dragging = True

    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if self.dragging and self.resize_direction and self._pixmap:
            pos = event.pos()
            scaled_rect = self.pixmap().rect()  # 获取缩放后的图片区域
            
            # 计算缩放比例
            if self._pixmap.width() > 0 and self._pixmap.height() > 0:
                scale_x = scaled_rect.width() / self._pixmap.width()
                scale_y = scaled_rect.height() / self._pixmap.height()
                
                # 计算偏移（居中显示时的偏移）
                offset_x = (self.width() - scaled_rect.width()) // 2
                offset_y = (self.height() - scaled_rect.height()) // 2
                
                # 将鼠标位置转换为相对于图片的比例
                rel_x = max(0, min(1, (pos.x() - offset_x) / scaled_rect.width())) if scaled_rect.width() > 0 else 0
                rel_y = max(0, min(1, (pos.y() - offset_y) / scaled_rect.height())) if scaled_rect.height() > 0 else 0
                
                if self.resize_direction == 'left':
                    self.region_left = max(0.0, min(self.region_right - 0.01, rel_x))
                elif self.resize_direction == 'right':
                    self.region_right = max(self.region_left + 0.01, min(1.0, rel_x))
                elif self.resize_direction == 'top':
                    self.region_top = max(0.0, min(self.region_bottom - 0.01, rel_y))
                elif self.resize_direction == 'bottom':
                    self.region_bottom = max(self.region_top + 0.01, min(1.0, rel_y))
                elif self.resize_direction == 'all' and self.drag_start_pos:
                    # 移动整个矩形
                    dx = rel_x - self.drag_start_pos[0]
                    dy = rel_y - self.drag_start_pos[1]
                    
                    new_left = max(0.0, min(1.0, self.region_left + dx))
                    new_right = max(0.0, min(1.0, self.region_right + dx))
                    new_top = max(0.0, min(1.0, self.region_top + dy))
                    new_bottom = max(0.0, min(1.0, self.region_bottom + dy))
                    
                    # 确保矩形在边界内
                    if new_left >= 0 and new_right <= 1 and new_left < new_right:
                        self.region_left = new_left
                        self.region_right = new_right
                    if new_top >= 0 and new_bottom <= 1 and new_top < new_bottom:
                        self.region_top = new_top
                        self.region_bottom = new_bottom
                    
                    self.drag_start_pos = (rel_x, rel_y)
                
                # 发送信号通知区域变化
                self.region_changed.emit(self.region_left, self.region_top, self.region_right, self.region_bottom)
                self.update()  # 重绘

    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton:
            if self.dragging:
                # 拖拽结束后发送最终的区域值
                self.region_changed.emit(self.region_left, self.region_top, self.region_right, self.region_bottom)
            self.dragging = False
            self.resize_direction = None
            self.drag_start_pos = None

    def paintEvent(self, event):
        """重写paintEvent以绘制区域"""
        super().paintEvent(event)  # 先绘制原始图片
        
        # 如果有图片且区域参数有效，则绘制区域
        if self._pixmap and self._pixmap.width() > 0 and self._pixmap.height() > 0:
            painter = QPainter(self)
            
            # 计算区域坐标
            pixmap_rect = self._pixmap.rect()
            scaled_rect = self.pixmap().rect()  # 获取缩放后的图片区域
            
            # 计算缩放比例
            scale_x = scaled_rect.width() / pixmap_rect.width()
            scale_y = scaled_rect.height() / pixmap_rect.height()
            
            # 计算偏移（居中显示时的偏移）
            offset_x = (self.width() - scaled_rect.width()) // 2
            offset_y = (self.height() - scaled_rect.height()) // 2
            
            # 计算实际区域坐标
            x = offset_x + int(self.region_left * scaled_rect.width())
            y = offset_y + int(self.region_top * scaled_rect.height())
            width = int((self.region_right - self.region_left) * scaled_rect.width())
            height = int((self.region_bottom - self.region_top) * scaled_rect.height())
            
            # 绘制区域边框
            pen = QPen(Qt.GlobalColor.red, 2, Qt.PenStyle.DashLine)
            brush = QBrush(Qt.GlobalColor.transparent)  # 透明填充
            painter.setPen(pen)
            painter.setBrush(brush)
            painter.drawRect(x, y, width, height)
            
            # 绘制角点
            point_pen = QPen(Qt.GlobalColor.blue, 6)
            painter.setPen(point_pen)
            painter.drawPoint(x, y)  # 左上角
            painter.drawPoint(x + width, y)  # 右上角
            painter.drawPoint(x, y + height)  # 左下角
            painter.drawPoint(x + width, y + height)  # 右下角

from PySide6.QtWidgets import QSizePolicy