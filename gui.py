import os
import time
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
from tktooltip import ToolTip
from tkinter import filedialog as tkFileDialog
from operator import indexOf
from functools import partial
last_scroll_time = None

entry_bg = "grey"
frame_bg = "#a9a9a9"
image_bg = "grey"
buttoncolour = "grey"

textboxpos = "N"
textlength = 33 
space_to_border = 1
space_to_image_x = 5
space_to_image_y = 29


grid_bg = "#a9a9a9"

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
        "autosave":manager.autosave
        }
    
    try: #Try to save the preference to prefs.json
        with open("prefs.json", "w+") as savef:
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
        self.variable.set("Show Unassigned")  # Set the default option
        self.variable.trace_add("write", self.on_option_selected)
        
        #Initialization for lists.
        #Main window renderlist
        self.gridsquarelist = []
        self.displayedlist = {}
        
        #Main window sorted lists
        self.unassigned_squarelist = []
        self.assigned_squarelist = []
        self.moved_squarelist = []    
        
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
        
        # Paned window that holds the almost top level stuff.
        self.toppane = Panedwindow(self, orient="horizontal")
        
        # Frame for the left hand side that holds the setup and also the destination buttons.
        self.leftui = tk.Frame(self.toppane, width=363)
        #self.leftui.grid(row=0, column=0, sticky="NESW")
        self.leftui.grid_propagate(False) #to turn off auto scaling.
        self.leftui.columnconfigure(0, weight=1)
        self.toppane.add(self.leftui, weight=1)
        
        #Add a checkbox to check for sorting preference.
        self.sortbydatecheck = tk.Checkbutton(self.leftui, text="Sort by Date", variable=self.sortbydatevar, onvalue=True, offvalue=False, command=self.sortbydatevar)
        self.sortbydatecheck.grid(row=2, column=0, sticky="w", padx=25)
        
        self.panel = tk.Label(self.leftui, wraplength=300, justify="left", text="Text")
        self.panel.grid(row=3, column=0, columnspan=200,
                        rowspan=200, sticky="NSEW")
        self.columnconfigure(0, weight=1)

        self.buttonframe = tk.Frame(master=self.leftui)
        self.buttonframe.grid(
            column=0, row=1, sticky="NSEW")
        self.buttonframe.columnconfigure(0, weight=1)
        
        self.entryframe = tk.Frame(master=self.leftui)
        self.entryframe.columnconfigure(1, weight=1)
        
        self.sdpEntry = tk.Entry(
            self.entryframe, takefocus=False)  # scandirpathEntry
        self.ddpEntry = tk.Entry(
            self.entryframe, takefocus=False)  # dest dir path entry

        sdplabel = tk.Button(
            self.entryframe, text="Source Folder:", command=partial(self.filedialogselect, self.sdpEntry, "d"))
        
        ddplabel = tk.Button(
            self.entryframe, text="Destination Folder:", command=partial(self.filedialogselect, self.ddpEntry, "d"))
        
        self.activebutton = tk.Button(
            self.entryframe, text="New Session", command=partial(fileManager.validate, self))
        ToolTip(self.activebutton,delay=1,msg="Start a new Session with the entered source and destination")
        
        self.loadpathentry = tk.Entry(
            self.entryframe, takefocus=False, textvariable=self.sessionpathvar)
        
        self.loadbutton = tk.Button(
            self.entryframe, text="Load Session", command=self.fileManager.loadsession)
        ToolTip(self.loadbutton,delay=1,msg="Load and start the selected session data.")
        
        loadfolderbutton = tk.Button(self.entryframe, text="Session Data:", command=partial(
            self.filedialogselect, self.loadpathentry, "f"))
        ToolTip(loadfolderbutton,delay=1,msg="Select a session json file to open.")
        
        loadfolderbutton.grid(row=3, column=0, sticky='e')
        
        self.loadbutton.grid(row=3, column=2, sticky='ew')
        
        self.loadpathentry.grid(row=3, column=1, sticky='ew', padx=2)
        
        sdplabel.grid(row=0, column=0, sticky="e")
        
        self.sdpEntry.grid(row=0, column=1, sticky="ew", padx=2)
        
        ddplabel.grid(row=1, column=0, sticky="e")
        
        self.ddpEntry.grid(row=1, column=1, sticky="ew", padx=2)
        
        self.activebutton.grid(row=1, column=2, sticky="ew")
        
        self.excludebutton = tk.Button(
            self.entryframe, text="Manage Exclusions", command=self.excludeshow)
        self.excludebutton.grid(row=0, column=2)
        
        # show the entry frame, sticky it to the west so it mostly stays put.
        self.entryframe.grid(row=0, column=0, sticky="ew")
        
        # Finish setup for the left hand bar.
        # Start the grid setup
        imagegridframe = tk.Frame(self.toppane)
        imagegridframe.grid(row=0, column=1, sticky="NSEW")
        
        # Replacing Text widget with Canvas for image grid
        self.imagegrid = tk.Text(
            imagegridframe, wrap ='word', borderwidth=0, highlightthickness=0, state="disabled", background=grid_bg)

        vbar = tk.Scrollbar(imagegridframe, orient='vertical',command=lambda *args: throttled_yview(self.imagegrid, *args))
        vbar.grid(row=0, column=1, sticky='ns')
        
        self.imagegrid.configure(yscrollcommand=vbar.set)
        self.imagegrid.grid(row=0, column=0, sticky="NSEW")
        imagegridframe.rowconfigure(0, weight=1)
        imagegridframe.columnconfigure(0, weight=1)
        
        self.toppane.add(imagegridframe, weight=3)
        self.toppane.grid(row=0, column=0, sticky="NSEW")
        self.toppane.configure()
        
        self.columnconfigure(0, weight=10)
        self.columnconfigure(1, weight=0)
        self.rowconfigure(0, weight=10)
        self.rowconfigure(1, weight=0)
        
        self.protocol("WM_DELETE_WINDOW", self.closeprogram)
        
        self.winfo_toplevel().title("Simple Image Sorter: Multiview Edition v2.4")
        
        self.leftui.bind("<Configure>", self.buttonResizeOnWindowResize)
        
        self.buttonResizeOnWindowResize("a")
        

    def isnumber(self, char):
        return char.isdigit()

    def closeprogram(self):
        if len(self.assigned_squarelist) != 0:
            if askokcancel("Designated but Un-Moved files, really quit?","You have destination designated, but unmoved files. (Simply cancel and Move All if you want)"):
                saveprefs(self.fileManager, self)
                self.destroy()
                exit(0)
        else:

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
        if imageobject.dupename:
            text += "Image has Duplicate Filename!\n"
        text += "Leftclick to select this for assignment. Rightclick to open full view"
        return text
    

    def makegridsquare(self, parent, imageobj, setguidata):
        frame = tk.Frame(parent, borderwidth=0, width=self.thumbnailsize + 14, height=self.thumbnailsize+24, padx = 0, pady = 0)
        frame.obj = imageobj
        truncated_filename = self.truncate_text(frame, imageobj, textlength)
        truncated_name_var = tk.StringVar(frame, value=truncated_filename)
        frame.obj2 = truncated_name_var
        
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
                               height=self.thumbnailsize) #centering adjustments here
            tooltiptext=tk.StringVar(frame,self.tooltiptext(imageobj))

            ToolTip(canvas,msg=tooltiptext.get,delay=1)
            canvas.create_image(
                self.thumbnailsize/2, self.thumbnailsize/2, anchor="center", image=img)
            
            
            # Create a frame for the Checkbutton to control its height
            check_frame = tk.Frame(frame, height=24)  # Set a fixed height (e.g., 30 pixels)
            check_frame.grid(column=0, row=1, sticky="NSEW")  # Place the frame in the grid
            check_frame.grid_propagate(False)
            
            check = tk.Checkbutton(check_frame, textvariable=truncated_name_var, variable=imageobj.checked, onvalue=True, offvalue=False, width=textlength)
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
            if imageobj.dupename:
                frame.configure(
                    highlightbackground="yellow", highlightthickness=2)
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

    def buttonResizeOnWindowResize(self, b=""):
        if len(self.buttons) > 0:
            for x in self.buttons:
                x.configure(wraplength=(self.buttons[0].winfo_width()-1))
                
    #Create secondary window for image viewing
    def displayimage(self, imageobj, a):
        path = imageobj.path
        
        if hasattr(self, 'second_window'):
            self.second_window.destroy()
        
        self.second_window = tk.Toplevel()
        second_window = self.second_window
        second_window.rowconfigure(0, weight=1)
        second_window.columnconfigure(0, weight=1)
        second_window.title("Image: " + path)
        second_window.geometry(self.imagewindowgeometry)
        second_window.bind("<Button-3>", partial(bindhandler, second_window, "destroy"))
        second_window.protocol("WM_DELETE_WINDOW", self.saveimagewindowgeo)
        second_window.obj = imageobj
        
        geometry = self.imagewindowgeometry.split('+')[0]

        Image_frame = CanvasImage(self.second_window, path, geometry)
        Image_frame.grid(sticky='nswe') #Initialize Frame grid statement in canvasimage, Add to main window grid

        Image_frame.rescale(min(second_window.winfo_width()/Image_frame.imwidth, second_window.winfo_height()/Image_frame.imheight)) #Scales to the fucking window WOO!
        Image_frame.center_image()

    def saveimagewindowgeo(self):
        self.imagewindowgeometry = self.second_window.winfo_geometry()
        self.checkdupename(self.second_window.obj)
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
        for x in destinations:
            color = x['color']
            if x['name'] != "SKIP" and x['name'] != "BACK":
                if(itern < len(hotkeys)):
                    newbut = tk.Button(buttonframe, text=hotkeys[itern] + ": " + x['name'], command=partial(
                        self.fileManager.setDestination, x, {"widget": None}), anchor="w", wraplength=(self.leftui.winfo_width()/columns)-1)
                    self.bind_all(hotkeys[itern], partial(
                        self.fileManager.setDestination, x))
                    fg = 'white'
                    if luminance(color) == 'light':
                        fg = "black"
                    newbut.configure(bg=color, fg=fg)
                    if(len(x['name']) >= 13):
                        newbut.configure(font=smallfont)
                else:
                    newbut = tk.Button(buttonframe, text=x['name'], command=partial(
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
        self.entryframe.grid_remove()
        # options frame
        optionsframe = tk.Frame(self.leftui)
        
        valcmd = self.register(self.isnumber)
        squaresperpageentry = tk.Entry(
            optionsframe, textvariable=self.squaresperpage, takefocus=False)
        if self.squaresperpage.get() < 0: #this wont let you save -1
            self.squaresperpage.set(1)
        ToolTip(squaresperpageentry,delay=1,msg="How many more images to add when Load Images is clicked")
        for n in range(0, itern):
            squaresperpageentry.unbind(hotkeys[n])
        addpagebut = tk.Button(
            optionsframe, text="Load More Images", command=self.load_more_images)

        ToolTip(addpagebut,msg="Add another batch of files from the source folders.", delay=1)
        

        squaresperpageentry.grid(row=1, column=0, sticky="EW",)
        
        addpagebut.grid(row=1, column=1, sticky="EW")
        self.addpagebutton = addpagebut
        
        # save button
        savebutton = tk.Button(optionsframe,text="Save Session",command=partial(self.fileManager.savesession,True))
        ToolTip(savebutton,delay=1,msg="Save this image sorting session to a file, where it can be loaded at a later time. Assigned destinations and moved images will be saved.")
        savebutton.grid(column=0,row=0,sticky="ew")
        moveallbutton = tk.Button(
            optionsframe, text="Move All", command=self.fileManager.moveall)
        moveallbutton.grid(column=1, row=2, sticky="EW")
        ToolTip(moveallbutton,delay=1,msg="Move all images to their assigned destinations, if they have one.")
        clearallbutton = tk.Button(
            optionsframe, text="Clear Selection", command=self.fileManager.clear)
        
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
        
        options = ["Show Moved", "Show Assigned", "Show Unassigned", ] #"Show All"
        option_menu = tk.OptionMenu(optionsframe, self.variable, *options)
        option_menu.grid(row = 2, column = 0, sticky = "EW")
        option_menu.config(width = 10)
        
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

    def displaygrid(self, imagelist, range): #dummy to handle sortimages calls for now...
        for i in range:
            gridsquare = self.makegridsquare(self.imagegrid, imagelist[i], True)
            self.gridsquarelist.append(gridsquare)
            if gridsquare.obj.moved == False:
                self.unassigned_squarelist.append(gridsquare)
            elif gridsquare.obj.moved:
                self.moved_squarelist.append(gridsquare)
            
            gridsquare.canvas_window = self.imagegrid.window_create(
                "insert", window=gridsquare)
            self.displayedlist[gridsquare] = gridsquare.canvas_window
            
        self.refresh_rendered_list()
        
    #This renders the given squarelist.
    def render_squarelist(self, squarelist):
        current_squares = set(self.displayedlist.keys())
        
        #delete
        for gridsquare in current_squares:
            if gridsquare not in squarelist:
                self.imagegrid.window_configure(gridsquare, window="")

                # Remove the entry from the dictionary
                del self.displayedlist[gridsquare]
                
        #self.displayedlist.clear() #rearrange pics when reassigning. Not fully implemented. Optional.
                
        # Add
        for gridsquare in squarelist:
            if gridsquare not in self.displayedlist:
                
                gridsquare.canvas_window = self.imagegrid.window_create(
                    "insert", window=gridsquare)
                self.displayedlist[gridsquare] = gridsquare.canvas_window
        
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
        print("###############################################")
        a1 = len(self.unassigned_squarelist)
        a2 = len(self.assigned_squarelist)
        a3 = len(self.moved_squarelist)
        print(f"C:{len(current_list)}:G:{len(self.gridsquarelist)}:U:{a1}:A:{a2}:M:{a3}:D:{len(self.displayedlist)}")
        print(f"U:{self.show_unassigned.get()}:A:{self.show_assigned.get()}:M:{self.show_moved.get()}")
    
    def clicked_show_unassigned(self): #Turn you on.
        if self.show_unassigned.get() == False:
            self.show_assigned.set(False)
            self.show_moved.set(False)
            self.show_unassigned.set(True)
            self.refresh_rendered_list()
            
    def clicked_show_assigned(self):
        if self.show_assigned.get() == False:
            self.show_unassigned.set(False)
            self.show_moved.set(False)
            self.show_assigned.set(True)
            self.refresh_rendered_list()
            
    def clicked_show_moved(self):
        if self.show_moved.get() == False:
            self.show_assigned.set(False)
            self.show_unassigned.set(False)
            self.show_moved.set(True)
            self.refresh_rendered_list()
    """    
    def clicked_show_all(self):
        if self.show_all.get() == False:
            self.show_assigned.set(False)
            self.show_unassigned.set(False)
            self.show_moved.set(False)
            self.show_all.set(True)
            self.refresh_rendered_list()
            """ 
            
    def set_active_window(self, destwindow, dest_squarelist, dest_path, dest_grid):
        self.dest_active_window = destwindow
        self.active_dest_squarelist = dest_squarelist
        self.active_dest_path = dest_path
        self.active_dest_grid = dest_grid
        
    def showthisdest(self, dest, *args):
        destwindow = tk.Toplevel()
        dest_squarelist = []
        displayed_dest_squares = {}
        destwindow.geometry(str(int(self.winfo_screenwidth(
        )*0.80)) + "x" + str(self.winfo_screenheight()-120)+"+365+60")
        destwindow.winfo_toplevel().title(
            "Files designated for" + dest['path'])
        destgrid = tk.Text(destwindow, wrap='word', borderwidth=0,
                           highlightthickness=0, state="disabled", background='#a9a9a9')
        destgrid.grid(row=0, column=0, sticky="NSEW")
        destwindow.columnconfigure(0, weight=1)
        destwindow.rowconfigure(0, weight=1)
        vbar = tk.Scrollbar(destwindow, orient='vertical',
                            command=destgrid.yview)
        vbar.grid(row=0, column=1, sticky='ns')
        self.destination_windows.append((destgrid, dest['path'], dest_squarelist,displayed_dest_squares, destwindow))
        destwindow.bind("<FocusIn>", lambda event: self.set_active_window(destwindow, dest_squarelist, dest['path'],destgrid))
        destwindow.protocol("WM_DELETE_WINDOW", lambda: self.close_destination_window(destwindow))
        self.refresh_destinations()
        self.set_active_window(destwindow, dest_squarelist, dest['path'],destgrid)
        
    def close_destination_window(self, destwindow):
        for window in self.destination_windows:
            if window[4] == destwindow:
                self.destination_windows.remove(window)
                break
        destwindow.destroy()

    
    def refresh_destinations(self):
        
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
    


def throttled_yview(widget, *args):
    """Throttle scroll events for both MouseWheel and Scrollbar slider"""
    global last_scroll_time

    now = time.time()

    if last_scroll_time is None or (now - last_scroll_time) > 0.01:  # 100ms throttle
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
