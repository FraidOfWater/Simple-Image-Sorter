import os
import time
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

logger = logging.getLogger("GUI")
logger.setLevel(logging.WARNING)  # Set to the lowest level you want to handle

handler = logging.StreamHandler()
handler.setLevel(logging.WARNING)

formatter = logging.Formatter('%(message)s')
handler.setFormatter(formatter)

logger.addHandler(handler)

throttle_time = None
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
        self.hotkeys = "123456qwerty7890uiopasdfghjklzxcvbnm"
        self.interactive_buttons = True # Color change on hover

        #Technical preferences
        self.throttle_time = None
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
        # Dark Mode
        """
        self.main_colour =              'black'
        self.square_colour =            'black'
        self.grid_background_colour =   'black'
        self.canvasimage_background =   'black'
        self.text_colour =              'white'
        self.button_press_colour =      'white'
        self.pressed_text_colour =      'black'
        self.button_colour =            'black'
        self.text_field_colour =        'white'
        self.text_field_text_colour =   'black'
        self.pane_divider_colour =      'grey'
        """
        # Midnight Blue
        self.main_colour =              '#202041'
        self.square_colour =            '#888BF8'
        self.grid_background_colour =   '#303276'
        self.canvasimage_background =   '#141433'
        self.text_colour =              'white'
        self.pressed_text_colour =      'white'
        self.button_press_colour =      '#303276'
        self.button_colour =            '#24255C'
        self.text_field_colour =        'white'
        self.text_field_text_colour =   'black'
        self.pane_divider_colour =      'grey'
        

        #GUI CONTROLLED PREFRENECES
        self.squaresperpage = tk.IntVar()
        self.sortbydatevar = tk.BooleanVar()
        self.squaresperpage.set(120)
        self.hideonassignvar = tk.BooleanVar()
        self.hideonassignvar.set(True)
        self.hidemovedvar = tk.BooleanVar()
        self.showhiddenvar = tk.BooleanVar()

        #Default window positions and sizes
        self.main_geometry = (str(self.winfo_screenwidth()-5)+"x" + str(self.winfo_screenheight()-120)+"+0+60")
        self.viewer_geometry = str(int(self.winfo_screenwidth()*0.80)) + "x" + str(self.winfo_screenheight()-120)+"+365+60"
        self.destpane_geometry = 0
        self.leftpane_width = 363
        ##END OF PREFS
        
        #Initialization for lists.
        self.gridsquarelist = [] # List to hold all gridsquares made
        #Buttons list
        self.buttons = []

    def initialize(self): #Initializating GUI
        global throttle_time
        throttle_time = self.throttle_time

        self.geometry(self.main_geometry)
        #Styles
        self.smallfont = tkfont.Font(family='Helvetica', size=10)

        style = ttk.Style()
        self.style = style
        style.configure('Theme_dividers.TPanedwindow', background=self.pane_divider_colour)  # Panedwindow, the divider colour.
        style.configure("Theme_square.TCheckbutton", background=self.grid_background_colour, foreground=self.text_colour) # Theme for Square
        style.configure("Theme_checkbox.TCheckbutton", background=self.main_colour, foreground=self.text_colour, highlightthickness = 0) # Theme for checkbox

        #style.configure("textc.TCheckbutton", foreground=self.text_colour, background=self.main_colour)
        

        # Paned window that holds the almost top level stuff.
        self.toppane = Panedwindow(self, orient="horizontal")

        # Frame for the left hand side that holds the setup and also the destination buttons.
        self.leftui = tk.Frame(self.toppane, width=self.leftpane_width, bg=self.main_colour)
        self.leftui.grid_propagate(False) #to turn off auto scaling.
        self.leftui.columnconfigure(0, weight=1)

        self.toppane.add(self.leftui, weight=0) # 0 here, it stops the divider from moving itself. The divider pos is saved by prefs, this complicates it, so auto scaling based on text amount in source and dest folder is disabled.

        # This setups all the buttons and text
        self.first_page_buttons()

        # Start the grid setup
        imagegridframe = tk.Frame(self.toppane,bg=self.main_colour)
        imagegridframe.grid(row=0, column=2, sticky="NSEW") #this is in second so content frame inside this.
        self.imagegridframe = imagegridframe

        self.imagegrid = tk.Text(imagegridframe, wrap='word', borderwidth=0, highlightthickness=0, state="disabled", background=self.grid_background_colour)

        vbar = tk.Scrollbar(imagegridframe, orient='vertical',command=self.imagegrid.yview)
        vbar.grid(row=0, column=1, sticky='ns')
        self.imagegrid.configure(yscrollcommand=vbar.set)
        self.imagegrid.grid(row=0, column=0, sticky="NSEW")
        imagegridframe.rowconfigure(0, weight=1)
        imagegridframe.columnconfigure(0, weight=1)

        self.toppane.add(imagegridframe, weight=3)
        self.toppane.grid(row=0, column=0, sticky="NSEW")
        self.toppane.configure(style='Theme_dividers.TPanedwindow')

        self.columnconfigure(0, weight=10)
        self.columnconfigure(1, weight=0)
        self.rowconfigure(0, weight=10)
        self.rowconfigure(1, weight=0)

        self.protocol("WM_DELETE_WINDOW", self.closeprogram)
        self.winfo_toplevel().title("Simple Image Sorter: Multiview Edition v2.4")

        self.leftui.bind("<Configure>", self.buttonResizeOnWindowResize)
        self.buttonResizeOnWindowResize("a")    

    def first_page_buttons(self):
        self.panel = tk.Label(self.leftui, wraplength=350, justify="left", bg=self.main_colour,fg=self.text_colour, text="""Select a source directory to search for images in above.
The program will find all png, gif, jpg, bmp, pcx, tiff, Webp, and psds. It can has as many sub-folders as you like, the program will scan them all (except exclusions).
Enter a root folder to sort to for the "Destination field" too. The destination directory MUST have sub folders, since those are the folders that you will be sorting to.
\d (unless you delete prefs.json). Remember that it's one per line, no commas or anything.
You can change the hotkeys in prefs.json, just type a string of letters and numbers and it'll use that. It differentiates between lower and upper case (anything that uses shift), but not numpad.

By default the program will only load a portion of the images in the folder for performance reasons. Press the "Add Files" button to make it load another chunk. You can configure how many it adds and loads at once in the program.  

Right-click on Destination Buttons to show which images are assigned to them. (Does not show those that have already been moved)  
Right-click on Thumbnails to show a zoomable full view. You can also **rename** images from this view.  

Thanks to FooBar167 on stackoverflow for the advanced (and memory efficient!) Zoom and Pan tkinter class.
Thank you for using this program!""")
        
        self.panel.grid(row=3, column=0, columnspan=200, rowspan=200, sticky="NSEW")

        self.buttonframe = tk.Frame(master=self.leftui,bg=self.main_colour)
        self.buttonframe.grid(column=0, row=1, sticky="NSEW")
        self.buttonframe.columnconfigure(0, weight=1)

        self.entryframe = tk.Frame(master=self.leftui,bg=self.main_colour)
        self.entryframe.columnconfigure(1, weight=1)
        self.entryframe.grid(row=0, column=0, sticky="ew")

        self.excludebutton = tk.Button(self.entryframe, text="Manage Exclusions", command=self.excludeshow,
                                       bg=self.button_colour, fg=self.text_colour, activebackground = self.button_press_colour, activeforeground=self.pressed_text_colour)
        self.excludebutton.grid(row=0, column=2)

        self.sdpEntry = tk.Entry(self.entryframe, takefocus=False, 
                                 background=self.grid_background_colour, foreground=self.text_colour)  # scandirpathEntry
        self.sdpEntry.grid(row=0, column=1, sticky="ew", padx=2)
        self.sdpEntry.insert(0, self.source_folder)

        self.sdplabel = tk.Button(self.entryframe, text="Source Folder:", command=partial(self.filedialogselect, self.sdpEntry, "d"), 
                                  bg=self.button_colour, fg=self.text_colour, activebackground = self.button_press_colour, activeforeground=self.pressed_text_colour)
        self.sdplabel.grid(row=0, column=0, sticky="e")

        self.ddpEntry = tk.Entry(self.entryframe, takefocus=False, 
                                 background=self.grid_background_colour, foreground=self.text_colour)  # dest dir path entry
        self.ddpEntry.grid(row=1, column=1, sticky="ew", padx=2)
        self.ddpEntry.insert(0, self.destination_folder)

        self.ddplabel = tk.Button(self.entryframe, text="Destination Folder:", command=partial(self.filedialogselect, self.ddpEntry, "d"),
                                  bg=self.button_colour, fg=self.text_colour, activebackground = self.button_press_colour, activeforeground=self.pressed_text_colour)
        self.ddplabel.grid(row=1, column=0, sticky="e")

        self.activebutton = tk.Button(self.entryframe, text="New Session", command=partial(self.fileManager.validate, self),
                                      bg=self.button_colour, fg=self.text_colour, activebackground = self.button_press_colour, activeforeground=self.pressed_text_colour)
        ToolTip(self.activebutton,delay=1,msg="Start a new Session with the entered source and destination")
        self.activebutton.grid(row=1, column=2, sticky="ew")

        self.loadpathentry = tk.Entry(self.entryframe, takefocus=False, textvariable=self.sessionpathvar, 
                                      background=self.grid_background_colour, foreground=self.text_colour)
        self.loadpathentry.grid(row=3, column=1, sticky='ew', padx=2)

        self.loadbutton = tk.Button(self.entryframe, text="Load Session", command=self.fileManager.loadsession,
                                    bg=self.button_colour, fg=self.text_colour, activebackground = self.button_press_colour, activeforeground=self.pressed_text_colour)
        ToolTip(self.loadbutton,delay=1,msg="Load and start the selected session data.")
        self.loadbutton.grid(row=3, column=2, sticky='ew')

        self.loadfolderbutton = tk.Button(self.entryframe, text="Session Data:", command=partial(self.filedialogselect, self.loadpathentry, "f"),
                                          bg=self.button_colour, fg=self.text_colour, activebackground = self.button_press_colour, activeforeground=self.pressed_text_colour)
        ToolTip(self.loadfolderbutton,delay=1,msg="Select a session json file to open.")
        self.loadfolderbutton.grid(row=3, column=0, sticky='e')

        # Add a button for sortbydate option
        self.sortbydate_button = ttk.Checkbutton(self.leftui, text="Sort by Date", variable=self.sortbydatevar, onvalue=True, offvalue=False, 
                                                 command=self.sortbydatevar,style="Theme_checkbox.TCheckbutton")
        self.sortbydate_button.grid(row=2, column=0, sticky="w", padx=25)

        #If it is set in prefs, this makes the buttons blink when hovered over.
        if self.interactive_buttons:
            #Option for making the buttons change color on hover
            self.excludebutton.bind("<Enter>", lambda e: self.excludebutton.config(bg=self.button_press_colour, fg=self.pressed_text_colour))
            
            self.excludebutton.bind("<Leave>", lambda e: self.excludebutton.config(bg=self.button_colour, fg=self.text_colour)) 
            self.activebutton.bind("<Enter>", lambda e: self.activebutton.config(bg=self.button_press_colour, fg=self.pressed_text_colour))
            self.activebutton.bind("<Leave>", lambda e: self.activebutton.config(bg=self.button_colour, fg=self.text_colour))

            self.sdpEntry.bind("<FocusIn>", lambda e: self.sdpEntry.config(bg=self.text_field_colour, fg=self.text_field_text_colour))
            self.sdpEntry.bind("<FocusOut>", lambda e: self.sdpEntry.config(bg=self.grid_background_colour, fg=self.text_colour))

            self.ddpEntry.bind("<FocusIn>", lambda e: self.ddpEntry.config(bg=self.text_field_colour, fg=self.text_field_text_colour))
            self.ddpEntry.bind("<FocusOut>", lambda e: self.ddpEntry.config(bg=self.grid_background_colour, fg=self.text_colour))

            self.sdplabel.bind("<Enter>", lambda e: self.sdplabel.config(bg=self.button_press_colour, fg=self.pressed_text_colour))
            self.sdplabel.bind("<Leave>", lambda e: self.sdplabel.config(bg=self.button_colour, fg=self.text_colour))

            self.ddplabel.bind("<Enter>", lambda e: self.ddplabel.config(bg=self.button_press_colour, fg=self.pressed_text_colour))
            self.ddplabel.bind("<Leave>", lambda e: self.ddplabel.config(bg=self.button_colour, fg=self.text_colour))

            self.loadbutton.bind("<Enter>", lambda e: self.loadbutton.config(bg=self.button_press_colour, fg=self.pressed_text_colour))
            self.loadbutton.bind("<Leave>", lambda e: self.loadbutton.config(bg=self.button_colour, fg=self.text_colour))

            self.loadfolderbutton.bind("<Enter>", lambda e: self.loadfolderbutton.config(bg=self.button_press_colour, fg=self.pressed_text_colour))
            self.loadfolderbutton.bind("<Leave>", lambda e: self.loadfolderbutton.config(bg=self.button_colour, fg=self.text_colour))

            self.loadpathentry.bind("<FocusIn>", lambda e: self.loadpathentry.config(bg=self.text_field_colour, fg=self.text_field_text_colour))
            self.loadpathentry.bind("<FocusOut>", lambda e: self.loadpathentry.config(bg=self.grid_background_colour, fg=self.text_colour))

    def isnumber(self, char):
        return char.isdigit()

    def showall(self):
        for x in self.fileManager.imagelist:
            if x.guidata["show"] == False:
                x.guidata["frame"].grid()
        self.hidemoved()
        self.hideassignedsquare(self.fileManager.imagelist)

    def closeprogram(self):
        if self.fileManager.hasunmoved:
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
        excludetext = tkst.ScrolledText(excludewindow, bg=self.main_colour, fg=self.text_colour)
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

    def makegridsquare(self, parent, imageobj, setguidata):
        frame = tk.Frame(parent, borderwidth=0, bg=self.square_colour,
                         highlightthickness = 0, highlightcolor=self.imageborder_selected_colour, padx = 0, pady = 0) #unclear if width and height needed
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
                               height=self.thumbnailsize,bg=self.square_colour, highlightthickness=self.image_border_thickness, highlightcolor=self.imageborder_selected_colour, highlightbackground = self.imageborder_default_colour) #The gridbox color.
            canvas.grid(column=0, row=0, sticky="NSEW")
            tooltiptext=tk.StringVar(frame,self.tooltiptext(imageobj))
            ToolTip(canvas,msg=tooltiptext.get,delay=1)

            frame.rowconfigure(0, weight=4)
            frame.rowconfigure(1, weight=1)

            canvas.create_image(
                self.thumbnailsize/2+self.image_border_thickness, self.thumbnailsize/2+self.image_border_thickness, anchor="center", image=img) #If you use gridboxes, you must +1 to thumbnailsize/2, so it counteracts the highlighthickness.
            
            # Create a frame for the Checkbutton to control its height
            check_frame = tk.Frame(frame, height=self.checkbox_height,bg=self.grid_background_colour, highlightthickness=self.text_box_thickness, highlightcolor=self.text_box_selection_colour, highlightbackground=self.text_box_colour) 
            check_frame.grid(column=0, row=1, sticky="NSEW")  # Place the frame in the grid
            check_frame.grid_propagate(False)
            check = ttk.Checkbutton(check_frame, textvariable=truncated_name_var, variable=imageobj.checked, onvalue=True, offvalue=False, style="Theme_square.TCheckbutton")
            check.grid(sticky="NSEW")

            if(setguidata):  # save the data to the image obj to both store a reference and for later manipulation
                imageobj.setguidata(
                    {"img": img, "frame": frame, "canvas": canvas, "check": check, "show": True,"tooltip":tooltiptext})
            
            # anything other than rightclicking toggles the checkbox, as we want.
            canvas.bind("<Button-1>", partial(bindhandler, check, "invoke"))
            canvas.bind(
                "<Button-3>", partial(self.displayimage, imageobj))
            check.bind("<Button-3>", partial(self.displayimage, imageobj))

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
                    highlightbackground="brown", highlightthickness=2)
        except Exception as e:
            logger.error(e)
        return frame

    def displaygrid(self, imagelist, range):
        for i in range:
            gridsquare = self.makegridsquare(
                self.imagegrid, imagelist[i], True)
            self.gridsquarelist.append(gridsquare)
            self.imagegrid.window_create("insert", window=gridsquare,  padx=self.gridsquare_padx, pady=self.gridsquare_pady)

    def buttonResizeOnWindowResize(self, b=""):
        if len(self.buttons) > 0:
            for x in self.buttons:
                x.configure(wraplength=(self.buttons[0].winfo_width()-1))

    def truncate_text(self, imageobj): #max_length must be over 3+extension or negative indexes happen.
        filename = imageobj.name.get()
        base_name, ext = os.path.splitext(filename)
        smallfont = self.smallfont
        text_width = smallfont.measure(filename)

        if text_width+24 <= self.thumbnailsize:

            return filename # Return whole filename
        
        ext = ".." + ext
        
        while True: # Return filename that has been truncated.
            test_text = base_name + ext # Test with one less character
            text_width = smallfont.measure(test_text)
            if text_width+24 < self.thumbnailsize:  # Reserve space for ellipsis
                break
            base_name = base_name[:-1]
        return test_text
    
    def displayimage(self, imageobj, a):
        path = imageobj.path

        if hasattr(self, 'imagewindow'):
            self.second_window.destroy()

        self.second_window  = tk.Toplevel()
        second_window = self.second_window
        second_window.configure(background=self.main_colour)
        second_window.rowconfigure(1, weight=1)
        second_window.columnconfigure(0, weight=1)
        second_window.title("Image: " + path)
        second_window.geometry(self.viewer_geometry)
        second_window.bind("<Button-3>", self.save_viewer_geometry)
        second_window.protocol("WM_DELETE_WINDOW", self.save_viewer_geometry)
        second_window.obj = imageobj
        second_window.transient(self)

        self.Image_frame = CanvasImage(second_window, self.canvasimage_background, imageobj, self)
        self.Image_frame.grid(column=0, row=1)
        self.Image_frame.rescale(min(second_window.winfo_width()/self.Image_frame.imwidth, second_window.winfo_height()/self.Image_frame.imheight))

        renameframe = tk.Frame(second_window)
        renameframe.columnconfigure(1, weight=1)
        renameframe.grid(column=0, row=0, sticky="EW")

        namelabel = tk.Label(renameframe, text="Image Name:")
        namelabel.grid(column=0, row=0, sticky="W")

        nameentry = tk.Entry(renameframe, textvariable=imageobj.name, takefocus=False)
        nameentry.grid(row=0, column=1, sticky="EW")
        
    def save_viewer_geometry(self,):
        if hasattr(self, 'second_window') and self.second_window and self.second_window.winfo_exists():
            self.viewer_geometry = self.second_window.winfo_geometry()
            self.checkdupename(self.second_window.obj)
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
        smallfont = self.smallfont
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
                btn.bind("<Enter>", lambda e, btn=btn: btn.config(bg=self.text_colour, fg=self.main_colour))
                btn.bind("<Leave>", lambda e, btn=btn: btn.config(bg=self.button_colour, fg=self.text_colour))  # Reset to original colors
            self.entryframe.grid_remove()
        # options frame
        optionsframe = tk.Frame(self.leftui,bg=self.main_colour)
        optionsframe.columnconfigure(0, weight=1)
        optionsframe.columnconfigure(1, weight=3)
        optionsframe.grid(row=0, column=0, sticky="ew")

        self.squaresperpageentry = tk.Entry(
            optionsframe, textvariable=self.squaresperpage, takefocus=False, background=self.grid_background_colour, foreground=self.text_colour)
        if self.squaresperpage.get() < 0: #this wont let you save -1
            self.squaresperpage.set(1)
        ToolTip(self.squaresperpageentry,delay=1,msg="How many more images to add when Load Images is clicked")
        self.squaresperpageentry.grid(row=2, column=0, sticky="EW",)
        for n in range(0, itern):
            self.squaresperpageentry.unbind(hotkeys[n])

        self.addpagebut = tk.Button(
            optionsframe, text="Load More Images", command=self.addpage,bg=self.button_colour, fg=self.text_colour, activebackground = self.button_press_colour, activeforeground=self.pressed_text_colour)
        ToolTip(self.addpagebut,msg="Add another batch of files from the source folders.", delay=1)
        self.addpagebut.grid(row=2, column=1, sticky="EW")
        self.addpagebutton = self.addpagebut

        # save button
        self.savebutton = tk.Button(optionsframe,text="Save Session",command=partial(self.fileManager.savesession,True),bg=self.button_colour, fg=self.text_colour, activebackground = self.button_press_colour, activeforeground=self.pressed_text_colour)
        ToolTip(self.savebutton,delay=1,msg="Save this image sorting session to a file, where it can be loaded at a later time. Assigned destinations and moved images will be saved.")
        self.savebutton.grid(column=0,row=0,sticky="ew")
        self.savebutton.configure(relief = tk.RAISED)

        self.moveallbutton = tk.Button(
            optionsframe, text="Move All", command=self.fileManager.moveall,bg=self.button_colour, fg=self.text_colour, activebackground = self.button_press_colour, activeforeground=self.pressed_text_colour)
        ToolTip(self.moveallbutton,delay=1,msg="Move all images to their assigned destinations, if they have one.")
        self.moveallbutton.grid(column=1, row=3, sticky="EW")

        self.clearallbutton = tk.Button(
            optionsframe, text="Clear Selection", command=self.fileManager.clear,bg=self.button_colour, fg=self.text_colour, activebackground = self.button_press_colour, activeforeground=self.pressed_text_colour)
        ToolTip(self.clearallbutton,delay=1,msg="Clear your selection on the grid and any other windows with checkable image grids.")
        self.clearallbutton.grid(row=3, column=0, sticky="EW")

        hideonassign = tk.Checkbutton(optionsframe, text="Hide Assigned",
                                      variable=self.hideonassignvar, onvalue=True, offvalue=False, bg=self.button_colour,fg=self.text_colour)
        ToolTip(hideonassign,delay=1,msg="When checked, images that are assigned to a destination be hidden from the grid.")
        hideonassign.grid(column=1, row=0, sticky='W')
        self.hideonassign = hideonassign
        
        showhidden = tk.Checkbutton(optionsframe, text="Show Hidden Images",
                                    variable=self.showhiddenvar, onvalue=True, offvalue=False, command=self.showhiddensquares, bg=self.button_colour,fg=self.text_colour)
        showhidden.grid(column=0, row=1, sticky="W")
        self.showhidden = showhidden

        hidemoved = tk.Checkbutton(optionsframe, text="Hide Moved",
                                   variable=self.hidemovedvar, onvalue=True, offvalue=False, command=self.hidemoved, bg=self.button_colour,fg=self.text_colour)
        ToolTip(hidemoved,delay=1,msg="When checked, images that are moved will be hidden from the grid.")
        hidemoved.grid(column=1, row=1, sticky="w")

        if self.interactive_buttons:
            #Option for making the buttons change color on hover
            self.clearallbutton.bind("<Enter>", lambda e: self.clearallbutton.config(bg=self.button_press_colour, fg=self.pressed_text_colour))
            self.clearallbutton.bind("<Leave>", lambda e: self.clearallbutton.config(bg=self.button_colour, fg=self.text_colour))
    
            self.addpagebut.bind("<Enter>", lambda e: self.addpagebut.config(bg=self.button_press_colour, fg=self.pressed_text_colour))
            self.addpagebut.bind("<Leave>", lambda e: self.addpagebut.config(bg=self.button_colour, fg=self.text_colour))
    
            self.moveallbutton.bind("<Enter>", lambda e: self.moveallbutton.config(bg=self.button_press_colour, fg=self.pressed_text_colour))
            self.moveallbutton.bind("<Leave>", lambda e: self.moveallbutton.config(bg=self.button_colour, fg=self.text_colour))
    
            self.savebutton.bind("<Enter>", lambda e: self.savebutton.config(bg=self.button_press_colour, fg=self.pressed_text_colour))
            self.savebutton.bind("<Leave>", lambda e: self.savebutton.config(bg=self.button_colour, fg=self.text_colour))
    
            self.squaresperpageentry.bind("<FocusIn>", lambda e: self.squaresperpageentry.config(bg=self.text_field_colour, fg=self.text_field_text_colour))
            self.squaresperpageentry.bind("<FocusOut>", lambda e: self.squaresperpageentry.config(bg=self.grid_background_colour, fg=self.text_colour))

        self.bind_all("<Button-1>", self.setfocus)

    def handle_setdestination_call(self, state, x=None, event=None):
        if x:
            self.fileManager.setDestination(x, event)
        self.key_pressed = state
    def setfocus(self, event):
        event.widget.focus_set()

    # todo: make 'moved' and 'assigned' lists so the show all etc just has to iterate over those.
    def hideassignedsquare(self, imlist):
        if self.hideonassignvar.get():
            for x in imlist:
                if x.dest != "":
                    self.imagegrid.window_configure(
                        x.guidata["frame"], window='')
                    x.guidata["show"] = False

    def hideallsquares(self):
        for x in self.gridsquarelist:
            self.imagegrid.window_configure(x, window="")

    def showhiddensquares(self):
        if self.showhiddenvar.get():
            for x in self.gridsquarelist:
                try:
                    x.obj.guidata["frame"] = x
                    self.imagegrid.window_create("insert", window=x)
                except:
                    pass

        else:
            self.hideassignedsquare(self.fileManager.imagelist)
            self.hidemoved()

    def showunassigned(self, imlist):
        for x in imlist:
            if x.guidata["show"] or x.dest == "":
                self.imagegrid.window_create(
                    "insert", window=x.guidata["frame"])

    def showthisdest(self, dest, *args): #If a destination window is already open, just update it.

        self.dest = dest['path']
        if not hasattr(self, 'destwindow') or not self.destwindow or not self.destwindow.winfo_exists():
            #Make new window
            self.destwindow = tk.Toplevel()
            self.destwindow.columnconfigure(0, weight=1)
            self.destwindow.rowconfigure(0, weight=1)
            self.destwindow.winfo_toplevel().title("Files designated for " + dest['path'])
            self.destwindow.geometry(str(int(self.winfo_screenwidth() * 0.80)) + "x" + str(self.winfo_screenheight() - 120) + "+365+60")
            self.destwindow.bind("<Button-3>", self.close_destination_window)
            self.destwindow.protocol("WM_DELETE_WINDOW", self.close_destination_window)
            self.destwindow.transient(self)

            if self.destpane_geometry != 0:
                try:
                    self.destwindow.geometry(self.destpane_geometry)
                except Exception as e:
                    logger.error(f"Couldn't load destwindow geometry")

            self.destgrid = tk.Text(self.destwindow, wrap='word', borderwidth=0, 
                                    highlightthickness=0, state="disabled", background=self.main_colour)
            self.destgrid.grid(row=0, column=0, sticky="NSEW")

            #scrollbars
            vbar = tk.Scrollbar(self.destwindow, orient='vertical',
                                command=lambda *args: throttled_yview(self.destgrid, self.page_mode, *args))
            vbar.grid(row=0, column=1, sticky='ns')
            self.destgrid['yscrollcommand'] = vbar.set  # Link scrollbar to text widget
            for x in self.fileManager.imagelist:
                if x.dest == dest['path']:
                    newframe = self.makegridsquare(self.destgrid, x, False)
                    self.destgrid.window_create("insert", window=newframe)
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

    def hidemoved(self):
        if self.hidemovedvar.get():
            for x in self.fileManager.imagelist:
                if x.moved:
                    try:
                        self.imagegrid.window_configure(
                            x.guidata["frame"], window='')
                    except Exception as e:
                        pass

    def addpage(self, *args):
        filelist = self.fileManager.imagelist
        if len(self.gridsquarelist) < len(filelist):
            listmax = min(len(self.gridsquarelist) +
                          self.squaresperpage.get(), len(filelist))
            ran = range(len(self.gridsquarelist), listmax)
            sublist = filelist[ran[0]:listmax]
            print(f"Loading: {len(sublist)}")
            self.fileManager.generatethumbnails(sublist)
            self.displaygrid(self.fileManager.imagelist, ran)
        else:
            self.addpagebutton.configure(text="No More Images!",background="#DD3333")

    def checkdupename(self, imageobj):
        if imageobj.name.get() in self.fileManager.existingnames:
            imageobj.dupename=True
            imageobj.guidata["frame"].configure(
                    highlightbackground="yellow", highlightthickness=2)
            

        else:
            imageobj.dupename=False
            imageobj.guidata["frame"].configure(highlightthickness=0)
            self.fileManager.existingnames.add(imageobj.name.get())
        imageobj.guidata['tooltip'].set(self.tooltiptext(imageobj))
