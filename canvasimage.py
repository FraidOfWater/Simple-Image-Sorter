# -*- coding: utf-8 -*-
# Advanced zoom for images of various types from small to huge up to several GB
import math
import warnings
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import threading
import time
import logging
from math import floor
from autoscrollbar import AutoScrollbar

logger = logging.getLogger("Canvasimage")
logger.setLevel(logging.ERROR)  # Set to the lowest level you want to handle

handler = logging.StreamHandler()
handler.setLevel(logging.ERROR)

formatter = logging.Formatter('%(message)s')
handler.setFormatter(formatter)

logger.addHandler(handler)
class CanvasImage:
    """ Display and zoom image """
    def __init__(self, master, imagewindowgeometry, viewer_colour, imageobj, gui):

        self.obj = imageobj
        path = imageobj.path
        self.gui = gui

        viewer_x_centering = gui.viewer_x_centering
        viewer_y_centering = gui.viewer_y_centering
        filter_mode = gui.filter_mode
        self.viewer_colour = viewer_colour

        
        
        print("")
        print(f"{self.obj.name.get()[:30]}.")

        """ Initialize core attributes and lists"""
        self.path = path  # path to the image, should be public for outer classes
        
        geometry_width, geometry_height = imagewindowgeometry.split('x',1)

        # Fix for lag in first image that is placed!
        self.count = 0
        self.count1 = 3

        # Logic for quick displaying of first frame.
        self.first = True           # Flag that turns off when the initial picture has been rendered.
        self.replace_first = True   # Flag that turns off when the pyramid has created the same picture in higher quality and rendered it.
        self.replace_await = False

        # The initial quality of placeholder image, used to display the image just a bit faster.
        accepted_modes = ["NEAREST", "BILINEAR", "BICUBIC", "LANCZOS"]

        if filter_mode.upper() in accepted_modes:
            self.__first_filter = getattr(Image.Resampling, filter_mode.upper())
        else:
            self.__first_filter = Image.Resampling.BILINEAR

        self.__filter = Image.Resampling.LANCZOS  # The end qualtiy of the image. #NEAREST, BILINEAR, BICUBIC
        # Lists, attributes and other flags.
        self.frames = []            # Stores loaded frames for .Gif, .Webp
        self.original_frames = []   # Could be used for zooming logic
        self.default_delay = tk.BooleanVar()    # Frame refresh time. Unique for each frame, or use singular, default reported by image?
        self.default_delay.set(True)            # Fallback to default_delay. This is linked to the button in GUI: default_delay_button.
        self.viewer_x_centering = viewer_x_centering
        self.viewer_y_centering = viewer_y_centering

        self.lazy_index = 0
        self.lazy_loading = True    # Flag that turns off when all frames have been loaded to frames.
        
        # Navigator locking mechanism
        self.og_posx = 0
        self.og_posy = 0
        self.last_state = ""

        # Image scaling defaults
        self.imscale = 1.0  # Scale for the canvas image zoom
        self.__delta = 1.15  # Zoom step magnitude

        # Misc
        self.__previous_state = 0  # previous state of the keyboard

        """Opening the image"""
        try:
            self.image = Image.open(path) #redundant

        except FileNotFoundError:
            logger.error(f"File not found: {path}")
            return
        except Exception as e:
            logger.error(f"An error occurred: {e}")
            return

        # Decide if this image huge or not
        self.__huge = False # huge or not
        self.__huge_size = 14000 # define size of the huge image
        self.__band_width = 1024 # width of the tile band

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
        # Set ratio coefficient for image pyramid
        self.__ratio = max(self.imwidth, self.imheight) / self.__huge_size if self.__huge else 1.0
        self.__curr_img = 0  # current image from the pyramid
        self.__scale = self.imscale * self.__ratio  # image pyramid scale
        self.__reduction = 2 # reduction degree of image pyramid

        """ Initialization of frame in master widget"""
        self.__imframe = ttk.Frame(master)

        # Vertical and horizontal scrollbars for __imframe
        hbar = AutoScrollbar(self.__imframe, orient='horizontal')
        vbar = AutoScrollbar(self.__imframe, orient='vertical')
        #hbar.grid(row=1, column=0, sticky='we')
        #vbar.grid(row=0, column=1, sticky='ns')

        # Create canvas and bind it with scrollbars. Public for outer classes
        self.canvas = tk.Canvas(self.__imframe, bg=self.viewer_colour,
                                highlightthickness=0, xscrollcommand=hbar.set,
                                yscrollcommand=vbar.set, width=geometry_width, height = geometry_height)  # Set canvas dimensions to remove scrollbars
        self.canvas.grid(row=0, column=0, sticky='nswe') # Place into grid
        #self.canvas.grid_propagate(True) #Experimental

        # threading here?
        self.creation_time = time.time()
        self.canvas_height = int(geometry_height)
        self.canvas_width = int(geometry_width)
        self.__pyramid = [self.smaller()] if self.__huge else [Image.open(self.path)]
        self.pyramid = []
        if not imageobj.isanimated:
            w, h = self.__pyramid[-1].size
            self.pyramid_ready = threading.Event()
            threading.Thread(target=lambda:self.lazy_pyramid(w,h), daemon=True).start()
        else:
            try:
                self.length = imageobj.framecount

                new_width = self.canvas_width
                new_height = self.canvas_height
                width, height = self.image.size
                aspect_ratio = width / height

                if new_width / new_height > aspect_ratio:
                    new_width = int(new_height*aspect_ratio)
                else:
                    new_height = int(new_width / aspect_ratio)

                self.new_size = (new_width, new_height)

                self.load_frames_thread = threading.Thread(target=self.load_frames, daemon=True).start()
                self.lazy_load() #could change this to do itself before the threding, this loads the first picture, then waits for new ones. no buffering message

            except Exception as e:
                logger.error(f"Can't access imageinfo. {e}")

        self.canvas.update()  # Wait until the canvas has finished creating.

        #Try to load frames from gif and webp images.
        self.container = self.canvas.create_rectangle((0, 0, self.imwidth, self.imheight), width=0)
        #this creates displays first image?
        self.canvas.bind('<Configure>', lambda event: (self.__show_image()))  # canvas is resized from displayimage, time to show image.
        # Create image pyramid
        #old place for image:

        # bind scrollbars to the canvas
        #hbar.configure(command=self.__scroll_x)
        #vbar.configure(command=self.__scroll_y)

        # Bind events to the Canvas
        self.canvas.bind('<ButtonPress-1>', self.__move_from)  # remember canvas position / panning
        self.canvas.bind('<ButtonRelease-1>', lambda event: self.time_set(event))  # remember canvas position / panning

        self.canvas.bind('<B1-Motion>',     self.__move_to)  # move canvas to the new position / panning
        self.canvas.bind('<MouseWheel>', self.__wheel)  # zoom for Windows and MacOS, but not Linux / zoom pyramid.
        self.canvas.bind('<Button-5>',   self.__wheel)  # zoom for Linux, wheel scroll down
        self.canvas.bind('<Button-4>',   self.__wheel)  # zoom for Linux, wheel scroll up
        #if not hasattr(self.gui, "second_window"): # right click close dock view
        #    self.canvas.bind("<Button-3>", self.close_window)
        # Handle keystrokes in idle mode, because program slows down on a weak computers,
        # when too many key stroke events in the same time
        self.canvas.bind('<Key>', lambda event: self.canvas.after_idle(self.key_listener, event))

        self.canvas.bind('<KeyPress-Control_L>', lambda event: self.on_control_press(event))
        self.canvas.bind('<KeyRelease-Control_L>', lambda event: self.on_control_release(event))
        self.canvas.bind('<KeyPress-Control_R>', lambda event: self.on_control_press(event))
        self.canvas.bind('<KeyRelease-Control_R>', lambda event: self.on_control_release(event))

        self.canvas.bind('<KeyPress-Shift_L>', lambda event: self.on_control_press_s(event))
        self.canvas.bind('<KeyRelease-Shift_L>', lambda event: self.on_control_release_s(event))
        self.canvas.bind('<KeyPress-Shift_R>', lambda event: self.on_control_press_s(event))
        self.canvas.bind('<KeyRelease-Shift_R>', lambda event: self.on_control_release_s(event))

        try:
            self.__image.close()
        except Exception as e:
            logger.error(f"Error in destroy displayimage: {e}")

    def on_control_press(self, event):
        self.control_pressed = True
        self.canvas.bind('<Key>', lambda event: self.canvas.after_idle(self.keystroke, event))
        self.canvas.focus_set()
        #logger.debug(self.control_pressed)
    
    def on_control_release(self, event):
        self.control_pressed = False
        logger.debug(self.control_pressed)
        #self.last_state = "quickzoom"

    def on_control_press_s(self, event):
        self.control_pressed = True
        self.canvas.bind('<Key>', lambda event: self.canvas.after_idle(self.keystroke, event))
        self.canvas.focus_set()
        #logger.debug(self.control_pressed)
    
    def on_control_release_s(self, event):
        self.control_pressed = False
        #logger.debug(self.control_pressed)
        self.last_state = "quickscroll"
            
    def key_listener(self, event):
        # 1. When moving, we want to be unimpeded until we click enter. If show next and caps lock is OFF, give it to navigator.
        # 2. This sets the initial one. In keystroke we must recognize if the flag is tripped. To return control.
        flag = False
        if event.keysym == "Return":
            self.gui.enter_toggle = not self.gui.enter_toggle
            self.last_state = "Return"
        if event.state & 0x4:
            self.canvas.bind('<Key>', lambda event: self.canvas.after_idle(self.keystroke, event))
            self.canvas.after_idle(self.keystroke, event)
            self.canvas.focus_set()
            self.last_state = "ctrl+event"
            flag = True
        if event.state & 0x1:
            self.canvas.bind('<Key>', lambda event: self.canvas.after_idle(self.keystroke, event))
            self.canvas.after_idle(self.keystroke, event)
            self.canvas.focus_set()
            self.last_state = "shift+event"
            flag = True
        if flag:
            flag = False
            return

        if self.gui.show_next.get() and not self.gui.enter_toggle: # Enter wasnt pressed
            self.canvas.after_idle(self.gui.navigator, event)
        elif self.gui.show_next.get() and self.gui.enter_toggle: # Enter was pressed, focus on image viewer.
            self.focus_canvasimage()
        elif not self.gui.show_next.get():
            self.canvas.bind('<Key>', lambda event: self.canvas.after_idle(self.keystroke, event))
            self.canvas.after_idle(self.keystroke, event)


    def lazy_pyramid(self,w,h): # Loads the image pyramid lazily. We want to render the image first, we need the pyramid only for zooming later.
        try:
            self.pyramid = [Image.open(self.path)]
            self.replace_first = True
            while w > 512 and h > 512:
                w /= self.__reduction
                h /= self.__reduction
                self.pyramid.append(self.pyramid[-1].resize((int(w), int(h)), self.__filter))
                if self.replace_first:
                    self.replace_first = False
                    self.replace_await = True
                    self.__pyramid = self.pyramid
                    self.pyramid_ready.wait()
                    self.__show_image()
            self.__pyramid = self.pyramid # pass the whole zoom pyramid when it is ready.
        except Exception as e:
            logger.info("Thread caught.")

    def load_frames(self): # This loads the frames for gif and webp lazily
        try:
            #Happy ending, all frames found, return.
            if not self.frames:
                #threading creates first picture because thats the fastest way? Immediate. Canvas is already there. It should probably use centering logic, though.
                # The image is created, and lazy_load is going to take over., because frames is no longer empty.canvas_width = self.canvas.winfo_width()
                #centering of frames and rescaling?
                frame = ImageTk.PhotoImage(self.image.resize(self.new_size), Image.Resampling.LANCZOS)

                canvas_width = self.canvas_width
                canvas_height = self.canvas_height
                frame_width = frame.width()
                frame_height = frame.height()
                x_offset = (canvas_width - frame_width) // 2
                y_offset = (canvas_height - frame_height) // 2


                self.imageid = self.canvas.create_image(x_offset, y_offset, anchor='nw', image=frame)
                self.frames.append(frame)

                end_time2 = time.time()
                elapsed_time = end_time2 - self.creation_time

                b = round(self.obj.file_size/1.048576/1000000,2) #file size in MB
                
                print(f"Size: {b} MB. Frames: {self.obj.framecount}")
                print(f"F:  {elapsed_time}")
                del end_time2
                self.first = False # Flags that the first has been created

                for i in range(1, self.obj.framecount):
                    self.image.seek(i)
                    logger.debug(f"Load: {self.lazy_index+1}/{self.obj.framecount} ({self.obj.frametimes[self.lazy_index]})")
                    frame = ImageTk.PhotoImage(self.image.resize(self.new_size), Image.Resampling.LANCZOS)
                    self.frames.append(frame)




                """All frames have been loaded"""
                self.lazy_loading = False # Lower the lazy_loading flag so animate can take over.
                self.timeit()             # Tell time it took to load all.
                return

        except Exception as e:
            if hasattr(self, 'frames'): # This wont let the error display if the window is being closed.
                logger.error(f"Error loading frames: {e}")

    def close_window(self, x=None):
        if self.obj.isanimated:
            self.frames.clear()
            self.original_frames.clear()
            del self.frames
            del self.original_frames
        try:
            for img in self.pyramid:
                img.close()
            self.pyramid.clear()
            del self.pyramid
        except Exception as e:
            logger.error(f"Error in closing pyramid : {e}")

        try:
            for img in self.__pyramid:
                img.close()
            self.__pyramid.clear()
            del self.__pyramid
        except Exception as e:
            logger.error(f"Error in closing __pyramid: {e}")

        try:
            self.image.close()
            del self.image
        except Exception as e:
            logger.error(f"Error in closing image: {e}")

        try:
            self.__image.close()
            del self.__image
        except Exception as e:
            logger.error(f"Error in closing __image: {e}")

        self.destroy()

    def timeit(self): # Returns how fast the image was loaded to canvas.
        time_it_time = time.time()
        elapsed_time = time_it_time - self.creation_time
        print(f"L:  {elapsed_time}")
        del time_it_time

    def lazy_load(self): # Lazily loads the frames

        if not self.lazy_loading: #If lazy no longer needed and must pass on to main animation thread.
            logger.debug("All frames loaded, stopping lazy_load")
            self.animate_image()
            return

        elif not self.frames or not len(self.frames) > self.lazy_index: #if the list is still empty. Wait.
            logger.debug("Buffering") #Ideally 0 buffering, update somethng so frames is initialzied quaranteed.
            self.canvas.after(self.obj.delay, self.lazy_load)
            return

        elif self.lazy_index != self.obj.framecount:
            #Checks if more frames than index is trying and less than max allowed.
            self.canvas.itemconfig(self.imageid, image=self.frames[self.lazy_index])

            if self.default_delay.get():
                logger.debug(f"Lazy: {self.lazy_index+1}/{self.obj.framecount} ({self.obj.delay}) ###")
                self.canvas.after(self.obj.delay, self.run_multiple)
                return
            else:
                logger.debug(f"Lazy: {self.lazy_index+1}/{self.obj.framecount} ({self.obj.frametimes[self.lazy_index]}) ###")
                self.canvas.after(self.obj.frametimes[self.lazy_index], self.run_multiple)
                return

        else:
            logger.error("Error in lazy load, take a look")
            self.canvas.after(self.obj.delay, self.lazy_load)

    def animate_image(self): # Switches the frames to make it animated
        self.canvas.itemconfig(self.imageid, image=self.frames[self.lazy_index])
        if self.default_delay.get():
            logger.debug(f"{self.lazy_index+1}/{self.obj.framecount} ({self.obj.delay})")
            self.canvas.after(self.obj.delay, self.run_multiple2)

        else:
            logger.debug(f"{self.lazy_index+1}/{self.obj.framecount} ({self.obj.frametimes[self.lazy_index]})")
            self.canvas.after(self.obj.frametimes[self.lazy_index], self.run_multiple2)

    def run_multiple(self): # Helper function to run lazy_load again #make it handle going over.
        self.lazy_index += 1
        self.lazy_load()

    def run_multiple2(self): # Helper function to run animate_image again
        self.lazy_index = (self.lazy_index + 1) % len(self.frames)
        self.animate_image()

    def smaller(self): # Resize image proportionally and return smaller image
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
        self.__imframe.rowconfigure(0, weight=0)  # make frame expandable
        self.__imframe.columnconfigure(0, weight=0) #weight = to remove scrollbars

    def pack(self, **kw):
        """ Exception: cannot use pack with this widget """
        raise Exception('Cannot use pack with the widget ' + self.__class__.__name__)

    def place(self, **kw):
        """ Exception: cannot use place with this widget """
        raise Exception('Cannot use place with the widget ' + self.__class__.__name__)

    def __scroll_x(self, *args, **kwargs): # noinspection PyUnusedLocal
        """ Scroll canvas horizontally and redraw the image """
        self.canvas.xview(*args)  # scroll horizontally
        self.__show_image()  # redraw the image

    def __scroll_y(self, *args, **kwargs): # noinspection PyUnusedLocal
        """ Scroll canvas vertically and redraw the image """
        self.canvas.yview(*args)  # scroll vertically
        self.__show_image()  # redraw the image

    def __show_image(self): # Heavily modified to support gif
        try:
            if self.obj.isanimated: #Let another function handle if animated
                if self.frames:
                    pass
            else:
                """ Show image on the Canvas. Implements correct image zoom almost like in Google Maps """
                box_image = self.canvas.coords(self.container)  # get image area
                box_canvas = (self.canvas.canvasx(0),  # get visible area of the canvas
                              self.canvas.canvasy(0),
                              self.canvas.canvasx(self.canvas_width),
                              self.canvas.canvasy(self.canvas_height))
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
                        imagetk = ImageTk.PhotoImage(image.resize((int(x2 - x1), int(y2 - y1)), self.__filter)) #new resize for no reason?
                        imageid = self.canvas.create_image(max(box_canvas[0], box_img_int[0]),
                                                       max(box_canvas[1], box_img_int[1]),
                                                    anchor='nw', image=imagetk)
                    else:  # show normal image
                        if self.count < self.count1: # fixes lag on movign rescaled picture.
                                self.manual_wheel()
                                #logger.debug(f"scroll event {self.__curr_img}, {(max(0, self.__curr_img))} {self.count} {self.count1}")
                                self.count += 1
                        a = round(self.obj.file_size/1000000,2) #file size
                        b = round(self.obj.file_size/1.048576/1000000,2) #file size in MB
                        c = round(self.gui.fast_render_size,2) #Prefs set limit in MB
                        if self.first:
                            self.first = False
                            image = self.__pyramid[(max(0, self.__curr_img))]

                            if b < c: # if small render high quality
                                print(f"Size: {b} MB. Frames: {self.obj.framecount}")
                                imagetk = ImageTk.PhotoImage(image.resize((int(x2 - x1), int(y2 - y1)), self.__filter))
                            else:
                                print(f"Size: {b} MB. Frames: {self.obj.framecount}")
                                imagetk = ImageTk.PhotoImage(image.resize((int(x2 - x1), int(y2 - y1)), self.__first_filter))
                            self.imageid = self.canvas.create_image(max(box_canvas[0], box_img_int[0]),
                                                       max(box_canvas[1], box_img_int[1]),
                                                    anchor='nw', image=imagetk)
                            end_time = time.time()
                            elapsed_time = end_time - self.creation_time
                            del end_time
                            print(f"F:  {elapsed_time}")
                            self.canvas.lower(self.imageid)  # set image into background
                            self.canvas.imagetk = imagetk  # keep an extra reference to prevent garbage-collection
                            self.pyramid_ready.set() #tell threading that second picture is allowed to render.


                        elif self.replace_await and b > self.gui.fast_render_size: # only render second time if needed.
                            self.replace_await = False
                            image = self.__pyramid[(max(0, self.__curr_img))]
                            imagetk = ImageTk.PhotoImage(image.resize((int(x2 - x1), int(y2 - y1)), self.__filter))
                            self.imageid = self.canvas.create_image(max(box_canvas[0], box_img_int[0]),
                                                       max(box_canvas[1], box_img_int[1]),
                                                    anchor='nw', image=imagetk)

                            end_time = time.time()
                            elapsed_time = end_time - self.creation_time
                            #del self.creation_time
                            del end_time
                            print(f"B:  {elapsed_time}")
                            self.canvas.lower(self.imageid)  # set image into background
                            self.canvas.imagetk = imagetk

                        else:
                            image = self.__pyramid[(max(0, self.__curr_img))].crop(  # crop current img from pyramid
                                            (int(x1 / self.__scale), int(y1 / self.__scale),
                                             int(x2 / self.__scale), int(y2 / self.__scale)))
                            imagetk = ImageTk.PhotoImage(image.resize((int(x2 - x1), int(y2 - y1)), self.__filter)) #new resize for no reason?
                            self.imageid = self.canvas.create_image(max(box_canvas[0], box_img_int[0]),
                                                       max(box_canvas[1], box_img_int[1]),
                                                    anchor='nw', image=imagetk)
                            self.canvas.lower(self.imageid)  # set image into background
                            self.canvas.imagetk = imagetk
        except Exception as e:
            logger.info("Thread caught.")

    def time_set(self, event):
        time1 = time.time()
        press_time = time1 - self.time_from_click
        flag = False

        if (self.og_posx == event.x or self.og_posy == event.y) and press_time < 0.2:
            flag = True
        if self.gui.show_next.get() and flag and not self.gui.enter_toggle:
            self.gui.enter_toggle = True
            self.gui.current_selection.canvas.configure(highlightbackground = self.gui.imageborder_locked_colour, highlightcolor = self.gui.imageborder_locked_colour)
            self.canvas.bind('<Key>', lambda event: self.canvas.after_idle(self.keystroke, event))
        else:
            self.gui.enter_toggle = False
            self.gui.current_selection.canvas.configure(highlightbackground = self.gui.imageborder_selected_colour, highlightcolor = self.gui.imageborder_selected_colour)
            self.canvas.bind('<Key>', lambda event: self.canvas.after_idle(self.gui.navigator, event))

    def __move_from(self, event): # Remember previous coordinates for scrolling with the mouse
        self.time_from_click = time.time()
        self.og_posx = event.x
        self.og_posy = event.y
        self.canvas.focus_set()
        self.canvas.scan_mark(event.x, event.y)

    def __move_to(self, event): # Drag (move) canvas to the new position
        self.canvas.scan_dragto(event.x, event.y, gain=1)
        self.__show_image()  # zoom tile and show it on the canvas

    def is_image_inside_viewport(self):
        """ Check if the image is entirely within the visible canvas area """
        # Get the image and canvas bounding boxes
        img_bbox = self.canvas.coords(self.container)  # (x1, y1, x2, y2) for the image
        canvas_bbox = (self.canvas.canvasx(0), self.canvas.canvasy(0), 
                       self.canvas.canvasx(self.canvas_width), self.canvas.canvasy(self.canvas_height))
        
        # Check if the image is fully inside the canvas bounds
        if (img_bbox[0] >= canvas_bbox[0] and img_bbox[1] >= canvas_bbox[1] and 
            img_bbox[2] <= canvas_bbox[2] and img_bbox[3] <= canvas_bbox[3]):
            return True  # Image is fully inside
        return False  # Image is partially or fully outside

    def is_image_cropped(self):
        """ Check if the image is cropped and if so, determine the direction(s) """
        img_bbox = self.canvas.coords(self.container)
        canvas_bbox = (self.canvas.canvasx(0), self.canvas.canvasy(0), 
                       self.canvas.canvasx(self.canvas_width), self.canvas.canvasy(self.canvas_height))
        
        # Initialize flags for each cropping direction
        cropped_width = False
        cropped_height = False

        # Check if the image overflows horizontally
        print(floor(img_bbox[0]), canvas_bbox[0], floor(img_bbox[2]), floor(canvas_bbox[2]))
        if floor(img_bbox[0]) < canvas_bbox[0] or floor(img_bbox[2]) > canvas_bbox[2]:
            cropped_width = True
        
        # Check if the image overflows vertically
        print(floor(img_bbox[1]), floor(canvas_bbox[1]), floor(img_bbox[3]), floor(canvas_bbox[3]))
        if floor(img_bbox[1]) < canvas_bbox[1] or floor(img_bbox[3]) > canvas_bbox[3]:
            cropped_height = True

        # Return whether the image is cropped, and in which direction(s)
        return cropped_width, cropped_height

    def outside(self, x, y): # Checks if the point (x,y) is outside the image area
        bbox = self.canvas.coords(self.container)  # get image area
        if bbox[0] < x < bbox[2] and bbox[1] < y < bbox[3]:
            return False  # point (x,y) is inside the image area
        else:
            return True  # point (x,y) is outside the image area

    def __wheel(self, event=None, direction=None): # Zoom with mouse wheel
        if event:
            x = self.canvas.canvasx(event.x)
            y = self.canvas.canvasy(event.y)

            """ re-enable this if you dont want scrolling outside the image """
            #if self.outside(x, y): return  # zoom only inside image area
        else: 
            x = self.canvas.canvasx(self.canvas_width // 2)
            y = self.canvas.canvasy(self.canvas_height // 2)
        scale = 1.0

        # Respond to Linux (event.num) or Windows (event.delta) wheel event
        if (event and (event.num == 5 or event.delta == -120)) or direction == "down":  # scroll down, smaller
            if round(self.__min_side * self.imscale) < 30: return  # image is less than 30 pixels
            self.imscale /= self.__delta
            scale        /= self.__delta
        elif (event and (event.num == 4 or event.delta == 120)) or direction == "up":  # scroll up, bigger
            i = min(self.canvas_width, self.canvas_height) >> 1
            if i < self.imscale: return  # 1 pixel is bigger than the visible area
            self.imscale *= self.__delta
            scale        *= self.__delta

        # Take appropriate image from the pyramid
        k = self.imscale * self.__ratio  # temporary coefficient
        self.__curr_img = min((-1) * int(math.log(k, self.__reduction)), len(self.__pyramid) - 1)
        self.__scale = k * math.pow(self.__reduction, max(0, self.__curr_img))

        self.canvas.scale('all', x, y, scale, scale)  # rescale all objects

        # Redraw some figures before showing image on the screen
        self.redraw_figures()    # method for child classes
        self.__show_image()

        #logger.debug(f"after scroll event {self.__curr_img}, {(max(0, self.__curr_img))}")

    def rescale_gif_frames(self, scale): # Unused logic for now. Should be used for zooming
        if self.obj.isanimated:
            new_size = (int(self.new_size[0] * scale), int(self.new_size[1] * scale))
            for i in range(self.obj.framecount):
                self.frames[i] = ImageTk.PhotoImage(self.image.resize(new_size, Image.Resampling.LANCZOS))
            self.canvas.itemconfig(self.imageid, image=self.frames[self.lazy_index])  # Update the current frame on canvas

    def manual_wheel(self): # Fixes laggy panning on first picture
        x = self.canvas_width
        y = self.canvas_height
        scale = 1.0

        k = self.imscale * self.__ratio # temporary coefficient
        self.__curr_img = min((-1) * int(math.log(k, self.__reduction)), len(self.__pyramid) - 1) #presumably changes the displayed image. Yes. We need pyramid to change the iterated frames.
        self.__scale = k * math.pow(self.__reduction, max(0, self.__curr_img)) #positioning dont change
        self.canvas.scale('all', x, y, scale, scale)  # rescale all objects

    def focus_canvasimage(self):
        self.gui.current_selection.canvas.configure(highlightbackground = self.gui.imageborder_locked_colour, highlightcolor = self.gui.imageborder_locked_colour)
        self.canvas.bind('<Key>', lambda event: self.canvas.after_idle(self.keystroke, event))

    

    def keystroke(self, event): # Scrolling and zooming with the keyboard
        print(self.is_image_inside_viewport())
        print(self.is_image_cropped())
        width, height = self.is_image_cropped()
        if not width and not height:
            right = -1
            left = 1
            up = 1
            down = -1
        elif width and height:
            right = 1
            left = -1
            up = -1
            down = 1
        elif width:
            right = 1
            left = -1
            up = 1
            down = -1
        elif height:
            right = 1
            left = -1
            up = -1
            down = 1

        if event.keysym == "Return" and self.gui.show_next.get():
            self.gui.current_selection.canvas.configure(highlightbackground = self.gui.imageborder_locked_colour, highlightcolor = self.gui.imageborder_locked_colour)
            self.gui.enter_toggle = not self.gui.enter_toggle
            self.last_state = "Return"

        if not self.gui.enter_toggle and self.gui.show_next.get() and not event.state & 0x4 and not event.state & 0x1:
            self.gui.current_selection.canvas.configure(highlightcolor="blue", highlightbackground = "blue")
            self.canvas.bind('<Key>', lambda event: self.canvas.after_idle(self.gui.navigator, event))
            if self.last_state == "quickzoom" or self.last_state == "quickscroll":
                self.canvas.after_idle(self.gui.navigator, event)
            return
        # if press enter, focus on keystroke. If press enter again, focus on moving again. a switch.
        check = ["w","a","s","d"]
            #wasd = 87,65,83,68
            #updownleftright = 38,40,37,39
        for x in check:
            if x in self.gui.hotkeys:
                disable_wasd = True
                break
            else:
                disable_wasd = False
                break
        if not event.keycode in [37,38,39,40] or (event.keycode in [65,68,83,87] and not disable_wasd):
            return
        
        # Up, Down, Left, Right keystrokes
        if not event.state & 0x4 and not event.state & 0x1:
            if event.keycode in [68, 39]:    # scroll right, keys 'd' or 'Right'
                self.__scroll_x('scroll', right, 'unit', event=event)
            elif event.keycode in [65, 37]:    # scroll left, keys 'a' or 'Left'
                self.__scroll_x('scroll', left, 'unit', event=event)
            elif event.keycode in [87, 38]:    # scroll up, keys 'w' or 'Up'
                self.__scroll_y('scroll', up, 'unit', event=event)
            elif event.keycode in [83, 40]:    # scroll down, keys 's' or 'Down'
                self.__scroll_y('scroll', down, 'unit', event=event)

        if event.state & 0x4: # If ctrl pressed, use zoom
            if event.keycode in [87, 38]:   # Up
                self.__wheel(None,"up")
            elif event.keycode in [83, 40]: # Down
                self.__wheel(None,"down")
            if event.keycode in [68, 39] and not event.state & 0x1:    # scroll right, keys 'd' or 'Right'
                self.__scroll_x('scroll', right, 'unit', event=event)
            elif event.keycode in [65, 37] and not event.state & 0x1:    # scroll left, keys 'a' or 'Left'
                self.__scroll_x('scroll', left, 'unit', event=event)
        if event.state & 0x1:
            if event.keycode in [68, 39]:    # RIGHT
                self.__scroll_x('scroll', right, 'unit', event=event)
            elif event.keycode in [65, 37]:    # LEFT
                self.__scroll_x('scroll', left, 'unit', event=event)
            if not event.state & 0x4:
                if event.keycode in [87, 38]:    # UP
                    self.__scroll_y('scroll', up, 'unit', event=event)
                elif event.keycode in [83, 40]:    # DOWN
                    self.__scroll_y('scroll', down, 'unit', event=event)

    def crop(self, bbox): # Crop rectangle from the image and return it
        if self.__huge:     # image is huge and not totally in RAM
            band = bbox[3] - bbox[1]    # width of the tile band
            self.__tile[1][3] = band    # set the tile height
            self.__tile[2] = self.__offset + self.imwidth * bbox[1] * 3    # set offset of the band
            self.__image.close()
            self.__image = Image.open(self.path)    # reopen / reset image
            self.__image.size = (self.imwidth, band)    # set size of the tile band
            self.__image.tile = [self.__tile]
            return self.__image.crop((bbox[0], 0, bbox[2], band))
        else:    # image is totally in RAM
            return self.__pyramid[0].crop(bbox)

    def destroy(self): # ImageFrame destructor
        self.canvas.destroy()
        self.__imframe.destroy()

    def rescale(self, scale): # Rescales the image to fit image viewer
        """ Rescale the Image without doing anything else """
        if  not self.obj.isanimated:
            self.__scale=scale
            self.imscale=scale

            self.canvas.scale('all', self.canvas_width, 0, scale, scale)  # rescale all objects

    def center_image(self): # Centers the iamge in the image viewer
        """ Center the image on the canvas """
        if not self.obj.isanimated:
            canvas_width = self.canvas_width
            canvas_height = self.canvas_height

            # Calculate scaled image dimensions
            scaled_image_width = self.imwidth * self.imscale
            scaled_image_height = self.imheight * self.imscale

            # Calculate offsets to center the image
            if self.viewer_x_centering:
                x_offset = (canvas_width - scaled_image_width)-int((canvas_width - scaled_image_width)/2)
            else:
                x_offset = 0
            if self.viewer_y_centering:
                y_offset = (canvas_height - scaled_image_height)/2
            else:
                y_offset = 0

            # Update the position of the image container
            self.canvas.coords(self.container, x_offset, y_offset, x_offset + scaled_image_width, y_offset + scaled_image_height)