import os
import time
import sys
import json
import pyvips
import tkinter as tk
import logging
import random
from math import floor,sqrt
from PIL import Image, ImageTk
from canvasimage import CanvasImage
import tkinter.font as tkfont
import tkinter.scrolledtext as tkst
from tkinter.messagebox import askokcancel
from tkinter.ttk import Panedwindow
from tkinter import ttk
from tktooltip import ToolTip
from tkinter import filedialog as tkFileDialog
from operator import indexOf
from functools import partial
import threading
last_scroll_time = None

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
    if hsp > 115.6:
        return 'light'
    else:
        return 'dark'


def disable_event():
    pass

def randomColor():
    color = '#'
    hexletters = '0123456789ABCDEF'
    for i in range(0, 6):
        color += hexletters[floor(random.random()*16)]
    return color

if getattr(sys, 'frozen', False):  # Check if running as a bundled executable
    script_dir = os.path.dirname(sys.executable)  # Get the directory of the executable
    prefs_path = os.path.join(script_dir, "prefs.json")
else:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    prefs_path = os.path.join(script_dir, "prefs.json") 

def saveprefs(manager, gui):
    
    sdp = gui.sdpEntry.get() if os.path.exists(gui.sdpEntry.get()) else ""
    ddp = gui.ddpEntry.get() if os.path.exists(gui.ddpEntry.get()) else ""

    save = {
        
        #paths
        "exclude": manager.exclude,
        "srcpath": sdp, 
        "despath": ddp,
        "lastsession": gui.sessionpathvar.get(),

        #User settings
        "thumbnailsize": gui.thumbnailsize, 
        "textlength":gui.textlength,
        "squaresperpage": gui.squaresperpage.get(), 
        "sortbydate": gui.sortbydatevar.get(),
        "default_delay": gui.default_delay.get(),
        "viewer_x_centering": gui.viewer_x_centering,
        "viewer_y_centering": gui.viewer_y_centering,
        "filter_mode": gui.filter_mode,
        "fast_render_size": gui.fast_render_size,

        #Customization
        "checkbox_height":gui.checkbox_height,
        "gridsquare_padx":gui.gridsquare_padx,
        "gridsquare_pady":gui.gridsquare_pady,

        #Window positions
        "geometry": gui.winfo_geometry(),
        "imagewindowgeometry": gui.imagewindowgeometry, 
        "destinationwindow":gui.save,
        "toppane_width":gui.leftui.winfo_width(),
        "middlepane_width":gui.image_display_frame.winfo_width(),
        
        #Window colours
        "canvas_colour":gui.canvas_colour,
        "selectcolour":gui.selectcolour,

        "background_colour":gui.background_colour,
        "grid_background_colour":gui.grid_background_colour,
        "active_background_colour":gui.active_background_colour,
        "active_foreground_colour":gui.active_foreground_colour,

        "text_colour":gui.text_colour,
        
        "button_colour":gui.button_colour,
        "divider_colour":gui.divider_colour,

        "interactive_buttons":gui.interactive_buttons,

        "text_box_thickness":gui.text_box_thickness,
        "image_border_thickness":gui.image_border_thickness,
        "text_box_selection_colour":gui.text_box_selection_colour,
        "image_border_selection_colour":gui.image_border_selection_colour,
        "text_box_colour":gui.text_box_colour,
        "image_border_colour":gui.image_border_colour,
        #Misc
        "hotkeys": gui.hotkeys,
        "threads": manager.threads, 
        "autosave":manager.autosave,
        "hideonassign": gui.hideonassignvar.get(), 
        "hidemoved": gui.hidemovedvar.get(),
        "show_next": gui.show_next.get(),
        "dock_view": gui.dock_view.get(),
        "dock_side": gui.dock_side.get(),
        "extra_buttons": gui.extra_buttons,
        "force_scrollbar": gui.force_scrollbar,
        }
    
    try: #Try to save the preference to prefs.json
        with open(prefs_path, "w+") as savef:
            json.dump(save, savef,indent=4, sort_keys=False)
            logging.debug(save)
    except Exception as e:
        logging.warning(("Failed to save prefs:", e))
        
    try: #Attempt to save the session if autosave is enabled
        if manager.autosave:
            manager.savesession(False)
    except Exception as e:
        logging.warning(("Failed to save session:", e))


