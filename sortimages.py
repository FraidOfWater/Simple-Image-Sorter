import os
from sys import exit
from tkinter import messagebox
from shutil import move as shmove
import tkinter as tk
import tkinter.scrolledtext as tkst
from PIL import Image,ImageTk
from functools import partial
from math import floor
import json
import random
from math import floor,sqrt
from tkinter import filedialog as tkFileDialog
import tkinter.font as tkfont
from collections import deque

#I am aware this code is fingerpaint-tier

# -*- coding: utf-8 -*-
# Advanced zoom for images of various types from small to huge up to several GB

button_colour = 'black'
background_colour = 'black'
text_colour = 'white'

canvas_colour = 'black'
active_background_colour = 'white'
active_foreground_colour = 'black'

import math
import warnings
from tkinter import ttk
from PIL import Image, ImageTk
script_dir = os.path.dirname(os.path.abspath(__file__))
prefs_path = os.path.join(script_dir, "prefs.json")
selected_option = "Corner"
rescalemode_temp = True
class AutoScrollbar(ttk.Scrollbar):
    """ A scrollbar that hides itself if it's not needed. Works only for grid geometry manager """
    def set(self, lo, hi):
        if float(lo) <= 0.0 and float(hi) >= 1.0:
            self.grid_remove()
        else:
            self.grid()
            ttk.Scrollbar.set(self, lo, hi)

    def pack(self, **kw):
        raise tk.TclError('Cannot use pack with the widget ' + self.__class__.__name__)

    def place(self, **kw):
        raise tk.TclError('Cannot use place with the widget ' + self.__class__.__name__)

