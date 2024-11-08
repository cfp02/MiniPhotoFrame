# display_manager.py
from PIL import Image

def show_photo(file_name):
    image = Image.open(file_name)
    image.show()  # Opens the default image viewer on the Pi