last_scroll_time = None
last_scroll_time2 = None
current_scroll_direction = -1
flag1 = []
flag_len = 1

def throttled_yview(widget, page_mode, *args):
    """Throttle scroll events for both MouseWheel and Scrollbar slider"""
    global flag1
    global flag_len
    #global last_scroll_time
    #global throttle_time
    #now = time.time()
    #if not last_scroll_time:
    #    last_scroll_time = now
    #else:
    #    if (now - last_scroll_time) > 0.0:  # 100ms throttle
    #        last_scroll_time = now
#
    #    else:
    #        print("GET THROTTLED IDIOT!!!!!")
    #        return
    print(len(flag1))
    
    
    if len(flag1) > flag_len:
        return
    flag1.append("a")
    if args[0] == "scroll":
        current_view = widget.yview()
        
        if int(args[1]) > 0:
            direction = 1
        else:
            direction = -1

        new_position = current_view[0] + (direction * 0.01)
        new_position = max(0.0, min(1.0, new_position))

        if page_mode:
            widget.yview(*args)

        else:
            widget.update()
            widget.yview_moveto(new_position)            

    elif args[0] == "moveto":
        moveto = float(args[1])
        widget.yview_moveto(moveto)
    widget.update()
    flag1.pop(0)


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
    global current_scroll_direction
    global flag1
    global flag_len
    widget = args[0]
    command = args[1]
    global last_scroll_time2
    global throttle_time
    throttle_time = 0.01
    now = time.time()
    if last_scroll_time2 is None or (now - last_scroll_time2) > throttle_time:  # 100ms throttle
            last_scroll_time2 = now
    if command == "scroll1":
        widget.yview_scroll(-1*floor(args[2].delta/120), "units")
        widget.yview_scroll(40*1*floor(args[2].delta/120), "pixels") # counteracts stupid scroll by tk.text get f##cked!
        
    if command == "scroll":
        widget.yview_scroll(-1*floor(args[2].delta/120), "units") 

    elif command == "invoke":
        if last_scroll_time2 is None or (now - last_scroll_time2) < throttle_time:  # 100ms throttle
            last_scroll_time2 = now
            widget.invoke()

    elif command == "scroll1":
        pass