class CanvasImage:
    """ Display and zoom image """
    def __init__(self, placeholder, path):
        """ Initialize the ImageFrame """
        self.imscale = 1.0  # scale for the canvas image zoom, public for outer classes
        self.__delta = 1.3  # zoom magnitude
        self.__filter = Image.LANCZOS  # could be: NEAREST, BILINEAR, BICUBIC and ANTIALIAS
        self.__previous_state = 0  # previous state of the keyboard
        self.path = path  # path to the image, should be public for outer classes
        # Create ImageFrame in placeholder widget
        self.__imframe = ttk.Frame(placeholder)  # placeholder of the ImageFrame object
        # Vertical and horizontal scrollbars for canvas
        hbar = AutoScrollbar(self.__imframe, orient='horizontal')
        vbar = AutoScrollbar(self.__imframe, orient='vertical')
        hbar.grid(row=1, column=0, sticky='we')
        vbar.grid(row=0, column=1, sticky='ns')
        # Create canvas and bind it with scrollbars. Public for outer classes
        self.canvas = tk.Canvas(self.__imframe, bg=background_colour, highlightthickness=0, #canvas that the image is in
                                xscrollcommand=hbar.set, yscrollcommand=vbar.set)
        self.canvas.grid(row=0, column=0, sticky='nswe')
        self.canvas.update()  # wait till canvas is created
        self.canvas.configure(width=tkroot.winfo_width()-guiframe.winfo_width(), height=tkroot.winfo_height()) #Limits the image inside the canvas and disables the scrollbar flicker
        hbar.configure(command=self.__scroll_x)  # bind scrollbars to the canvas
        vbar.configure(command=self.__scroll_y)
        # Bind events to the Canvas
        self.canvas.bind('<Configure>', lambda event: self.__show_image())  # canvas is resized
        self.canvas.bind('<ButtonPress-1>', self.__move_from)  # remember canvas position
        self.canvas.bind('<B1-Motion>',     self.__move_to)  # move canvas to the new position
        self.canvas.bind('<MouseWheel>', self.__wheel)  # zoom for Windows and MacOS, but not Linux
        self.canvas.bind('<Button-5>',   self.__wheel)  # zoom for Linux, wheel scroll down
        self.canvas.bind('<Button-4>',   self.__wheel)  # zoom for Linux, wheel scroll up
        # Handle keystrokes in idle mode, because program slows down on a weak computers,
        # when too many key stroke events in the same time
        self.canvas.bind('<Key>', lambda event: self.canvas.after_idle(self.__keystroke, event))
        # Decide if this image huge or not
        self.__huge = False  # huge or not
        self.__huge_size = 14000  # define size of the huge image
        self.__band_width = 1024  # width of the tile band
        Image.MAX_IMAGE_PIXELS = 1000000000  # suppress DecompressionBombError for the big image
        with warnings.catch_warnings():  # suppress DecompressionBombWarning
            warnings.simplefilter('ignore')
            self.__image = Image.open(self.path)  # open image, but down't load it
        self.imwidth, self.imheight = self.__image.size  # public for outer classes
        if self.imwidth * self.imheight > self.__huge_size * self.__huge_size and \
           self.__image.tile[0][0] == 'raw':  # only raw images could be tiled
            self.__huge = True  # image is huge
            self.__offset = self.__image.tile[0][2]  # initial tile offset
            self.__tile = [self.__image.tile[0][0],  # it have to be 'raw'
                           [0, 0, self.imwidth, 0],  # tile extent (a rectangle)
                           self.__offset,
                           self.__image.tile[0][3]]  # list of arguments to the decoder
        self.__min_side = min(self.imwidth, self.imheight)  # get the smaller image side
        # Create image pyramid
        self.__pyramid = [self.smaller()] if self.__huge else [Image.open(self.path)]
        # Set ratio coefficient for image pyramid
        self.__ratio = max(self.imwidth, self.imheight) / self.__huge_size if self.__huge else 1.0
        self.__curr_img = 0  # current image from the pyramid
        self.__scale = self.imscale * self.__ratio  # image pyramide scale
        self.__reduction = 2  # reduction degree of image pyramid
        w, h = self.__pyramid[-1].size
        while w > 512 and h > 512:  # top pyramid image is around 512 pixels in size
            w /= self.__reduction  # divide on reduction degree
            h /= self.__reduction  # divide on reduction degree
            self.__pyramid.append(self.__pyramid[-1].resize((int(w), int(h)), self.__filter))
        # Put image into container rectangle and use it to set proper coordinates to the image
        self.container = self.canvas.create_rectangle((0, 0, self.imwidth, self.imheight), width=0)
        self.__show_image()  # show image on the canvas
        self.__image.close()
        self.canvas.focus_set()  # set focus on the canvas
        self.canvas.update_idletasks() # Fixes the brief appearance of the scrollbars before hiding them.
        self.__imframe.rowconfigure(0, weight=1)  # make canvas expandable ####weight to 0 for no schock
        self.__imframe.columnconfigure(0, weight=1)

    def smaller(self):
        """ Resize image proportionally and return smaller image """
        w1, h1 = float(self.imwidth), float(self.imheight)
        w2, h2 = float(self.__huge_size), float(self.__huge_size)
        aspect_ratio1 = w1 / h1
        aspect_ratio2 = w2 / h2  # it equals to 1.0
        if aspect_ratio1 == aspect_ratio2:
            image = Image.new('RGB', (int(w2), int(h2)))
            k = h2 / h1  # compression ratio
            w = int(w2)  # band length
        elif aspect_ratio1 > aspect_ratio2:
            image = Image.new('RGB', (int(w2), int(w2 / aspect_ratio1)))
            k = h2 / w1  # compression ratio
            w = int(w2)  # band length
        else:  # aspect_ratio1 < aspect_ration2
            image = Image.new('RGB', (int(h2 * aspect_ratio1), int(h2)))
            k = h2 / h1  # compression ratio
            w = int(h2 * aspect_ratio1)  # band length
        i, j, n = 0, 1, round(0.5 + self.imheight / self.__band_width)
        while i < self.imheight:
            print('\rOpening image: {j} from {n}'.format(j=j, n=n), end='')
            band = min(self.__band_width, self.imheight - i)  # width of the tile band
            self.__tile[1][3] = band  # set band width
            self.__tile[2] = self.__offset + self.imwidth * i * 3  # tile offset (3 bytes per pixel)
            self.__image.close()
            self.__image = Image.open(self.path)  # reopen / reset image
            self.__image.size = (self.imwidth, band)  # set size of the tile band
            self.__image.tile = [self.__tile]  # set tile
            cropped = self.__image.crop((0, 0, self.imwidth, band))  # crop tile band
            image.paste(cropped.resize((w, int(band * k)+1), self.__filter), (0, int(i * k)))
            i += band
            j += 1
        print('\r' + 30*' ' + '\r', end='')  # hide printed string
        return image

    def redraw_figures(self):
        """ Dummy function to redraw figures in the children classes """
        pass

    def grid(self, **kw):
        """ Put CanvasImage widget on the parent widget """
        self.__imframe.grid(**kw)  # place CanvasImage widget on the grid
        self.__imframe.grid(sticky='nswe')  # make frame container sticky

    def pack(self, **kw):
        """ Exception: cannot use pack with this widget """
        raise Exception('Cannot use pack with the widget ' + self.__class__.__name__)

    def place(self, **kw):
        """ Exception: cannot use place with this widget """
        raise Exception('Cannot use place with the widget ' + self.__class__.__name__)

    # noinspection PyUnusedLocal
    def __scroll_x(self, *args, **kwargs):
        """ Scroll canvas horizontally and redraw the image """
        self.canvas.xview(*args)  # scroll horizontally
        self.__show_image()  # redraw the image

    # noinspection PyUnusedLocal
    def __scroll_y(self, *args, **kwargs):
        """ Scroll canvas vertically and redraw the image """
        self.canvas.yview(*args)  # scroll vertically
        self.__show_image()  # redraw the image

    def __show_image(self):
        """ Show image on the Canvas. Implements correct image zoom almost like in Google Maps """
        box_image = self.canvas.coords(self.container)  # get image area
        box_canvas = (self.canvas.canvasx(0),  # get visible area of the canvas
                      self.canvas.canvasy(0),
                      self.canvas.canvasx(self.canvas.winfo_width()),
                      self.canvas.canvasy(self.canvas.winfo_height()))
        box_img_int = tuple(map(int, box_image))  # convert to integer or it will not work properly
        # Get scroll region box
        box_scroll = [min(box_img_int[0], box_canvas[0]), min(box_img_int[1], box_canvas[1]),
                      max(box_img_int[2], box_canvas[2]), max(box_img_int[3], box_canvas[3])]
        # Horizontal part of the image is in the visible area
        if  box_scroll[0] == box_canvas[0] and box_scroll[2] == box_canvas[2]:
            box_scroll[0]  = box_img_int[0]
            box_scroll[2]  = box_img_int[2]
        # Vertical part of the image is in the visible area
        if  box_scroll[1] == box_canvas[1] and box_scroll[3] == box_canvas[3]:
            box_scroll[1]  = box_img_int[1]
            box_scroll[3]  = box_img_int[3]
        # Convert scroll region to tuple and to integer
        self.canvas.configure(scrollregion=tuple(map(int, box_scroll)))  # set scroll region
        x1 = max(box_canvas[0] - box_image[0], 0)  # get coordinates (x1,y1,x2,y2) of the image tile
        y1 = max(box_canvas[1] - box_image[1], 0)
        x2 = min(box_canvas[2], box_image[2]) - box_image[0]
        y2 = min(box_canvas[3], box_image[3]) - box_image[1]
        if int(x2 - x1) > 0 and int(y2 - y1) > 0:  # show image if it in the visible area
            if self.__huge and self.__curr_img < 0:  # show huge image
                h = int((y2 - y1) / self.imscale)  # height of the tile band
                self.__tile[1][3] = h  # set the tile band height
                self.__tile[2] = self.__offset + self.imwidth * int(y1 / self.imscale) * 3
                self.__image.close()
                self.__image = Image.open(self.path)  # reopen / reset image
                self.__image.size = (self.imwidth, h)  # set size of the tile band
                self.__image.tile = [self.__tile]
                image = self.__image.crop((int(x1 / self.imscale), 0, int(x2 / self.imscale), h))
            else:  # show normal image
                image = self.__pyramid[max(0, self.__curr_img)].crop(  # crop current img from pyramid
                                    (int(x1 / self.__scale), int(y1 / self.__scale),
                                     int(x2 / self.__scale), int(y2 / self.__scale)))
            #
            imagetk = ImageTk.PhotoImage(image.resize((int(x2 - x1), int(y2 - y1)), self.__filter))
            imageid = self.canvas.create_image(max(box_canvas[0], box_img_int[0]),
                                               max(box_canvas[1], box_img_int[1]),
                                               anchor='nw', image=imagetk)
            self.canvas.lower(imageid)  # set image into background
            self.canvas.imagetk = imagetk  # keep an extra reference to prevent garbage-collection

    def __move_from(self, event):
        """ Remember previous coordinates for scrolling with the mouse """
        self.canvas.scan_mark(event.x, event.y)

    def __move_to(self, event):
        """ Drag (move) canvas to the new position """
        self.canvas.scan_dragto(event.x, event.y, gain=1)
        self.__show_image()  # zoom tile and show it on the canvas

    def outside(self, x, y):
        """ Checks if the point (x,y) is outside the image area """
        bbox = self.canvas.coords(self.container)  # get image area
        if bbox[0] < x < bbox[2] and bbox[1] < y < bbox[3]:
            return False  # point (x,y) is inside the image area
        else:
            return True  # point (x,y) is outside the image area

    def __wheel(self, event):
        """ Zoom with mouse wheel """
        x = self.canvas.canvasx(event.x)  # get coordinates of the event on the canvas
        y = self.canvas.canvasy(event.y)
        #if self.outside(x, y): return  # zoom only inside image area
        scale = 1.0
        # Respond to Linux (event.num) or Windows (event.delta) wheel event
        if event.num == 5 or event.delta == -120:  # scroll down, smaller
            if round(self.__min_side * self.imscale) < 30: return  # image is less than 30 pixels
            self.imscale /= self.__delta
            scale        /= self.__delta
        if event.num == 4 or event.delta == 120:  # scroll up, bigger
            i = min(self.canvas.winfo_width(), self.canvas.winfo_height()) >> 1
            if i < self.imscale: return  # 1 pixel is bigger than the visible area
            self.imscale *= self.__delta
            scale        *= self.__delta
        # Take appropriate image from the pyramid
        k = self.imscale * self.__ratio  # temporary coefficient
        self.__curr_img = min((-1) * int(math.log(k, self.__reduction)), len(self.__pyramid) - 1)
        self.__scale = k * math.pow(self.__reduction, max(0, self.__curr_img))
        #
        self.canvas.scale('all', x, y, scale, scale)  # rescale all objects
        # Redraw some figures before showing image on the screen
        self.redraw_figures()  # method for child classes
        self.__show_image()

    def __keystroke(self, event):
        """ Scrolling with the keyboard.
            Independent from the language of the keyboard, CapsLock, <Ctrl>+<key>, etc. """
        if event.state - self.__previous_state == 4:  # means that the Control key is pressed
            pass  # do nothing if Control key is pressed
        else:
            self.__previous_state = event.state  # remember the last keystroke state
            # Up, Down, Left, Right keystrokes
            if event.keycode in [68, 39, 102]:  # scroll right, keys 'd' or 'Right'
                self.__scroll_x('scroll',  1, 'unit', event=event)
            elif event.keycode in [65, 37, 100]:  # scroll left, keys 'a' or 'Left'
                self.__scroll_x('scroll', -1, 'unit', event=event)
            elif event.keycode in [87, 38, 104]:  # scroll up, keys 'w' or 'Up'
                self.__scroll_y('scroll', -1, 'unit', event=event)
            elif event.keycode in [83, 40, 98]:  # scroll down, keys 's' or 'Down'
                self.__scroll_y('scroll',  1, 'unit', event=event)

    def crop(self, bbox):
        """ Crop rectangle from the image and return it """
        if self.__huge:  # image is huge and not totally in RAM
            band = bbox[3] - bbox[1]  # width of the tile band
            self.__tile[1][3] = band  # set the tile height
            self.__tile[2] = self.__offset + self.imwidth * bbox[1] * 3  # set offset of the band
            self.__image.close()
            self.__image = Image.open(self.path)  # reopen / reset image
            self.__image.size = (self.imwidth, band)  # set size of the tile band
            self.__image.tile = [self.__tile]
            return self.__image.crop((bbox[0], 0, bbox[2], band))
        else:  # image is totally in RAM
            return self.__pyramid[0].crop(bbox)

    def destroy(self):
        """ ImageFrame destructor """
        self.__image.close()
        map(lambda i: i.close, self.__pyramid)  # close all pyramid images
        del self.__pyramid[:]  # delete pyramid list
        del self.__pyramid  # delete pyramid variable
        self.canvas.destroy()
        self.__imframe.destroy()

    def rescale(self, scale):
        """ Rescale the Image without doing anything else """
        self.__scale=scale
        self.imscale=scale

        self.canvas.scale('all', self.canvas.winfo_width(), 0, scale, scale)  # rescale all objects
        self.redraw_figures()
        self.__show_image()

    def center_image(self):
        global selected_option
        """ Center the image on the canvas """
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        # Calculate scaled image dimensions
        scaled_image_width = self.imwidth * self.imscale
        scaled_image_height = self.imheight * self.imscale

        # Calculate offsets to center the image
        #["Corner", "y-Center", "xy-Center", ""]
        if selected_option == "y-Center":  # Corner but center y
            print("y")
            x_offset = 0
            y_offset = (canvas_height - scaled_image_height) // 2
        elif selected_option == "xy-Center":  # True center
            print("xy")
            x_offset = (canvas_width - scaled_image_width) // 2
            y_offset = (canvas_height - scaled_image_height) // 2
        elif selected_option == "x-Center":  # Top center x wise
            print("x")
            x_offset = (canvas_width - scaled_image_width) // 2
            y_offset = 0
        else:  # Corner
            x_offset = 0
            y_offset = 0


        # Update the position of the image container
        self.canvas.coords(self.container, x_offset, y_offset, x_offset + scaled_image_width, y_offset + scaled_image_height)

        #print(f"Centered")

        self.__show_image()


