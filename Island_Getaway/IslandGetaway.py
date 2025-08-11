# python
# Dynamic Island-like effect for MacBook Pro notch area
# Requires: pip install PyQt5

import sys
import time
import requests
import subprocess
from PyQt5.QtCore import Qt, QTimer, QRect, QPropertyAnimation, QEasingCurve
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QSizePolicy, QPushButton, QHBoxLayout
from PyQt5.QtGui import QFont, QPainter, QColor, QBrush, QPainterPath

class DynamicIsland(QWidget):
    def __init__(self):
        super().__init__()
        self.screen = QApplication.primaryScreen()
        geometry = self.screen.geometry()
        self.screen_width = geometry.width()
        self.screen_height = geometry.height()
        print(f"Screen size: {self.screen_width}x{self.screen_height}")

        # --- Notch and Dynamic Island dimensions ---
        self.notch_width = int(self.screen_width * 0.13)
        self.notch_height = 30
        self.notch_x = (self.screen_width - self.notch_width) // 2
        self.notch_y = 0

        self.island_width = int(self.notch_width * 2.2)
        self.island_height = self.notch_height + 60
        self.island_x = self.notch_x - int((self.island_width - self.notch_width) // 2)
        self.island_y = 0

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setGeometry(self.island_x, self.island_y, self.island_width, self.island_height)
        self.hide()

        # Layout for stacking labels
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top bar layout for clock and weather stacked vertically
        top_bar = QWidget(self)
        top_layout = QVBoxLayout(top_bar)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(0)

        self.clock = QLabel(self)
        self.clock.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self.clock.setFont(QFont('Arial', 20))
        self.clock.setStyleSheet("color: white;")
        top_layout.addWidget(self.clock)
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_clock)

        self.weather = QLabel(self)
        self.weather.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self.weather.setFont(QFont('Arial', 16))
        self.weather.setStyleSheet("color: white;")
        self.weather.setWordWrap(False)
        self.weather.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.weather.setText('Loading weather...')
        self.weather.setCursor(Qt.PointingHandCursor)  # Show clickable cursor
        self.weather.mousePressEvent = self.show_detailed_weather  # Attach click handler
        top_layout.addWidget(self.weather)
        self.weather_timer = QTimer(self)
        self.weather_timer.timeout.connect(self.update_weather)
        self.weather_timer.start(600000)
        self.update_weather()

        self.detailed_weather_visible = False  # Track state

        layout.addWidget(top_bar)

        # --- Bottom bar with widgets ---
        self.bottom_bar = QWidget(self)
        self.bottom_layout = QHBoxLayout(self.bottom_bar)
        self.bottom_layout.setContentsMargins(10, 5, 10, 5)
        self.bottom_layout.setSpacing(10)

        # Terminal emoji widget
        self.terminal_btn = QLabel("🖥️", self)
        self.terminal_btn.setFont(QFont('Arial', 20))
        self.terminal_btn.setStyleSheet("color: white; padding: 4px; border-radius: 8px;")
        self.terminal_btn.setAlignment(Qt.AlignCenter)
        self.terminal_btn.setFixedSize(32, 32)
        self.terminal_btn.setAttribute(Qt.WA_Hover)
        self.bottom_layout.addWidget(self.terminal_btn)

        # Internet emoji widget (use QPushButton for better event handling)
        from PyQt5.QtWidgets import QPushButton
        self.internet_btn = QPushButton("🌐", self)
        self.internet_btn.setFont(QFont('Arial', 20))
        self.internet_btn.setStyleSheet("color: white; background: transparent; border: none; padding: 4px; border-radius: 8px;")
        self.internet_btn.setFixedSize(32, 32)
        self.internet_btn.setCursor(Qt.PointingHandCursor)
        self.bottom_layout.addWidget(self.internet_btn)
        self.internet_btn.installEventFilter(self)

        # Add more widgets here if needed
        # Example: self.bottom_layout.addWidget(QLabel("⭐", self))

        layout.addWidget(self.bottom_bar)

        # --- Terminal interface (hidden by default) ---
        self.terminal_widget = QWidget(self)
        self.terminal_widget.setStyleSheet("background: #111; border-radius: 8px; border: 1px solid #222;")
        self.terminal_widget.setMinimumSize(400, 160)
        self.terminal_widget.setMaximumSize(self.screen_width, self.screen_height)
        self.terminal_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.terminal_widget.setWindowFlags(Qt.SubWindow | Qt.FramelessWindowHint)
        self.terminal_widget.setMouseTracking(True)
        self.terminal_widget.setAttribute(Qt.WA_TranslucentBackground, False)
        self.terminal_widget.setAttribute(Qt.WA_StyledBackground, True)
        self.terminal_widget.setCursor(Qt.SizeFDiagCursor)

        self.terminal_layout = QVBoxLayout(self.terminal_widget)
        self.terminal_layout.setContentsMargins(12, 12, 12, 12)
        self.terminal_layout.setSpacing(8)
        self.terminal_layout.setAlignment(Qt.AlignTop)

        self.terminal_output = QLabel("", self.terminal_widget)
        self.terminal_output.setFont(QFont('Arial', 14))
        self.terminal_output.setStyleSheet("color: #00FF00; background: #222; border-radius: 4px; padding: 8px; border: 1px solid #333;")
        self.terminal_output.setWordWrap(True)
        self.terminal_output.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.terminal_output.setMinimumHeight(80)
        self.terminal_layout.addWidget(self.terminal_output)

        from PyQt5.QtWidgets import QLineEdit, QPushButton
        self.terminal_input = QLineEdit(self.terminal_widget)
        self.terminal_input.setFont(QFont('Arial', 14))
        self.terminal_input.setStyleSheet("color: #00FF00; background: #222; border-radius: 4px; padding: 8px; border: 1px solid #333;")
        self.terminal_input.setAlignment(Qt.AlignLeft)
        self.terminal_input.setMinimumHeight(32)
        self.terminal_layout.addWidget(self.terminal_input)
        self.terminal_input.returnPressed.connect(self.run_terminal_command)

        # Back button to return to standard island
        self.back_btn = QPushButton("⬅️ Back", self.terminal_widget)
        self.back_btn.setStyleSheet("color: white; background: #333; border-radius: 6px; padding: 6px; border: none;")
        self.back_btn.setFixedWidth(80)
        self.back_btn.clicked.connect(self.show_standard_island)
        self.terminal_layout.addWidget(self.back_btn, alignment=Qt.AlignRight)

        self.terminal_widget.hide()
        layout.addWidget(self.terminal_widget, alignment=Qt.AlignCenter)

        # --- Search bubble (hidden by default) ---
        from PyQt5.QtWidgets import QLineEdit, QGraphicsDropShadowEffect
        self.search_bubble = QWidget(None)
        self.search_bubble.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.search_bubble.setAttribute(Qt.WA_TranslucentBackground)
        self.search_bubble.setStyleSheet("background: #000; border-radius: 24px; border: 1px solid #333;")
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(18)
        shadow.setColor(QColor(0,0,0,180))
        shadow.setOffset(0, 6)
        self.search_bubble.setGraphicsEffect(shadow)
        bubble_layout = QVBoxLayout(self.search_bubble)
        bubble_layout.setContentsMargins(16, 16, 16, 16)
        self.search_bar = QLineEdit(self.search_bubble)
        self.search_bar.setFont(QFont('Arial', 14))
        self.search_bar.setStyleSheet("color: white; background: transparent; border: none;")
        self.search_bar.setPlaceholderText("Type to search...")
        bubble_layout.addWidget(self.search_bar)
        self.search_bubble.hide()
        self.search_bar.returnPressed.connect(self.launch_search)

        # --- Enable resizing from bottom right corner ---
        self.terminal_widget.grabbed = False
        self.terminal_widget.old_pos = None
        self.terminal_widget.installEventFilter(self)
        self.terminal_btn.installEventFilter(self)

        # Ensure mouse tracking and hover logic for main island
        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(350)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)

        self.search_anim = QPropertyAnimation(self, b"geometry")
        self.search_anim.setDuration(350)
        self.search_anim.setEasingCurve(QEasingCurve.OutCubic)

        self.is_mouse_over = False
        self.mouse_timer = QTimer(self)
        self.mouse_timer.timeout.connect(self.check_mouse)
        self.hide_delay_timer = QTimer(self)
        self.hide_delay_timer.setSingleShot(True)
        self.hide_delay_timer.timeout.connect(self.animate_hide)
        self.mouse_timer.start(50)

    def eventFilter(self, obj, event):
        from PyQt5.QtCore import QEvent
        if obj == self.terminal_btn:
            if event.type() == QEvent.Enter:
                import subprocess
                subprocess.Popen(['open', '-a', 'Terminal'])
            elif event.type() == QEvent.MouseButtonPress:
                import subprocess
                subprocess.Popen(['open', '-a', 'Terminal'])
        if obj == self.internet_btn:
            if event.type() == QEvent.Enter:
                self.show_search_bar()
            elif event.type() == QEvent.Leave:
                self.hide_search_bar()
        return super().eventFilter(obj, event)

    def show_terminal_island(self):
        if not self.is_terminal_mode:
            self.is_terminal_mode = True
            self.animate_terminal_expand()
            self.terminal_widget.show()
            self.bottom_bar.hide()
            self.clock.hide()
            self.weather.hide()

    def show_standard_island(self):
        if self.is_terminal_mode:
            self.is_terminal_mode = False
            self.animate_terminal_collapse()
            self.terminal_widget.hide()
            self.bottom_bar.show()
            self.clock.show()
            self.weather.show()

    def animate_terminal_expand(self):
        # Animate to a larger geometry for terminal mode
        new_height = self.island_height + 120
        new_rect = QRect(self.island_x, self.island_y, self.island_width, new_height)
        self.anim.stop()
        self.anim.setStartValue(self.geometry())
        self.anim.setEndValue(new_rect)
        self.anim.start()
        self.setGeometry(new_rect)

    def animate_terminal_collapse(self):
        # Animate back to original geometry
        orig_rect = QRect(self.island_x, self.island_y, self.island_width, self.island_height)
        self.anim.stop()
        self.anim.setStartValue(self.geometry())
        self.anim.setEndValue(orig_rect)
        self.anim.start()
        self.setGeometry(orig_rect)

    def run_terminal_command(self):
        cmd = self.terminal_input.text()
        if not cmd.strip():
            return
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
            output = result.stdout if result.stdout else result.stderr
        except Exception as e:
            output = str(e)
        self.terminal_output.setText(output)
        self.terminal_input.clear()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        radius = 32
        # Use current widget size for background
        width = self.width()
        height = self.height()
        path.addRoundedRect(0, 0, width, height, radius, radius)
        painter.fillPath(path, QBrush(QColor(0, 0, 0)))

    def update_clock(self):
        self.clock.setText(time.strftime('%H:%M:%S'))

    def update_weather(self):
        import time
        try:
            # Add cache-busting timestamp to the URL
            ts = int(time.time())
            resp = requests.get(f'https://wttr.in/?format=3&t={ts}', timeout=5)
            print(f"Weather response: {resp.text}")
            if resp.status_code == 200 and resp.text.strip():
                import re
                # Match temperature (e.g. 23°C or -5°F) and any emoji
                temp_match = re.search(r'(-?\d+\s*°[CF])', resp.text)
                emoji_match = re.search(r'([\U0001F300-\U0001FAFF\u2600-\u26FF])', resp.text)
                if temp_match and emoji_match:
                    temp = temp_match.group(1)
                    emoji = emoji_match.group(1)
                    self.weather.setText(f"{temp} {emoji}")
                else:
                    self.weather.setText('Weather unavailable')
            else:
                # Also add cache-busting to fallback
                fallback = requests.get(f'https://wttr.in/Pittsburgh?format=3&t={ts}', timeout=5)
                if fallback.status_code == 200 and fallback.text.strip():
                    import re
                    temp_match = re.search(r'(-?\d+\s*°[CF])', fallback.text)
                    emoji_match = re.search(r'([\U0001F300-\U0001FAFF\u2600-\u26FF])', fallback.text)
                    if temp_match and emoji_match:
                        temp = temp_match.group(1)
                        emoji = emoji_match.group(1)
                        self.weather.setText(f"{temp} {emoji}")
                    else:
                        self.weather.setText('Weather unavailable')
                else:
                    self.weather.setText('Weather unavailable')
        except Exception as e:
            print(f"Weather error: {e}")
            self.weather.setText('Weather unavailable')

    def check_mouse(self):
        pos = QApplication.instance().desktop().cursor().pos()
        # Use global geometry for the island and terminal widget
        island_rect = self.frameGeometry()
        terminal_rect = self.terminal_widget.frameGeometry() if self.terminal_widget.isVisible() else None
        in_island = island_rect.contains(pos)
        in_terminal = terminal_rect and terminal_rect.contains(pos)
        in_notch = (self.notch_x <= pos.x() <= self.notch_x + self.notch_width and
                    self.notch_y <= pos.y() <= self.notch_y + self.notch_height)
        # Only trigger opening if mouse is inside the notch
        if in_notch or (self.isVisible() and (in_island or in_terminal)):
            if not self.is_mouse_over:
                self.is_mouse_over = True
                if in_notch:
                    self.animate_show()
            self.hide_delay_timer.stop()
        else:
            if self.is_mouse_over:
                self.is_mouse_over = False
                self.hide_delay_timer.start(1500)

    def animate_show(self):
        self.show()
        self.raise_()
        self.activateWindow()
        self.clock_timer.start(1000)
        self.mouse_timer.stop()
        start_rect = QRect(self.notch_x, self.notch_y, self.notch_width, self.notch_height)
        end_rect = QRect(self.island_x, self.island_y, self.island_width, self.island_height)
        self.anim.stop()
        self.anim.setStartValue(start_rect)
        self.anim.setEndValue(end_rect)
        self.anim.finished.connect(self.on_show_animation_finished)
        self.anim.start()

    def on_show_animation_finished(self):
        self.mouse_timer.start(50)
        try:
            self.anim.finished.disconnect(self.on_show_animation_finished)
        except Exception:
            pass

    def animate_hide(self):
        self.clock_timer.stop()
        start_rect = QRect(self.island_x, self.island_y, self.island_width, self.island_height)
        end_rect = QRect(self.notch_x, self.notch_y, self.notch_width, self.notch_height)
        self.anim.stop()
        self.anim.setStartValue(start_rect)
        self.anim.setEndValue(end_rect)
        self.anim.finished.connect(self.hide_island)
        self.anim.start()

    def hide_island(self):
        super().hide()
        try:
            self.anim.finished.disconnect(self.hide_island)
        except Exception:
            pass

    def show_search_bar(self):
        # Position bubble below the current island geometry
        island_rect = self.geometry()
        bubble_width = island_rect.width() - 40
        bubble_height = 56
        bubble_x = island_rect.x() + 25
        bubble_y = island_rect.y() + island_rect.height() - 12  # removing some padding space here because im a trash developer
        self.search_bubble.setGeometry(bubble_x, bubble_y, bubble_width, bubble_height)
        # Set black rounded background with padding and border for visibility
        self.search_bubble.setStyleSheet("background-color: #111; border-radius: 24px; border: 2px solid #222; padding: 8px;")
        # Make the search bar fill the bubble and have rounded corners
        self.search_bar.setStyleSheet("color: white; background: #000; border-radius: 16px; border: none; padding: 10px 16px; font-size: 16px;")
        self.search_bubble.setAttribute(Qt.WA_StyledBackground, True)
        self.search_bubble.setAttribute(Qt.WA_TranslucentBackground, True)
        self.search_bubble.show()
        self.search_bar.setFocus()

    def hide_search_bar(self):
        self.search_bubble.hide()

    def launch_search(self):
        import webbrowser
        query = self.search_bar.text().strip()
        if query:
            url = f"https://bangathome.free.nf/?q={query.replace(' ', '+')}"
            webbrowser.open(url)
        self.search_bar.clear()
        self.hide_search_bar()

    def show_detailed_weather(self, event):
        if not self.detailed_weather_visible:
            # Expand Dynamic Island for detailed weather
            expanded_height = self.island_height + 80
            expanded_rect = QRect(self.island_x, self.island_y, self.island_width, expanded_height)
            self.anim.stop()
            self.anim.setStartValue(self.geometry())
            self.anim.setEndValue(expanded_rect)
            self.anim.start()
            self.setGeometry(expanded_rect)
            self.weather.setFont(QFont('Arial', 16, QFont.Bold))
            self.weather.setText(self.get_detailed_weather())
            self.weather.setWordWrap(True)
            self.detailed_weather_visible = True
        else:
            # Collapse Dynamic Island back to original size
            orig_rect = QRect(self.island_x, self.island_y, self.island_width, self.island_height)
            self.anim.stop()
            self.anim.setStartValue(self.geometry())
            self.anim.setEndValue(orig_rect)
            self.anim.start()
            self.setGeometry(orig_rect)
            self.weather.setFont(QFont('Arial', 16))
            self.weather.setText(self.get_weather_summary())
            self.weather.setWordWrap(False)
            self.detailed_weather_visible = False

    def get_detailed_weather(self):
        # Example: get latest weather and emoji
        try:
            resp = requests.get('https://wttr.in/?format=3', timeout=5)
            if resp.status_code == 200 and resp.text.strip():
                import re
                temp_match = re.search(r'(-?\d+\s*°[CF])', resp.text)
                emoji_match = re.search(r'([\U0001F300-\U0001FAFF\u2600-\u26FF])', resp.text)
                temp = temp_match.group(1) if temp_match else "N/A"
                emoji = emoji_match.group(1) if emoji_match else ""


                resp = requests.get('https://wttr.in/?format=j1', timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    temp = data['current_condition'][0]['temp_C']
                    humidity = data['current_condition'][0]['humidity']
                    wind = data['current_condition'][0]['windspeedKmph']
                    desc = data['current_condition'][0]['weatherDesc'][0]['value']
                    details = f"Temperature: {temp}°C\nHumidity: {humidity}%\nWind: {wind} km/h\nForecast: {desc}"
                return details
            else:
                return "Detailed Weather Report:\nWeather unavailable"
        except Exception:
            return "Detailed Weather Report:\nWeather unavailable"

    def get_weather_summary(self):
        # Get latest weather and emoji for summary
        try:
            resp = requests.get('https://wttr.in/?format=3', timeout=5)
            if resp.status_code == 200 and resp.text.strip():
                import re
                temp_match = re.search(r'(-?\d+\s*°[CF])', resp.text)
                emoji_match = re.search(r'([\U0001F300-\U0001FAFF\u2600-\u26FF])', resp.text)
                temp = temp_match.group(1) if temp_match else "N/A"
                emoji = emoji_match.group(1) if emoji_match else ""
                return f"{temp} {emoji}"
            else:
                return "Weather unavailable"
        except Exception:
            return "Weather unavailable"


