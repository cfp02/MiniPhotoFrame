# display_manager.py
import cv2
from screeninfo import get_monitors
from iptcinfo3 import IPTCInfo
import logging
import os
import platform
import numpy as np

# Suppress IPTCInfo warnings
iptcinfo_logger = logging.getLogger('iptcinfo')
iptcinfo_logger.setLevel(logging.ERROR)

# Force OpenCV to use X11 on Linux
if platform.system() == 'Linux':
    os.environ['QT_QPA_PLATFORM'] = 'xcb'

def get_caption(image_path):
    """Get caption and date from image IPTC info"""
    try:
        info = IPTCInfo(image_path)
        caption = info['caption/abstract']
        date = info['date created']
        
        if date:
            date = date.decode('utf-8')
            # Split date yyyymmdd into yyyy/mm/dd
            date = date[:4] + '/' + date[4:6] + '/' + date[6:]
        
        if caption is None:
            # Use filename as caption if no IPTC caption
            caption = os.path.basename(image_path)
            if len(caption) > 15 and caption.endswith('.jpg'):
                caption = caption[:-4]  # Remove .jpg extension
        else:
            caption = caption.decode('UTF-8')
            
        if date:
            caption = f"{caption} - {date}"
            
        return caption
    except Exception as e:
        print(f"Error reading caption: {e}")
        return os.path.basename(image_path)

def get_display_image(image_path):
    """Prepare image for display with caption"""
    target_width = 1800   # Fixed width for landscape
    target_height = 1200  # Fixed height
    
    # Read and process image
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error loading image: {image_path}")
        return None
        
    # Scale image to target dimensions
    img_height, img_width = img.shape[:2]
    img_aspect_ratio = img_width / img_height
    
    if img_height > img_width:  # Portrait
        new_height = target_height
        new_width = int(target_height * img_aspect_ratio)
    else:  # Landscape
        new_width = target_width
        new_height = target_height
        
    img = cv2.resize(img, (new_width, new_height))
    
    # Add caption
    caption = get_caption(image_path)
    
    # Caption settings
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.7
    thickness = 1
    text_color = (255, 255, 255)  # White
    outline_color = (0, 0, 0)      # Black
    outline_thickness = 3
    
    # Get text size and position
    text_size = cv2.getTextSize(caption, font, font_scale, thickness)[0]
    text_x = int((img.shape[1] - text_size[0]) / 2)  # Center text
    text_y = img.shape[0] - 25  # Bottom padding
    
    # Draw text outline (background)
    cv2.putText(img, caption, (text_x, text_y), font, font_scale, 
                outline_color, outline_thickness, cv2.LINE_AA)
    # Draw text (foreground)
    cv2.putText(img, caption, (text_x, text_y), font, font_scale,
                text_color, thickness, cv2.LINE_AA)
    
    return img

def show_photo(image_path, display_interval):
    """Display photo with proper scaling and return key press"""
    img = get_display_image(image_path)
    if img is None:
        return None
        
    # Get screen info
    screen = get_monitors()[0]
    screen_width = screen.width
    screen_height = screen.height
    
    # Calculate padding with proper scaling for screen height
    image_height = img.shape[0]  # Should be 1200
    image_width = img.shape[1]   # Should be 1800 for landscape
    image_ratio = screen_height / image_height  # Scale padding based on screen height
    lr_padding = int((screen_width - image_width * image_ratio)/2) # + 17
    
    # Add padding
    img = cv2.copyMakeBorder(
        src=img,
        top=0,
        bottom=0,
        left=lr_padding,
        right=lr_padding,
        borderType=cv2.BORDER_CONSTANT,
        value=[0, 0, 0]  # Black borders
    )
    
    # Display in fullscreen
    window_name = "Photo Frame"
    cv2.namedWindow(window_name, cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    cv2.imshow(window_name, img)
    
    # Wait for key press or interval
    key = cv2.waitKey(display_interval * 1000)
    cv2.destroyAllWindows()
    
    if key == -1:  # No key pressed
        return "next"
    elif key == 27:  # ESC
        return "exit"
    elif key == ord('r'):  # Reshuffle
        return "reshuffle"
    elif key == ord('n'):  # New images
        return "new"
    elif key == ord('b'):  # Back
        return "back"
    else:
        return "next"

def show_photo_simple(image_path, display_interval):
    """Display photo centered on screen with full black borders, no captions"""
    # Read image
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error loading image: {image_path}")
        return None
        
    # Get screen dimensions
    screen = get_monitors()[0]
    screen_width = screen.width
    screen_height = screen.height
    
    # Calculate scaling to fit within screen while maintaining aspect ratio
    img_height, img_width = img.shape[:2]
    width_ratio = screen_width / img_width
    height_ratio = screen_height / img_height
    scale_factor = min(width_ratio, height_ratio)
    
    # Scale image
    new_width = int(img_width * scale_factor)
    new_height = int(img_height * scale_factor)
    img = cv2.resize(img, (new_width, new_height))
    
    # Create black canvas of screen size
    canvas = np.zeros((screen_height, screen_width, 3), dtype=img.dtype)
    
    # Calculate position to center image
    y_offset = (screen_height - new_height) // 2
    x_offset = (screen_width - new_width) // 2
    
    # Place image on canvas
    canvas[y_offset:y_offset+new_height, x_offset:x_offset+new_width] = img
    
    # Display fullscreen
    window_name = "Photo Frame"
    cv2.namedWindow(window_name, cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    cv2.imshow(window_name, canvas)
    
    # Wait for key press or interval
    key = cv2.waitKey(display_interval * 1000)
    cv2.destroyAllWindows()
    
    if key == -1:  # No key pressed
        return "next"
    elif key == 27:  # ESC
        return "exit"
    elif key == ord('r'):  # Reshuffle
        return "reshuffle"
    elif key == ord('n'):  # New images
        return "new"
    elif key == ord('b'):  # Back
        return "back"
    else:
        return "next"
