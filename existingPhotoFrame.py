from iptcinfo3 import IPTCInfo
import os
import time
import cv2
from screeninfo import get_monitors
import random
import sys
#import cvzone

# Suppress IPTCInfo warnings
import logging
iptcinfo_logger = logging.getLogger('iptcinfo')
iptcinfo_logger.setLevel(logging.ERROR)

use_date = True
# folder_file_path = 'PhotoFramePhotos(WithCaptions)'
folder_file_path = 'C:\\Users\\black\\Documents\\PhotoFramePhotos(WithCaptions)'
bar_gradient_file_path = 'BarGradient.png'
image_list_file = 'image_list.txt'

def get_caption(image_name):
    image_path = get_image_path(image_name)
    info = IPTCInfo(image_path)
    caption = info['caption/abstract']
    date = info['date created']
    date = date.decode('utf-8')
    #split date yyyymmdd into yyyy/mm/dd
    date = date[:4] + '/' + date[4:6] + '/' + date[6:]
    if caption == None:
        #use filename as caption if no caption
        # caption = ''
        # make sure filename is long enough to remove the .jpg as well as the number and date (formate example: _01_01-04-2023.jpg)
        if len(image_name) > 15:
            caption = image_name[:-18]

    else:
        caption = caption.decode('UTF-8')
        # print (caption)
    if use_date:
        caption = str(caption) + " - " + str(date)
        
    # print(caption)
    if caption == '':
        print('No Caption')
    # print(len(caption))
    return(caption)

def look_for_no_caption():
    for file in os.listdir(folder_file_path):
        if not file.endswith(".jpg"):
            continue
        #sends image path to get_caption function
        thiscaption = IPTCInfo(get_image_path(file))['caption/abstract']
        if get_caption(file) == '' or thiscaption == None:
            print(file)

def get_combined_image_cv2(image_name):
    image_path = get_image_path(image_name)
    image_height = 1200
    image_width = 1800
    img = cv2.imread(image_path)
    # if image is portrait, scale it to fit the screen height. The height will be set to 1200, and the width will be scaled to keep the aspect ratio
    if img.shape[0] > img.shape[1]:
        scale = image_height / img.shape[0]
        img = cv2.resize(img, (int(img.shape[1]*scale), image_height))
    caption = get_caption(image_name)
    # print(caption)
    myFont = 0
    bottomLeftCornerOfText = (int(img.shape[1]/2.8), int(image_height-25))

    # Black font (overlay)
    fontScale = 0.7
    fontColor = (255,255,255)
    thickness = 1
    lineType = cv2.LINE_AA
    # White font (background)
    fontScaleWhite = 0.7
    fontColorWhite = (0,0,0)
    thicknessWhite = 3
    # lineType = cv2.LINE_AA

    # add transparent bar at the bottom of the image
    # bar_img = cv2.imread("BarGradient.png", cv2.IMREAD_UNCHANGED)
    # alpha = .2
    # img = cvzone.overlayPNG(img, bar_img)
    cv2.putText(img, caption, bottomLeftCornerOfText, myFont, fontScaleWhite, fontColorWhite, thicknessWhite, lineType)
    cv2.putText(img, caption, bottomLeftCornerOfText, myFont, fontScale, fontColor, thickness, lineType)

    return img


