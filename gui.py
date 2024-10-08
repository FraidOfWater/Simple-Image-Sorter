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

button_colour = 'black'
background_colour = 'black'
text_colour = 'white'

canvas_colour = 'black'
active_background_colour = 'white'
active_foreground_colour = 'black'
divider_colour = 'grey'

textboxpos = "N"
textlength = 33 

gridsquare_padx = 5
gridsquare_pady = 5
checkbox_height = 24

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

#script_dir = os.path.dirname(os.path.abspath(__file__))
#prefs_path = os.path.join(script_dir, "prefs.json")

def saveprefs(manager, gui):
    
    sdp = gui.sdpEntry.get() if os.path.exists(gui.sdpEntry.get()) else ""
    ddp = gui.ddpEntry.get() if os.path.exists(gui.ddpEntry.get()) else ""

    save = {
        "srcpath": sdp, 
        "despath": ddp, 
        "exclude": manager.exclude, 
        "hotkeys": gui.hotkeys, 
        "thumbnailsize": gui.thumbnailsize, 
        "threads": manager.threads, 
        "hideonassign": gui.hideonassignvar.get(), 
        "hidemoved": gui.hidemovedvar.get(), 
        "sortbydate": gui.sortbydatevar.get(), 
        "squaresperpage": gui.squaresperpage.get(), 
        "geometry": gui.winfo_geometry(),
        "imagewindowgeometry": gui.imagewindowgeometry, 
        "lastsession": gui.sessionpathvar.get(),
        "autosave":manager.autosave,
        "toppane_width":gui.leftui.winfo_width()
        }
    
    try: #Try to save the preference to prefs.json
        with open(prefs_path, "w+") as savef:
            json.dump(save, savef,indent=4, sort_keys=True)
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
        
        #Initialization for view-button values
        self.show_unassigned = tk.BooleanVar()
        self.show_unassigned.set(True)
        self.show_assigned = tk.BooleanVar()
        self.show_moved = tk.BooleanVar()
        #self.show_all = tk.BooleanVar()
        
        #Initialization for view-button
        self.variable = tk.StringVar()
        self.variable.trace_add("write", self.on_option_selected)
        
        #Initialization for lists.
        #Main window renderlist
        self.gridsquarelist = []
        self.displayedlist = {}
        
        #Main window sorted lists
        self.unassigned_squarelist = []
        self.assigned_squarelist = []
        self.moved_squarelist = []    
        self.running = []
        
        #Focused destination window information
        self.active_dest_squarelist = []
        self.dest_active_window = None
        self.active_dest_path = None
        self.active_dest_grid = None
        
        #Destination window list
        self.destination_windows = []
        
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
        
        # store the reference to the file manager class.
        self.fileManager = fileManager
        self.geometry(str(self.winfo_screenwidth()-5)+"x" +
                      str(self.winfo_screenheight()-120))
        self.geometry("+0+60")
        self.buttons = []
        self.hotkeys = "123456qwerty7890uiop[asdfghjkl;zxcvbnm,.!@#$%^QWERT&*()_UIOPASDFGHJKLZXCVBNM<>"

        #Default toppane width
        self.toppane_width = 363
        
        # Paned window that holds the almost top level stuff.
        self.toppane = Panedwindow(self, orient="horizontal")
        
        # Frame for the left hand side that holds the setup and also the destination buttons.
        self.leftui = tk.Frame(self.toppane, width=self.toppane_width, bg=background_colour)
        #self.leftui.grid(row=0, column=0, sticky="NESW")
        self.toppane.grid_propagate(False)
        self.leftui.grid_propagate(False) #to turn off auto scaling.
        
        self.leftui.columnconfigure(0, weight=1)
        self.toppane.add(self.leftui, weight=0)
        
        
        #Add a checkbox to check for sorting preference.
        style = ttk.Style()
        style.configure("darkmode.TCheckbutton", background="black", foreground="white", highlightthickness = 0)
        self.sortbydatecheck = ttk.Checkbutton(self.leftui, text="Sort by Date", variable=self.sortbydatevar, onvalue=True, offvalue=False, command=self.sortbydatevar,style="darkmode.TCheckbutton")
        self.sortbydatecheck.grid(row=2, column=0, sticky="w", padx=25)
        
        self.panel = tk.Label(self.leftui, wraplength=300, justify="left", text="Text",bg=background_colour,fg=text_colour)
        self.panel.grid(row=3, column=0, columnspan=200,
                        rowspan=200, sticky="NSEW")
        self.columnconfigure(0, weight=1)

        self.buttonframe = tk.Frame(master=self.leftui,bg=background_colour)
        self.buttonframe.grid(
            column=0, row=1, sticky="NSEW")
        self.buttonframe.columnconfigure(0, weight=1)
        
        self.entryframe = tk.Frame(master=self.leftui,bg=background_colour)
        self.entryframe.columnconfigure(1, weight=1)
        
        self.sdpEntry = tk.Entry(
            self.entryframe, takefocus=False, background=background_colour, foreground=text_colour)  # scandirpathEntry
        self.ddpEntry = tk.Entry(
            self.entryframe, takefocus=False, background=background_colour, foreground=text_colour)  # dest dir path entry

        self.sdplabel = tk.Button(
            self.entryframe, text="Source Folder:", command=partial(self.filedialogselect, self.sdpEntry, "d"), bg=background_colour, fg=text_colour)
        
        self.ddplabel = tk.Button(
            self.entryframe, text="Destination Folder:", command=partial(self.filedialogselect, self.ddpEntry, "d"),bg=background_colour, fg=text_colour)
        
        self.activebutton = tk.Button(
            self.entryframe, text="New Session", command=partial(fileManager.validate, self),bg=background_colour, fg=text_colour)
        ToolTip(self.activebutton,delay=1,msg="Start a new Session with the entered source and destination")
        
        self.loadpathentry = tk.Entry(
            self.entryframe, takefocus=False, textvariable=self.sessionpathvar, background=background_colour, foreground=text_colour)
        
        self.loadbutton = tk.Button(
            self.entryframe, text="Load Session", command=self.fileManager.loadsession,bg=background_colour, fg=text_colour)
        ToolTip(self.loadbutton,delay=1,msg="Load and start the selected session data.")
        
        self.loadfolderbutton = tk.Button(self.entryframe, text="Session Data:", command=partial(
            self.filedialogselect, self.loadpathentry, "f"),bg=background_colour, fg=text_colour)
        ToolTip(self.loadfolderbutton,delay=1,msg="Select a session json file to open.")
        
        self.loadfolderbutton.grid(row=3, column=0, sticky='ew')
        
        self.loadbutton.grid(row=3, column=2, sticky='ew')
        
        self.loadpathentry.grid(row=3, column=1, sticky='ew', padx=2)
        
        self.sdplabel.grid(row=0, column=0, sticky="ew")
        
        self.sdpEntry.grid(row=0, column=1, sticky="ew", padx=2)
        
        self.ddplabel.grid(row=1, column=0, sticky="ew")
        
        self.ddpEntry.grid(row=1, column=1, sticky="ew", padx=2)
        
        self.activebutton.grid(row=1, column=2, sticky="ew")
        

        self.excludebutton = tk.Button(
            self.entryframe, text="Manage Exclusions", command=self.excludeshow,bg=background_colour, fg=text_colour)
        
        self.excludebutton.grid(row=0, column=2)

        """ #Option for making the buttons change color on hover
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
        """
        
        # show the entry frame, sticky it to the west so it mostly stays put.
        self.entryframe.grid(row=0, column=0, sticky="ew")
        
        # Finish setup for the left hand bar.
        # Start the grid setup
        imagegridframe = tk.Frame(self.toppane,bg=background_colour)
        imagegridframe.grid(row=0, column=1, sticky="NSEW")
        
        # Replacing Text widget with Canvas for image grid
        self.imagegrid = tk.Text(
            imagegridframe, wrap ='word', borderwidth=0, highlightthickness=0, state="disabled", background=background_colour)

        vbar = tk.Scrollbar(imagegridframe, orient='vertical',command=lambda *args: throttled_yview(self.imagegrid, *args))
        vbar.grid(row=0, column=1, sticky='ns')
        
        self.imagegrid.configure(yscrollcommand=vbar.set)
        self.imagegrid.grid(row=0, column=0, sticky="NSEW")
        imagegridframe.rowconfigure(0, weight=1)
        imagegridframe.columnconfigure(0, weight=1)
        style11 = ttk.Style()

        style11.configure('Custom.TPanedwindow', background=divider_colour)  # No border for the PanedWindow
        
        self.toppane.add(imagegridframe, weight=3)
        self.toppane.grid(row=0, column=0, sticky="NSEW")
        self.toppane.configure(style='Custom.TPanedwindow')
        self.columnconfigure(0, weight=10)
        self.columnconfigure(1, weight=0)
        self.rowconfigure(0, weight=10)
        self.rowconfigure(1, weight=0)
        
        self.protocol("WM_DELETE_WINDOW", self.closeprogram)
        
        self.winfo_toplevel().title("Simple Image Sorter: Multiview Edition v2.4")
        
    def exclude_on_enter(self, event):
        self.excludebutton.config(bg=text_colour, fg=background_colour)
    def exclude_on_leave(self, event):
        self.excludebutton.config(bg=background_colour, fg=text_colour)

    def active_on_enter(self,event):
        self.activebutton.config(bg=text_colour, fg=button_colour)
    def active_on_leave(self,event):
        self.activebutton.config(bg=button_colour, fg=text_colour)

    def sdpEntry_on_enter(self,event):
        self.sdpEntry.config(bg=text_colour, fg=button_colour)
    def sdpEntry_on_leave(self,event):
        self.sdpEntry.config(bg=button_colour, fg=text_colour)

    def ddpEntry_on_enter(self,event):
        self.ddpEntry.config(bg=text_colour, fg=button_colour)
    def ddpEntry_on_leave(self,event):
        self.ddpEntry.config(bg=button_colour, fg=text_colour)

    def sdplabel_on_enter(self,event):
        self.sdplabel.config(bg=text_colour, fg=button_colour)
    def sdplabel_on_leave(self,event):
        self.sdplabel.config(bg=button_colour, fg=text_colour)
        
    def ddplabel_on_enter(self,event):
        self.ddplabel.config(bg=text_colour, fg=button_colour)
    def ddplabel_on_leave(self, event):
        self.ddplabel.config(bg=button_colour, fg=text_colour)

    def loadbutton_on_enter(self,event):
        self.loadbutton.config(bg=text_colour, fg=button_colour)
    def loadbutton_on_leave(self, event):
        self.loadbutton.config(bg=button_colour, fg=text_colour)

    def loadfolderbutton_on_enter(self,event):
        self.loadfolderbutton.config(bg=text_colour, fg=button_colour)
    def loadfolderbutton_on_leave(self, event):
        self.loadfolderbutton.config(bg=button_colour, fg=text_colour)

    def loadpathentry_on_enter(self,event):
        self.loadpathentry.config(bg=text_colour, fg=button_colour)
    def loadpathentry_on_leave(self, event):
        self.loadpathentry.config(bg=button_colour, fg=text_colour)

        

    def isnumber(self, char):
        return char.isdigit()

    def closeprogram(self):
        if len(self.assigned_squarelist) != 0:
            if askokcancel("Designated but Un-Moved files, really quit?","You have destination designated, but unmoved files. (Simply cancel and Move All if you want)"):
                try:
                    self.saveimagewindowgeo()
                except Exception as e:
                    pass
                saveprefs(self.fileManager, self)
                self.destroy()
                exit(0)
        else:
            try:
                self.saveimagewindowgeo()
            except Exception as e:
                pass
            saveprefs(self.fileManager, self)
            self.destroy()
            exit(0)


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
        except:
            pass


    def tooltiptext(self,imageobject):
        text=""
        text += "Leftclick to select this for assignment. Rightclick to open full view"
        return text
    

    def makegridsquare(self, parent, imageobj, setguidata):
        frame = tk.Frame(parent, borderwidth=0, bg=background_colour, highlightthickness = 1, highlightcolor='grey')
        frame.obj = imageobj
        truncated_filename = self.truncate_text(frame, imageobj, textlength)
        truncated_name_var = tk.StringVar(frame, value=truncated_filename)
        frame.obj2 = truncated_name_var
        frame.grid_propagate(True)
        
        try:
            if setguidata:
                if not os.path.exists(imageobj.thumbnail):
                    self.fileManager.makethumb(imageobj)
                try:
                    buffer = pyvips.Image.new_from_file(imageobj.thumbnail)
                    img = ImageTk.PhotoImage(Image.frombuffer(
                        "RGB", [buffer.width, buffer.height], buffer.write_to_memory()))
                except:  # Pillow fallback
                    img = ImageTk.PhotoImage(Image.open(imageobj.thumbnail))
            else:
                img = imageobj.guidata['img']

            canvas = tk.Canvas(frame, width=self.thumbnailsize, 
                               height=self.thumbnailsize,bg=background_colour, highlightthickness=1, highlightcolor='grey') #The gridbox color.
            tooltiptext=tk.StringVar(frame,self.tooltiptext(imageobj))

            ToolTip(canvas,msg=tooltiptext.get,delay=1)
            frame.canvas = canvas
            
            canvas_image_id = canvas.create_image(
                self.thumbnailsize/2+1, self.thumbnailsize/2+1, anchor="center", image=img) #If you use gridboxes, you must +1 to thumbnailsize/2, so it counteracts the highlighthickness.
            frame.canvas_image_id = canvas_image_id
            
            # Create a frame for the Checkbutton to control its height
            check_frame = tk.Frame(frame, height=checkbox_height,bg=background_colour)  # Set a fixed height (e.g., 30 pixels)
            check_frame.grid(column=0, row=1, sticky="NSEW")  # Place the frame in the grid

            check_frame.grid_propagate(True)
            
            check = ttk.Checkbutton(check_frame, textvariable=truncated_name_var, variable=imageobj.checked, onvalue=True, offvalue=False, width=textlength,style="darkmode.TCheckbutton")
            check.grid(sticky="NSEW")
            
            canvas.grid(column=0, row=0, sticky="NSEW")
            check.grid(column=0, row=1, sticky=textboxpos)
            
            frame.rowconfigure(0, weight=4)
            frame.rowconfigure(1, weight=1)
            frame.config(height=self.thumbnailsize+12) #might not be needed? unclear what does
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
            frame.configure(height=self.thumbnailsize+10)
        except Exception as e:
            logging.error(e)
        return frame
    
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
    def displayimage(self, imageobj, a):
        path = imageobj.path
        # Check if the second window exists and is open
        if not hasattr(self, 'second_window') or not self.second_window or not self.second_window.winfo_exists():
            # Create a new window if it doesn't exist
            self.second_window = tk.Toplevel()
            second_window = self.second_window
            second_window.configure(background=background_colour)
            second_window.rowconfigure(1, weight=1)
            second_window.columnconfigure(0, weight=1)
            second_window.title("Image: " + path)
            second_window.geometry(self.imagewindowgeometry)
            second_window.bind("<Button-3>", partial(bindhandler, second_window, "destroy"))
            second_window.protocol("WM_DELETE_WINDOW", self.saveimagewindowgeo)

            renameframe = tk.Frame(second_window)
            renameframe.grid(column=0, row=0, sticky="EW")
            renameframe.columnconfigure(1, weight=1)

            namelabel = tk.Label(renameframe, text="Image Name:")
            namelabel.grid(column=0, row=0, sticky="W")

            self.name_var = tk.StringVar(value=imageobj.name)
            nameentry = tk.Entry(renameframe, textvariable=imageobj.name, takefocus=False)
            nameentry.grid(row=0, column=1, sticky="EW")

            second_window.obj = imageobj

            # Create the initial Image_frame
            self.Image_frame = CanvasImage(self.second_window, path, self.imagewindowgeometry.split('+')[0], canvas_colour)
            self.Image_frame.grid(row=1, column=0, sticky='nswe')  # Initialize Frame grid statement in canvasimage, Add to main window grid
            self.Image_frame.rescale(min(second_window.winfo_width() / self.Image_frame.imwidth, ((second_window.winfo_height()-renameframe.winfo_height()) / (self.Image_frame.imheight))))  # Scales to the window
            self.Image_frame.center_image()
        else:
            # If the window exists, remove the previous Image_frame from the grid
            self.imagewindowgeometry = self.second_window.winfo_geometry()
            self.Image_frame.destroy()
            del self.Image_frame  # Remove the previous image frame from the grid

            # Create a new Image_frame with the new image
            self.Image_frame = CanvasImage(self.second_window, path, self.imagewindowgeometry.split('+')[0], canvas_colour)
            self.Image_frame.grid(row=1, column=0, sticky='nswe')  # Add the new image frame to the grid
            self.Image_frame.rescale(min(self.second_window.winfo_width() / self.Image_frame.imwidth, self.second_window.winfo_height() / self.Image_frame.imheight))  # Scales to the window
            self.Image_frame.center_image()


    def saveimagewindowgeo(self):
        self.imagewindowgeometry = self.second_window.winfo_geometry()
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
        original_colors = {}
        for x in destinations:
            color = x['color']
            if x['name'] != "SKIP" and x['name'] != "BACK":
                if(itern < len(hotkeys)):
                    newbut = tk.Button(buttonframe, text=hotkeys[itern] + ": " + x['name'], command=partial(
                        self.fileManager.setDestination, x, {"widget": None}), anchor="w", wraplength=(self.leftui.winfo_width()/columns)-1)
                    random.seed(x['name'])
                    self.bind_all(hotkeys[itern], partial(
                        self.fileManager.setDestination, x))
                    fg = text_colour
                    if luminance(color) == 'light':
                        fg = text_colour
                    newbut.configure(bg=color, fg=fg)
                    original_colors[newbut] = {'bg': color, 'fg': fg}  # Store both colors
                    if(len(x['name']) >= 13):
                        newbut.configure(font=smallfont)
                else:
                    newbut = tk.Button(buttonframe, text=x['name'],command=partial(
                        self.fileManager.setDestination, x, {"widget": None}), anchor="w")
                itern += 1
            #elif x['name'] == "SKIP":
            #    newbut = tk.Button(buttonframe, text="SKIP (Space)", command=skip, bg=button_colour, fg=text_colour)
            #    tkroot.bind("<space>", skip)
            #elif x['name'] == "BACK":
            #    newbut = tk.Button(buttonframe, text="BACK", command=back, bg=button_colour, fg=text_colour)

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
                btn.bind("<Enter>", lambda e, btn=btn: btn.config(bg=text_colour, fg=background_colour))
                btn.bind("<Leave>", lambda e, btn=btn: btn.config(bg=button_colour, fg=text_colour))  # Reset to original colors
            self.entryframe.grid_remove()
        # options frame
        optionsframe = tk.Frame(self.leftui,bg=background_colour)
        
        valcmd = self.register(self.isnumber)
        squaresperpageentry = tk.Entry(
            optionsframe, textvariable=self.squaresperpage, takefocus=False, background=background_colour, foreground=text_colour)
        if self.squaresperpage.get() < 0: #this wont let you save -1
            self.squaresperpage.set(1)
        ToolTip(squaresperpageentry,delay=1,msg="How many more images to add when Load Images is clicked")
        for n in range(0, itern):
            squaresperpageentry.unbind(hotkeys[n])
        addpagebut = tk.Button(
            optionsframe, text="Load More Images", command=self.load_more_images,bg=background_colour, fg=text_colour)

        ToolTip(addpagebut,msg="Add another batch of files from the source folders.", delay=1)
        

        squaresperpageentry.grid(row=1, column=0, sticky="EW",)
        
        addpagebut.grid(row=1, column=1, sticky="EW")
        self.addpagebutton = addpagebut
        
        # save button
        savebutton = tk.Button(optionsframe,text="Save Session",command=partial(self.fileManager.savesession,True),bg=background_colour, fg=text_colour)
        ToolTip(savebutton,delay=1,msg="Save this image sorting session to a file, where it can be loaded at a later time. Assigned destinations and moved images will be saved.")
        savebutton.grid(column=0,row=0,sticky="ew")
        moveallbutton = tk.Button(
            optionsframe, text="Move All", command=self.fileManager.moveall,bg=background_colour, fg=text_colour)
        moveallbutton.grid(column=1, row=2, sticky="EW")
        ToolTip(moveallbutton,delay=1,msg="Move all images to their assigned destinations, if they have one.")
        clearallbutton = tk.Button(
            optionsframe, text="Clear Selection", command=self.fileManager.clear,bg=background_colour, fg=text_colour)
        
        #optional dedicated buttons for views instead of 1 for all.
        #show_moved_button = tk.Button(optionsframe, text="Show moved", command=self.clicked_show_moved)
        #show_moved_button.grid(row=3, column=0, sticky="EW")
        #ToolTip(show_moved_button, msg="Shows moved images", delay=1)
        
        #show_assigned_button = tk.Button(optionsframe, text="Show assigned", command=self.clicked_show_assigned)
        #show_assigned_button.grid(row=4, column=1, sticky="EW")
        #ToolTip(show_moved_button, msg="Shows assigned images", delay=1)
        
        #show_unassigned_button = tk.Button(optionsframe, text="Show unassigned", command=self.clicked_show_unassigned)
        #show_unassigned_button.grid(row=2, column=1, sticky="EW")
        #ToolTip(show_moved_button, msg="Shows unassigned images", delay=1)
        style1 = ttk.Style()
        style1.configure('darkmode.TMenubutton', background=background_colour, foreground=text_colour, highlightthickness = 0)
        style1.map('darkmode.TMenubutton',
           background=[('active', active_background_colour),  # Hover background
                       ('pressed', active_background_colour)],  # Clicked background
           foreground=[('active', active_foreground_colour),  # Hover text color
                       ('pressed', active_foreground_colour)])  # Clicked text color
        options = ["Show Unassigned", "Show Moved", "Show Assigned", "Show Unassigned", ] #"Show All"
        option_menu = ttk.OptionMenu(optionsframe, self.variable, *options)
        option_menu.grid(row = 2, column = 0, sticky = "EW")
        option_menu.config(style='darkmode.TMenubutton')
        
        ToolTip(clearallbutton,delay=1,msg="Clear your selection on the grid and any other windows with checkable image grids.")
        clearallbutton.grid(row=0, column=1, sticky="EW")
        optionsframe.columnconfigure(0, weight=1)
        optionsframe.columnconfigure(1, weight=3)  
        self.optionsframe = optionsframe
        self.optionsframe.grid(row=0, column=0, sticky="ew")
        self.bind_all("<Button-1>", self.setfocus)
        
    def on_option_selected(self, *args):
        selected_option = self.variable.get()
        if selected_option == "Show Unassigned":
            self.clicked_show_unassigned()
        elif selected_option == "Show Assigned":
            self.clicked_show_assigned()
        elif selected_option == "Show Moved":
            self.clicked_show_moved()
        #elif selected_option == "Show All":
        #    self.clicked_show_all()

    def setfocus(self, event):
        event.widget.focus_set()

    def displaygrid(self, imagelist, range1): #dummy to handle sortimages calls for now...
        for i in range1:
            gridsquare = self.makegridsquare(self.imagegrid, imagelist[i], True)
            self.gridsquarelist.append(gridsquare)
            if gridsquare.obj.moved == False:
                self.unassigned_squarelist.append(gridsquare)
                gridsquare.obj.isvisible = True
            elif gridsquare.obj.moved:
                self.moved_squarelist.append(gridsquare)
                gridsquare.obj.isvisible = False

            if gridsquare.obj.isanimated: #animated 
                #temp
                gridsquare.canvas_window = self.imagegrid.window_create("insert", window=gridsquare, padx=gridsquare_padx, pady=gridsquare_pady)
                self.displayedlist[gridsquare] = gridsquare.canvas_window
                threading.Thread(target=self.load_frames, args=(gridsquare,)).start()
                    
            else: #normal static
                gridsquare.obj.isanimated = False
                gridsquare.canvas_window = self.imagegrid.window_create("insert", window=gridsquare, padx=gridsquare_padx, pady=gridsquare_pady)
                self.displayedlist[gridsquare] = gridsquare.canvas_window

        self.refresh_rendered_list() #attempts to render both img and gif.
           
    def load_frames(self, gridsquare):
        #print(f"Creating frames. {gridsquare.obj.truncated}")
        try:            
            with Image.open(gridsquare.obj.path) as self.img:
                
                if self.img.format in ['GIF', 'WEBP']:
                    gridsquare.obj.delay = self.img.info.get('duration', 50)
                    for i in range(self.img.n_frames):
                        self.img.seek(i)  # Move to the ith frame
                        frame = self.img.copy()
                        frame.thumbnail((256, 256), Image.Resampling.NEAREST)
                        tk_image = ImageTk.PhotoImage(frame)
                        
                        gridsquare.obj.frames.append(tk_image)
                        gridsquare.obj.isanimated = True
                        gridsquare.canvas.itemconfig(gridsquare.canvas_image_id, image=gridsquare.obj.frames[gridsquare.obj.index])
                    #print(f"All frames loaded. Name: {gridsquare.obj.truncated} Count: {len(gridsquare.obj.frames)} Duration: {gridsquare.obj.delay}")
        except Exception as e: #fallback to static.
            print(f"Fallback to static, cant load frames: {e}")
            gridsquare.obj.isanimated = False
            gridsquare.canvas.itemconfig(gridsquare.canvas_image_id, image=gridsquare.obj.frames[gridsquare.obj.index])

        self.refresh_rendered_list()
        self.start_gifs()

    #pre. Makes a list of all isanimated and isvisible pics and calls for their animation.
    #would be good if they used the same clock but no.
    def start_gifs(self):
        #check displayed list for isanimated and animate them
        current_squares = set(self.displayedlist.keys())
        for i in current_squares:
            #print(f"{i.obj.isanimated} and { i.obj.isvisible}")
            if i.obj.isanimated and i.obj.isvisible:
                #print(f"{i in self.running}")
                if i not in self.running:
                    if len(i.obj.frames) > 0: #makes sure not trying to render before frames are ready.
                        x = False
                        self.animation_loop(i,x)


    #Post. animate a frame for each picture in the list and run this again.
    def animation_loop(self, i,x): #frame by frame as to not freeze the main one XD
        #One time check
        if x == False:
            if i not in self.running:
                self.running.append(i)
            else:
                return

        i.obj.index = (i.obj.index + 1) % len(i.obj.frames)
        #print(f"Loop: {i.obj.truncated}, length: {i.obj.index}/{len(i.obj.frames)}, delay: {i.obj.delay}")
        i.canvas.itemconfig(i.canvas_image_id, image=i.obj.frames[i.obj.index]) #change the frame
        if(i.obj.isvisible):
            x = True
            i.canvas.after(i.obj.delay, lambda: self.animation_loop(i,x)) #run again.

    #This renders the given squarelist.
    def render_squarelist(self, squarelist):
        self.running = []
        current_squares = set(self.displayedlist.keys())
        
        #delete
        for gridsquare in current_squares:
            if gridsquare not in squarelist:
                self.imagegrid.window_configure(gridsquare, window="")

                # Remove the entry from the dictionary
                del self.displayedlist[gridsquare]
                gridsquare.obj.isvisible = False
                
        #self.displayedlist.clear() #rearrange pics when reassigning. Not fully implemented. Optional.
                
        # Add
        for gridsquare in squarelist:
            if gridsquare not in self.displayedlist:
                
                gridsquare.canvas_window = self.imagegrid.window_create(
                    "insert", window=gridsquare)
                self.displayedlist[gridsquare] = gridsquare.canvas_window
                gridsquare.obj.isvisible = True

         #shouldnt activate for setdestination.
        
    def refresh_rendered_list(self):
        current_list = None
        if self.show_unassigned.get():
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
        if self.show_unassigned.get() == False:
            self.show_assigned.set(False)
            self.show_moved.set(False)
            self.show_unassigned.set(True)
            self.refresh_rendered_list()
            self.running = []
            self.start_gifs()
            
    def clicked_show_assigned(self):
        if self.show_assigned.get() == False:
            self.show_unassigned.set(False)
            self.show_moved.set(False)
            self.show_assigned.set(True)
            self.refresh_rendered_list()
            self.running = []
            self.start_gifs()
            
    def clicked_show_moved(self):
        if self.show_moved.get() == False:
            self.show_assigned.set(False)
            self.show_unassigned.set(False)
            self.show_moved.set(True)
            self.refresh_rendered_list()
            self.running = []
            self.start_gifs()
    """    
    def clicked_show_all(self):
        if self.show_all.get() == False:
            self.show_assigned.set(False)
            self.show_unassigned.set(False)
            self.show_moved.set(False)
            self.show_all.set(True)
            self.refresh_rendered_list()
            """ 
            
    def set_active_window(self, dest_squarelist):

        self.active_dest_squarelist = dest_squarelist

        
    def showthisdest(self, dest, *args):
        destwindow = tk.Toplevel()
        dest_squarelist = []
        dest_running = []


        destwindow.geometry(str(int(self.winfo_screenwidth(
        )*0.80)) + "x" + str(self.winfo_screenheight()-120)+"+365+60")
        destwindow.winfo_toplevel().title(
            "Files designated for" + dest['path'])
        destgrid = tk.Text(destwindow, wrap='word', borderwidth=0,
                           highlightthickness=0, state="disabled", background=background_colour)
        destgrid.grid(row=0, column=0, sticky="NSEW")
        destwindow.columnconfigure(0, weight=1)
        destwindow.rowconfigure(0, weight=1)
        vbar = tk.Scrollbar(destwindow, orient='vertical',
                            command=destgrid.yview)
        vbar.grid(row=0, column=1, sticky='ns')
        self.destination_windows.append((destgrid, dest['path'], dest_squarelist, dest_running, destwindow))
        destwindow.bind("<FocusIn>", lambda event: self.set_active_window(dest_squarelist))
        destwindow.protocol("WM_DELETE_WINDOW", lambda: self.close_destination_window(destwindow, dest_running))
        self.refresh_destinations()
        self.set_active_window(dest_squarelist)
        
    def close_destination_window(self, destwindow, dest_running):
        for window in self.destination_windows:
            if window[4] == destwindow:
                for i in dest_running:
                    i.obj.isrunning = False
                self.destination_windows.remove(window)
                break
        destwindow.destroy()

    
    def refresh_destinations(self):
        if not self.destination_windows:
            return  # Exit if there are no destination windows
        for destination in self.destination_windows:
            destgrid = destination[0]
            dest_path = destination[1]
            dest_squarelist = destination[2]
                        
            combined_squarelist = self.assigned_squarelist + self.moved_squarelist
            filtered_images = [gridsquare.obj for gridsquare in combined_squarelist if hasattr(gridsquare.obj, 'dest') and gridsquare.obj.dest == dest_path]
                        
            # Add
            for img in filtered_images:
                if not any(gridsquare.obj == img for gridsquare in dest_squarelist):
                    new_frame = self.makegridsquare(destgrid, img, False)
                    
                    color = next((d['color'] for d in self.fileManager.destinations if d['path'] == img.dest), None)
                    if color:
                        new_frame['background'] = color
                        new_frame.children['!canvas']['background'] = color  # Assuming the canvas is the first child
                    
                    canvas_window_id = destgrid.window_create("insert", window=new_frame)
                    new_frame.canvas_id = canvas_window_id
                    dest_squarelist.append(new_frame)
                    #new_frame.obj.isanimating = False #it is added to flag that animating should allow it
                    print(f"Isrunning? {new_frame.obj.isrunning}")
            
                    
                    

            # Remove
            to_remove = []  # Temporary list to track images to remove
            for gridsquare in dest_squarelist:
                if gridsquare.obj not in filtered_images:
                    # Hide the window associated with the image
                    try:
                        destgrid.window_configure(gridsquare, window="")
                    except Exception as e:
                        print(f"Error configuring window for image {gridsquare.obj}: {e}")

                    to_remove.append(gridsquare)  # Mark for removal

            # Remove the images from the dest_squarelist
            for gridsquare in to_remove:
                dest_squarelist.remove(gridsquare)
                gridsquare.obj.isrunning = False ## it is flagged that animating should not allow it
                print(f"Isrunning after removal? {gridsquare.obj.isrunning}")
                

        self.start_gifs_indestinations() #when it is removed, it should call this and this should allow it.
        #it this is called and stuff is still isvisible, it should reject it. so animatined
    
    #pre. Makes a list of all isanimated and isvisible pics and calls for their animation.
    def start_gifs_indestinations(self):
        for destination in self.destination_windows: #go through all instances and lists for them.
            destgrid = destination[0]
            dest_path = destination[1]
            dest_squarelist = destination[2]
            dest_running = destination[3]
        
            #check displayed list for isanimated and animate them
            current_index = 0
            index_length = 0
            for i in dest_squarelist:
                print(f"Will allow running? {i.obj.isrunning}")
                #When is animating? It is animating when the loop runs once. should be set to false when closed.
                if i.obj.isanimated: #if isanimating dont allow
                    if i not in dest_running:
                        index_length = len(i.obj.frames)
                        if index_length > 0:
                            current_index = i.obj.index
                            x = False
                            self.animation_loop_indestinations(i, current_index, index_length, x, dest_running)


    #Post. animate a frame for each picture in the list and run this again.
    def animation_loop_indestinations(self, i, current_index, index_length, x, dest_running): #frame by frame as to not freeze the main one XD
        if x == False:
            i.obj.isrunning = True
            self.dest_running.append(i)
            print(f"Ran? {i.obj.isrunning}")
        current_index = (current_index + 1) % index_length
        i.canvas.itemconfig(i.canvas_image_id, image=i.obj.frames[current_index]) #change the frame
        if(i.obj.isrunning): #so visible will deny uppstream and this will die out soon.
            x = True
            i.canvas.after(i.obj.delay, lambda: self.animation_loop_indestinations(i, current_index, index_length,x, dest_running)) #run again.
            
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

    if last_scroll_time is None or (now - last_scroll_time) > 0.00:  # 100ms throttle
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
    elif command == "destroy":
        widget.destroy()
