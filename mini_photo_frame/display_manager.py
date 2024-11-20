# display_manager.py
import os
from PIL import Image
from screeninfo import get_monitors
import cv2
import platform


def show_photo(file_name, delay_seconds):
    '''
    Takes a file name and displays the image fullscreen on the device.
    '''

    # Get the dimensions of the file, identify which is the larger dimension, and resize the image to have the long edge stretch the full length of that screen dimension.

    img = cv2.imread(file_name)
    img_height, img_width, _ = img.shape

    scaling_factor = 2 if platform.system() == 'Darwin' else 1


    # Get the screen dimensions
    screen_width, screen_height = get_monitors()[0].width, get_monitors()[0].height
    screen_width = screen_width * scaling_factor
    screen_height = screen_height * scaling_factor
    img_aspect_ratio = img_width / img_height
    screen_aspect_ratio = screen_width / screen_height

    if img_aspect_ratio > screen_aspect_ratio:
        # Image is wider relative to the screen
        new_width = screen_width
        new_height = int(screen_width / img_aspect_ratio)
    else:
        # Image is taller relative to the screen
        new_width = int(screen_height * img_aspect_ratio)
        new_height = screen_height

    img_resized = cv2.resize(img, (new_width, new_height))

     # Calculate the borders to center the image
    top_border = (screen_height - new_height) // 2
    bottom_border = screen_height - new_height - top_border
    left_border = (screen_width - new_width) // 2
    right_border = screen_width - new_width - left_border

    # print('Screen size:', screen_width, screen_height)

    # Create a canvas with black borders
    canvas = cv2.copyMakeBorder(img_resized, 
                                top=top_border, 
                                bottom=bottom_border, 
                                left=left_border, 
                                right=right_border, 
                                borderType=cv2.BORDER_CONSTANT, 
                                value=[0, 0, 0])
    
    # Ensure the canvas size matches the screen resolution
    assert canvas.shape[0] == screen_height, f"Height mismatch: canvas={canvas.shape[0]}, screen={screen_height}"
    assert canvas.shape[1] == screen_width, f"Width mismatch: canvas={canvas.shape[1]}, screen={screen_width}"

    cv2.namedWindow("test", cv2.WND_PROP_FULLSCREEN)          
    cv2.setWindowProperty("test", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    cv2.imshow("test", canvas)
    # Waits until a key is pressed, and stores that key value for us to use
    key=cv2.waitKey(delay_seconds*1000)

    cv2.destroyAllWindows()
    return key