class GUIManager(tk.Tk):
    thumbnailsize = 256
    def __init__(self, fileManager) -> None:
        super().__init__()
        
        self.button_colour = 'black'
        self.background_colour = 'black'
        self.grid_background_colour = 'black'

        self.text_colour = 'white'

        self.canvas_colour = 'black'
        self.active_background_colour = 'white'
        self.active_foreground_colour = 'black'
        self.selectcolour = 'grey'
        self.divider_colour = 'grey'


        self.textlength = 34 # Maximum length allowed for filenames. #must use square or canvas to limit text length.

        self.gridsquare_padx = 2
        self.gridsquare_pady = 2
        self.checkbox_height = 25

        self.interactive_buttons = False # Color change on hover

        self.text_box_thickness = 0
        self.image_border_thickness = 1
        
        self.text_box_selection_colour  = "grey"
        self.image_border_selection_colour  = "grey"

        self.text_box_colour = "white"
        self.image_border_colour = "white"
        
        self.default_delay = tk.BooleanVar()    # Whether to use global delay from a gif or a per frame delay.
        self.default_delay.set(True)
        self.viewer_x_centering = False
        self.viewer_y_centering = False
        self.show_next = tk.BooleanVar()
        self.dock_view = tk.BooleanVar()
        self.dock_side = tk.BooleanVar()
        self.dock_side.set(True)
        self.extra_buttons = False
        self.dock_view.set(True)
        self.show_next.set(False)
        self.fast_render_size = 5 # Size at which we start to buffer the image to load the displayimage faster. We use NEAREST, then when LANCZOS is ready, we swap it to that.
        self.filter_mode = "BILINEAR"
        self.fix_flag = True
        self.started_not_integrated = False
        self.force_scrollbar = True
        if getattr(sys, 'frozen', False):  # Check if running as a bundled executable
            script_dir = os.path.dirname(sys.executable)  # Get the directory of the executable
            prefs_path = os.path.join(script_dir, "prefs.json")
        else:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            prefs_path = os.path.join(script_dir, "prefs.json") 

        #script_dir = os.path.dirname(os.path.abspath(__file__))
        #prefs_path = os.path.join(script_dir, "prefs.json")
        #i didnt know how to port these from sortimages.
        try:
            with open(prefs_path, "r") as prefsfile:
                jdata = prefsfile.read()
                jprefs = json.loads(jdata)
                #updates the colours if configured
                if "background_colour" in jprefs:
                    self.background_colour = jprefs['background_colour']
                if "grid_background_colour" in jprefs:
                    self.grid_background_colour = jprefs['grid_background_colour']
                if "button_colour" in jprefs:
                    self.button_colour = jprefs['button_colour']
                if "text_colour" in jprefs:
                    self.text_colour = jprefs['text_colour']
                if "canvas_colour" in jprefs:
                    self.canvas_colour = jprefs['canvas_colour']
                if "active_background_colour" in jprefs:
                    self.active_background_colour = jprefs['active_background_colour']
                if "active_foreground_colour" in jprefs:
                    self.active_foreground_colour = jprefs['active_foreground_colour']
                if "selectcolour" in jprefs:
                    self.selectcolour = jprefs['selectcolour']
                if "divider_colour" in jprefs:
                    self.divider_colour = jprefs['divider_colour']
                if "textlength" in jprefs:
                    self.textlength = jprefs['textlength']
                if "gridsquare_padx" in jprefs:
                    self.gridsquare_padx = jprefs['gridsquare_padx']
                if "gridsquare_pady" in jprefs:
                    self.gridsquare_pady = jprefs['gridsquare_pady']
                if "checkbox_height" in jprefs:
                    self.checkbox_height = jprefs['checkbox_height']
                if "interactive_buttons" in jprefs:
                    self.interactive_buttons = jprefs['interactive_buttons']
                if "text_box_thickness" in jprefs:
                    self.text_box_thickness = jprefs['text_box_thickness']
                if "image_border_thickness" in jprefs:
                    self.image_border_thickness = jprefs['image_border_thickness']
                if "text_box_selection_colour" in jprefs:
                    self.text_box_selection_colour = jprefs['text_box_selection_colour']
                if "image_border_selection_colour" in jprefs:
                    self.image_border_selection_colour = jprefs['image_border_selection_colour']
                if "text_box_colour" in jprefs:
                    self.text_box_colour = jprefs['text_box_colour']
                if "image_border_colour" in jprefs:
                    self.image_border_colour = jprefs['image_border_colour']
                if "default_delay" in jprefs:
                    self.default_delay.set(jprefs['default_delay'])
                if "viewer_x_centering" in jprefs:
                    self.viewer_x_centering = jprefs['viewer_x_centering']
                if "viewer_y_centering" in jprefs:
                    self.viewer_y_centering = jprefs['viewer_y_centering']
                if "fast_render_size" in jprefs:
                    self.fast_render_size = jprefs['fast_render_size']
                if "show_next" in jprefs:
                    self.show_next.set(jprefs['show_next'])
                if "dock_view" in jprefs:
                    self.dock_view.set(jprefs['dock_view'])
                    self.started_not_integrated = not self.dock_view.get()
                if "dock_side" in jprefs:
                    self.dock_side.set(jprefs['dock_side'])
                if "extra_buttons" in jprefs:
                    self.extra_buttons = jprefs['extra_buttons']
                if "force_scrollbar" in jprefs:
                    self.force_scrollbar = jprefs['force_scrollbar']
                if "filter_mode" in jprefs:
                    self.filter_mode = jprefs['filter_mode']

        except Exception as e:
            logging.error("Error loading prefs.json, it is possibly corrupt, try deleting it, or else it doesn't exist and will be created upon exiting the program.")
            logging.error(e)

        #Initialization for view-button values
        self.show_unassigned = tk.BooleanVar()
        self.show_unassigned.set(True)
        self.show_assigned = tk.BooleanVar()
        self.show_moved = tk.BooleanVar()
        #self.show_all = tk.BooleanVar()
        self.show_animated = tk.BooleanVar()
        
        #Initialization for view-button
        self.variable = tk.StringVar()
        self.variable.trace_add("write", self.on_option_selected)
        
        #Initialization for lists.
        #Main window renderlist
        self.gridsquarelist = []
        self.displayedlist = []
        self.last_viewed_image_pos = 0
        self.destgrid_updateslist = []
        self.current_selection = []
        self.current_selection_obj = None
        self.current_selection_obj_flag = False
        self.templist = []
        #Main window sorted lists
        self.unassigned_squarelist = []
        self.assigned_squarelist = []
        self.filtered_images = []
        self.moved_squarelist = []    
        #self.animated_squarelist = []
        self.running = []
        self.track_animated = []
        self.dest_squarelist = []
        self.render_refresh = []
        self.queue = []
        self.clear_all = False
        self.save = 0
        self.refresh_flag = False
        
        #Old (Hideonassing on off implementation?) (That's just "show all" I guess.)
        self.hideonassignvar = tk.BooleanVar()
        self.hideonassignvar.set(True)
        self.hidemovedvar = tk.BooleanVar()
        self.sortbydatevar = tk.BooleanVar()
        self.squaresperpage = tk.IntVar()
        self.squaresperpage.set(120)
        self.sessionpathvar = tk.StringVar()
        self.imagewindowgeometry = str(int(self.winfo_screenwidth(
        )*0.80)) + "x" + str(self.winfo_screenheight()-120)+"+365+60"
        self.destination_window_geometry = 0
        
        # store the reference to the file manager class.
        self.fileManager = fileManager
        self.geometry(str(self.winfo_screenwidth()-5)+"x" +
                      str(self.winfo_screenheight()-120))
        self.geometry("+0+60")
        self.buttons = []
        self.hotkeys = "123456qwerty7890uiopasdfghjklzxcvbnm"

        #Default toppane width
        self.toppane_width = 363
        self.middlepane_width = 363
        
        # Paned window that holds the almost top level stuff.
        self.toppane = Panedwindow(self, orient="horizontal")
        
        # Frame for the left hand side that holds the setup and also the destination buttons.
        self.leftui = tk.Frame(self.toppane, width=self.toppane_width, bg=self.background_colour)
        
        self.leftui.grid_propagate(False) #to turn off auto scaling.
        self.leftui.columnconfigure(0, weight=1)
        self.toppane.add(self.leftui, weight=0) # 0 here, it stops the divider from moving itself. The divider pos is saved by prefs, this complicates it, so auto scaling based on text amount in source and dest folder is disabled.
        
        
        #Add a checkbox to check for sorting preference.
        style = ttk.Style()
        style.configure("darkmode.TCheckbutton", background=self.background_colour, foreground=self.text_colour)
        self.sortbydatecheck = ttk.Checkbutton(self.leftui, text="Sort by Date", variable=self.sortbydatevar, onvalue=True, offvalue=False, command=self.sortbydatevar,style="darkmode.TCheckbutton")
        self.sortbydatecheck.grid(row=2, column=0, sticky="w", padx=25)
        
        self.panel = tk.Label(self.leftui, wraplength=300, justify="left", text="""

    Select a Source Directory: Choose a directory to search for images. The program will scan for the following file types: PNG, GIF, JPG, BMP, PCX, TIFF, WebP, and PSD. It can include as many subfolders as you like, and the program will scan all of them (except for any exclusions).

    Set the Destination Directory: Enter a root folder in the "Destination field" where the sorted images will be placed. The destination directory must contain subfolders, as these will be the folders you are sorting into.

    Preferences: You can specify exclusions in the prefs.json file (one per line, no commas). If you want to change the hotkeys, you can do so in prefs.json by typing a string of letters and numbers. The program differentiates between lowercase and uppercase letters (anything that requires the Shift key) but does not differentiate for the numpad.

    Loading Images: For performance reasons, the program will only load a portion of the images in the folder by default. To load more images, press the "Add Files" button. You can configure how many images are added and loaded at once within the program settings.

    Right-Click Options:
        Right-click on the Destination Buttons to see which images are assigned to them (note that this does not include images that have already been moved).
        Right-click on Thumbnails to view a zoomable full-size image. You can also rename images from this view.

    Acknowledgments: Special thanks to FooBar167 on Stack Overflow for the advanced and memory-efficient Zoom and Pan Tkinter class.
"""
                              ,bg=self.background_colour,fg=self.text_colour)
        self.panel.grid(row=3, column=0, columnspan=200,
                        rowspan=200, sticky="NSEW")
        self.columnconfigure(0, weight=1)

        self.buttonframe = tk.Frame(master=self.leftui,bg=self.background_colour)
        self.buttonframe.grid(
            column=0, row=3, sticky="NSEW")
        self.buttonframe.columnconfigure(0, weight=1)
        
        
        
        self.entryframe = tk.Frame(master=self.leftui,bg=self.background_colour)
        self.entryframe.columnconfigure(1, weight=1)
        
        self.sdpEntry = tk.Entry(
            self.entryframe, takefocus=False, background="white", foreground="black")  # scandirpathEntry
        self.ddpEntry = tk.Entry(
            self.entryframe, takefocus=False,  background="white", foreground="black")  # dest dir path entry

        self.sdplabel = tk.Button(
            self.entryframe, text="Source Folder:", command=partial(self.filedialogselect, self.sdpEntry, "d"), bg=self.button_colour, fg=self.text_colour)
        
        self.ddplabel = tk.Button(
            self.entryframe, text="Destination Folder:", command=partial(self.filedialogselect, self.ddpEntry, "d"),bg=self.button_colour, fg=self.text_colour)
        
        self.activebutton = tk.Button(
            self.entryframe, text="New Session", command=partial(fileManager.validate, self),bg=self.button_colour, fg=self.text_colour)
        ToolTip(self.activebutton,delay=1,msg="Start a new Session with the entered source and destination")
        
        self.loadpathentry = tk.Entry(
            self.entryframe, takefocus=False, textvariable=self.sessionpathvar,  background="white", foreground="black")
        
        self.loadbutton = tk.Button(
            self.entryframe, text="Load Session", command=self.fileManager.loadsession,bg=self.button_colour, fg=self.text_colour)
        ToolTip(self.loadbutton,delay=1,msg="Load and start the selected session data.")
        
        self.loadfolderbutton = tk.Button(self.entryframe, text="Session Data:", command=partial(
            self.filedialogselect, self.loadpathentry, "f"),bg=self.button_colour, fg=self.text_colour)
        ToolTip(self.loadfolderbutton,delay=1,msg="Select a session json file to open.")
        
        self.loadfolderbutton.grid(row=3, column=0, sticky='e') #ew for buttons that are the same size on start display.
        
        self.loadbutton.grid(row=3, column=2, sticky='ew')
        
        self.loadpathentry.grid(row=3, column=1, sticky='ew', padx=2)
        
        self.sdplabel.grid(row=0, column=0, sticky="e") #ew
        
        self.sdpEntry.grid(row=0, column=1, sticky="ew", padx=2)
        
        self.ddplabel.grid(row=1, column=0, sticky="e") #ew
        
        self.ddpEntry.grid(row=1, column=1, sticky="ew", padx=2)
        
        self.activebutton.grid(row=1, column=2, sticky="ew")
        
        self.excludebutton = tk.Button(
            self.entryframe, text="Manage Exclusions", command=self.excludeshow,bg=self.button_colour, fg=self.text_colour)
        self.excludebutton.grid(row=0, column=2)

        #If it is set in prefs, this makes the buttons blink when hovered over.
        if self.interactive_buttons:
            #Option for making the buttons change color on hover
            self.excludebutton.bind("<Enter>", self.exclude_on_enter)
            self.excludebutton.bind("<Leave>", self.exclude_on_leave) 
            self.activebutton.bind("<Enter>", self.active_on_enter)
            self.activebutton.bind("<Leave>", self.active_on_leave)

            self.sdpEntry.bind("<Enter>", self.sdpEntry_on_enter)
            self.sdpEntry.bind("<Leave>", self.sdpEntry_on_leave)

            self.ddpEntry.bind("<Enter>", self.ddpEntry_on_enter)
            self.ddpEntry.bind("<Leave>", self.ddpEntry_on_leave)

            self.sdplabel.bind("<Enter>", self.sdplabel_on_enter)
            self.sdplabel.bind("<Leave>", self.sdplabel_on_leave)

            self.ddplabel.bind("<Enter>", self.ddplabel_on_enter)
            self.ddplabel.bind("<Leave>", self.ddplabel_on_leave)

            self.loadbutton.bind("<Enter>", self.loadbutton_on_enter)
            self.loadbutton.bind("<Leave>", self.loadbutton_on_leave)

            self.loadfolderbutton.bind("<Enter>", self.loadfolderbutton_on_enter)
            self.loadfolderbutton.bind("<Leave>", self.loadfolderbutton_on_leave)

            self.loadpathentry.bind("<Enter>", self.loadpathentry_on_enter)
            self.loadpathentry.bind("<Leave>", self.loadpathentry_on_leave)

            
        
        # show the entry frame, sticky it to the west so it mostly stays put.
        self.entryframe.grid(row=0, column=0, sticky="ew")
        
        # Finish setup for the left hand bar.
        # Start the grid setup
        self.image_display_frame = tk.Frame(self.toppane, bg=self.background_colour, width = self.middlepane_width)
        
        
        imagegridframe = tk.Frame(self.toppane,bg=self.background_colour)
        imagegridframe.grid(row=0, column=2, sticky="NSEW") #this is in second so content frame inside this.
        self.imagegridframe = imagegridframe
        
        # Replacing Text widget with Canvas for image grid
        self.imagegrid = tk.Text(
            self.imagegridframe, wrap ='word', borderwidth=0, highlightthickness=0, state="disabled", background=self.grid_background_colour)
        vbar = tk.Scrollbar(imagegridframe, orient='vertical',command=lambda *args: throttled_yview(self.imagegrid, *args))

    
        
        self.imagegridframe = imagegridframe
        if self.dock_side.get():
            if self.force_scrollbar:
                vbar.grid(row=0, column=1, sticky='ns')
                self.imagegrid.configure(yscrollcommand=vbar.set)
            self.imagegrid.grid(row=0, column=0, sticky="NSEW")  
            imagegridframe.rowconfigure(1, weight=0)
            imagegridframe.rowconfigure(0, weight=1)
            imagegridframe.columnconfigure(1, weight=0)
            imagegridframe.columnconfigure(0, weight=1)
            self.toppane.add(self.image_display_frame, weight=0)
            self.toppane.add(imagegridframe, weight=1)
        else:
            if self.force_scrollbar:
                vbar.grid(row=0, column=0, sticky='ns')
                self.imagegrid.configure(yscrollcommand=vbar.set)
            self.imagegrid.grid(row=0, column=1, sticky="NSEW") 
            imagegridframe.rowconfigure(1, weight=0)
            imagegridframe.rowconfigure(0, weight=1)
            imagegridframe.columnconfigure(0, weight=0)
            imagegridframe.columnconfigure(1, weight=1)
            self.toppane.add(imagegridframe, weight=1)
            self.toppane.add(self.image_display_frame, weight=0)
        
        self.vbar = vbar
        if not self.force_scrollbar:
            vbar.grid(row=0, column=1, sticky='ns')
            self.vbar.grid_forget()
        
        


        style11 = ttk.Style()
        style11.configure('Custom.TPanedwindow', background=self.divider_colour)  # No border for the PanedWindow
        
        
        self.toppane.grid(row=0, column=0, sticky="NSEW")
        self.toppane.configure(style='Custom.TPanedwindow')
        self.columnconfigure(0, weight=10)
        self.columnconfigure(1, weight=0)
        self.rowconfigure(0, weight=10)
        self.rowconfigure(1, weight=0)
        
        self.protocol("WM_DELETE_WINDOW", self.closeprogram)
        
        self.winfo_toplevel().title("Simple Image Sorter: Multiview Edition v2.4")
    def exclude_on_enter(self, event):
        self.excludebutton.config(bg=self.active_background_colour, fg=self.active_foreground_colour)
    def exclude_on_leave(self, event):
        self.excludebutton.config(bg=self.button_colour, fg=self.text_colour)

    def active_on_enter(self,event):
        self.activebutton.config(bg=self.active_background_colour, fg=self.active_foreground_colour)
    def active_on_leave(self,event):
        self.activebutton.config(bg=self.button_colour, fg=self.text_colour)

    def sdpEntry_on_enter(self,event):
        self.sdpEntry.config(bg=self.active_background_colour, fg=self.active_foreground_colour)
    def sdpEntry_on_leave(self,event):
        self.sdpEntry.config(bg=self.background_colour, fg=self.text_colour)

    def ddpEntry_on_enter(self,event):
        self.ddpEntry.config(bg=self.active_background_colour, fg=self.active_foreground_colour)
    def ddpEntry_on_leave(self,event):
        self.ddpEntry.config(bg=self.background_colour, fg=self.text_colour)

    def sdplabel_on_enter(self,event):
        self.sdplabel.config(bg=self.active_background_colour, fg=self.active_foreground_colour)
    def sdplabel_on_leave(self,event):
        self.sdplabel.config(bg=self.button_colour, fg=self.text_colour)
        
    def ddplabel_on_enter(self,event):
        self.ddplabel.config(bg=self.active_background_colour, fg=self.active_foreground_colour)
    def ddplabel_on_leave(self, event):
        self.ddplabel.config(bg=self.button_colour, fg=self.text_colour)

    def loadbutton_on_enter(self,event):
        self.loadbutton.config(bg=self.active_background_colour, fg=self.active_foreground_colour)
    def loadbutton_on_leave(self, event):
        self.loadbutton.config(bg=self.button_colour, fg=self.text_colour)

    def loadfolderbutton_on_enter(self,event):
        self.loadfolderbutton.config(bg=self.active_background_colour, fg=self.active_foreground_colour)
    def loadfolderbutton_on_leave(self, event):
        self.loadfolderbutton.config(bg=self.button_colour, fg=self.text_colour)

    def loadpathentry_on_enter(self,event):
        self.loadpathentry.config(bg=self.active_background_colour, fg=self.active_foreground_colour)
    def loadpathentry_on_leave(self, event):
        self.loadpathentry.config(bg=self.background_colour, fg=self.text_colour)
        

    def isnumber(self, char):
        return char.isdigit()

    def closeprogram(self):
        if len(self.assigned_squarelist) != 0:
            if askokcancel("Designated but Un-Moved files, really quit?","You have destination designated, but unmoved files. (Simply cancel and Move All if you want)"):
                if hasattr(self, 'second_window') and self.second_window:
                    self.saveimagewindowgeo()
                self.close_destination_window()
                saveprefs(self.fileManager, self)
                self.destroy()
                #exit(0)
        else:
            if hasattr(self, 'second_window') and self.second_window:
                self.saveimagewindowgeo()
            self.close_destination_window()
            saveprefs(self.fileManager, self)
            self.destroy()
            #exit(0)


    def excludeshow(self):
        excludewindow = tk.Toplevel()
        excludewindow.winfo_toplevel().title(
            "Folder names to ignore, one per line. This will ignore sub-folders too.")
        excludetext = tkst.ScrolledText(excludewindow)
        for x in self.fileManager.exclude:
            excludetext.insert("1.0", x+"\n")
        excludetext.pack()
        excludewindow.protocol("WM_DELETE_WINDOW", partial(
            self.excludesave, text=excludetext, toplevelwin=excludewindow))

    def excludesave(self, text, toplevelwin):
        text = text.get('1.0', tk.END).splitlines()
        exclude = []
        for line in text:
            exclude.append(line)
        self.fileManager.exclude = exclude
        try:
            toplevelwin.destroy()
        except Exception as e:
            logging.error(f"Error in excludesave: {e}")


    def tooltiptext(self,imageobject):
        text=""
        if imageobject.dupename:
            text += "Image has Duplicate Filename!\n"
        text += "Leftclick to select this for assignment. Rightclick to open full view"
        return text
    

    def makegridsquare(self, parent, imageobj, setguidata, dest):
        frame = tk.Frame(parent, borderwidth=0, width=self.thumbnailsize, height=self.thumbnailsize, highlightthickness = 0, highlightcolor='blue', padx = 0, pady = 0,bg=self.background_colour) #unclear if width and height needed
        frame.obj = imageobj
        truncated_filename = self.truncate_text(frame, imageobj, self.textlength)
        truncated_name_var = tk.StringVar(frame, value=truncated_filename)
        frame.obj2 = truncated_name_var
        frame.grid_propagate(True)
        
        try:
            if setguidata:
                if not os.path.exists(imageobj.thumbnail):
                    self.fileManager.makethumb(imageobj)
                try:
                    #this is faster
                    img = ImageTk.PhotoImage(Image.open(imageobj.thumbnail))
                    
                except:  # Pyvips fallback
                    buffer = pyvips.Image.new_from_file(imageobj.thumbnail)
                    img = ImageTk.PhotoImage(Image.frombuffer(
                        "RGB", [buffer.width, buffer.height], buffer.write_to_memory()))
            else:
                img = imageobj.guidata['img']

            canvas = tk.Canvas(frame, width=self.thumbnailsize, 
                               height=self.thumbnailsize,bg=self.background_colour, highlightthickness=self.image_border_thickness, highlightcolor=self.image_border_selection_colour, highlightbackground = self.image_border_colour) #The gridbox color.
            tooltiptext=tk.StringVar(frame,self.tooltiptext(imageobj)) #CHECK PROFILE

            ToolTip(canvas,msg=tooltiptext.get,delay=1) #CHECK PROFILE
            frame.canvas = canvas #Not sure what does
            #Added reference for animation support. We use this to refresh the frame 1/20, 2/20..
            canvas_image_id = canvas.create_image(
                self.thumbnailsize/2+self.image_border_thickness, self.thumbnailsize/2+self.image_border_thickness, anchor="center", image=img) #If you use gridboxes, you must +1 to thumbnailsize/2, so it counteracts the highlighthickness.
            canvas.image = img #Not sure what does
            frame.canvas_image_id = canvas_image_id #Not sure what does
            
            # Create a frame for the Checkbutton to control its height
            check_frame = tk.Frame(frame, height=self.checkbox_height,bg=self.background_colour, highlightthickness=self.text_box_thickness, highlightcolor=self.text_box_selection_colour, highlightbackground=self.text_box_colour) 
            check_frame.grid(column=0, row=1, sticky="NSEW")  # Place the frame in the grid
            check_frame.grid_propagate(False)
            self.style5 = ttk.Style()
            self.style5.configure("textc.TCheckbutton",
                foreground=self.text_colour,  # Text color
                background=self.background_colour)  # Background color
            
            #Create different dest for destinations to control view better.
            if not dest:
                check = ttk.Checkbutton(check_frame, textvariable=truncated_name_var, variable=imageobj.checked, onvalue=True, offvalue=False, command=lambda: (self.uncheck_show_next(imageobj)), style="darkmode.TCheckbutton")
            else:
                check = ttk.Checkbutton(check_frame, textvariable=truncated_name_var, variable=imageobj.destchecked, onvalue=True, offvalue=False, command=lambda: (self.uncheck_show_next(imageobj)), style="darkmode.TCheckbutton")
            check.grid(sticky="NSEW")
            
            canvas.grid(column=0, row=0, sticky="NSEW")
            
            frame.rowconfigure(0, weight=4)
            frame.rowconfigure(1, weight=1)
            if(setguidata):  # save the data to the image obj to both store a reference and for later manipulation
                imageobj.setguidata(
                    {"img": img, "frame": frame, "canvas": canvas, "check": check, "show": True,"tooltip":tooltiptext})
            # anything other than rightclicking toggles the checkbox, as we want.
            canvas.bind("<Button-1>", partial(bindhandler, check, "invoke"))
            canvas.bind(
                "<Button-3>", lambda e: (self.displayimage(imageobj), self.setfocus(e))) #lambda e: (self.toggle_image_display(imageobj, e), self.setfocus(e))
            check.bind("<Button-3>", lambda e: (self.displayimage(imageobj), self.setfocus(e)))
            #make blue if only one that is blue, must remove other blue ones. blue ones are stored the gridsquare in a global list.
            #
            canvas.bind("<MouseWheel>", partial(
                bindhandler, parent, "scroll"))
            frame.bind("<MouseWheel>", partial(
                bindhandler, self.imagegrid, "scroll"))
            
            check.bind("<MouseWheel>", partial(
                bindhandler, self.imagegrid, "scroll"))
            if imageobj.moved:
                frame.configure(
                    highlightbackground="green", highlightthickness=2)
                if os.path.dirname(imageobj.path) in self.fileManager.destinationsraw:
                    color = self.fileManager.destinations[indexOf(
                        self.fileManager.destinationsraw,os.path.dirname(imageobj.path))]['color']
                    frame['background'] = color
                    canvas['background'] = color
            if imageobj.dupename:
                frame.configure(
                    highlightbackground="yellow", highlightthickness=2)
        except Exception as e:
            logging.error(e)
        return frame
    
    def uncheck_show_next(self, imageobj):
        self.current_selection_obj_flag = False
            
    #max_length must be over 3+extension or negative indexes happen.
    def truncate_text(self, frame, imageobj, max_length):
        """Truncate the text to fit within the specified max_length."""
        filename = imageobj.name.get()
        base_name, ext = os.path.splitext(filename)
        if len(filename) > max_length:
            # Subtract 3 for the ellipsis and ext for ext.
            base_name = base_name[:max_length - (3+len(ext))] + ".." + ext
            return base_name
        return base_name + ext
    #Create secondary window for image viewing
    
    def displayimage(self, imageobj):
        self.middlepane_width = self.image_display_frame.winfo_width()
        path = imageobj.path
        pass_fast_render_size = int(self.fast_render_size)
        logging.debug(f"{int(self.fast_render_size) * 1000000} converted {int(pass_fast_render_size)}")

        # Close already open windows, IF: integrated viewer option is on, BUT KEEP OPEN IF show next is on.
        if hasattr(self, 'second_window') and self.second_window and not self.show_next.get():
            self.saveimagewindowgeo()
        elif hasattr(self, 'second_window') and self.second_window and self.dock_view.get():
            self.saveimagewindowgeo()

        # This handles the middlepane viewer. This block runs if there already is something there.
        if self.dock_view.get():

            if hasattr(self, 'Image_frame'):
                #scrub the middlepane, we would do this regardless.
                if self.Image_frame:
                    self.Image_frame.closing = False
                    self.Image_frame.close_window()
                    del self.Image_frame            
            geometry = str(self.middlepane_width) + "x" + str(self.winfo_height())
            self.Image_frame = CanvasImage(self.image_display_frame, path, geometry, self.canvas_colour, imageobj, int(pass_fast_render_size), self.viewer_x_centering, self.viewer_y_centering, self.filter_mode)
            self.Image_frame.grid(row = 0, column = 0, sticky = "NSEW")
            self.Image_frame.default_delay.set(self.default_delay.get()) #tell imageframe if animating, what delays to use
            self.Image_frame.rescale(min(self.middlepane_width / self.Image_frame.imwidth, self.winfo_height() / self.Image_frame.imheight))  # Scales to the window
            self.Image_frame.center_image()
            
            logging.info("Rescaled and Centered")    

            self.current_selection_obj = imageobj
            self.current_selection_obj_flag = True

            # Logic for show next
            self.show_next_method(imageobj)
            
            return

        # Then, if imageviewer is a standalone window, we use this
        if not hasattr(self, 'second_window') or not self.second_window or not self.second_window.winfo_exists():
            
            self.second_window = tk.Toplevel() #create a new window
            second_window = self.second_window
            second_window.configure(background=self.background_colour)
            second_window.rowconfigure(0, weight=1)
            second_window.columnconfigure(0, weight=1)
            second_window.title("Image: " + path)
            second_window.geometry(self.imagewindowgeometry)
            second_window.bind("<Button-3>", self.saveimagewindowgeo)
            second_window.protocol("WM_DELETE_WINDOW", self.saveimagewindowgeo)
            second_window.obj = imageobj
            second_window.transient(self)

            # Create the initial Image_frame
        else:
            if self.show_next.get(): #just refresh the window.
                self.second_window.title("Image: " + path)
                if self.Image_frame:
                    self.Image_frame.closing = False
                    self.Image_frame.close_window()
                    del self.Image_frame
    
        geometry = self.imagewindowgeometry.split('+')[0]
        self.Image_frame = CanvasImage(self.second_window, path, geometry, self.canvas_colour, imageobj, int(pass_fast_render_size), self.viewer_x_centering, self.viewer_y_centering, self.filter_mode)
        self.Image_frame.default_delay.set(self.default_delay.get()) #tell imageframe if animating, what delays to use
        self.Image_frame.grid(sticky='nswe')  # Initialize Frame grid statement in canvasimage, Add to main window grid
        self.Image_frame.rescale(min(self.second_window.winfo_width() / self.Image_frame.imwidth, self.second_window.winfo_height() / self.Image_frame.imheight))  # Scales to the window
        self.Image_frame.center_image()

        logging.info("Rescaled and Centered")
        self.current_selection_obj = imageobj
        self.current_selection_obj_flag = True
        
        if self.show_next.get():
            for index in self.displayedlist:
                logging.debug(f"{index.obj.id} vs {imageobj.id}")
                if index.obj.id == imageobj.id:
                    logging.debug(f"victory for {index.obj.id} vs {imageobj.id}")
                    self.last_viewed_image_pos = self.displayedlist.index(index)
                    logging.debug(f"testing index {self.last_viewed_image_pos}, name {self.displayedlist[self.last_viewed_image_pos]} true imageframe name {imageobj.name.get()}")
                    if self.current_selection:
                        self.current_selection[0].canvas.configure(highlightcolor=self.image_border_selection_colour, highlightbackground = self.image_border_colour)
                        if self.templist and not self.templist[-1] == imageobj:
                            self.templist = []
                        self.current_selection = []
                    self.displayedlist[self.last_viewed_image_pos].canvas.configure(highlightbackground = self.text_box_selection_colour, highlightcolor = self.text_box_selection_colour)
                    self.current_selection.append(self.displayedlist[self.last_viewed_image_pos])
                    break

    def show_next_method(self, imageobj):
        if self.show_next.get():
                for index in self.displayedlist:
                    logging.debug(f"{index.obj.id} vs {imageobj.id}")
                    if index.obj.id == imageobj.id:
                        logging.debug(f"victory for {index.obj.id} vs {imageobj.id}")
                        self.last_viewed_image_pos = self.displayedlist.index(index)
                        logging.debug(f"testing index {self.last_viewed_image_pos}, name {self.displayedlist[self.last_viewed_image_pos]} true imageframe name {imageobj.name.get()}")
                        if self.current_selection: # restore old?
                            self.current_selection[0].canvas.configure(highlightcolor=self.image_border_selection_colour, highlightbackground = self.image_border_colour)
                            if self.templist and not self.templist[-1] == imageobj:
                                self.templist = []
                            self.current_selection = []
                        self.displayedlist[self.last_viewed_image_pos].canvas.configure(highlightbackground = self.text_box_selection_colour, highlightcolor = self.text_box_selection_colour)
                        self.current_selection.append(self.displayedlist[self.last_viewed_image_pos])
                        break

    def saveimagewindowgeo(self, event=None):
        if hasattr(self, 'second_window') and self.second_window and self.second_window.winfo_exists():
            self.Image_frame.closing = False #warns threads that they must close
            self.imagewindowgeometry = self.second_window.winfo_geometry()
            #self.checkdupename(self.second_window.obj)
            self.Image_frame.close_window()
            del self.Image_frame
            self.second_window.destroy()

    def filedialogselect(self, target, type):
        if type == "d":
            path = tkFileDialog.askdirectory()
        elif type == "f":
            d = tkFileDialog.askopenfile(initialdir=os.getcwd(
            ), title="Select Session Data File", filetypes=(("JavaScript Object Notation", "*.json"),))
            path = d.name
        if isinstance(target, tk.Entry):
            target.delete(0, tk.END)
            target.insert(0, path)

    #to recolor the colors for darkmode.
    def darken_color(self, color, factor=0.5):
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

    def guisetup(self, destinations):
        self.sortbydatecheck.destroy() #Hides the sortbydate checkbox when you search
        sdpEntry = self.sdpEntry
        ddpEntry = self.ddpEntry
        sdpEntry.config(state=tk.DISABLED)
        ddpEntry.config(state=tk.DISABLED)
        panel = self.panel
        buttonframe = self.buttonframe
        hotkeys = self.hotkeys
        for key in hotkeys:
            self.unbind_all(key)
        for x in self.buttons:
            x.destroy()  # clear the gui
        
        panel.destroy()
        guirow = 1
        guicol = 0
        itern = 0
        smallfont = tkfont.Font(family='Helvetica', size=10)
        columns = 1
        
        if len(destinations) > int((self.leftui.winfo_height()/35)-2):
            columns=2
            buttonframe.columnconfigure(1, weight=1)
        if len(destinations) > int((self.leftui.winfo_height()/15)-4):
            columns = 3
            buttonframe.columnconfigure(2, weight=1)
        original_colors = {} #Used to return their color when hovered off
        for x in destinations:
            color = x['color']
            if x['name'] != "SKIP" and x['name'] != "BACK":
                if(itern < len(hotkeys)):
                    newbut = tk.Button(buttonframe, text=hotkeys[itern] + ": " + x['name'], command=partial(
                        self.fileManager.setDestination, x, {"widget": None}), anchor="w", wraplength=(self.leftui.winfo_width()/columns)-1)
                    random.seed(x['name'])
                    self.bind_all(hotkeys[itern], partial(
                        self.fileManager.setDestination, x))
                    fg = self.text_colour
                    if luminance(color) == 'light':
                        fg = self.text_colour
                    newbut.configure(bg=color, fg=fg)
                    original_colors[newbut] = {'bg': color, 'fg': fg}  # Store both colors
                    if(len(x['name']) >= 13):
                        newbut.configure(font=smallfont)
                else:
                    newbut = tk.Button(buttonframe, text=x['name'],command=partial(
                        self.fileManager.setDestination, x, {"widget": None}), anchor="w")
                itern += 1

            newbut.config(font=("Courier", 12), width=int(
                (self.leftui.winfo_width()/12)/columns), height=1)
            ToolTip(newbut,msg="Rightclick to show images assigned to this destination",delay=1)
            if len(x['name']) > 20:
                newbut.config(font=smallfont)
            newbut.dest = x
            if guirow > ((self.leftui.winfo_height()/35)-2):
                guirow = 1
                guicol += 1
            newbut.grid(row=guirow, column=guicol, sticky="nsew")
            newbut.bind("<Button-3>", partial(self.showthisdest, x))

            self.buttons.append(newbut)
            guirow += 1
            # Store the original colors for all buttons
            original_colors[newbut] = {'bg': newbut.cget("bg"), 'fg': newbut.cget("fg")}  # Store both colors

            # Bind hover events for each button
            newbut.bind("<Enter>", lambda e, btn=newbut: btn.config(bg=self.darken_color(original_colors[btn]['bg']), fg='white'))
            newbut.bind("<Leave>", lambda e, btn=newbut: btn.config(bg=original_colors[btn]['bg'], fg=original_colors[btn]['fg']))  # Reset to original colors

        # For SKIP and BACK buttons, set hover to white
        for btn in self.buttons:
            if btn['text'] == "SKIP (Space)" or btn['text'] == "BACK":
                btn.bind("<Enter>", lambda e, btn=btn: btn.config(bg=self.text_colour, fg=self.background_colour))
                btn.bind("<Leave>", lambda e, btn=btn: btn.config(bg=self.button_colour, fg=self.text_colour))  # Reset to original colors
            self.entryframe.grid_remove()
        # options frame
        optionsframe = tk.Frame(self.leftui,bg=self.background_colour)
        
        valcmd = self.register(self.isnumber)
        self.squaresperpageentry = tk.Entry(
            optionsframe, textvariable=self.squaresperpage, takefocus=False, background=self.background_colour, foreground=self.text_colour)
        if self.squaresperpage.get() < 0: #this wont let you save -1
            self.squaresperpage.set(1)
        ToolTip(self.squaresperpageentry,delay=1,msg="How many more images to add when Load Images is clicked")
        for n in range(0, itern):
            self.squaresperpageentry.unbind(hotkeys[n])
        self.addpagebut = tk.Button(
            optionsframe, text="Load More Images", command=self.load_more_images,bg=self.background_colour, fg=self.text_colour)
        
        ToolTip(self.addpagebut,msg="Add another batch of files from the source folders.", delay=1)
        

        self.squaresperpageentry.grid(row=1, column=0, sticky="EW",)
        
        self.addpagebut.grid(row=1, column=1, sticky="EW")
        self.addpagebutton = self.addpagebut
    
        style3 = ttk.Style()
        style3.configure("darkmode1.TCheckbutton", background=self.background_colour, foreground=self.text_colour, highlightthickness = 0)

        custom_buttons_frame  = tk.Frame(self.leftui,bg=self.background_colour)
        custom_buttons_frame.grid(row = 1, column = 0, sticky = "ew")
        custom_buttons_frame.columnconfigure(0, weight = 1)
        custom_buttons_frame.columnconfigure(1, weight = 1)
        custom_buttons_frame.columnconfigure(2, weight = 1)
        custom_buttons_frame.columnconfigure(3, weight = 1)
        custom_buttons_frame.columnconfigure(4, weight = 1)

        self.default_delay_button = ttk.Checkbutton(custom_buttons_frame, text="Default speed", variable=self.default_delay, onvalue=True, offvalue=False, command=lambda: (self.default_delay_buttonpress(), self.default_delay) ,style="darkmode1.TCheckbutton")
        self.default_delay_button.grid(row=0, column=0, sticky="ew")      
        self.show_next_button = ttk.Checkbutton(custom_buttons_frame, text="Show next", variable=self.show_next, onvalue=True, offvalue=False, command=lambda: self.show_next ,style="darkmode1.TCheckbutton")
        self.show_next_button.grid(row=0, column=1, sticky="ew")
        self.dock_view_button = ttk.Checkbutton(custom_buttons_frame, text="Dock view", variable=self.dock_view, onvalue=True, offvalue=False, command=lambda: (self.dock_view_buttonpress()) ,style="darkmode1.TCheckbutton")
        self.dock_view_button.grid(row=0, column=2, sticky="ew")
        self.dock_side_button = ttk.Checkbutton(custom_buttons_frame, text="Dock side", variable=self.dock_side, onvalue=True, offvalue=False, command=lambda: (self.dock_side_buttonpress()) ,style="darkmode1.TCheckbutton")
        self.dock_side_button.grid(row=0, column=3, sticky="ew")

        if self.extra_buttons:
            
            self.centering_option = tk.StringVar()
            self.centering_option.trace_add("write", self.centering_options_method)

            if self.viewer_x_centering and self.viewer_y_centering:
                self.centering_option.set("Center")
            elif self.viewer_x_centering and not self.viewer_y_centering:
                self.centering_option.set("Only x centering")
            elif not self.viewer_x_centering and self.viewer_y_centering:
                self.centering_option.set("Only y centering")
            else:
                self.centering_option.set("No centering")


            options1 = ["Center", "Only x centering", "Only y centering", "No centering"]
            self.centering_options_button = tk.OptionMenu(custom_buttons_frame, self.centering_option, *options1)
            self.centering_options_button.config(bg=self.background_colour, fg=self.text_colour,activebackground=self.active_background_colour, activeforeground=self.active_foreground_colour)

            self.centering_options_button.grid(row=0, column=4, sticky="ew")



        # save button
        self.savebutton = tk.Button(optionsframe,text="Save Session",command=partial(self.fileManager.savesession,True),bg=self.button_colour, fg=self.text_colour)
        ToolTip(self.savebutton,delay=1,msg="Save this image sorting session to a file, where it can be loaded at a later time. Assigned destinations and moved images will be saved.")
        self.savebutton.grid(column=0,row=0,sticky="ew")
        self.moveallbutton = tk.Button(
            optionsframe, text="Move All", command=self.fileManager.moveall,bg=self.button_colour, fg=self.text_colour)
        self.moveallbutton.grid(column=1, row=2, sticky="EW")
        ToolTip(self.moveallbutton,delay=1,msg="Move all images to their assigned destinations, if they have one.")
        self.clearallbutton = tk.Button(
            optionsframe, text="Clear Selection", command=self.fileManager.clear,bg=self.button_colour, fg=self.text_colour)
        ToolTip(self.clearallbutton,delay=1,msg="Clear your selection on the grid and any other windows with checkable image grids.")
        self.clearallbutton.grid(row=0, column=1, sticky="EW")
        
        style1 = ttk.Style()
        style1.configure('darkmode.TMenubutton', background=self.button_colour, foreground=self.text_colour, borderwidth = 2, arrowcolor = "grey")

        style1.map('darkmode.TMenubutton',
           background=[('active', self.active_background_colour)],  # Clicked background
           foreground=[('active', self.active_foreground_colour)])  # Clicked text color
        

        options = ["Show Unassigned", "Show Assigned", "Show Moved", "Show Animated"] #"Show All"
        option_menu = tk.OptionMenu(optionsframe, self.variable, *options)
        self.variable.set(options[0])
        option_menu.grid(row = 2, column = 0, sticky = "EW")
        option_menu.config(bg=self.background_colour, fg=self.text_colour,activebackground=self.active_background_colour, activeforeground=self.active_foreground_colour)

        optionsframe.columnconfigure(0, weight=1)
        optionsframe.columnconfigure(1, weight=3)

        self.optionsframe = optionsframe
        self.optionsframe.grid(row=0, column=0, sticky="ew")
        self.bind_all("<Button-1>", self.setfocus)

        self.clearallbutton.bind("<Enter>", self.clearallbutton_on_enter)
        self.clearallbutton.bind("<Leave>", self.clearallbutton_on_leave)

        self.addpagebut.bind("<Enter>", self.addpagebut_on_enter)
        self.addpagebut.bind("<Leave>", self.addpagebut_on_leave)

        self.moveallbutton.bind("<Enter>", self.moveallbutton_on_enter)
        self.moveallbutton.bind("<Leave>", self.moveallbutton_on_leave)

        self.savebutton.bind("<Enter>", self.savebutton_on_enter)
        self.savebutton.bind("<Leave>", self.savebutton_on_leave)

        self.squaresperpageentry.bind("<Enter>", self.squaresperpageentry_on_enter)
        self.squaresperpageentry.bind("<Leave>", self.squaresperpageentry_on_leave)

    def default_delay_buttonpress(self):
        if hasattr(self, 'Image_frame') and self.Image_frame:
            self.Image_frame.default_delay.set(self.default_delay.get())

    def dock_view_buttonpress(self):
        self.middlepane_width = self.image_display_frame.winfo_width()
        self.image_display_frame.configure(width = self.middlepane_width)
        self.current_selection_obj = None
        self.current_selection_obj_flag = False
        if self.started_not_integrated:
            self.toppane.forget(self.image_display_frame)
            self.started_not_integrated = False

        if self.dock_view.get():
            if hasattr(self, 'second_window') and self.second_window and self.second_window.winfo_exists(): #the button attempts to close the standalone viewer
                self.saveimagewindowgeo()
                print("This message only if second window has closed")
                if self.show_next.get():
                    print("This message only success")
                    #if closing window and autodisplay on we want to pass the image to the integrated viewer
                    imageobj = self.current_selection[-1].obj
                    self.displayimage(imageobj)
            self.toppane.forget(self.imagegridframe)
            if self.dock_side.get():                    
                self.toppane.add(self.image_display_frame, weight = 0) #readd the middpane
                self.toppane.add(self.imagegridframe, weight = 1) #readd imagegrid
            else:
                self.toppane.add(self.imagegridframe, weight = 1) #readd imagegrid
                self.toppane.add(self.image_display_frame, weight = 0) #readd the middpane
                
            
        
        # Forget, we want to use standalone viewer now.
        else:
            try:
                self.toppane.forget(self.image_display_frame)
                if hasattr(self, 'Image_frame'):
                    #scrub the middlepane, we would do this regardless.
                    if self.Image_frame:
                        self.Image_frame.closing = False
                        self.Image_frame.close_window()
                        del self.Image_frame
                        imageobj = self.current_selection[-1].obj
                        self.displayimage(imageobj)
            except Exception as e:
                self.current_selection_obj = None
                self.current_selection_obj_flag = False
    
    def dock_side_buttonpress(self):
        self.middlepane_width = self.image_display_frame.winfo_width()
        self.image_display_frame.configure(width = self.middlepane_width)
        if self.dock_view.get():
            self.toppane.forget(self.image_display_frame)
            self.toppane.forget(self.imagegridframe)
            if self.dock_side.get():
                if self.force_scrollbar:

                    self.vbar.grid(row=0, column=1, sticky='ns')
                    self.imagegrid.configure(yscrollcommand=self.vbar.set)
                    self.imagegrid.grid(row=0, column=0, sticky="NSEW")  

                    self.imagegridframe.columnconfigure(1, weight=0)
                    self.imagegridframe.columnconfigure(0, weight=1)
                self.toppane.add(self.image_display_frame, weight = 0) #readd the middpane
                self.toppane.add(self.imagegridframe, weight = 1) #readd imagegrid
            else:
                if self.force_scrollbar:

                    self.vbar.grid(row=0, column=0, sticky='ns')
                    self.imagegrid.configure(yscrollcommand=self.vbar.set)
                    self.imagegrid.grid(row=0, column=1, sticky="NSEW") 

                    self.imagegridframe.columnconfigure(0, weight=0)
                    self.imagegridframe.columnconfigure(1, weight=1)
                                
                self.toppane.add(self.imagegridframe, weight = 1) #readd imagegrid
                self.toppane.add(self.image_display_frame, weight = 0) #readd the middpane


    def squaresperpageentry_on_enter(self,event):
        self.squaresperpageentry.config(bg=self.active_background_colour, fg=self.active_foreground_colour)
    def squaresperpageentry_on_leave(self, event):
        self.squaresperpageentry.config(bg=self.background_colour, fg=self.text_colour)

    def clearallbutton_on_enter(self,event):
        self.clearallbutton.config(bg=self.active_background_colour, fg=self.active_foreground_colour)
    def clearallbutton_on_leave(self, event):
        self.clearallbutton.config(bg=self.button_colour, fg=self.text_colour)

    def addpagebut_on_enter(self,event):
        self.addpagebut.config(bg=self.active_background_colour, fg=self.active_foreground_colour)
    def addpagebut_on_leave(self, event):
        self.addpagebut.config(bg=self.button_colour, fg=self.text_colour)
    
    def moveallbutton_on_enter(self,event):
        self.moveallbutton.config(bg=self.active_background_colour, fg=self.active_foreground_colour)
    def moveallbutton_on_leave(self, event):
        self.moveallbutton.config(bg=self.button_colour, fg=self.text_colour)
    
    def savebutton_on_enter(self,event):
        self.savebutton.config(bg=self.active_background_colour, fg=self.active_foreground_colour)
    def savebutton_on_leave(self, event):
        self.savebutton.config(bg=self.button_colour, fg=self.text_colour)

    
    def centering_options_method(self, *args):
        selected_option = self.centering_option.get()
        "Center", "Only x centering", "Only y centering", "No centering"
        if selected_option == "Center":
            self.viewer_x_centering = True
            self.viewer_y_centering = True
        if selected_option == "Only x centering":
            self.viewer_x_centering = True
            self.viewer_y_centering = False
        if selected_option == "Only y centering":
            self.viewer_x_centering = False
            self.viewer_y_centering = True
        if selected_option == "No centering":
            self.viewer_x_centering = False
            self.viewer_y_centering = False
        self.displayimage(self.current_selection_obj)


    def on_option_selected(self, *args):
        selected_option = self.variable.get()
        if selected_option == "Show Unassigned":
            self.show_unassigned.set(False)
            self.clicked_show_unassigned()
        elif selected_option == "Show Assigned":
            self.clicked_show_assigned()
        elif selected_option == "Show Moved":
            self.clicked_show_moved()
        elif selected_option == "Show Animated":
            self.clicked_show_animated()
        #elif selected_option == "Show All":
        #    self.clicked_show_all()

    def setfocus(self, event):
        event.widget.focus_set()

    def displaygrid(self, imagelist, range): #dummy to handle sortimages calls for now...
        number_of_animated = 0 #Just to tell user how many gifs and webps are being attempted to load
        for i in range:
            gridsquare = self.makegridsquare(self.imagegrid, imagelist[i], True, False)
            self.gridsquarelist.append(gridsquare)
            if not gridsquare.obj.moved:
                self.unassigned_squarelist.append(gridsquare)
                gridsquare.obj.isvisible = True

            elif gridsquare.obj.moved:
                self.moved_squarelist.append(gridsquare)
                gridsquare.obj.isvisible = False

            if gridsquare.obj.isanimated: # If the imageobj is a gif or webp, we render the square
                # Static fallback image in case we fail to animate.
                gridsquare.canvas_window = self.imagegrid.window_create("insert", window=gridsquare, padx=self.gridsquare_padx, pady=self.gridsquare_pady)
                self.displayedlist.append(gridsquare)
                threading.Thread(target=self.fileManager.load_frames, args=(gridsquare,)).start()
                number_of_animated += 1

            else: # Normal image
                gridsquare.canvas_window = self.imagegrid.window_create("insert", window=gridsquare, padx=self.gridsquare_padx, pady=self.gridsquare_pady)
                self.displayedlist.append(gridsquare)

        logging.info(f"Trying to animate {number_of_animated} pictures.")
        self.refresh_rendered_list()
        self.start_gifs()
    
    def start_gifs(self):
        logging.debug("starting gifs, if you see two of these, something is wrong.") #should only run once. Otherwise two processes try to change the frame leading to speed issues.
        # Check the visible list for pictures to animate.
        self.running = []
        current_squares = self.displayedlist
        load_these = []
        for i in current_squares: #could let in unanimated... because threading. check for frames?
            if i.obj.isanimated and i.obj.isvisible:
                if i not in [tup[0] for tup in self.running]: # not already displayed
                    load_these.append(i)
        for a in load_these:
            self.lazy_load(a)
    
    def lazy_load(self, i):
        try:
            if i.obj.frames and i.obj.index != i.obj.framecount and i.obj.lazy_loading:
                if len(i.obj.frames) > i.obj.index:
                    logging.debug(f"Lazy frame to canvas {i.obj.index}/{i.obj.framecount}")
                    i.canvas.itemconfig(i.canvas_image_id, image=i.obj.frames[i.obj.index])

                    if self.default_delay.get():
                        logging.debug(f"{i.obj.name.get()}: {i.obj.index}/{len(i.obj.frames)}, default: {i.obj.delay}: frametime : {i.obj.frametimes[i.obj.index]} ")
                        i.canvas.after(i.obj.delay, lambda: self.run_multiple(i)) #run again.
                    else:
                        logging.debug(f"{i.obj.name.get()}: {i.obj.index}/{len(i.obj.frames)}, default: {i.obj.delay}: frametime : {i.obj.frametimes[i.obj.index]} ")
                        i.canvas.after(i.obj.frametimes[i.obj.index], lambda: self.run_multiple(i)) #or a.obj.delay

                else: #wait for frame to load.
                    logging.debug("Buffering")
                    i.canvas.after(i.obj.delay, lambda: self.lazy_load(i))
            else:
                if not i.obj.lazy_loading and i.obj.frames: #if all loaded
                    logging.debug("Moving to animate_loop method")
                    x = False
                    self.animation_loop(i, x)
                else: # 0 frames?
                    logging.debug("0 frames")
                    i.canvas.after(i.obj.delay, lambda: self.lazy_load(i))
        except Exception as e:
            logging.error(f"Lazy load couldn't process the frame: {e}. Likely because of threading.")

    def run_multiple(self, i):
        i.obj.index = (i.obj.index + 1) % i.obj.framecount
        self.lazy_load(i)

    #Post. animate a frame for each picture in the list and run this again.
    def animation_loop(self, i,x, random_id = None): #frame by frame as to not freeze the main one XD
        #One time check
        if x == False:
            if i not in self.running:
                random_id = random.randint(1,1000000)
                self.running.append((i, random_id))
            else:
                return
            
        i.canvas.itemconfig(i.canvas_image_id, image=i.obj.frames[i.obj.index]) #change the frame
        if(i.obj.isvisible and random_id in [tup[1] for tup in self.running]): #and i in self.running
            x = True
            if self.default_delay.get():
                logging.debug(f"Loop frame to canvas {i.obj.index}/{len(i.obj.frames)} ms: {i.obj.delay}")
                i.canvas.after(i.obj.delay, lambda: self.run_multiple2(i,x, random_id)) #run again.
            else:
                logging.debug(f"Loop frame to canvas {i.obj.index}/{len(i.obj.frames)} ms: {i.obj.frametimes[i.obj.index]}")
                i.canvas.after(i.obj.frametimes[i.obj.index], lambda: self.run_multiple2(i,x, random_id)) #run again.""
        else:
            logging.debug(f"ended animation for {i.obj.name.get()}")
            pass

    def run_multiple2(self, i, x, random_id):
        i.obj.index = (i.obj.index + 1) % i.obj.framecount

        self.animation_loop(i, x, random_id)
    
    #This renders the given squarelist.
    def render_squarelist(self, squarelist):
        current_squares = self.displayedlist.copy()

        if self.clear_all:
            for gridsquare in current_squares:
                if gridsquare in squarelist:
                    self.imagegrid.window_configure(gridsquare, window="")
                    self.displayedlist.remove(gridsquare)
                    gridsquare.obj.isvisible = False
            
            self.clear_all = False

        #delete
        for gridsquare in current_squares:
            if gridsquare not in squarelist:
                self.imagegrid.window_configure(gridsquare, window="")
                self.displayedlist.remove(gridsquare)
                gridsquare.obj.isvisible = False
                
        # Readd
        if self.show_assigned.get():
            for gridsquare in self.render_refresh:
                self.imagegrid.window_configure(gridsquare, window="")
                gridsquare.canvas_window = self.imagegrid.window_create(
                            "1.0", window=gridsquare)
                gridsquare.obj.isvisible = True
                self.displayedlist.append(gridsquare)
            self.render_refresh = []
            

        # Addd
        for gridsquare in squarelist:
            if gridsquare not in self.displayedlist:
                if self.show_assigned.get():
                    gridsquare.canvas_window = self.imagegrid.window_create(
                        "1.0", window=gridsquare)
                else:
                    gridsquare.canvas_window = self.imagegrid.window_create(
                        "insert", window=gridsquare)
                self.displayedlist.append(gridsquare)
                gridsquare.obj.isvisible = True

    def refresh_rendered_list(self):
        current_list = None
        if self.show_unassigned.get():
            
            if self.show_animated.get():
                unassigned_animated = [item for item in self.unassigned_squarelist if item.obj.isanimated]
                self.render_squarelist(unassigned_animated)
                current_list = unassigned_animated
            else:
                self.render_squarelist(self.unassigned_squarelist)
                current_list = self.unassigned_squarelist
           
        elif self.show_assigned.get():
            self.render_squarelist(self.assigned_squarelist)
            current_list = self.assigned_squarelist
          
        elif self.show_moved.get():
            self.render_squarelist(self.moved_squarelist)
            current_list = self.moved_squarelist 
        
        #Debugging
        #print("###############################################")
        #a1 = len(self.unassigned_squarelist)
        #a2 = len(self.assigned_squarelist)
        #a3 = len(self.moved_squarelist)
        #print(f"C:{len(current_list)}:G:{len(self.gridsquarelist)}:U:{a1}:A:{a2}:M:{a3}:D:{len(self.displayedlist)}")
        #print(f"U:{self.show_unassigned.get()}:A:{self.show_assigned.get()}:M:{self.show_moved.get()}")
    
    def clicked_show_unassigned(self): #Turn you on.
        if not self.fix_flag:
            if self.show_unassigned.get() == False:
                self.show_assigned.set(False)
                self.show_moved.set(False)
                self.show_unassigned.set(True)
                self.show_animated.set(False)
                self.clear_all = True
                self.running = []
                self.refresh_rendered_list()
                self.start_gifs()
        else:
            self.show_unassigned.set(True)
            self.fix_flag = False

    def clicked_show_assigned(self):
        if self.show_assigned.get() == False:
            self.show_unassigned.set(False)
            self.show_moved.set(False)
            self.show_assigned.set(True)
            self.show_animated.set(False)
            self.clear_all = True
            self.running = []
            self.refresh_rendered_list()
            self.start_gifs()
            
    def clicked_show_moved(self):
        if self.show_moved.get() == False:
            self.show_assigned.set(False)
            self.show_unassigned.set(False)
            self.show_moved.set(True)
            self.show_animated.set(False)
            self.clear_all = True
            self.running = []
            self.refresh_rendered_list()
            self.start_gifs()

    def clicked_show_animated(self):
        if self.show_animated.get() == False:
            self.show_assigned.set(False)
            self.show_unassigned.set(True)
            self.show_moved.set(False)
            self.show_animated.set(True)
            self.clear_all = True
            self.refresh_rendered_list()
            self.running = []
            self.start_gifs()

    def showthisdest(self, dest, *args):
        #If a destination window is already open, just update it.
        self.dest = dest['path']
        if not hasattr(self, 'destwindow') or not self.destwindow or not self.destwindow.winfo_exists():
            #Make new window
            self.destwindow = tk.Toplevel()
            self.destwindow.columnconfigure(0, weight=1)
            self.destwindow.rowconfigure(0, weight=1)     
            self.destwindow.winfo_toplevel().title("Files designated for " + dest['path'])
            self.destwindow.bind("<Button-3>", self.close_destination_window)
            self.destwindow.protocol("WM_DELETE_WINDOW", self.close_destination_window)        
            self.destwindow.geometry(str(int(self.winfo_screenwidth() * 0.80)) + "x" + str(self.winfo_screenheight() - 120) + "+365+60")
            self.destwindow.transient(self)
            if self.save != 0:
                try:
                    self.destwindow.geometry(self.save)
                except Exception as e:
                    logging.error(f"Couldn't load destwindow geometry")
            self.destgrid = tk.Text(self.destwindow, wrap='word', borderwidth=0, highlightthickness=0, state="disabled", background=self.background_colour)
            self.destgrid.grid(row=0, column=0, sticky="NSEW")
            #scrollbars
            vbar = tk.Scrollbar(self.destwindow, orient='vertical',command=lambda *args: throttled_yview(self.destgrid, *args))

            #vbar = tk.Scrollbar(self.destwindow, orient='vertical', command=self.destgrid.yview)
            vbar.grid(row=0, column=1, sticky='ns')
            self.destgrid['yscrollcommand'] = vbar.set  # Link scrollbar to text widget
        else:
            pass
            
        # Refresh the destinations and set the active window
        self.filtered_images = []
        self.refresh_destinations()

    def close_destination_window(self, event=None):
        if event:
            for square in self.dest_squarelist:
                if square.winfo_x() <= event.x <= square.winfo_x() + square.winfo_width() and \
                   square.winfo_y() <= event.y <= square.winfo_y() + square.winfo_height():
                    logging.debug("Click inside a square, not closing.")
                    return  # Click is inside a square, do not close
            
        try:
            if hasattr(self, 'destwindow'):
                self.save = self.destwindow.winfo_geometry()
                self.destgrid.destroy()
                del self.destgrid
                self.destwindow.destroy()
                self.destwindow = None
                del self.destwindow
                self.dest_squarelist = []
                self.filtered_images = []
                self.queue = []
                
                logging.debug(f"Destination window destroyed")
        except Exception as e:
            logging.debug(f"Destination window was not open: {e}")
    
    def refresh_destinations(self):
        #so when view changes, squarelist is updated, the 
        if hasattr(self, 'destgrid') and self.destgrid: #If a destination window is open
            destgrid = self.destgrid
            dest_path = self.dest            
            #make a list of destination pics to compare current squarelist against.
            #to rollback to this just delete self.combined_squarelists from sortimages.
            combined_squarelist = self.assigned_squarelist + self.moved_squarelist
            #combined_squarelist = self.combined_squarelist
            temp = False
            #here jut replace filtere_images with unique dest list.
            #what if just 1 list like this, add only if dest is same. So we generate it once per switch ,then just add to it.
            if not self.filtered_images:
                temp = True
                self.filtered_images = [gridsquare.obj for gridsquare in combined_squarelist if gridsquare.obj.dest == dest_path]
            filtered_images = self.filtered_images
    

            #this basically regenerates squares that we want to change place in the gridview.
            
            try:
                for gridsquare in self.destgrid_updateslist: #the list to remove.
                    if gridsquare.obj in filtered_images:
                        try: #remove old placement
                            self.destgrid.window_configure(gridsquare, window="")
                        except Exception as e:
                            logging.error(f"Error configuring window for image {gridsquare.obj}: {e}")
                        self.dest_squarelist.remove(gridsquare) ##remove pic from squarelist  so it is generated again!
                        self.queue.append(gridsquare) #this adds to the queue to be generated along new ones.
                        self.destgrid_updateslist.remove(gridsquare) # remove from updateslist as the task is compelte
            except Exception as e:
                logging.error(f"Erron in refresh_destinations {e}")

            # Add new images to the destination grid #-- we can still add a changed_ list here.
            #basically at initial load, check the whole list, then subsequently, we can only check the changed.
            #initial load filtere_images

            #updates only queue?
            if temp:
                for img in filtered_images:
                    if not any(gridsquare.obj == img for gridsquare in self.dest_squarelist):
                        new_frame = self.makegridsquare(self.destgrid, img, False, True)
                        color = next((d['color'] for d in self.fileManager.destinations if d['path'] == img.dest), None)
                        if color:
                            new_frame['background'] = color
                            new_frame.children['!canvas']['background'] = color  # Assuming the canvas is the first child
                            #if luminance(color) == 'light':
                            #    self.style5.configure("textc.TCheckbutton", foreground="black", background=color, selectcolor="grey")
                            #else:
                             #   self.style5.configure("textc.TCheckbutton", foreground="white", background=color, selectcolor="grey")
                        canvas_window_id = self.destgrid.window_create("1.0", window=new_frame)
                        new_frame.canvas_id = canvas_window_id
                        self.dest_squarelist.append(new_frame)
                        new_frame.obj.isvisibleindestination = True
            else:
                for square in self.queue:
                    new_frame = self.makegridsquare(self.destgrid, square.obj, False, True)
                    color = next((d['color'] for d in self.fileManager.destinations if d['path'] == square.obj.dest), None)
                    if color:
                        new_frame['background'] = color
                        new_frame.children['!canvas']['background'] = color  # Assuming the canvas is the first child
                        #if luminance(color) == 'light':
                        #    self.style5.configure("textc.TCheckbutton", foreground="black", background=color, selectcolor="grey")
                        #else:
                         #   self.style5.configure("textc.TCheckbutton", foreground="white", background=color, selectcolor="grey")
                    canvas_window_id = self.destgrid.window_create("1.0", window=new_frame)
                    new_frame.canvas_id = canvas_window_id
                    self.dest_squarelist.append(new_frame)
                    new_frame.obj.isvisibleindestination = True
                    self.queue.remove(square)
            # Remove images no longer present #this can be done like filtered list too. just record all deletes.
            to_remove = [] #OPTIMIZE
            for gridsquare in self.dest_squarelist:
                if gridsquare.obj not in filtered_images:
                    try:
                        self.destgrid.window_configure(gridsquare, window="")
                    except Exception as e:
                        logging.error(f"Error configuring window for image {gridsquare.obj}: {e}")
                    to_remove.append(gridsquare)

            # Remove gridsquares from the list
            for gridsquare in to_remove:
                self.dest_squarelist.remove(gridsquare)
                gridsquare.obj.isvisibleindestination = False
            self.start_gifs_indestinations()

    def start_gifs_indestinations(self):
        # Check if images in the current destination view are animated or not. 
        current_index = 0
        for i in self.dest_squarelist:
            if i.obj.isanimated and i.obj.isvisibleindestination: # This prevents the same .gif or .webp having two or more loops at the same time, causing the index counting to double in speed.  
                current_index = 0
                x = False
                self.animation_loop_indestinations(i, current_index, x)
    
    def animation_loop_indestinations(self, i, index, x):  # Frame by frame animation
        if x == False:
            if i not in self.track_animated:
                self.track_animated.append(i)
                logging.debug(f"appended: {len(self.track_animated)} {self.track_animated}")
            else:
                logging.debug("rejected")
                return
        logging.debug(f"Loading frames: {index}/{i.obj.framecount} :Delay: {i.obj.delay}")
        i.canvas.itemconfig(i.canvas_image_id, image=i.obj.frames[index])  # Change the frame
        
        if(i.obj.isvisibleindestination):
            x = True
            if self.default_delay.get():
                logging.debug(f"{i.obj.name.get()}: {index}/{len(i.obj.frames)}, delay: {i.obj.delay}")
                i.canvas.after(i.obj.delay, lambda: self.run_multiple3(i,index,x)) #run again.
            else:
                logging.debug(f"{i.obj.name.get()}: {index}/{len(i.obj.frames)}, delay: {i.obj.frametimes[index]}")
                i.canvas.after(i.obj.frametimes[index], lambda: self.run_multiple3(i,index,x)) #run again.
        else:
            logging.debug("dest animations ended")
            pass
    
    def run_multiple3(self, i, index, x):
        index = (index + 1) % i.obj.framecount
        self.animation_loop_indestinations(i,index,x)

    def load_more_images(self, *args):
        filelist = self.fileManager.imagelist
        if len(self.gridsquarelist) < len(filelist):
            listmax = min(len(self.gridsquarelist) +
                          self.squaresperpage.get(), len(filelist))
            ran = range(len(self.gridsquarelist), listmax)
            sublist = filelist[ran[0]:listmax]
            self.fileManager.generatethumbnails(sublist)
            self.displaygrid(self.fileManager.imagelist, ran)            
        else:
            self.addpagebutton.configure(text="No More Images!",background="#DD3333")

def throttled_yview(widget, *args):
    """Throttle scroll events for both MouseWheel and Scrollbar slider"""
    global last_scroll_time

    now = time.time()

    if last_scroll_time is None or (now - last_scroll_time) > 0.025:  # 100ms throttle
        last_scroll_time = now
        widget.yview(*args)

# Throttled scrollbar callback
def throttled_scrollbar(*args):
    throttled_yview(args[0], 'yview', *args[1:])

def bindhandler(*args):
    widget = args[0]
    command = args[1]
    if command == "scroll":
        widget.yview_scroll(-1*floor(args[2].delta/120), "units")
    elif command == "invoke":
        widget.invoke()
