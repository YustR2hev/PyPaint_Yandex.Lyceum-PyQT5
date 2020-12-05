from PyQt5.QtCore import Qt, QPoint, QRect, QTimer, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont, QPixmap, QIcon, QImage, QTransform
from PyQt5.QtWidgets import QMainWindow, QButtonGroup, QComboBox, \
    QFontComboBox, QLabel, QApplication, QSlider, QColorDialog, QFileDialog

import sys
import types
import random

from mainwindow import Ui_MainWindow

EASEL_DIMENSIONS = 600, 400

SELECTION_PEN = QPen(QColor(0xff, 0xff, 0xff), 1, Qt.DashLine)
PREVIEW_PEN = QPen(QColor(0xff, 0xff, 0xff), 1, Qt.SolidLine)

FONT_SIZES = [7, 8, 9, 10, 11, 12, 13, 14, 18, 24, 36, 48, 64, 72, 96, 144, 288]

BRUSH_MULT = 3
SPRAY_PAINT_MULT = 5
SPRAY_PAINT_N = 100

MODES = [
    'eraser', 'fill',
    'dropper',
    'pen', 'brush',
    'spray', 'text',
    'line', 'polyline',
    'rect', 'polygon',
    'ellipse'
]

COLORS = [
    '#000000', '#82817f', '#820300', '#868417', '#007e03', '#037e7b', '#040079',
    '#81067a', '#7f7e45', '#05403c', '#0a7cf6', '#093c7e', '#7e07f9', '#7c4002',

    '#ffffff', '#c1c1c1', '#f70406', '#fffd00', '#08fb01', '#0bf8ee', '#0000fa',
    '#b92fc2', '#fffc91', '#00fd83', '#87f9f9', '#8481c4', '#dc137d', '#fb803c',
]


def build_font(config):
    font = config['font']
    font.setPointSize(config['fontsize'])
    font.setBold(config['bold'])
    font.setItalic(config['italic'])
    font.setUnderline(config['underline'])
    return font


