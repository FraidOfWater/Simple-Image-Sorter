import os
import time
import pyvips
import tkinter as tk
import logging
import random
from math import floor,sqrt,ceil
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

logger = logging.getLogger("GUI")
logger.setLevel(logging.WARNING)  # Set to the lowest level you want to handle

handler = logging.StreamHandler()
handler.setLevel(logging.WARNING)

formatter = logging.Formatter('%(levelname)s - %(name)s - %(message)s')
handler.setFormatter(formatter)

logger.addHandler(handler)

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

def darken_color(color, factor=0.5): #Darken a given color by a specified factor
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

class GUIManager(tk.Tk):
    def __init__(self, fileManager) -> None:
        super().__init__()
        self.fileManager = fileManager

        #DEFAULT VALUES FOR PREFS.JSON. This is essentially the preference file the program creates at the very start.
        #paths
        self.source_folder = ""
        self.destination_folder = ""
        self.sessionpathvar = tk.StringVar()

        #Preferences
        self.thumbnailsize = 256
        self.max_text_length = 34 # Maximum length allowed for filenames. #must use square or canvas to limit text length.
        self.hotkeys = "123456qwerty7890uiopasdfghjklzxcvbnm"
        self.extra_buttons = True
        self.force_scrollbar = True
        self.interactive_buttons = True # Color change on hover
        self.page_mode = False # Scroll a whole page or no?
        self.flicker_free_dock_view = True
        #Technical preferences
        self.filter_mode =  "BILINEAR"
        self.fast_render_size = 5 # Size at which we start to buffer the image to load the displayimage faster. We use NEAREST, then when LANCZOS is ready, we swap it to that.
        #threads # Exlusively for fileManager
        #autosave # Exlusively for fileManager

        #Customization
        self.checkbox_height = 25
        self.gridsquare_padx = 2
        self.gridsquare_pady = 2
        self.text_box_thickness = 0
        self.image_border_thickness = 1
        self.text_box_colour =                  "white"
        self.text_box_selection_colour  =       "blue"
        self.imageborder_default_colour =       "white"
        self.imageborder_selected_colour =      "blue"
        self.imageborder_locked_colour =        "yellow"

        self.actual_gridsquare_width = self.thumbnailsize + self.gridsquare_padx #+ self.image_border_thickness + self.text_box_thickness
        self.actual_gridsquare_height = self.thumbnailsize + self.gridsquare_pady + self.checkbox_height

        #Window colours
        self.background_colour =        'black'
        self.text_colour =              'white'
        self.canvas_colour =            'black'
        self.grid_background_colour =   'black'
        self.active_background_colour = 'white'
        self.active_text_colour =       'black'
        self.button_colour =            'black'
        self.pane_divider_colour =      'grey'

        #GUI CONTROLLED PREFRENECES
        self.squaresperpage = tk.IntVar()
        self.sortbydatevar = tk.BooleanVar()
        self.default_delay = tk.BooleanVar()    # Whether to use global delay from a gif or a per frame delay.
        self.viewer_x_centering = True
        self.viewer_y_centering = True
        self.show_next = tk.BooleanVar()
        self.dock_view = tk.BooleanVar()
        self.dock_side = tk.BooleanVar()
        self.squaresperpage.set(120)
        self.default_delay.set(True)
        self.show_next.set(True)
        self.dock_view.set(True)
        self.dock_side.set(True)
        
        #Default window positions and sizes
        self.main_geometry = (str(self.winfo_screenwidth()-5)+"x" + str(self.winfo_screenheight()-120)+"+0+60")
        self.viewer_geometry = str(int(self.winfo_screenwidth()*0.80)) + "x" + str(self.winfo_screenheight()-120)+"+365+60"
        self.destpane_geometry = 0
        self.leftpane_width = 363
        self.middlepane_width = 363
        ##END OF PREFS
        
        # Flags
        self.fix_flag = True
        self.started_not_integrated = False
        self.refresh_flag = False
        self.clear_all = False # To scrub views after view change
        self.key_pressed = False
        self.enter_toggle = False
        #Dock view flicker free
        self.old_img_frame = []
        
        # Tracking index
        # we are trying to save the image displayed by user (the gridbox is "selected")
        # we need 1 variable to do this. Every time displayimage is called, x = imageobj.
        # when this variable is changed, the old is overwritten, but before this happens, its border colour should be reset.
        self.last_selection = None
        self.current_selection = None
        self.current_displayed = None
        self.focused_on_secondwindow = False
        
        # Tracking index (key control)
        self.__previous_state = 0
        self.last_call_time = 0
        self.throttle_delay = 0.1
        self.navigation_key_pressed = False

        #Initialization for view-button values
        self.show_unassigned = tk.BooleanVar()
        self.show_assigned = tk.BooleanVar()
        self.show_moved = tk.BooleanVar()
        self.show_animated = tk.BooleanVar()
        self.show_unassigned.set(True)
        
        #Initialization for lists.
        self.gridsquarelist = [] # List to hold all gridsquares made
        self.displayedlist = [] # List to hold all gridsquares currently displayed
        #Main window sorted lists
        self.unassigned_squarelist = []
        self.assigned_squarelist = []
        self.filtered_images = []
        self.moved_squarelist = []    
        #Animation tracking
        self.running = []
        self.track_animated = []
        #Destwindow lists
        self.dest_squarelist = [] # List to hold all gridsquares destined for the destination
        self.destgrid_updateslist = [] # List to hold all gridsquare refreshes from setdestination
        self.render_refresh = [] # List to hold all gridsquares refreshes from setdestination
        self.queue = []
        #Buttons list
        self.buttons = []

    def initialize(self): #Initializating GUI
        
        self.geometry(self.main_geometry)
        #Styles

        style = ttk.Style()
        self.style = style
        style.configure("darkmode.TCheckbutton", background=self.background_colour, foreground=self.text_colour)
        style.configure('Custom.TPanedwindow', background=self.pane_divider_colour)  # No border for the PanedWindow
        style.configure("textc.TCheckbutton", foreground=self.text_colour, background=self.background_colour)
        style.configure("darkmode1.TCheckbutton", background=self.background_colour, foreground=self.text_colour, highlightthickness = 0)
        style.configure('darkmode.TMenubutton', background=self.button_colour, foreground=self.text_colour, borderwidth = 2, arrowcolor = "grey")
        style.map('darkmode.TMenubutton',
           background=[('active', self.active_background_colour)],  # Clicked background
           foreground=[('active', self.active_text_colour)])  # Clicked text color
        
        

        # Paned window that holds the almost top level stuff.
        self.toppane = Panedwindow(self, orient="horizontal")
        
        # Frame for the left hand side that holds the setup and also the destination buttons.
        self.leftui = tk.Frame(self.toppane, width=self.leftpane_width, bg=self.background_colour)
        self.leftui.grid_propagate(False) #to turn off auto scaling.
        self.leftui.columnconfigure(0, weight=1)
        
        self.toppane.add(self.leftui, weight=0) # 0 here, it stops the divider from moving itself. The divider pos is saved by prefs, this complicates it, so auto scaling based on text amount in source and dest folder is disabled.
        
        # This setups all the buttons and text
        self.first_page_buttons()

        # Start the grid setup
        self.middlepane_frame = tk.Frame(self.toppane, bg=self.background_colour, width = self.middlepane_width)

        imagegridframe = tk.Frame(self.toppane,bg=self.background_colour)
        imagegridframe.grid(row=0, column=2, sticky="NSEW") #this is in second so content frame inside this.
        self.imagegridframe = imagegridframe
        
        self.imagegrid = tk.Text(
            imagegridframe, wrap ='word', borderwidth=0, highlightthickness=0, state="normal", background=self.grid_background_colour)
        self.imagegrid.bind("<Up>", lambda e: "break")
        self.imagegrid.bind("<Down>", lambda e: "break")
        self.imagegrid.bind("<KeyPress>", lambda event: (self.imagegrid.after_idle(self.navigator, event), self.navigation_key_pressed_toggle(False)))
        self.imagegrid.bind("<KeyRelease>", lambda event: (self.imagegrid.after_idle(self.navigator, event), self.navigation_key_pressed_toggle(True)))
        
        vbar = tk.Scrollbar(imagegridframe, orient='vertical',command=lambda *args: throttled_yview(self.imagegrid, *args))
        self.vbar = vbar
        
        self.imagegrid.configure(state="disabled")
        
        # Set the correct side for the dock view.
        self.initial_dock_setup()
        
        self.toppane.grid(row=0, column=0, sticky="NSEW")
        self.toppane.configure(style='Custom.TPanedwindow')

        self.columnconfigure(0, weight=10)
        self.columnconfigure(1, weight=0)
        self.rowconfigure(0, weight=10)
        self.rowconfigure(1, weight=0)
        
        
        
        self.protocol("WM_DELETE_WINDOW", self.closeprogram)
        self.winfo_toplevel().title("Simple Image Sorter: QOL")

    def first_page_buttons(self):
        self.panel = tk.Label(self.leftui, wraplength=350, justify="left", bg=self.background_colour,fg=self.text_colour, text="""

                Select a Source Directory: 
Choose a folder to search for images,
All subfolders will be scanned as well.

                Set the Destination Directory: 
Choose a folder to sort into,
The folder must contain subfolders, these are the folders you sort into.

                Exclusions: 
One per line, no commas.
                              
                Loading Images:
To load more images, press the "Add Files" button. Choose how many images are added in the program settings.
                              
                Right-Click:
on Destination Buttons,
to see which images are assigned to them,
(Does not include moved)    
                              
                Right-Click:                
on Thumbnails,
to view a zoomable full-size image,
(Note that you cannot zoom gifs or webps.)

                Enter / Left-Click:
on thumbnails or in viewer,
to lock the image, so you can
zoom and pan using navigation keys.
(ctrl, shift)

                Preferences:
Choose preferences inside prefs.json,
You can change the hotkeys.
You can customize most elements.
You can change thumbnailsize
(Adjust maximum name length suit to you).
You can force scrollbars on/off for the imagegrid.
You can do scrolling by pages.
                
                Acknowledgments: 
Special thanks to FooBar167 on Stack Overflow for the advanced and memory-efficient Zoom and Pan Tkinter class.
        """
                              )
        self.panel.grid(row=3, column=0, columnspan=200, rowspan=200, sticky="NSEW")

        self.buttonframe = tk.Frame(master=self.leftui,bg=self.background_colour)
        self.buttonframe.grid(column=0, row=3, sticky="NSEW")
        self.buttonframe.columnconfigure(0, weight=1)

        self.entryframe = tk.Frame(master=self.leftui,bg=self.background_colour)
        self.entryframe.columnconfigure(1, weight=1)
        self.entryframe.grid(row=0, column=0, sticky="ew")

        self.excludebutton = tk.Button(self.entryframe, text="Manage Exclusions", command=self.excludeshow,bg=self.button_colour, fg=self.text_colour)
        self.excludebutton.grid(row=0, column=2)

        self.sdpEntry = tk.Entry(self.entryframe, takefocus=False, background=self.background_colour, foreground=self.text_colour)  # scandirpathEntry
        self.sdpEntry.grid(row=0, column=1, sticky="ew", padx=2)
        self.sdpEntry.insert(0, self.source_folder)

        self.sdplabel = tk.Button(self.entryframe, text="Source Folder:", command=partial(self.filedialogselect, self.sdpEntry, "d"), bg=self.button_colour, fg=self.text_colour)
        self.sdplabel.grid(row=0, column=0, sticky="e") #ew

        self.ddpEntry = tk.Entry(self.entryframe, takefocus=False,   background=self.background_colour, foreground=self.text_colour)  # dest dir path entry
        self.ddpEntry.grid(row=1, column=1, sticky="ew", padx=2)
        self.ddpEntry.insert(0, self.destination_folder)

        self.ddplabel = tk.Button(self.entryframe, text="Destination Folder:", command=partial(self.filedialogselect, self.ddpEntry, "d"),bg=self.button_colour, fg=self.text_colour)
        self.ddplabel.grid(row=1, column=0, sticky="e") #ew
        
        self.activebutton = tk.Button(self.entryframe, text="New Session", command=partial(self.fileManager.validate, self),bg=self.button_colour, fg=self.text_colour)
        ToolTip(self.activebutton,delay=1,msg="Start a new Session with the entered source and destination")
        self.activebutton.grid(row=1, column=2, sticky="ew")
        
        self.loadpathentry = tk.Entry(self.entryframe, takefocus=False, textvariable=self.sessionpathvar,  background=self.background_colour, foreground=self.text_colour)
        self.loadpathentry.grid(row=3, column=1, sticky='ew', padx=2)

        self.loadbutton = tk.Button(self.entryframe, text="Load Session", command=self.fileManager.loadsession,bg=self.button_colour, fg=self.text_colour)
        ToolTip(self.loadbutton,delay=1,msg="Load and start the selected session data.")
        self.loadbutton.grid(row=3, column=2, sticky='ew')

        self.loadfolderbutton = tk.Button(self.entryframe, text="Session Data:", command=partial(self.filedialogselect, self.loadpathentry, "f"),bg=self.button_colour, fg=self.text_colour)
        ToolTip(self.loadfolderbutton,delay=1,msg="Select a session json file to open.")
        self.loadfolderbutton.grid(row=3, column=0, sticky='e') #ew for buttons that are the same size on start display.

        # Add a button for sortbydate option
        self.sortbydate_button = ttk.Checkbutton(self.leftui, text="Sort by Date", variable=self.sortbydatevar, onvalue=True, offvalue=False, command=self.sortbydatevar,style="darkmode.TCheckbutton")
        self.sortbydate_button.grid(row=2, column=0, sticky="w", padx=25)
        
        #If it is set in prefs, this makes the buttons blink when hovered over.
        if self.interactive_buttons:
            #Option for making the buttons change color on hover
            self.excludebutton.bind("<Enter>", lambda e: self.excludebutton.config(bg=self.active_background_colour, fg=self.active_text_colour))
            
            self.excludebutton.bind("<Leave>", lambda e: self.excludebutton.config(bg=self.button_colour, fg=self.text_colour)) 
            self.activebutton.bind("<Enter>", lambda e: self.activebutton.config(bg=self.active_background_colour, fg=self.active_text_colour))
            self.activebutton.bind("<Leave>", lambda e: self.activebutton.config(bg=self.button_colour, fg=self.text_colour))

            self.sdpEntry.bind("<Enter>", lambda e: self.sdpEntry.config(bg=self.active_background_colour, fg=self.active_text_colour))
            self.sdpEntry.bind("<Leave>", lambda e: self.sdpEntry.config(bg=self.background_colour, fg=self.text_colour))

            self.ddpEntry.bind("<Enter>", lambda e: self.ddpEntry.config(bg=self.active_background_colour, fg=self.active_text_colour))
            self.ddpEntry.bind("<Leave>", lambda e: self.ddpEntry.config(bg=self.background_colour, fg=self.text_colour))

            self.sdplabel.bind("<Enter>", lambda e: self.sdplabel.config(bg=self.active_background_colour, fg=self.active_text_colour))
            self.sdplabel.bind("<Leave>", lambda e: self.sdplabel.config(bg=self.button_colour, fg=self.text_colour))

            self.ddplabel.bind("<Enter>", lambda e: self.ddplabel.config(bg=self.active_background_colour, fg=self.active_text_colour))
            self.ddplabel.bind("<Leave>", lambda e: self.ddplabel.config(bg=self.button_colour, fg=self.text_colour))

            self.loadbutton.bind("<Enter>", lambda e: self.loadbutton.config(bg=self.active_background_colour, fg=self.active_text_colour))
            self.loadbutton.bind("<Leave>", lambda e: self.loadbutton.config(bg=self.button_colour, fg=self.text_colour))

            self.loadfolderbutton.bind("<Enter>", lambda e: self.loadfolderbutton.config(bg=self.active_background_colour, fg=self.active_text_colour))
            self.loadfolderbutton.bind("<Leave>", lambda e: self.loadfolderbutton.config(bg=self.button_colour, fg=self.text_colour))

            self.loadpathentry.bind("<Enter>", lambda e: self.loadpathentry.config(bg=self.active_background_colour, fg=self.active_text_colour))
            self.loadpathentry.bind("<Leave>", lambda e: self.loadpathentry.config(bg=self.background_colour, fg=self.text_colour))

    def initial_dock_setup(self):
        #Left
        if self.dock_side.get() and self.dock_view.get():
            if self.force_scrollbar:
                self.vbar.grid(row=0, column=1, sticky='ns')
                self.imagegrid.configure(yscrollcommand=self.vbar.set)
            self.imagegrid.grid(row=0, column=0, sticky="NSEW")  
            self.imagegridframe.rowconfigure(1, weight=0)
            self.imagegridframe.rowconfigure(0, weight=1)
            self.imagegridframe.columnconfigure(1, weight=0)
            self.imagegridframe.columnconfigure(0, weight=1)
            self.toppane.add(self.middlepane_frame, weight=0)
            self.toppane.add(self.imagegridframe, weight=1)
        #Right
        elif self.dock_view.get():
            if self.force_scrollbar:
                self.vbar.grid(row=0, column=0, sticky='ns')
                self.imagegrid.configure(yscrollcommand=self.vbar.set)
            self.imagegrid.grid(row=0, column=1, sticky="NSEW") 
            self.imagegridframe.rowconfigure(1, weight=0)
            self.imagegridframe.rowconfigure(0, weight=1)
            self.imagegridframe.columnconfigure(0, weight=0)
            self.imagegridframe.columnconfigure(1, weight=1)
            self.toppane.add(self.imagegridframe, weight=1)
            self.toppane.add(self.middlepane_frame, weight=0)
        else:
            self.imagegridframe.grid_forget()
            if self.force_scrollbar:
                self.vbar.grid(row=0, column=1, sticky='ns')
                self.imagegrid.configure(yscrollcommand=self.vbar.set)
            self.imagegrid.grid(row=0, column=0, sticky="NSEW")  
            self.imagegridframe.rowconfigure(1, weight=0)
            self.imagegridframe.rowconfigure(0, weight=1)
            self.imagegridframe.columnconfigure(1, weight=0)
            self.imagegridframe.columnconfigure(0, weight=1)
            self.toppane.add(self.imagegridframe, weight=1)

        if not self.force_scrollbar:
            self.vbar.grid(row=0, column=1, sticky='ns')
            self.vbar.grid_forget()

    def closeprogram(self):
        if len(self.assigned_squarelist) != 0:
            if askokcancel("Designated but Un-Moved files, really quit?","You have destination designated, but unmoved files. (Simply cancel and Move All if you want)"):
                self.save_viewer_geometry()
                self.close_destination_window()
                self.fileManager.saveprefs(self)
                self.destroy()
        else:
            self.save_viewer_geometry()
            self.close_destination_window()
            self.fileManager.saveprefs(self)
            self.destroy()

    def excludeshow(self):
        excludewindow = tk.Toplevel()
        excludewindow.winfo_toplevel().title(
            "Folder names to ignore, one per line. This will ignore sub-folders too.")
        excludetext = tkst.ScrolledText(excludewindow, bg=self.background_colour, fg=self.text_colour)
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
            logger.error(f"Error in excludesave: {e}")

    def tooltiptext(self,imageobject):
        text=""
        if imageobject.dupename:
            text += "Image has Duplicate Filename!\n"
        text += "Leftclick to select this for assignment. Rightclick to open full view"
        return text
    
    def makegridsquare(self, parent, imageobj, setguidata, dest):
        frame = tk.Frame(parent, borderwidth=0, width=self.thumbnailsize, height=self.thumbnailsize, highlightthickness = 0, highlightcolor=self.imageborder_selected_colour, padx = 0, pady = 0,bg=self.background_colour) #unclear if width and height needed
        frame.obj = imageobj
        truncated_filename = self.truncate_text(imageobj)
        truncated_name_var = tk.StringVar(frame, value=truncated_filename)
        frame.obj2 = truncated_name_var # This is needed or it is garbage collected I guess
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
                               height=self.thumbnailsize,bg=self.background_colour, highlightthickness=self.image_border_thickness, highlightcolor=self.imageborder_selected_colour, highlightbackground = self.imageborder_default_colour) #The gridbox color.
            canvas.grid(column=0, row=0, sticky="NSEW")
            tooltiptext=tk.StringVar(frame,self.tooltiptext(imageobj)) #CHECK PROFILE
            canvas.image = img
            ToolTip(canvas,msg=tooltiptext.get,delay=1) #CHECK PROFILE
            frame.canvas = canvas
            frame.rowconfigure(0, weight=4)
            frame.rowconfigure(1, weight=1)

            #Added reference for animation support. We use this to refresh the frame 1/20, 2/20..
            canvas_image_id = canvas.create_image(
                self.thumbnailsize/2+self.image_border_thickness, self.thumbnailsize/2+self.image_border_thickness, anchor="center", image=img) #If you use gridboxes, you must +1 to thumbnailsize/2, so it counteracts the highlighthickness.
            frame.canvas_image_id = canvas_image_id 
            
            # Create a frame for the Checkbutton to control its height
            check_frame = tk.Frame(frame, height=self.checkbox_height,bg=self.background_colour, highlightthickness=self.text_box_thickness, highlightcolor=self.text_box_selection_colour, highlightbackground=self.text_box_colour) 
            check_frame.grid(column=0, row=1, sticky="NSEW")  # Place the frame in the grid
            check_frame.grid_propagate(False)
            
            #Create different dest for destinations to control view better. These also call a command to cancel the viewer image from being moved by keypresses, if we interact with other gridsquares first.
            if not dest:
                check = ttk.Checkbutton(check_frame, textvariable=truncated_name_var, variable=imageobj.checked, onvalue=True, offvalue=False, command=lambda: (self.uncheck_show_next()), style="darkmode.TCheckbutton")
            else:
                check = ttk.Checkbutton(check_frame, textvariable=truncated_name_var, variable=imageobj.destchecked, onvalue=True, offvalue=False, command=lambda: (self.uncheck_show_next()), style="darkmode.TCheckbutton")
            check.grid(sticky="NSEW")

            if(setguidata):  # save the data to the image obj to both store a reference and for later manipulation
                imageobj.setguidata(
                    {"img": img, "frame": frame, "canvas": canvas, "check": check, "show": True,"tooltip":tooltiptext})
            # anything other than rightclicking toggles the checkbox, as we want.
            canvas.bind("<Button-1>", partial(bindhandler, check, "invoke"))
            canvas.bind(
                "<Button-3>", lambda e: (self.displayimage(frame)))
            check.bind("<Button-3>", lambda e: (self.displayimage(frame)))
            #make blue if only one that is blue, must remove other blue ones. blue ones are stored the gridsquare in a global list.
            #
            canvas.bind("<MouseWheel>", partial(
                bindhandler, parent, "scroll"))
            frame.bind("<MouseWheel>", partial(
                bindhandler, self.imagegrid, "scroll"))
            
            check.bind("<MouseWheel>", partial(
                bindhandler, self.imagegrid, "scroll"))
            canvas.bind('<KeyPress>', lambda event: (canvas.after_idle(self.navigator, event), self.navigation_key_pressed_toggle(True)))
            frame.bind('<KeyPress>', lambda event: (frame.after_idle(self.navigator, event), self.navigation_key_pressed_toggle(True)))
            check.bind('<KeyPress>', lambda event: (check.after_idle(self.navigator, event), self.navigation_key_pressed_toggle(True)))
            canvas.bind('<KeyRelease>', lambda event: self.navigation_key_pressed_toggle(False))
            frame.bind('<KeyRelease>', lambda event: self.navigation_key_pressed_toggle(False))
            check.bind('<KeyRelease>', lambda event: self.navigation_key_pressed_toggle(False))

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
                    highlightbackground="brown", highlightthickness=2)
        except Exception as e:
            logger.error(e)
        return frame
    
    def navigation_key_pressed_toggle(self, state):
        # IF locked, but we click away anyway.
        self.navigation_key_pressed = state
        
    def navigator(self, event): # Scrolling with the keyboard #might need to disable wasd.
        if event.keysym == "Return":
            self.enter_toggle = not self.enter_toggle
        if self.enter_toggle:
            self.Image_frame.focus_canvasimage()
            self.current_selection.canvas.configure(highlightbackground = self.imageborder_locked_colour, highlightcolor = self.imageborder_locked_colour) # Change new frame's frame
        # Independent from the language of the keyboard, CapsLock, <Ctrl>+<key>, etc.
        """Throttling"""
        if not self.show_next.get():
            return
        current_time = time.time()
        if not self.navigation_key_pressed:
            pass
        elif current_time - self.last_call_time >= self.throttle_delay: #and key pressed down... so you can tap as fast as you like.
            self.last_call_time = current_time
        else:
            print("Victim of throttler")
            return
        """Throttling"""
        
        if event.state - self.__previous_state == 4:  # means that the Control key is pressed
            pass  # do nothing if Control key is pressed
        else:
            
            self.__previous_state = event.state    # remember the last keystroke state
            items_per_row = int(max(1, self.imagegrid.winfo_width() / self.actual_gridsquare_width))
            items_per_rowy = int(max(1, self.imagegrid.winfo_height() / self.actual_gridsquare_height))
            current_index = self.displayedlist.index(self.current_selection)
            last_row = max(0,floor((current_index) / items_per_row))
            list_length = len(self.displayedlist)
            check = ["w","a","s","d"]
            #wasd = 87,65,83,68
            #updownleftright = 38,40,37,39
            for x in check:
                if x in self.hotkeys:
                    disable_wasd = True
                    break
                else:
                    disable_wasd = False
                    break
            if not event.keycode in [37,38,39,40] or (event.keycode in [65,68,83,87] and not disable_wasd):
                return
            if event.keycode == 68 and not disable_wasd or event.keycode == 39:    # scroll right, keys 'd' or 'Right' [D,RIGHT]
                if not list_length > current_index+1:
                    return
                self.current_selection = self.displayedlist[current_index+1]
            elif event.keycode == 65 and not disable_wasd or event.keycode == 37:    # scroll left, keys 'a' or 'Left' [A,LEFT]
                if not list_length > current_index-1 or current_index == 0:
                    return
                self.current_selection = self.displayedlist[current_index-1]
            elif event.keycode == 87 and not disable_wasd or event.keycode == 38:    # scroll up, keys 'w' or 'Up' [W,UP]
                if not list_length > current_index-items_per_row or current_index-items_per_row < 0:
                    return
                self.current_selection = self.displayedlist[current_index-items_per_row]
            elif event.keycode == 83 and not disable_wasd or event.keycode == 40:    # scroll down, keys 's' or 'Down' [S,DOWN]
                if not list_length > current_index+items_per_row:
                    return
                self.current_selection = self.displayedlist[current_index+items_per_row]
            self.show_next_method(self.current_selection)
            self.displayimage(self.current_selection)
            current_index = self.displayedlist.index(self.current_selection)
            current_row = max(0,floor((current_index) / items_per_row))
            total_rows = list_length / items_per_row
            # Calculate the index for the first and last visible items in the current bounding box
            first_visible_index = self.imagegrid.yview()[0] * total_rows  # Index of the first visible item
            last_visible_index = self.imagegrid.yview()[1] * total_rows  # Index of the last visible item
            # Check if we're at the top or bottom of the visible area and scroll accordingly
            self.page_mode = False
            if self.page_mode:
                
                if (event.keycode in [87, 38] or last_row < current_row) or current_row == 0:  # Up (W, Up)
                    if current_row == 1: #
                        self.imagegrid.yview_moveto(0)
                        return
                
                if current_row < ceil(first_visible_index):  # If we're at the top of the visible area
                    target_scroll = (current_row-items_per_rowy) / total_rows
                    self.imagegrid.yview_moveto(target_scroll)

                elif event.keycode in [83, 40] or last_row < current_row:  # Down (S, Down)
                    if current_row >= list_length-items_per_rowy:
                        self.imagegrid.yview_moveto(1)
                        return

                    if current_row > ceil(last_visible_index-1):  # If we're at the bottom of the visible area
                        target_scroll = (current_row) / total_rows
                        self.imagegrid.yview_moveto(target_scroll)
            else:
                if event.keycode in [87, 38] or last_row < current_row:
                    if current_row == 1: #
                        self.imagegrid.yview_moveto(0)
                        return
                
                if current_row < floor(first_visible_index):
                    self.imagegrid.yview_scroll(-1, "units") 

                elif event.keycode in [83, 40] or last_row < current_row:
                    if current_row >= list_length-items_per_rowy:
                        self.imagegrid.yview_moveto(1)
                        return

                    if current_row > ceil(last_visible_index-1):
                        self.imagegrid.yview_scroll(1, "units")  # Scroll down one unit # non page      

    def uncheck_show_next(self):
        self.focused_on_secondwindow = False
            
    def truncate_text(self, imageobj): #max_length must be over 3+extension or negative indexes happen.
        """Truncate the text to fit within the specified thumbnailsized gridbox."""
        filename = imageobj.name.get()
        base_name, ext = os.path.splitext(filename)
        if len(filename) > self.max_text_length:
            # Subtract 3 for the ellipsis and ext for ext.
            base_name = base_name[:self.max_text_length - (3+len(ext))] + ".." + ext
            return base_name
        return base_name + ext
    
    def displayimage(self, frame, flag=True): #Create secondary window for image viewing
        self.enter_toggle = False
        imageobj = frame.obj
        items_per_row = int(max(1, self.imagegrid.winfo_width() / self.actual_gridsquare_width))
        row, col = map(int, self.imagegrid.index(tk.INSERT).split('.'))
        logger.debug(f"Row: {items_per_row}, Column: {col}, and {self.thumbnailsize} and {self.imagegrid.winfo_width()}")
        
        # This makes sure the initial view is set up correctly
        if self.middlepane_frame.winfo_width() != 1:
                self.middlepane_width = self.middlepane_frame.winfo_width()

        path = imageobj.path
        pass_fast_render_size = int(self.fast_render_size)

        # Close already open windows, IF: integrated viewer option is on, BUT KEEP OPEN IF show next is on. (Calls not made by user)
        if hasattr(self, 'second_window') and self.second_window and not self.show_next.get(): # Call not made by user, but sortimages
            self.save_viewer_geometry()
        elif hasattr(self, 'second_window') and self.second_window and self.dock_view.get():
            self.save_viewer_geometry()
        
        
        
                    
        if self.dock_view.get(): # This handles the middlepane viewer. Runs, IF second window is closed.

            geometry = str(self.middlepane_width) + "x" + str(self.winfo_height())
            self.Image_frame = CanvasImage(self.middlepane_frame, path, geometry, self.canvas_colour, imageobj, int(pass_fast_render_size), self.viewer_x_centering, self.viewer_y_centering, self.filter_mode, self)
            self.Image_frame.grid(row = 0, column = 0, sticky = "NSEW")
            self.Image_frame.default_delay.set(self.default_delay.get()) #tell imageframe if animating, what delays to use
            self.Image_frame.rescale(min(self.middlepane_width / self.Image_frame.imwidth, self.winfo_height() / self.Image_frame.imheight))  # Scales to the window
            self.Image_frame.center_image()
            logger.debug("Rescaled and Centered")    

            self.focused_on_secondwindow = True

            # Logic for show next
            if flag:
                self.show_next_method(frame)
            self.old_img_frame.append(self.Image_frame)
            if self.flicker_free_dock_view and self.dock_view.get():
                try:
                    if len(self.old_img_frame) > 1 and self.old_img_frame[0]:
                        self.old_img_frame[0].close_window()
                        self.old_img_frame.pop(0)
                        self.update_idletasks() 
                except Exception as e:
                    pass
            #if self.dock_view:
            #    print("attemtping")


            self.enter_toggle = False
            self.Image_frame.canvas.focus_set()
            #self.current_selection.focus_set()
            return

        # Standalone image viewer
        if not hasattr(self, 'second_window') or not self.second_window or not self.second_window.winfo_exists():
            self.old_img_frame.clear()
            # No window exists, create one
            self.second_window = tk.Toplevel() #create a new window
            second_window = self.second_window
            second_window.configure(background=self.background_colour)
            second_window.rowconfigure(0, weight=1)
            second_window.columnconfigure(0, weight=1)
            second_window.title("Image: " + path)
            second_window.geometry(self.viewer_geometry)
            second_window.bind("<Button-3>", self.save_viewer_geometry)
            second_window.protocol("WM_DELETE_WINDOW", self.save_viewer_geometry)
            second_window.obj = imageobj
            second_window.transient(self)

        elif self.show_next.get():
            self.second_window.title("Image: " + path)
            
        geometry = self.viewer_geometry.split('+')[0]
        self.Image_frame = CanvasImage(self.second_window, path, geometry, self.canvas_colour, imageobj, int(pass_fast_render_size), self.viewer_x_centering, self.viewer_y_centering, self.filter_mode, self)
        self.Image_frame.default_delay.set(self.default_delay.get()) #tell imageframe if animating, what delays to use
        self.Image_frame.grid(row = 0, column = 0, sticky = "NSEW")  # Initialize Frame grid statement in canvasimage, Add to main window grid
        self.Image_frame.rescale(min(self.second_window.winfo_width() / self.Image_frame.imwidth, self.second_window.winfo_height() / self.Image_frame.imheight))  # Scales to the window
        self.Image_frame.center_image()

        logger.debug("Rescaled and Centered")
        self.focused_on_secondwindow = True
        if flag:
            self.show_next_method(frame)
        
        if not self.show_next.get():
            self.second_window.after(100, lambda: self.Image_frame.canvas.focus_set())
        else:
            self.second_window.after(100, lambda: self.Image_frame.canvas.focus_set())
            #self.current_selection.focus_set()

    def show_next_method(self, frame): # Record current and last gridsquares that have been "selected". Change their colours.
        self.current_selection = frame # Update current_selection
        self.current_displayed = frame
        if self.last_selection and self.last_selection != self.current_selection: # Restore old frame's frame.
            self.last_selection.canvas.configure(highlightcolor=self.imageborder_default_colour, highlightbackground = self.imageborder_default_colour)
        self.current_selection.canvas.configure(highlightbackground = self.imageborder_selected_colour, highlightcolor = self.imageborder_selected_colour) # Change new frame's frame
        self.last_selection = self.current_selection # Update last_selection
            
    def save_viewer_geometry(self, event=None):
        if hasattr(self, 'second_window') and self.second_window and self.second_window.winfo_exists():
            self.viewer_geometry = self.second_window.winfo_geometry()
            #self.checkdupename(self.second_window.obj)
            if hasattr(self, 'Image_frame'):
                self.Image_frame.close_window()
                self.after(0, self.Image_frame.destroy)
                del self.Image_frame
            self.second_window.destroy()
            del self.second_window
        elif hasattr(self, 'Image_frame'):
            self.Image_frame.close_window()
            self.after(0, self.Image_frame.destroy) # Gives it time to close
            del self.Image_frame

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

    def guisetup(self, destinations):
        self.sortbydate_button.destroy() # Hide sortbydate button after it is no longer needed
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
                    self.bind_all(f"<KeyPress-{self.hotkeys[itern]}>", partial(
                        self.handle_setdestination_call, True, x))
                    self.bind_all(f"<KeyRelease-{hotkeys[itern]}>", partial(
                        self.handle_setdestination_call, False, None))
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
            newbut.bind("<Enter>", lambda e, btn=newbut: btn.config(bg=darken_color(original_colors[btn]['bg']), fg='white'))
            newbut.bind("<Leave>", lambda e, btn=newbut: btn.config(bg=original_colors[btn]['bg'], fg=original_colors[btn]['fg']))  # Reset to original colors

        # For SKIP and BACK buttons, set hover to white
        for btn in self.buttons:
            if btn['text'] == "SKIP (Space)" or btn['text'] == "BACK":
                btn.bind("<Enter>", lambda e, btn=btn: btn.config(bg=self.text_colour, fg=self.background_colour))
                btn.bind("<Leave>", lambda e, btn=btn: btn.config(bg=self.button_colour, fg=self.text_colour))  # Reset to original colors
            self.entryframe.grid_remove()
        # options frame
        optionsframe = tk.Frame(self.leftui,bg=self.background_colour)
        optionsframe.columnconfigure(0, weight=1)
        optionsframe.columnconfigure(1, weight=3)
        optionsframe.grid(row=0, column=0, sticky="ew")
        
        self.squaresperpageentry = tk.Entry(
            optionsframe, textvariable=self.squaresperpage, takefocus=False, background=self.background_colour, foreground=self.text_colour)
        if self.squaresperpage.get() < 0: #this wont let you save -1
            self.squaresperpage.set(1)
        ToolTip(self.squaresperpageentry,delay=1,msg="How many more images to add when Load Images is clicked")
        for n in range(0, itern):
            self.squaresperpageentry.unbind(hotkeys[n])
        self.squaresperpageentry.grid(row=1, column=0, sticky="EW",)

        self.addpagebut = tk.Button(
            optionsframe, text="Load More Images", command=self.load_more_images,bg=self.background_colour, fg=self.text_colour)
        ToolTip(self.addpagebut,msg="Add another batch of files from the source folders.", delay=1)
        self.addpagebut.grid(row=1, column=1, sticky="EW")
        self.addpagebutton = self.addpagebut

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

        if self.interactive_buttons:
            #Option for making the buttons change color on hover
            self.clearallbutton.bind("<Enter>", lambda e: self.clearallbutton.config(bg=self.active_background_colour, fg=self.active_text_colour))
            self.clearallbutton.bind("<Leave>", lambda e: self.clearallbutton.config(bg=self.button_colour, fg=self.text_colour))
    
            self.addpagebut.bind("<Enter>", lambda e: self.addpagebut.config(bg=self.active_background_colour, fg=self.active_text_colour))
            self.addpagebut.bind("<Leave>", lambda e: self.addpagebut.config(bg=self.button_colour, fg=self.text_colour))
    
            self.moveallbutton.bind("<Enter>", lambda e: self.moveallbutton.config(bg=self.active_background_colour, fg=self.active_text_colour))
            self.moveallbutton.bind("<Leave>", lambda e: self.moveallbutton.config(bg=self.button_colour, fg=self.text_colour))
    
            self.savebutton.bind("<Enter>", lambda e: self.savebutton.config(bg=self.active_background_colour, fg=self.active_text_colour))
            self.savebutton.bind("<Leave>", lambda e: self.savebutton.config(bg=self.button_colour, fg=self.text_colour))
    
            self.squaresperpageentry.bind("<Enter>", lambda e: self.squaresperpageentry.config(bg=self.active_background_colour, fg=self.active_text_colour))
            self.squaresperpageentry.bind("<Leave>", lambda e: self.squaresperpageentry.config(bg=self.background_colour, fg=self.text_colour))
    
        custom_buttons_frame  = tk.Frame(self.leftui,bg=self.background_colour)
        custom_buttons_frame.grid(row = 1, column = 0, sticky = "ew")
        custom_buttons_frame.columnconfigure(0, weight = 1)
        custom_buttons_frame.columnconfigure(1, weight = 1)
        custom_buttons_frame.columnconfigure(2, weight = 1)
        custom_buttons_frame.columnconfigure(3, weight = 1)
        custom_buttons_frame.columnconfigure(4, weight = 1)

        self.default_delay_button = ttk.Checkbutton(custom_buttons_frame, text="Default speed", variable=self.default_delay, onvalue=True, offvalue=False, command=lambda: (self.switch_to_default_delay(), self.default_delay))
        self.show_next_button = ttk.Checkbutton(custom_buttons_frame, text="Show next", variable=self.show_next, onvalue=True, offvalue=False, command=lambda: (self.focus_helper(self.show_next)))
        self.dock_view_button = ttk.Checkbutton(custom_buttons_frame, text="Dock view", variable=self.dock_view, onvalue=True, offvalue=False, command=lambda: (self.change_viewer(), self.focus_helper(self.dock_view)))
        self.dock_side_button = ttk.Checkbutton(custom_buttons_frame, text="Dock side", variable=self.dock_side, onvalue=True, offvalue=False, command=lambda: (self.change_dock_side(), self.focus_helper(self.dock_side)))
        
        if self.dock_view.get():
            self.dock_side_button.state(['!disabled'])
        else:
            self.dock_side_button.state(['disabled'])

        self.default_delay_button.grid(row=0, column=0, sticky="ew")
        self.show_next_button.grid(row=0, column=1, sticky="ew")
        self.dock_view_button.grid(row=0, column=2, sticky="ew")
        self.dock_side_button.grid(row=0, column=3, sticky="ew")
        
        self.default_delay_button.configure(style="darkmode1.TCheckbutton")
        self.show_next_button.configure(style="darkmode1.TCheckbutton")
        self.dock_view_button.configure(style="darkmode1.TCheckbutton")
        self.dock_side_button.configure(style="darkmode1.TCheckbutton")

        view_options = ["Show Unassigned", "Show Assigned", "Show Moved", "Show Animated"]
        optionmenuvar = tk.StringVar()
        optionmenuvar.trace_add("write", lambda *args: self.on_option_selected(optionmenuvar.get()))
        optionmenuvar.set(view_options[0])

        option_menu = tk.OptionMenu(optionsframe, optionmenuvar, *view_options)
        option_menu.config(bg=self.background_colour, fg=self.text_colour,activebackground=self.active_background_colour, activeforeground=self.active_text_colour, highlightbackground=self.background_colour, highlightcolor=self.active_text_colour, highlightthickness=1)
        option_menu.grid(row = 2, column = 0, sticky = "EW")
        

        centering_options = ["Center", "Only x centering", "Only y centering", "No centering"]
        centering_preference = tk.StringVar()
        centering_preference.trace_add("write", lambda *args: self.change_centering(centering_preference.get()))
        centering_preference.set(centering_options[0])
        
        self.centering_options_button = tk.OptionMenu(custom_buttons_frame, centering_preference, *centering_options)
        self.centering_options_button.config(bg=self.background_colour, fg=self.text_colour,activebackground=self.active_background_colour, activeforeground=self.active_text_colour, highlightbackground=self.background_colour, highlightcolor=self.active_text_colour, highlightthickness=1)
        

        if self.extra_buttons:
            self.centering_options_button.grid(row=0, column=4, sticky="ew")
            # If extra buttons is true, we should load the correct text for the centering button.
            if self.viewer_x_centering and self.viewer_y_centering:
                centering_preference.set("Center")
            elif self.viewer_x_centering and not self.viewer_y_centering:
                centering_preference.set("Only x centering")
            elif not self.viewer_x_centering and self.viewer_y_centering:
                centering_preference.set("Only y centering")
            else:
                centering_preference.set("No centering")

        self.bind_all("<Button-1>", self.setfocus)

    def focus_helper(self, target):
        if target.get() and self.current_selection and self.show_next.get(): #except for side change.
            self.current_selection.focus_set()
        elif self.current_selection and hasattr(self, "Image_frame"):
            self.Image_frame.canvas.focus_set()
        elif self.current_selection:
            self.current_selection.focus_set()
            
    def handle_setdestination_call(self, state, x=None, event=None):
        if x:
            self.fileManager.setDestination(x, event)
        self.key_pressed = state
        
    def switch_to_default_delay(self):
        if hasattr(self, 'Image_frame'):
            self.Image_frame.default_delay.set(self.default_delay.get())

    def change_viewer(self):
        other_viewer_is_open = hasattr(self, 'second_window') and self.second_window and self.second_window.winfo_exists()
        if self.middlepane_frame.winfo_width() != 1:
            self.middlepane_width = self.middlepane_frame.winfo_width() #this updates it before middlepane is closed.
            
        self.middlepane_frame.configure(width = self.middlepane_width)
        self.focused_on_secondwindow = False

        if self.started_not_integrated:
            self.toppane.forget(self.middlepane_frame)
            self.started_not_integrated = False
        
        if self.dock_view.get():
            self.dock_side_button.state(['!disabled'])
            if other_viewer_is_open: # This also means dock_view was changed, so we should open the previous image displayed, if show_next is on.
                self.save_viewer_geometry() # Closes it
                self.displayimage(self.current_selection)

            self.toppane.forget(self.imagegridframe) # Reset the GUI.

            if self.dock_side.get():                    
                self.toppane.add(self.middlepane_frame, weight = 0) #readd the middpane
                self.toppane.add(self.imagegridframe, weight = 1) #readd imagegrid
            else:
                self.toppane.add(self.imagegridframe, weight = 1) #readd imagegrid
                self.toppane.add(self.middlepane_frame, weight = 0) #readd the middpane

            # Use standalone viewer
        else:
            self.dock_side_button.state(['disabled'])
            try:
                # Remove and forget the dock viewer pane and image_frame.
                self.toppane.forget(self.middlepane_frame)
                if hasattr(self, 'Image_frame'):
                    if self.Image_frame:
                        self.Image_frame.close_window()
                        self.after(0, self.Image_frame.destroy)
                        del self.Image_frame
                        self.displayimage(self.current_selection) # If something was displayed, we want to display it in standalone viewer.
            except Exception as e:
                pass
        bindhandler_1(self.imagegrid)
    
    def change_dock_side(self):
        if self.middlepane_frame.winfo_width() == 1:
            return
        #Pane remains at desired width when forgotten from view. It still exists!
        self.middlepane_width = self.middlepane_frame.winfo_width()
        self.middlepane_frame.configure(width = self.middlepane_width)
        if self.dock_view.get():
            self.toppane.forget(self.middlepane_frame)
            self.toppane.forget(self.imagegridframe)
            if self.dock_side.get():
                if self.force_scrollbar:

                    self.vbar.grid(row=0, column=1, sticky='ns')
                    self.imagegrid.configure(yscrollcommand=self.vbar.set)
                    self.imagegrid.grid(row=0, column=0, sticky="NSEW")  

                    self.imagegridframe.columnconfigure(1, weight=0)
                    self.imagegridframe.columnconfigure(0, weight=1)
                    
                self.toppane.add(self.middlepane_frame, weight = 0) #readd the middpane
                self.toppane.add(self.imagegridframe, weight = 1) #readd imagegrid
            else:
                if self.force_scrollbar:

                    self.vbar.grid(row=0, column=0, sticky='ns')
                    self.imagegrid.configure(yscrollcommand=self.vbar.set)
                    self.imagegrid.grid(row=0, column=1, sticky="NSEW") 

                    self.imagegridframe.columnconfigure(0, weight=0)
                    self.imagegridframe.columnconfigure(1, weight=1)
                                
                self.toppane.add(self.imagegridframe, weight = 1) #readd imagegrid
                self.toppane.add(self.middlepane_frame, weight = 0) #readd the middpane

    def change_centering(self, selected_option): # "Center", "Only x centering", "Only y centering", "No centering"
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
        if self.current_selection and hasattr(self, "Image_frame"):
            self.displayimage(self.current_selection)

    def on_option_selected(self, selected_option):
        if selected_option == "Show Unassigned":
            self.show_unassigned.set(False)
            self.clicked_show_unassigned()
        elif selected_option == "Show Assigned":
            self.clicked_show_assigned()
        elif selected_option == "Show Moved":
            self.clicked_show_moved()
        elif selected_option == "Show Animated":
            self.clicked_show_animated()
        if self.show_next.get() and len(self.displayedlist) >= 1 and hasattr(self, "Image_frame"):
            if not self.current_selection and self.displayedlist[0]:
                self.current_selection == self.displayedlist[0]
            self.displayimage(self.displayedlist[0])
        
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

        logger.debug(f"Trying to animate {number_of_animated} pictures.")
        self.refresh_rendered_list()
        self.start_gifs()
    
    def start_gifs(self):
        logger.debug("starting gifs, if you see two of these, something is wrong.") #should only run once. Otherwise two processes try to change the frame leading to speed issues.
        # Check the visible list for pictures to animate.
        self.running = []
        current_squares = self.displayedlist
        load_these = []
        for i in current_squares: #could let in unanimated... because threading. check for frames?
            if i.obj.isanimated and i.obj.isvisible:
                if i not in [tup[0] for tup in self.running]: # not already displayed
                    load_these.append(i)
        for a in load_these:
            if len(a.obj.frames) == a.obj.framecount and not a.obj.framecount == 0:
                logger.info(f"Animate: {a.obj.name.get()[:30]}")
                self.gen_id_and_animate(a)
                
            else:
                #logger.info(f"Lazy load: {a.obj.name.get()[:30]}")
                self.lazy_load(a)
                
    def gen_id_and_animate(self, i):
        random_id = random.randint(1,1000000)
        self.running.append((i, random_id))
        self.animate(i, False, random_id)
        logger.info(f"Animating: {len(self.running)}, Finished: {i.obj.name.get()[:30]}")

    def lazy_load(self, i):
        try:
            if i.obj.frames and i.obj.index != i.obj.framecount and i.obj.lazy_loading:
                
                if len(i.obj.frames) > i.obj.index:
                    i.canvas.itemconfig(i.canvas_image_id, image=i.obj.frames[i.obj.index])

                    if self.default_delay.get():
                        logger.debug(f"{i.obj.index+1}/{i.obj.framecount} ({i.obj.delay}): {i.obj.name.get()[:30]}")
                        i.canvas.after(i.obj.delay, lambda: self.lazy_load_loop(i)) #run again.
                    else:
                        logger.debug(f"{i.obj.index+1}/{i.obj.framecount} ({i.obj.frametimes[i.obj.index]}): {i.obj.name.get()[:30]}")
                        i.canvas.after(i.obj.frametimes[i.obj.index], lambda: self.lazy_load_loop(i)) #or a.obj.delay

                else: #wait for frame to load.
                    logger.debug(f"Buffering: {i.obj.name.get()[:30]}")
                    i.canvas.after(i.obj.delay, lambda: self.lazy_load(i))
            else:
                if not i.obj.lazy_loading and i.obj.frames: #if all loaded
                    logger.debug(f"Moving to animate_loop method: {i.obj.name.get()[:30]}")
                    self.gen_id_and_animate(i)
                else: # 0 frames?
                    logger.debug(f"0 frames, buffering: {i.obj.name.get()[:30]}")
                    i.canvas.after(i.obj.delay, lambda: self.lazy_load(i))
        except Exception as e:
            logger.error(f"Lazy load couldn't process the frame: {e}. Likely because of threading.")

    def lazy_load_loop(self, i):
        i.obj.index = (i.obj.index + 1) % i.obj.framecount
        self.lazy_load(i)
    
    def animate(self, i,x, random_id = None): #frame by frame as to not freeze the main one XD #Post. animate a frame for each picture in the list and run this again.
        i.canvas.itemconfig(i.canvas_image_id, image=i.obj.frames[i.obj.index]) #change the frame
        if(i.obj.isvisible and random_id in [tup[1] for tup in self.running]): #and i in self.running
            x = True
            if self.default_delay.get():
                logger.debug(f"{i.obj.index+1}/{i.obj.framecount} ({i.obj.delay}): {i.obj.name.get()[:30]}")
                i.canvas.after(i.obj.delay, lambda: self.animation_loop(i,x, random_id)) #run again.
            else:
                logger.debug(f"{i.obj.index+1}/{i.obj.framecount} ({i.obj.frametimes[i.obj.index]}): {i.obj.name.get()[:30]}")
                i.canvas.after(i.obj.frametimes[i.obj.index], lambda: self.animation_loop(i,x, random_id)) #run again.""
        else:
            base_name, ext = os.path.splitext(i.obj.name.get())
            logger.info(f"Ended: {base_name[:(30-len(ext))]+ext}")
            pass

    def animation_loop(self, i, x, random_id):
        i.obj.index = (i.obj.index + 1) % i.obj.framecount

        self.animate(i, x, random_id)
    
    def render_squarelist(self, squarelist): #This renders the given squarelist.
        
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
    
    def clicked_show_unassigned(self): #Turns you on~
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

    def showthisdest(self, dest, *args): #If a destination window is already open, just update it.
        
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
            if self.destpane_geometry != 0:
                try:
                    self.destwindow.geometry(self.destpane_geometry)
                except Exception as e:
                    logger.error(f"Couldn't load destwindow geometry")
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
                    logger.debug("Click inside a square, not closing.")
                    return  # Click is inside a square, do not close
            
        try:
            if hasattr(self, 'destwindow'):
                self.destpane_geometry = self.destwindow.winfo_geometry()
                self.destgrid.destroy()
                del self.destgrid
                self.destwindow.destroy()
                self.destwindow = None
                del self.destwindow
                self.dest_squarelist = []
                self.filtered_images = []
                self.queue = []
        except Exception as e:
            pass
    
    def refresh_destinations(self): #so when view changes, squarelist is updated, the 
        
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
                            logger.error(f"Error configuring window for image {gridsquare.obj}: {e}")
                        self.dest_squarelist.remove(gridsquare) ##remove pic from squarelist  so it is generated again!
                        self.queue.append(gridsquare) #this adds to the queue to be generated along new ones.
                        self.destgrid_updateslist.remove(gridsquare) # remove from updateslist as the task is compelte
            except Exception as e:
                logger.error(f"Error in refresh_destinations {e}")

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
                        #    self.style.configure("textc.TCheckbutton", foreground="black", background=color, selectcolor="grey")
                        #else:
                         #   self.style.configure("textc.TCheckbutton", foreground="white", background=color, selectcolor="grey")
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
                        logger.error(f"Error configuring window for image {gridsquare.obj}: {e}")
                    to_remove.append(gridsquare)

            # Remove gridsquares from the list
            for gridsquare in to_remove:
                self.dest_squarelist.remove(gridsquare)
                gridsquare.obj.isvisibleindestination = False
            self.start_gifs_destination()

    def start_gifs_destination(self): # Check if images in the current destination view are animated or not. 
        current_index = 0
        for i in self.dest_squarelist:
            if i.obj.isanimated and i.obj.isvisibleindestination: # This prevents the same .gif or .webp having two or more loops at the same time, causing the index counting to double in speed.  
                current_index = 0
                x = False
                self.animate_destination(i, current_index, x)
    
    def animate_destination(self, i, index, x):  # Frame by frame animation
        if x == False:
            if i not in self.track_animated:
                self.track_animated.append(i)
                logger.debug(f"Added to running list for destwindow. {len(self.track_animated)} {self.track_animated}")
            else:
                logger.debug(f"Already running in destwindow. {i.obj.name.get()[:10]}")
                return
        logger.debug(f"Loading frames: {index}/{i.obj.framecount} :Delay: {i.obj.delay}")
        i.canvas.itemconfig(i.canvas_image_id, image=i.obj.frames[index])  # Change the frame
        
        if(i.obj.isvisibleindestination):
            x = True
            if self.default_delay.get():
                logger.debug(f"{i.obj.name.get()}: {index}/{len(i.obj.frames)}, delay: {i.obj.delay}")
                i.canvas.after(i.obj.delay, lambda: self.destination_loop(i,index,x)) #run again.
            else:
                logger.debug(f"{i.obj.name.get()}: {index}/{len(i.obj.frames)}, delay: {i.obj.frametimes[index]}")
                i.canvas.after(i.obj.frametimes[index], lambda: self.destination_loop(i,index,x)) #run again.
        else:
            logger.info("Stopped destination window animations.")
            pass
    
    def destination_loop(self, i, index, x):
        index = (index + 1) % i.obj.framecount
        self.animate_destination(i,index,x)

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

last_scroll_time = None
def throttled_yview(widget, *args):
    """Throttle scroll events for both MouseWheel and Scrollbar slider"""
    global last_scroll_time

    now = time.time()

    if last_scroll_time is None or (now - last_scroll_time) > 0.025:  # 100ms throttle
        last_scroll_time = now
        widget.yview(*args)

def throttled_scrollbar(*args): # Throttled scrollbar callback

    throttled_yview(args[0], 'yview', *args[1:])

last_row_length = 0
def bindhandler_1(widget): # Fixes moving from dock view back to standalone view / could figure out custom values from rows, but eh.
    #global last_row_length
    #if last_row_length == 0:
    #    last_row_length = 1
    #if last_row_length % 2 == 0:
    #    #postivie goes down
    #    widget.yview_scroll(1, "units")
    #last_row_length += 1
    pass

def bindhandler(*args):
    widget = args[0]
    command = args[1]
    
    if command == "scroll":
        widget.yview_scroll(-1*floor(args[2].delta/120), "units")
    elif command == "invoke":
        widget.invoke()