def display_combined_image_cv2(image_name, delay_seconds):
    # window_name = 'test'
    screen_width = get_monitors()[0].width
    screen_height = get_monitors()[0].height
    img = get_combined_image_cv2(image_name)
    image_height = img.shape[0]  #1200
    image_width = img.shape[1] #1800
    image_ratio = screen_height / image_height # 3:4
    lr_padding = int((screen_width - image_width * image_ratio)/2) + 17
    
    img = cv2.copyMakeBorder(src = img, top = 0, bottom = 0, left = lr_padding, right = lr_padding, borderType = cv2.BORDER_CONSTANT)
    cv2.namedWindow("test", cv2.WND_PROP_FULLSCREEN)          
    cv2.setWindowProperty("test", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    cv2.imshow("test",img)
    # Waits until a key is pressed, and stores that key value for us to use
    key=cv2.waitKey(delay_seconds*1000)
    
    retval = "Next"

    #if escape key is pressed, exit
    if key == 27:
        retval = "Exit"

    #if r key is pressed, reshuffle the list
    if key == ord('r'):
        retval = "Reshuffle"
    
    #if n key is pressed, reshuffle and add new images to the start of the list
    if key == ord('n'):
        retval = "New Images"

    #if the b key is pressed, go back one image by returning the previous image index
    if key == ord('b'):
        retval = "Back"
    
    cv2.destroyAllWindows()
    return retval

# Get image_path from image name
def get_image_path(image):
    image_path = folder_file_path + "/" + image
    return image_path

# Checks image list against the list of images in the folder, returns list of new images
def check_for_new_images(image_list, image_list_file):
    current_images = image_list
    old_images = []
    image_list = []
    with open(image_list_file, 'r') as f:
        old_images = [line[:-1] for line in f]
        print(str(len(old_images)) + " old images")
    for image in current_images:
        if str(image) not in old_images:
            # print(image)
            image_list.append(str(image))
    print(str(len(image_list)) + " new images: ")
    print(image_list)
    return image_list

def return_all_photos_in_folder(folder_path):
    image_names = []
    for file in os.listdir(folder_path):
        if not file.endswith(".jpg"):
            continue
        image_names.append(file)
    return image_names

# Write full image list to file
def write_image_list_to_file(image_list, file_name):
    with open(file_name, 'w') as f:
        for item in image_list:
            f.write(item + "\n")

# Get when image was last edited
def get_edited_date(image):
    # get edited date of image
    image_path = get_image_path(image)
    edited_date = os.path.getmtime(image_path)
    # print(edited_date)
    return edited_date

# look at each image's edited date, and sort the list of images by edited date
def sort_images_by_edited_date(image_list):
    # get list of tuples with image name and edited date
    image_list_with_edited_date = []
    for image in image_list:
        image_list_with_edited_date.append((image, get_edited_date(image)))
    # sort list by edited date in reverse order (most recent first)
    image_list_with_edited_date.sort(key=lambda x: x[1], reverse=True)
    return [x[0] for x in image_list_with_edited_date]

def reconstruct_image_list_with_recent_pics(image_list, num_recent_pics):
    sorted_image_list = sort_images_by_edited_date(image_list)
    # Image list is first 10 images sorted by edited date, plus the already shuffled list
    image_list = sorted_image_list[:num_recent_pics] + image_list
    return image_list

# Get list of images that contain the search term
def get_images_with_search_term(image_list, search_term):
    image_list_with_search_term = []
    for image in image_list:
        # if search term is in image name, not case sensitive, add to list
        if search_term.lower() in image.lower():
            image_list_with_search_term.append(image)
    return image_list_with_search_term

def reconstruct_image_list_with_list_of_images(image_list, image_list_to_add):
    image_list = image_list_to_add + image_list
    return image_list

# Run the photo viewer
def run_photo_viewer_cv2(delay_seconds, search_term):
    # get list of all images in folder, and shuffle them
    image_list = return_all_photos_in_folder(folder_file_path)
    # print(image_list)
    random.shuffle(image_list)

    # write all image names to a text file (only run to reset the list)
    ## write_image_list_to_file(image_list, "image_list.txt")

    # get list of new images from most recent git pull
    #new_image_list = check_for_new_images(image_list, "image_list.txt")
    #print(new_image_list)

    # add new images to the start of the image list
    #image_list = new_image_list + image_list
    write_image_list_to_file(return_all_photos_in_folder(folder_file_path), "image_list.txt")

    # sorted_image_list = sort_images_by_edited_date(image_list)

    # if search term is not empty, get list of images that contain the search term
    # if search term is none, use the full image list with recent images at the start
    if search_term != None:
        searched_images = get_images_with_search_term(image_list, search_term)
        image_list = reconstruct_image_list_with_list_of_images(image_list, searched_images)
    else:
        # Image list is first 10 images sorted by edited date, plus the already shuffled list
        image_list = reconstruct_image_list_with_recent_pics(image_list, 10)

    i = 0
    while i < len(image_list):
        #print index and caption
        image = image_list[i]
        print(i, get_caption(image))
        #display the image
        retval = display_combined_image_cv2(image, delay_seconds)
        
        # print (retval)
        # print(i)
        if retval == "Reshuffle":
            #reshuffle the list
            random.shuffle(image_list)
            i = 0
        elif retval == "New Images":
            #reshuffle the list, put new images at the start
            reconstruct_image_list_with_recent_pics(image_list, 10)
            i = 0
       
        elif retval == "Back":
            #go back one image
            i = i - 1
        elif retval == "Exit":
            #exit the program
            exit()
        else:
            #go to next image
            i = i + 1
        
        #if we've reached the end of the list, go back to the start
        if i == len(image_list):
            #reshuffle the list and go back to start
            random.shuffle(image_list)
            i = 0


def main():
    # Remove the first argument, which is the name of the script
    args = sys.argv[1:]
    print("Arguments:", args)
    argument = None
    if len(args) == 0:
        print("No arguments passed, starting as normal")
    elif len(args) > 1:
        print("Too many arguments passed, starting as normal")
    elif len(args) == 1:
        # Argument is search term, pass that to the photo viewer
        argument = args[0].lower()
        print("Argument passed, starting with search term: " + args[0])
    
    # print names of images with no caption
    look_for_no_caption()
    #run the photo viewer!
    run_photo_viewer_cv2(45*60, argument)

if __name__ == "__main__":
    main()
    # print(get_images_with_search_term(return_all_photos_in_folder(folder_file_path), "avocet"))