tkroot = tk.Tk()
tkroot.config(bg=background_colour)
toppane = tk.Frame(tkroot)
toppane.config(bg=background_colour)
style = ttk.Style()
style.theme_use('classic')
destinations = []

# Load prefs to get geometry
try:
    with open(prefs_path,"r") as prefsfile:
        jdata=prefsfile.read()
        jprefs=json.loads(jdata)
        if "geometry" in jprefs:
            geometry = jprefs["geometry"]
        tkroot.geometry(geometry) # Just loads from prefs.
        if "rescalemode" in jprefs:
            rescalemode_temp = jprefs["rescalemode"]
        if "selected_option" in jprefs:
            selected_option = jprefs["selected_option"]


except Exception as e:
    print(f"Failed to load prefs.json: {e}")
    tkroot.geometry(str(tkroot.winfo_screenwidth())+"x"+str(tkroot.winfo_screenheight()-120))
    tkroot.geometry("+0+60")
    pass



buttons = []
imagelist= deque()
imgiterator = 0
guirow=1
guicol=0
sdp=""
ddp=""
exclude=[]
columns = 1

#more guisetup
#######
#textout=tkst.ScrolledText(text_frame)
#textout.config(state=tk.DISABLED)

#def tklog(instring):
#replaced print but I can't get the positoning correct
    #global #textout
    #textout.config(state=tk.NORMAL)
    #textout.insert(tk.INSERT,"\n"+instring)
    #textout.config(state=tk.DISABLED)


