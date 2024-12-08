from PyQt5.QtCore import Qt, QPoint, QByteArray, QTimer
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QFontDatabase, QFont
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow, QPushButton, QSlider
from spotify_auth import sp
import requests
from io import BytesIO


class SpotifyWidget(QMainWindow):
    def __init__(self, screen_width, screen_height):
        super().__init__()
        self.screen_width = int(screen_width)
        self.screen_height = int(screen_height)
        current_playback = sp.current_playback()
        if current_playback and current_playback['is_playing']:
            self.music_paused = False
        else: 
            self.music_paused = True
        self.dark_mode_enabled = False
        self.music_shuffled = False
        self.init_ui()
        self.offset = None  # For tracking window movement

    def init_ui(self):
        self.setWindowTitle("Spotify Widget")
        self.setWindowFlags(Qt.FramelessWindowHint) #| Qt.WindowStaysOnTopHint
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setGeometry(
            int(100),
            int(100),
            int(1000),
            int(500),
        )

        # Set transparent background
        self.setStyleSheet("background-color: rgba(0, 0, 0, 75);")
 
        # background plane label
        self.background_plane = QLabel("", self)
        self.background_plane.setStyleSheet(
            """
            background-color: rgba(255, 255, 255, 5);
            border: 1px solid rgba(255, 255, 255, 10);
            border-radius: 10px;
            """
        )
        self.background_plane.setGeometry(0, 0, 850, 500)


        stylesheet_top_ui = """
            QPushButton {
                border: none;
                background-color: rgba(255, 255, 255, 0);
                border-radius: 15px;
            }
            QPushButton:hover {
                background-color: #d3d3d3;
            }
            """

        # Close button
        self.close_button = QPushButton("", self)
        self.close_button.setGeometry(850 - 60, 10, 60, 60)
        self.set_svg_icon(self.close_button, "./assets/svg/x-letter.svg", 0.5)  # Initial icon (black)        
        self.close_button.setStyleSheet(stylesheet_top_ui)
        self.close_button.clicked.connect(self.close)

        # Minimize button
        self.minimize_button = QPushButton("", self)
        self.minimize_button.setGeometry(850 - 120, 10, 60, 60)
        self.set_svg_icon(self.minimize_button, "./assets/svg/minus.svg", 0.5)  # Initial icon (black)
        self.minimize_button.setStyleSheet(stylesheet_top_ui)
        self.minimize_button.clicked.connect(self.showMinimized)

        # Dark/light mode button
        # Update the dark mode button image path based on the current state
        dark_mode_image_path = "./assets/svg/moon.svg" if self.dark_mode_enabled else "./assets/svg/sun.svg"
        self.dark_mode_switch = QPushButton("", self)
        self.dark_mode_switch.setGeometry(850 - 180, 10, 60, 60)
        self.set_svg_icon(self.dark_mode_switch, dark_mode_image_path, 0.5)  # Initial icon (black)
        self.dark_mode_switch.setStyleSheet(stylesheet_top_ui)
        self.dark_mode_switch.clicked.connect(self.toggle_dark_mode)

        # Load custom fonts
        gotham_bold_id = QFontDatabase.addApplicationFont("./assets/fonts/GothamBold.ttf")
        gotham_light_id = QFontDatabase.addApplicationFont("./assets/fonts/GothamLight.ttf")

        # Get font families
        gotham_bold_family = QFontDatabase.applicationFontFamilies(gotham_bold_id)[0]
        gotham_light_family = QFontDatabase.applicationFontFamilies(gotham_light_id)[0]

        # Create specific font styles
        gotham_bold = QFont(gotham_bold_family, 25)
        gotham_bold.setBold(True)  # Ensure bold style is explicitly set

        gotham_light = QFont(gotham_light_family, 15)
        gotham_light.setWeight(QFont.Light)  # Set the light style explicitly
        

        # Get current track info
        current_track_info = self.get_current_track_info()
        if current_track_info:
            artist_name = current_track_info['artist_name']
            track_name = current_track_info['track_name']
        else:
            artist_name = "Artist"
            track_name = "Song"

        stylesheet_track_info = """
            color: "white";
            background-color: rgba(0, 0, 0, 0);
            """

        # Artist name label
        self.artist_label = QLabel(artist_name, self)
        self.artist_label.setStyleSheet(stylesheet_track_info)
        self.artist_label.setFont(gotham_light)
        self.artist_label.setGeometry(375, 250, 450, 50)

        # Song name label
        self.track_label = QLabel(track_name, self)
        self.track_label.setStyleSheet(stylesheet_track_info)
        self.track_label.setFont(gotham_bold)
        self.track_label.setGeometry(375, 50, 400, 150)
        self.track_label.setWordWrap(True)

        self.album_art_label = QLabel(self)
        self.album_art_label.setGeometry(50, 50, 275, 275)  # Adjust size and position
        #self.album_art_label.setStyleSheet("border: 2px solid white;")
        if current_track_info: self.update_album_art(current_track_info['album_image_url'])  

        media_button_stylesheet = """
            QPushButton {
                border: none;
                background-color: rgba(255, 255, 255, 0);
                padding: 10px;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 50);
            }
        """

        # Play Button with SVG icon
        # Update the play_button_path based on the current state
        self.play_button_path = "./assets/svg/media-play.svg" if self.music_paused else "./assets/svg/media-pause.svg"
        self.media_play_button = QPushButton("", self)
        self.media_play_button.setGeometry(400, 415, 50, 50)
        self.media_play_button.setStyleSheet(media_button_stylesheet)
        self.set_svg_icon(self.media_play_button, self.play_button_path, 0.5)  # Initial icon (black)
        self.media_play_button.clicked.connect(self.toggle_music)


        # Next Track Button
        self.next_button = QPushButton("", self)
        self.next_button.setGeometry(550, 415, 50, 50)
        self.next_button.setStyleSheet(media_button_stylesheet)
        self.set_svg_icon(self.next_button, "./assets/svg/media-step-forward.svg", 0.5)  # Initial icon (black)
        self.next_button.clicked.connect(self.next_track)

        # Previous Track Button
        self.previous_button = QPushButton("", self)
        self.previous_button.setGeometry(250, 415, 50, 50)
        self.previous_button.setStyleSheet(media_button_stylesheet)
        self.set_svg_icon(self.previous_button, "./assets/svg/media-step-backward.svg", 0.5)  # Initial icon (black)
        self.previous_button.clicked.connect(self.previous_track)

        # Shuffle Track Button
        self.shuffle_button = QPushButton("", self)
        self.shuffle_button.setGeometry(100, 415, 50, 50)
        self.shuffle_button.setStyleSheet(media_button_stylesheet)
        self.set_svg_icon(self.shuffle_button, "./assets/svg/random.svg", 0.5)  # Initial icon (black)
        self.shuffle_button.clicked.connect(self.toggle_shuffle_tracks)

        # Progress slider
        self.progress_slider = QSlider(Qt.Horizontal, self)
        self.progress_slider.setGeometry(0, 350, 850, 15)
        self.progress_slider.setStyleSheet("""

            QSlider::groove:horizontal {
                background: rgba(0, 0, 0, 0);  /* Transparent black background */
                height: 12px;  /* Groove height */
                
            }
            QSlider::handle:horizontal {
                background: white;  /* White handle */
                width: 15px;
                height: 15px;
                border-radius: 0px;
            }
            QSlider::sub-page:horizontal {
                background: white;  /* White for the filled portion */
            }
            QSlider::add-page:horizontal {
                background: rgba(0, 0, 0, 0);  /* Transparent black for the unfilled portion */
                border-radius: 5px;
            }
        """)
        self.progress_slider.setMinimum(0)
        self.progress_slider.setMaximum(100)
        self.progress_slider.sliderReleased.connect(self.seek_to_position)

        # Timer for updating progress
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_progress_bar)
        self.timer.start(1000)



    def toggle_music(self):
        """
        Toggle music on Spotify and update the icon.
        """
        try:
            if self.music_paused:
                sp.start_playback()  # Resume playback on the current device
                print("Playback resumed.")
            else:
                sp.pause_playback()  # Pause playback
                print("Playback paused.")

            self.music_paused = not self.music_paused  # Toggle the state
            # Update the play_button_path based on the current state
            self.play_button_path = "./assets/svg/media-play.svg" if self.music_paused else "./assets/svg/media-pause.svg"
            # Update the button icon
            self.set_svg_icon(self.media_play_button, self.play_button_path, 0.5)
        
        except Exception as e:
            print(f"Error toggling playback: {e}")


    def next_track(self):
        """
        Play next track on Spotify.
        """
        try:
            sp.next_track()
            print("Next track is playing.")
            
            self.set_as_playing()
            self.reset_progress_bar()
        except Exception as e:
            print(f"Error skipping song: {e}")

    def previous_track(self):
        """
        Either go to previous track or to beginning of track depending how far along in the track you are
        """
        try:
            # Get the current playback state
            current_playback = sp.current_playback()
            if not current_playback:
                print("No active playback detected.")
                return

            # Check the progress of the current track in milliseconds
            progress_ms = current_playback.get("progress_ms", 0)

            # If the track is past 5 seconds, restart the current track
            if progress_ms > 5000:  # 5 seconds threshold
                sp.seek_track(0)  # Seek to the beginning of the track
                print("Restarted the current track.")
            else:
                # Otherwise, skip to the previous track
                sp.previous_track()
                print("Went to the previous track.")

            self.set_as_playing()
            self.reset_progress_bar()
    
        except Exception as e:
            print(f"Error going back: {e}")

    def toggle_shuffle_tracks(self):
        """
        Turn on or off shuffle on playlist
        """
        try:
            sp.shuffle(not self.music_shuffled)
            self.music_shuffled = not self.music_shuffled
            if self.music_shuffled:
                print("Tracks shuffled.")
            else:
                print("Tracks unshuffled.")

        except Exception as e:
            print(f"Shuffleing tracks: {e}")

        
    def set_svg_icon(self, button, svg_path, size=1):
        """
        Load an SVG, change its color, and set it as the button's icon.
        """

        color = "black" if self.dark_mode_enabled is True else "white"
        # Load the SVG content
        with open(svg_path, "r") as file:
            svg_content = file.read()

        # Replace the fill color in the SVG content
        updated_svg_content = svg_content.replace("black", color)
        renderer = QSvgRenderer(QByteArray(updated_svg_content.encode("utf-8")))

        # Create a pixmap to render the SVG
        pixmap = QPixmap(100, 100)
        pixmap.fill(Qt.transparent)  # Transparent background
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()

        # Set the pixmap as the button's icon
        button.setIcon(QIcon(pixmap))
        button.setIconSize(pixmap.size()*size)

    def get_current_track_info(self):
        """
        Fetch details of the currently playing track, including its image.
        """
        try:
            # Get current playback info
            current_playback = sp.current_playback()

            if not current_playback or not current_playback['item']:
                print("No track is currently playing.")
                return None

            # Extract track details
            track_name = current_playback['item']['name']
            artist_name = ", ".join([artist['name'] for artist in current_playback['item']['artists']])
            album_name = current_playback['item']['album']['name']
            album_image_url = current_playback['item']['album']['images'][0]['url']  # Largest image
            track_duration = int(current_playback['item']['duration_ms'])
            track_progress = int(current_playback['progress_ms'])
            return {
                "track_name": track_name,
                "artist_name": artist_name,
                "album_name": album_name,
                "album_image_url": album_image_url,
                "track_duration": track_duration,
                "track_progress": track_progress
            }

        except Exception as e:
            print(f"Error fetching current track info: {e}")
            return None

    def toggle_dark_mode(self):
        """
        Toggle dark mode for the application and update all SVG icons.
        """
        # Toggle the dark mode state
        self.dark_mode_enabled = not self.dark_mode_enabled

        # Update the window background color
        if self.dark_mode_enabled:
            self.setStyleSheet("background-color: rgba(0, 0, 0, 200);")  # Dark mode background
        else:
            self.setStyleSheet("background-color: rgba(255, 255, 255, 200);")  # Light mode background

        # Update the dark mode switch icon
        dark_mode_image_path = "./assets/svg/moon.svg" if self.dark_mode_enabled else "./assets/svg/sun.svg"
        self.set_svg_icon(self.dark_mode_switch, dark_mode_image_path, 0.5)

        # Update all other buttons with SVG icons
        self.set_svg_icon(self.close_button, "./assets/svg/x-letter.svg", 0.5)
        self.set_svg_icon(self.minimize_button, "./assets/svg/minus.svg", 0.5)
        self.set_svg_icon(self.media_play_button, self.play_button_path, 0.5)
        self.set_svg_icon(self.next_button, "./assets/svg/media-step-forward.svg", 0.5)
        self.set_svg_icon(self.previous_button, "./assets/svg/media-step-backward.svg", 0.5)
        self.set_svg_icon(self.shuffle_button, "./assets/svg/random.svg", 0.5)


        # Update Stylesheets
        stylesheet_background_plane_light = """
            background-color: rgba(255, 255, 255, 5);
            border: 1px solid rgba(255, 255, 255, 10);
            border-radius: 10px;
            """
        
        stylesheet_background_plane_dark = """
            background-color: rgba(0, 0, 0, 5);
            border: 1px solid rgba(0, 0, 0, 10);
            border-radius: 10px;
            """
        stylesheet_background_plane = stylesheet_background_plane_dark if self.dark_mode_enabled else stylesheet_background_plane_light
        self.background_plane.setStyleSheet(stylesheet_background_plane)

        stylesheet_track_info_light = """
            color: "white";
            background-color: rgba(0, 0, 0, 0);
            """
        stylesheet_track_info_dark = """
            color: "black";
            background-color: rgba(0, 0, 0, 0);
            """
        stylesheet_track_info = stylesheet_track_info_dark if self.dark_mode_enabled else stylesheet_track_info_light
        self.artist_label.setStyleSheet(stylesheet_track_info)
        self.track_label.setStyleSheet(stylesheet_track_info)

        print(f"Dark mode enabled: {self.dark_mode_enabled}")

    def update_track_info(self, current_track_info=None):
        print("Updating track info.")
        current_track_info = self.get_current_track_info()

        if current_track_info:
            self.artist_label.setText(current_track_info['artist_name'])
            self.track_label.setText(current_track_info['track_name'])
            self.update_album_art(current_track_info['album_image_url'])
        else:
            self.artist_label.setText("Not Working")
            self.track_label.setText("Not Working")


    def set_as_playing(self):
        """
        Set music as playing 
        """
        if self.music_paused:
                self.music_paused = False  
                # Update the play_button_path based on the current state
                self.play_button_path = "./assets/svg/media-pause.svg"
                # Update the button icon
                self.set_svg_icon(self.media_play_button, self.play_button_path, 0.5)

    def set_as_paused(self):
        """
        Set music as paused 
        """
        if not self.music_paused:
                self.music_paused = True  
                # Update the play_button_path based on the current state
                self.play_button_path = "./assets/svg/media-play.svg"
                # Update the button icon
                self.set_svg_icon(self.media_play_button, self.play_button_path, 0.5)

    def update_progress_bar(self):
        """
        Update the progress slider based on the current playback position.
        If the track ends naturally, update the track info and reset the slider.
        """
        try:
            current_playback = sp.current_playback()

            if current_playback:
                progress_ms = current_playback['progress_ms']
                duration_ms = current_playback['item']['duration_ms']

                # Set play button, neccessary if paused on device
                if current_playback['is_playing']:
                    #print("Playback playing.")
                    self.set_as_playing()
                    if self.artist_label.text() == "Artist": self.update_track_info()
                else:
                    #print("Playback paused.")
                    self.set_as_paused()

                if progress_ms < 2000: 
                    print(f"Updating track info, progress: {progress_ms}")
                    self.update_track_info()


                # Calculate progress percentage
                progress_percent = int((progress_ms / duration_ms) * 100)

                # Update the slider value
                self.progress_slider.setValue(progress_percent)

        except Exception as e:
            print(f"Error updating progress bar: {e}")

    def seek_to_position(self):
        """
        Seek to the position selected on the progress slider.
        """
        try:
            current_playback = sp.current_playback()

            if current_playback and current_playback['is_playing']:
                duration_ms = current_playback['item']['duration_ms']

                # Calculate the new position in milliseconds
                new_position = int((self.progress_slider.value() / 100) * duration_ms)

                # Seek to the new position
                sp.seek_track(new_position)
                print(f"Seeked to {new_position} ms.")

        except Exception as e:
            print(f"Error seeking to position: {e}")

    def reset_progress_bar(self):
        """
        Reset the progress bar when the track changes.
        """
        self.progress_slider.setValue(0)
        self.timer.start(1000)

    def update_album_art(self, album_image_url):
        """
        Update the album art displayed in the overlay.
        """
        try:
            response = requests.get(album_image_url)
            image_data = BytesIO(response.content)

            pixmap = QPixmap()
            pixmap.loadFromData(image_data.getvalue())
            self.album_art_pixmap = pixmap  # Save the pixmap for reuse
            self.album_art_label.setPixmap(pixmap)
            self.album_art_label.setScaledContents(True)
        except Exception as e:
            print(f"Error updating album art: {e}")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.offset = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self.offset is not None and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.offset)

    def mouseReleaseEvent(self, event):
        self.offset = None


if __name__ == "__main__":
    app = QApplication([])
    screen_width = app.primaryScreen().size().width()
    screen_height = app.primaryScreen().size().height()
    widget = SpotifyWidget(screen_width, screen_height)
    widget.show()
    app.exec()