class Easel(QLabel):
    mode = 'rectangle'

    primary_color = QColor(Qt.black)
    secondary_color = None

    primary_color_updated = pyqtSignal(str)
    secondary_color_updated = pyqtSignal(str)

    config = {
        'size': 1,
        'fill': True,
        'font': QFont('Times'),
        'fontsize': 12,
        'bold': False,
        'italic': False,
        'underline': False,
    }

    active_color = None
    preview_pen = None

    timer_event = None

    def initialize(self):
        self.background_color = QColor(self.secondary_color) if self.secondary_color else QColor(Qt.white)
        self.eraser_color = QColor(self.secondary_color) if self.secondary_color else QColor(Qt.white)
        self.eraser_color.setAlpha(100)
        self.reset()

    def reset(self):
        self.setPixmap(QPixmap(*EASEL_DIMENSIONS))

        self.pixmap().fill(self.background_color)

    def set_primary_color(self, hex):
        self.primary_color = QColor(hex)

    def set_secondary_color(self, hex):
        self.secondary_color = QColor(hex)

    def set_config(self, key, value):
        self.config[key] = value

    def set_mode(self, mode):
        self.timer_cleanup()
        self.active_shape_fn = None
        self.active_shape_args = ()

        self.origin_pos = None

        self.current_pos = None
        self.last_pos = None

        self.history_pos = None
        self.last_history = []

        self.current_text = ""
        self.last_text = ""

        self.last_config = {}

        self.dash_offset = 0
        self.locked = False
        self.mode = mode

    def reset_mode(self):
        self.set_mode(self.mode)

    def on_timer(self):
        if self.timer_event:
            self.timer_event()

    def timer_cleanup(self):
        if self.timer_event:
            timer_event = self.timer_event
            self.timer_event = None
            timer_event(final=True)

    def mousePressEvent(self, event):
        fn = getattr(self, "%s_mousePressEvent" % self.mode, None)
        if fn:
            return fn(event)

    def mouseMoveEvent(self, event):
        fn = getattr(self, "%s_mouseMoveEvent" % self.mode, None)
        if fn:
            return fn(event)

    def mouseReleaseEvent(self, event):
        fn = getattr(self, "%s_mouseReleaseEvent" % self.mode, None)
        if fn:
            return fn(event)

    def mouseDoubleClickEvent(self, event):
        fn = getattr(self, "%s_mouseDoubleClickEvent" % self.mode, None)
        if fn:
            return fn(event)

    def generic_mousePressEvent(self, event):
        self.last_pos = event.pos()

        if event.button() == Qt.LeftButton:
            self.active_color = self.primary_color
        else:
            self.active_color = self.secondary_color

    def generic_mouseReleaseEvent(self, event):
        self.last_pos = None

    def eraser_mousePressEvent(self, event):
        self.generic_mousePressEvent(event)

    def eraser_mouseMoveEvent(self, event):
        if self.last_pos:
            p = QPainter(self.pixmap())
            p.setPen(QPen(self.eraser_color, 30, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawLine(self.last_pos, event.pos())

            self.last_pos = event.pos()
            self.update()

    def eraser_mouseReleaseEvent(self, event):
        self.generic_mouseReleaseEvent(event)

    def pen_mousePressEvent(self, event):
        self.generic_mousePressEvent(event)

    def pen_mouseMoveEvent(self, event):
        if self.last_pos:
            p = QPainter(self.pixmap())
            p.setPen(QPen(self.active_color, self.config['size'], Qt.SolidLine, Qt.SquareCap, Qt.RoundJoin))
            p.drawLine(self.last_pos, event.pos())

            self.last_pos = event.pos()
            self.update()

    def pen_mouseReleaseEvent(self, event):
        self.generic_mouseReleaseEvent(event)

    def brush_mousePressEvent(self, event):
        self.generic_mousePressEvent(event)

    def brush_mouseMoveEvent(self, event):
        if self.last_pos:
            p = QPainter(self.pixmap())
            p.setPen(QPen(self.active_color, self.config['size'] * BRUSH_MULT, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawLine(self.last_pos, event.pos())

            self.last_pos = event.pos()
            self.update()

    def brush_mouseReleaseEvent(self, event):
        self.generic_mouseReleaseEvent(event)

    def spray_mousePressEvent(self, event):
        self.generic_mousePressEvent(event)

    def spray_mouseMoveEvent(self, event):
        if self.last_pos:
            p = QPainter(self.pixmap())
            p.setPen(QPen(self.active_color, 1))

            for n in range(self.config['size'] * SPRAY_PAINT_N):
                xo = random.gauss(0, self.config['size'] * SPRAY_PAINT_MULT)
                yo = random.gauss(0, self.config['size'] * SPRAY_PAINT_MULT)
                p.drawPoint(event.x() + xo, event.y() + yo)

        self.update()

    def spray_mouseReleaseEvent(self, event):
        self.generic_mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if self.mode == 'text':
            if event.key() == Qt.Key_Backspace:
                self.current_text = self.current_text[:-1]
            else:
                self.current_text = self.current_text + event.text()

    def text_mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.current_pos is None:
            self.current_pos = event.pos()
            self.current_text = ""
            self.timer_event = self.text_timerEvent

        elif event.button() == Qt.LeftButton:

            self.timer_cleanup()
            p = QPainter(self.pixmap())
            p.setRenderHints(QPainter.Antialiasing)
            font = build_font(self.config)
            p.setFont(font)
            pen = QPen(self.primary_color, 1, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            p.setPen(pen)
            p.drawText(self.current_pos, self.current_text)
            self.update()

            self.reset_mode()

        elif event.button() == Qt.RightButton and self.current_pos:
            self.reset_mode()

    def text_timerEvent(self, final=False):
        p = QPainter(self.pixmap())
        p.setCompositionMode(QPainter.RasterOp_SourceXorDestination)
        pen = PREVIEW_PEN
        p.setPen(pen)
        if self.last_text:
            font = build_font(self.last_config)
            p.setFont(font)
            p.drawText(self.current_pos, self.last_text)

        if not final:
            font = build_font(self.config)
            p.setFont(font)
            p.drawText(self.current_pos, self.current_text)

        self.last_text = self.current_text
        self.last_config = self.config.copy()
        self.update()

    def fill_mousePressEvent(self, event):

        if event.button() == Qt.LeftButton:
            self.active_color = self.primary_color
        else:
            self.active_color = self.secondary_color

        image = self.pixmap().toImage()
        w, h = image.width(), image.height()
        x, y = event.x(), event.y()

        target_color = image.pixel(x, y)

        have_seen = set()
        queue = [(x, y)]

        def get_cardinal_points(have_seen, center_pos):
            points = []
            cx, cy = center_pos
            for x, y in [(1, 0), (0, 1), (-1, 0), (0, -1)]:
                xx, yy = cx + x, cy + y
                if (xx >= 0) and (xx < w) and (yy >= 0) and (yy < h) and (xx, yy) not in have_seen:
                    points.append((xx, yy))
                    have_seen.add((xx, yy))

            return points

        p = QPainter(self.pixmap())
        p.setPen(QPen(self.active_color))

        while queue:
            x, y = queue.pop()
            if image.pixel(x, y) == target_color:
                p.drawPoint(QPoint(x, y))
                queue.extend(get_cardinal_points(have_seen, (x, y)))

        self.update()

    def dropper_mousePressEvent(self, event):
        c = self.pixmap().toImage().pixel(event.pos())
        hex = QColor(c).name()

        if event.button() == Qt.LeftButton:
            self.set_primary_color(hex)
            self.primary_color_updated.emit(hex)

        elif event.button() == Qt.RightButton:
            self.set_secondary_color(hex)
            self.secondary_color_updated.emit(hex)

    def generic_shape_mousePressEvent(self, event):
        self.origin_pos = event.pos()
        self.current_pos = event.pos()
        self.timer_event = self.generic_shape_timerEvent

    def generic_shape_timerEvent(self, final=False):
        p = QPainter(self.pixmap())
        p.setCompositionMode(QPainter.RasterOp_SourceXorDestination)
        pen = self.preview_pen
        pen.setDashOffset(self.dash_offset)
        p.setPen(pen)
        if self.last_pos:
            getattr(p, self.active_shape_fn)(QRect(self.origin_pos, self.last_pos), *self.active_shape_args)

        if not final:
            self.dash_offset -= 1
            pen.setDashOffset(self.dash_offset)
            p.setPen(pen)
            getattr(p, self.active_shape_fn)(QRect(self.origin_pos, self.current_pos), *self.active_shape_args)

        self.update()
        self.last_pos = self.current_pos

    def generic_shape_mouseMoveEvent(self, event):
        self.current_pos = event.pos()

    def generic_shape_mouseReleaseEvent(self, event):
        if self.last_pos:
            self.timer_cleanup()

            p = QPainter(self.pixmap())
            p.setPen(QPen(self.primary_color, self.config['size'], Qt.SolidLine, Qt.SquareCap, Qt.MiterJoin))

            if self.config['fill']:
                p.setBrush(QBrush(self.secondary_color))
            getattr(p, self.active_shape_fn)(QRect(self.origin_pos, event.pos()), *self.active_shape_args)
            self.update()

        self.reset_mode()

    def line_mousePressEvent(self, event):
        self.origin_pos = event.pos()
        self.current_pos = event.pos()
        self.preview_pen = PREVIEW_PEN
        self.timer_event = self.line_timerEvent

    def line_timerEvent(self, final=False):
        p = QPainter(self.pixmap())
        p.setCompositionMode(QPainter.RasterOp_SourceXorDestination)
        pen = self.preview_pen
        p.setPen(pen)
        if self.last_pos:
            p.drawLine(self.origin_pos, self.last_pos)

        if not final:
            p.drawLine(self.origin_pos, self.current_pos)

        self.update()
        self.last_pos = self.current_pos

    def line_mouseMoveEvent(self, event):
        self.current_pos = event.pos()

    def line_mouseReleaseEvent(self, event):
        if self.last_pos:
            self.timer_cleanup()

            p = QPainter(self.pixmap())
            p.setPen(QPen(self.primary_color, self.config['size'], Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))

            p.drawLine(self.origin_pos, event.pos())
            self.update()

        self.reset_mode()

    def generic_poly_mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.history_pos:
                self.history_pos.append(event.pos())
            else:
                self.history_pos = [event.pos()]
                self.current_pos = event.pos()
                self.timer_event = self.generic_poly_timerEvent

        elif event.button() == Qt.RightButton and self.history_pos:
            self.timer_cleanup()
            self.reset_mode()

    def generic_poly_timerEvent(self, final=False):
        p = QPainter(self.pixmap())
        p.setCompositionMode(QPainter.RasterOp_SourceXorDestination)
        pen = self.preview_pen
        pen.setDashOffset(self.dash_offset)
        p.setPen(pen)
        if self.last_history:
            getattr(p, self.active_shape_fn)(*self.last_history)

        if not final:
            self.dash_offset -= 1
            pen.setDashOffset(self.dash_offset)
            p.setPen(pen)
            getattr(p, self.active_shape_fn)(*self.history_pos + [self.current_pos])

        self.update()
        self.last_pos = self.current_pos
        self.last_history = self.history_pos + [self.current_pos]

    def generic_poly_mouseMoveEvent(self, event):
        self.current_pos = event.pos()

    def generic_poly_mouseDoubleClickEvent(self, event):
        self.timer_cleanup()
        p = QPainter(self.pixmap())
        p.setPen(QPen(self.primary_color, self.config['size'], Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))

        if self.secondary_color:
            p.setBrush(QBrush(self.secondary_color))

        getattr(p, self.active_shape_fn)(*self.history_pos + [event.pos()])
        self.update()
        self.reset_mode()

    def polyline_mousePressEvent(self, event):
        self.active_shape_fn = 'drawPolyline'
        self.preview_pen = PREVIEW_PEN
        self.generic_poly_mousePressEvent(event)

    def polyline_timerEvent(self, final=False):
        self.generic_poly_timerEvent(final)

    def polyline_mouseMoveEvent(self, event):
        self.generic_poly_mouseMoveEvent(event)

    def polyline_mouseDoubleClickEvent(self, event):
        self.generic_poly_mouseDoubleClickEvent(event)

    def rect_mousePressEvent(self, event):
        self.active_shape_fn = 'drawRect'
        self.active_shape_args = ()
        self.preview_pen = PREVIEW_PEN
        self.generic_shape_mousePressEvent(event)

    def rect_timerEvent(self, final=False):
        self.generic_shape_timerEvent(final)

    def rect_mouseMoveEvent(self, event):
        self.generic_shape_mouseMoveEvent(event)

    def rect_mouseReleaseEvent(self, event):
        self.generic_shape_mouseReleaseEvent(event)

    def polygon_mousePressEvent(self, event):
        self.active_shape_fn = 'drawPolygon'
        self.preview_pen = PREVIEW_PEN
        self.generic_poly_mousePressEvent(event)

    def polygon_timerEvent(self, final=False):
        self.generic_poly_timerEvent(final)

    def polygon_mouseMoveEvent(self, event):
        self.generic_poly_mouseMoveEvent(event)

    def polygon_mouseDoubleClickEvent(self, event):
        self.generic_poly_mouseDoubleClickEvent(event)

    def ellipse_mousePressEvent(self, event):
        self.active_shape_fn = 'drawEllipse'
        self.active_shape_args = ()
        self.preview_pen = PREVIEW_PEN
        self.generic_shape_mousePressEvent(event)

    def ellipse_timerEvent(self, final=False):
        self.generic_shape_timerEvent(final)

    def ellipse_mouseMoveEvent(self, event):
        self.generic_shape_mouseMoveEvent(event)

    def ellipse_mouseReleaseEvent(self, event):
        self.generic_shape_mouseReleaseEvent(event)

    def roundrect_mousePressEvent(self, event):
        self.active_shape_fn = 'drawRoundedRect'
        self.active_shape_args = (25, 25)
        self.preview_pen = PREVIEW_PEN
        self.generic_shape_mousePressEvent(event)

    def roundrect_timerEvent(self, final=False):
        self.generic_shape_timerEvent(final)

    def roundrect_mouseMoveEvent(self, event):
        self.generic_shape_mouseMoveEvent(event)

    def roundrect_mouseReleaseEvent(self, event):
        self.generic_shape_mouseReleaseEvent(event)


class MainWindow(QMainWindow, Ui_MainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)

        self.horizontalLayout.removeWidget(self.canvas)
        self.canvas = Easel()
        self.canvas.initialize()
        self.canvas.setMouseTracking(True)
        self.canvas.setFocusPolicy(Qt.StrongFocus)
        self.horizontalLayout.addWidget(self.canvas)
        self.setWindowIcon(QIcon('Icon.png'))
        self.setWindowFlags(Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.show()

        mode_group = QButtonGroup(self)
        mode_group.setExclusive(True)

        for mode in MODES:
            btn = getattr(self, '%sButton' % mode)
            btn.pressed.connect(lambda mode=mode: self.canvas.set_mode(mode))
            mode_group.addButton(btn)

        self.primaryButton.pressed.connect(lambda: self.choose_color(self.set_primary_color))
        self.secondaryButton.pressed.connect(lambda: self.choose_color(self.set_secondary_color))

        for n, hex in enumerate(COLORS, 1):
            btn = getattr(self, 'colorButton_%d' % n)
            btn.setStyleSheet('QPushButton { background-color: %s; }' % hex)
            btn.hex = hex

            def patch_mousePressEvent(self_, event):
                if event.button() == Qt.LeftButton:
                    self.set_primary_color(self_.hex)

                elif event.button() == Qt.RightButton:
                    self.set_secondary_color(self_.hex)

            btn.mousePressEvent = types.MethodType(patch_mousePressEvent, btn)

        self.actionCopy.triggered.connect(self.copy_to_clipboard)

        self.timer = QTimer()
        self.timer.timeout.connect(self.canvas.on_timer)
        self.timer.setInterval(100)
        self.timer.start()

        self.set_primary_color('#000000')
        self.set_secondary_color('#ffffff')

        self.canvas.primary_color_updated.connect(self.set_primary_color)
        self.canvas.secondary_color_updated.connect(self.set_secondary_color)

        self.actionNewImage.triggered.connect(self.canvas.initialize)
        self.actionOpenImage.triggered.connect(self.open_file)
        self.actionSaveImage.triggered.connect(self.save_file)
        self.actionClearImage.triggered.connect(self.canvas.reset)
        self.actionInvertColors.triggered.connect(self.invert)
        self.actionFlipHorizontal.triggered.connect(self.flip_horizontal)
        self.actionFlipVertical.triggered.connect(self.flip_vertical)

        self.fontselect = QFontComboBox()
        self.fontToolbar.addWidget(self.fontselect)
        self.fontselect.currentFontChanged.connect(lambda f: self.canvas.set_config('font', f))
        self.fontselect.setCurrentFont(QFont('Times'))

        self.fontsize = QComboBox()
        self.fontsize.addItems([str(s) for s in FONT_SIZES])
        self.fontsize.currentTextChanged.connect(lambda f: self.canvas.set_config('fontsize', int(f)))

        self.fontToolbar.addWidget(self.fontsize)

        self.fontToolbar.addAction(self.actionBold)
        self.actionBold.triggered.connect(lambda s: self.canvas.set_config('bold', s))
        self.fontToolbar.addAction(self.actionItalic)
        self.actionItalic.triggered.connect(lambda s: self.canvas.set_config('italic', s))
        self.fontToolbar.addAction(self.actionUnderline)
        self.actionUnderline.triggered.connect(lambda s: self.canvas.set_config('underline', s))

        sizeicon = QLabel()
        sizeicon.setPixmap(QPixmap(':/icons/border-weight.png'))
        self.drawingToolbar.addWidget(sizeicon)
        self.sizeselect = QSlider()
        self.sizeselect.setRange(1, 20)
        self.sizeselect.setOrientation(Qt.Horizontal)
        self.sizeselect.valueChanged.connect(lambda s: self.canvas.set_config('size', s))
        self.drawingToolbar.addWidget(self.sizeselect)

        self.actionFillShapes.triggered.connect(lambda s: self.canvas.set_config('fill', s))
        self.drawingToolbar.addAction(self.actionFillShapes)
        self.actionFillShapes.setChecked(True)

        self.show()

    def choose_color(self, callback):
        dilalog = QColorDialog()
        if dilalog.exec():
            callback(dilalog.selectedColor().name())

    def set_primary_color(self, hex):
        self.canvas.set_primary_color(hex)
        self.primaryButton.setStyleSheet('QPushButton { background-color: %s; }' % hex)

    def set_secondary_color(self, hex):
        self.canvas.set_secondary_color(hex)
        self.secondaryButton.setStyleSheet('QPushButton { background-color: %s; }' % hex)

    def copy_to_clipboard(self):
        clipboard = QApplication.clipboard()

        if self.canvas.mode == 'selectrect' and self.canvas.locked:
            clipboard.setPixmap(self.canvas.selectrect_copy())

        elif self.canvas.mode == 'selectpoly' and self.canvas.locked:
            clipboard.setPixmap(self.canvas.selectpoly_copy())

        else:
            clipboard.setPixmap(self.canvas.pixmap())

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open file", "",
                                              "PNG image files (*.png); JPEG image files (*jpg); All files (*.*)")

        if path:
            pixmap = QPixmap()
            pixmap.load(path)

            image_weight = pixmap.width()
            image_height = pixmap.height()

            easel_weight, ch = EASEL_DIMENSIONS

            if image_weight / easel_weight < image_height / ch:
                pixmap = pixmap.scaledToWidth(easel_weight)
                hoff = (pixmap.height() - ch) // 2
                pixmap = pixmap.copy(
                    QRect(QPoint(0, hoff), QPoint(easel_weight, pixmap.height() - hoff))
                )

            elif image_weight / easel_weight > image_height / ch:
                pixmap = pixmap.scaledToHeight(ch)
                woff = (pixmap.width() - easel_weight) // 2
                pixmap = pixmap.copy(
                    QRect(QPoint(woff, 0), QPoint(pixmap.width() - woff, ch))
                )

            self.canvas.setPixmap(pixmap)

    def save_file(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save file", "", "PNG Image file (*.png)")

        if path:
            pixmap = self.canvas.pixmap()
            pixmap.save(path, "PNG")

    def invert(self):
        image_ = QImage(self.canvas.pixmap())
        image_.invertPixels()
        pixmap = QPixmap()
        pixmap.convertFromImage(image_)
        self.canvas.setPixmap(pixmap)

    def flip_horizontal(self):
        pixmap = self.canvas.pixmap()
        self.canvas.setPixmap(pixmap.transformed(QTransform().scale(-1, 1)))

    def flip_vertical(self):
        pixmap = self.canvas.pixmap()
        self.canvas.setPixmap(pixmap.transformed(QTransform().scale(1, -1)))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    app.exec_()