def randomColor():
    color = '#'
    hexletters = '0123456789ABCDEF';
    for i in range(0,6):
        color += hexletters[floor(random.random()*16)]
    return color

def luminance(hexin):
    color = tuple(int(hexin.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    r = color[0]
    g = color[1]
    b = color[2]
    hsp = sqrt(
        0.299 * (r**2) +
        0.587 * (g**2) +
        0.114 * (b**2)
        )
    if hsp >115.6:
        return 'light'
    else:
        return 'dark'



def validate():
    global sdp
    global ddp
    samepath =  (sdpEntry.get() == ddpEntry.get())
    if((os.path.isdir(sdpEntry.get())) and (os.path.isdir(ddpEntry.get())) and not samepath):
        sdp=sdpEntry.get()
        ddp=ddpEntry.get()
        setup(sdp,ddp)
        guisetup()
        displayimage()
        saveonexit()
    elif sdpEntry.get() == ddpEntry.get():
        sdpEntry.delete(0,len(sdpEntry.get()))
        ddpEntry.delete(0,len(ddpEntry.get()))
        sdpEntry.insert(0,"PATHS CANNOT BE SAME")
        ddpEntry.insert(0,"PATHS CANNOT BE SAME")
    else:
        sdpEntry.delete(0,len(sdpEntry.get()))
        ddpEntry.delete(0,len(ddpEntry.get()))
        sdpEntry.insert(0,"ERROR INVALID PATH")
        ddpEntry.insert(0,"ERROR INVALID PATH")


def setup(src,dest):
    global imagelist
    global destinations
    global imgiterator
    global exclude
    destinations = []
    imgiterator = 0
    #scan the destination
    if src[len(src)-1]=="\\":#trim trailing slashes
        src=src[:-1]
    if dest[len(dest)-1]=="\\":
        dest=dest[:-1]
    with os.scandir(dest) as it:
        for entry in it:
            if entry.is_dir():
                destinations.append({'name': entry.name,'path': entry.path})
        destinations.append({'name': "SKIP"})
        destinations.append({'name': "BACK"})
    #walk the source files
    for root,dirs,files in os.walk(src,topdown=True):
        dirs[:] = [d for d in dirs if d not in exclude]
        for name in files:
            ext = os.path.splitext(name)[1].lstrip(".")
            if ext == "png" or ext == "gif" or ext == "jpg" or ext == "jpeg" or ext == "bmp" or ext == "pcx" or ext == "tiff" or ext=="webp" or ext=="psd" or ext=="jfif":
                imagelist.append({"name":name, "path":os.path.join(root,name), "dest":""})

def disable_event():
    pass

tkroot.columnconfigure(0, weight=1)
tkroot.rowconfigure(0,weight=1)
toppane.columnconfigure(1,weight=3)
toppane.rowconfigure(0,weight=1)
toppane.grid(row=0,column=0,sticky="NSEW",rowspan=200)

guiframe=tk.Frame(toppane,bg=background_colour)
guiframe.grid(row=0,column=0,sticky="NS")

hotkeys = "123456qwerty7890uiop[asdfghjkl;zxcvbnm,.!@#$%^QWERT&*()_UIOPASDFGHJKLZXCVBNM<>"


panel = tk.Label(guiframe, bg=background_colour, fg=text_colour, wraplength=300, justify="left", text="""Select a source directory to search for images in above.
The program will find all png, gif, jpg, bmp, pcx, tiff, Webp, and psds. It can has as many sub-folders as you like, the program will scan them all (except exclusions).
Enter a root folder to sort to for the "Destination field" too. The destination directory MUST have sub folders, since those are the folders that you will be sorting to.
It is reccomended that the folder names are not super long. You can always rename them later if you desire longer names. Exclusions let you ignore folder names. They are saved (unless you delete prefs.json). Remember that it's one per line, no commas or anything.
You can change the hotkeys in prefs.json, just type a string of letters and numbers and it'll use that. It differentiates between lower and upper case (anything that uses shift), but not numpad.
Thanks to FooBar167 on stackoverflow for the advanced (and memory efficient!) Zoom and Pan tkinter class.
You can use arrow keys or click and drag to pan the image. Mouse Wheel Zooms the image.
Thanks you for using this program!""")
panel.grid(row=12,column=0,columnspan=200, sticky="NSEW")
rescalemode=tk.BooleanVar(value=True)
style = ttk.Style()
style.configure("darkmode.TCheckbutton", background="black", foreground="white", highlightthickness = 0)
style.map('darkmode.TCheckbutton',
           background=[('active', active_background_colour),  # Hover background
                       ('pressed', active_background_colour)],  # Clicked background
           foreground=[('active', active_foreground_colour),  # Hover text color
                       ('pressed', active_foreground_colour)])  # Clicked text color
rescalecheckbox = ttk.Checkbutton(guiframe,text="Auto-Zoom Images",variable=rescalemode, command=lambda: displayimage(),onvalue=True,offvalue=False,style="darkmode.TCheckbutton") # Refresh displayed image

rescalemode.set(rescalemode_temp)
rescalecheckbox.grid(row=3,column=0,sticky="E", padx= 10)






tkroot.columnconfigure(0, weight=1)
buttonframe = tk.Frame(guiframe,bg=button_colour)
buttonframe.grid(column=0,row=4,sticky="NSEW",rowspan=2,columnspan=3)
buttonframe.columnconfigure(0,weight=1)
buttonframe.columnconfigure(1,weight=1)
buttonframe.columnconfigure(2,weight=1)

def movefile(dest,event=None):
    global imgiterator
    global imageframe
    imageframe.canvas.delete("all")
    imageframe.imagetk=None
    shmove(imagelist[imgiterator]["path"],os.path.join(dest,imagelist[imgiterator]["name"]))
    print("Moved: " + imagelist[imgiterator]["name"] + " to " +dest)
    imagelist[imgiterator]["dest"] = os.path.join(dest,imagelist[imgiterator]["name"])
    imgiterator+=1
    displayimage()


def skip(event=None):
    global imgiterator
    imgiterator+=1
    displayimage()

def darken_color(color, factor=0.5):
    """Darken a given color by a specified factor."""
    # Convert hex color to RGB
    r = int(color[1:3], 16)
    g = int(color[3:5], 16)
    b = int(color[5:7], 16)

    # Darken the color
    r = int(r * factor)
    g = int(g * factor)
    b = int(b * factor)

    # Convert back to hex
    return f'#{r:02x}{g:02x}{b:02x}'

def guisetup():
    global guicol
    global guirow
    global panel
    global sdpEntry
    global ddpEntry
    global buttonframe
    global hotkeys
    global columns

    for x in buttons:
        x.destroy()  # Clear the GUI
    panel.destroy()
    guirow = 1
    guicol = 0
    itern = 0
    smallfont = tkfont.Font(family='Helvetica', size=10)
    columns = 1

    if len(destinations) > int((guiframe.winfo_height() / 35) - 2):
        columns = 2
        buttonframe.columnconfigure(1, weight=1)

    # Dictionary to store original colors
    original_colors = {}

    for x in destinations:
        if x['name'] != "SKIP" and x['name'] != "BACK":
            if itern < len(hotkeys):
                newbut = tk.Button(buttonframe, text=hotkeys[itern] + ": " + x['name'],
                                   command=partial(movefile, x['path']),
                                   anchor="w", wraplength=(guiframe.winfo_width() / columns) - 1,
                                   bg=button_colour, fg=text_colour)
                random.seed(x['name'])
                tkroot.bind_all(hotkeys[itern], partial(movefile, x['path']))
                color = randomColor()
                fg = text_colour
                if luminance(color) == 'light':
                    fg = text_colour
                newbut.configure(bg=color, fg=fg)
                original_colors[newbut] = {'bg': color, 'fg': fg}  # Store both colors
                if len(x['name']) >= 13:
                    newbut.configure(font=smallfont)
            else:
                newbut = tk.Button(buttonframe, text=x['name'],
                                   command=partial(movefile, x['path']),
                                   anchor="w", bg=button_colour, fg=text_colour)
            itern += 1
        elif x['name'] == "SKIP":
            newbut = tk.Button(buttonframe, text="SKIP (Space)", command=skip, bg=button_colour, fg=text_colour)
            tkroot.bind("<space>", skip)
        elif x['name'] == "BACK":
            newbut = tk.Button(buttonframe, text="BACK", command=back, bg=button_colour, fg=text_colour)

        newbut.config(font=("Courier", 12), width=int(guiframe.winfo_width()/10), height=1)

        if len(x['name']) > 20:
            newbut.config(font=smallfont)

        if guirow > ((tkroot.winfo_height() / 35) - 2):
            guirow = 1
            guicol += 1

        newbut.grid(row=guirow, column=guicol, sticky="ew")
        buttons.append(newbut)
        guirow += 1

        # Store the original colors for all buttons
        original_colors[newbut] = {'bg': newbut.cget("bg"), 'fg': newbut.cget("fg")}  # Store both colors

        # Bind hover events for each button
        newbut.bind("<Enter>", lambda e, btn=newbut: btn.config(bg=darken_color(original_colors[btn]['bg']), fg='white'))
        newbut.bind("<Leave>", lambda e, btn=newbut: btn.config(bg=original_colors[btn]['bg'], fg=original_colors[btn]['fg']))  # Reset to original colors

    # For SKIP and BACK buttons, set hover to white
    for btn in buttons:
        if btn['text'] == "SKIP (Space)" or btn['text'] == "BACK":
            btn.bind("<Enter>", lambda e, btn=btn: btn.config(bg=text_colour, fg=background_colour))
            btn.bind("<Leave>", lambda e, btn=btn: btn.config(bg=button_colour, fg=text_colour))  # Reset to original colors







def displayimage():
    if len(imagelist) > 0: # Prevents functions designed to refresh the image after a change from running if there are no images.
        global imgiterator
        global panel
        global guicol
        global imageframe
        global guiframe
        global tkroot
        global rescalemode
        if imgiterator >= len(imagelist):
            if messagebox.askokcancel("Images Sorted!","Reached the end of files, thanks for using Simple Image Sorter. Press OK to quit, or cancel to navigate back if you wish. If you had not reached the end of the files, this is a bug, please report it. Thank you!"):
                tkroot.destroy()
                saveonexit()
                exit(0)
            else:
                imgiterator = len(imagelist)-1
        print("Displaying: "+ imagelist[imgiterator]['path'])
        tkroot.winfo_toplevel().title("Simple Image Sorter: " +imagelist[imgiterator]['path'])
        imageframe = CanvasImage(toppane,imagelist[imgiterator]['path'])
        # takes the smaller scale (since that will be the limiting factor) and rescales the image to that so it fits the frame.
        if rescalemode.get():
            print(rescalemode.get())
            imageframe.rescale(min((tkroot.winfo_width()-guiframe.winfo_width())/imageframe.imwidth, tkroot.winfo_height()/imageframe.imheight)) #550

        else:
            pass

        imageframe.center_image()
        imageframe.grid(column=1,row=0,sticky="NSEW",rowspan=200)

def on_option_selected(self, *args):
    global selected_option
    print(f"{selected_option}")
    selected_option = variable.get()
    displayimage()

#Initialization for view-button
variable = tk.StringVar()
try:
    variable.set(selected_option)  # Set the default option
except:
    variable.set("Corner")  # Set the default option
variable.trace_add("write", on_option_selected)

style3 = ttk.Style()
style3.theme_use('classic')
style3.configure('darkmode.TMenubutton', background=background_colour, foreground=text_colour, highlightthickness = 0)
style3.map('darkmode.TMenubutton',
           background=[('active', active_background_colour),  # Hover background
                       ('pressed', active_background_colour)],  # Clicked background
           foreground=[('active', active_foreground_colour),  # Hover text color
                       ('pressed', active_foreground_colour)])  # Clicked text color

options = ["Corner", "Corner", "y-Center", "xy-Center", "x-Center"]
option_menu = ttk.OptionMenu(guiframe, variable, *options)
option_menu.grid(row = 3, column = 2, sticky = "ew")
option_menu.config(style='darkmode.TMenubutton')

def folderselect(_type):
    folder = tkFileDialog.askdirectory()
    if _type == "src":
        sdpEntry.delete(0,len(sdpEntry.get()))
        sdpEntry.insert(0,folder)
    if _type == "des":
        ddpEntry.delete(0,len(ddpEntry.get()))
        ddpEntry.insert(0,folder)

def saveonexit():
    global selected_option
    global rescalemode
    sdp = sdpEntry.get() if os.path.exists(sdpEntry.get()) else ""
    ddp = ddpEntry.get() if os.path.exists(ddpEntry.get()) else ""

    save = {
        "srcpath": sdp,
        "despath": ddp,
        "exclude": exclude,
        "hotkeys": hotkeys,
        #"sortbydate": sortbydatevar.get(),
        "rescalemode":rescalemode.get(),
        "selected_option":selected_option,
        "geometry":tkroot.winfo_geometry()
        }

    try: #Try to save the preference to prefs.json
        with open(prefs_path, "w+") as savef:
            json.dump(save, savef,indent=4, sort_keys=False)
            pass
    except Exception as e:
        pass

#gui setup
def active_on_enter(event):
    activebutton.config(bg=text_colour, fg=button_colour)

def active_on_leave(event):
    activebutton.config(bg=button_colour, fg=text_colour)

def sdpEntry_on_enter(event):
    sdpEntry.config(bg=text_colour, fg=button_colour)

def sdpEntry_on_leave(event):
    sdpEntry.config(bg=button_colour, fg=text_colour)

def ddpEntry_on_enter(event):
    ddpEntry.config(bg=text_colour, fg=button_colour)

def ddpEntry_on_leave(event):
    ddpEntry.config(bg=button_colour, fg=text_colour)

def sdplabel_on_enter(event):
    sdplabel.config(bg=text_colour, fg=button_colour)

def sdplabel_on_leave(event):
    sdplabel.config(bg=button_colour, fg=text_colour)
def ddplabel_on_enter(event):
    ddplabel.config(bg=text_colour, fg=button_colour)

def ddplabel_on_leave(event):
    ddplabel.config(bg=button_colour, fg=text_colour)
sdpEntry = tk.Entry(guiframe,bg=button_colour, fg=text_colour,disabledbackground=button_colour, disabledforeground=text_colour) #scandirpathEntry
ddpEntry= tk.Entry(guiframe,bg=button_colour, fg=text_colour,disabledbackground=button_colour, disabledforeground=text_colour)#dest dir path entry

sdplabel= tk.Button(guiframe,text="Source Folder:", bg=button_colour, fg=text_colour, command=partial(folderselect,"src"))
ddplabel= tk.Button(guiframe,bg=button_colour, fg=text_colour, text="Destination Folder:", command=partial(folderselect,"des" ))
activebutton=tk.Button(guiframe,text="Ready",command=validate,bg=button_colour, fg=text_colour)

sdplabel.grid(row=0,column=0,sticky="nsew")
sdpEntry.grid(row=0,column=1,sticky="nsew")
ddplabel.grid(row=1,column=0,sticky="nsew")
ddpEntry.grid(row=1,column=1,sticky="nsew")
activebutton.grid(row=1,column=2,sticky="ew", padx=1, pady=0, columnspan=2)

activebutton.bind("<Enter>", active_on_enter)
activebutton.bind("<Leave>", active_on_leave)

sdpEntry.bind("<Enter>", sdpEntry_on_enter)
sdpEntry.bind("<Leave>", sdpEntry_on_leave)

ddpEntry.bind("<Enter>", ddpEntry_on_enter)
ddpEntry.bind("<Leave>", ddpEntry_on_leave)

sdplabel.bind("<Enter>", sdplabel_on_enter)
sdplabel.bind("<Leave>", sdplabel_on_leave)

ddplabel.bind("<Enter>", ddplabel_on_enter)
ddplabel.bind("<Leave>", ddplabel_on_leave)

def exclude_on_enter(event):
    excludebutton.config(bg=text_colour, fg=background_colour)

def exclude_on_leave(event):
    excludebutton.config(bg=background_colour, fg=text_colour)

def excludeshow():
    global exclude
    excludewindow = tk.Toplevel()
    excludewindow.winfo_toplevel().title("Folder names to ignore, one per line. This will ignore sub-folders too.")
    excludetext=tkst.ScrolledText(excludewindow)
    for x in exclude:
        excludetext.insert("1.0",x+"\n")
    excludetext.pack()
    excludewindow.protocol("WM_DELETE_WINDOW",partial(excludesave,text=excludetext,toplevelwin=excludewindow))

excludebutton=tk.Button(guiframe,text="Manage Exclusions",command=excludeshow,bg=button_colour, fg=text_colour)
excludebutton.grid(row=0,column=2, sticky='ew', padx=1)
excludebutton.bind("<Enter>", exclude_on_enter)
excludebutton.bind("<Leave>", exclude_on_leave)
guiframe.columnconfigure(0, weight=0)
guiframe.columnconfigure(1, weight=0)
guiframe.columnconfigure(2, weight=0)
def excludesave(text,toplevelwin):
    global exclude
    global geometry
    text= text.get('1.0', tk.END).splitlines()
    exclude=[]
    for line in text:
        exclude.append(line)
    print("List of excluded folder names:")
    print(exclude)
    try:
        toplevelwin.destroy()
    except:
        pass
#INITIATE

try:
    with open(prefs_path,"r") as prefsfile:
        jdata=prefsfile.read()
        jprefs=json.loads(jdata)
        #print(jprefs)
        sdpEntry.delete(0,len(sdpEntry.get()))
        ddpEntry.delete(0,len(ddpEntry.get()))
        sdpEntry.insert(0,jprefs["srcpath"])
        ddpEntry.insert(0,jprefs["despath"])
        if 'hotkeys' in jprefs:
            hotkeys = jprefs["hotkeys"]
        exclude=jprefs["exclude"]
    if hotkeys=="":
        hotkeys="123456qwerty7890uiop[asdfghjkl;zxcvbnm,.!@#$%^QWERT&*()_UIOPASDFGHJKLZXCVBNM<>"

except Exception:
    pass
#textout.config(state=tk.DISABLED)
#textout.insert(tk.INSERT,"""No images Loaded yet.
#Enter a source directory in the relevant text field. It can has as many sub-folders as you like, the program will scan them all.
#Enter a root folder to sort to for the "Destination field" too.
#Both of these must have valid paths. That is, they are folders that actually exist.
#The destination directory MUST have sub folders, since those are the folders that you will be sorting to. It is reccomended that the folder names are not more than say, 20 characters long.
#You can always rename them later if you desire longer names.
#Thanks for using this program!""")
#textout.config(state=tk.DISABLED)
tkroot.winfo_toplevel().title("Simple Image Sorter v1.8.2")

def closeprogram():
    global sdp
    global ddp
    sdp = sdpEntry.get() if os.path.exists(sdpEntry.get()) else ""
    ddp = ddpEntry.get() if os.path.exists(ddpEntry.get()) else ""
    saveonexit()
    tkroot.destroy()
    exit(0)
tkroot.protocol("WM_DELETE_WINDOW",closeprogram)

def back():
    global imgiterator
    if imgiterator > 0:
        imgiterator-=1
        if imagelist[imgiterator]["dest"] !=  "":
            shmove(imagelist[imgiterator]["dest"],imagelist[imgiterator]["path"])
        displayimage()
    else:
        print("can't find last file to go back to!")


def buttonResizeOnWindowResize(b=""):
    if len(buttons)>0:
        for x in buttons:
            x.configure(wraplength=buttons[0].winfo_width()-1)
tkroot.bind("<Configure>", buttonResizeOnWindowResize)
buttonResizeOnWindowResize("a")
tkroot.mainloop()
