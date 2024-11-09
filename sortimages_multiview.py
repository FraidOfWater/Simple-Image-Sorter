# todo:
# Filename dupicate scanning to prevent collisions
# Check if filename already exists on move.
# implement undo
import os
import sys
import shutil
import tkinter as tk
from tkinter.messagebox import askokcancel
import json
import random
from tkinter import filedialog as tkFileDialog
import concurrent.futures as concurrent
import logging
from hashlib import md5
import pyvips
from gui import GUIManager, randomColor

logger = logging.getLogger("Sortimages")
logger.setLevel(logging.WARNING)  # Set to the lowest level you want to handle

handler = logging.StreamHandler()
handler.setLevel(logging.WARNING)

formatter = logging.Formatter('%(message)s')
handler.setFormatter(formatter)

logger.addHandler(handler)

"""# This can/should be commented if you build.

import ctypes
try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dll_path1 = os.path.join(script_dir, 'libvips-cpp-42.dll')
    dll_path2 = os.path.join(script_dir, 'libvips-42.dll')
    dll_path3 = os.path.join(script_dir, 'libglib-2.0-0.dll')
    dll_path4 = os.path.join(script_dir, 'libgobject-2.0-0.dll')
except FileNotFoundError:
    logger.error("The file was not found. (You are missing .dlls)")
ctypes.CDLL(dll_path1)
ctypes.CDLL(dll_path2)
ctypes.CDLL(dll_path3)
ctypes.CDLL(dll_path4)
"""

# The imagefile class. It holds all information about the image and the state its container is in.
class Imagefile:
    path = ""
    dest = ""
    dupename=False

    def __init__(self, name, path) -> None:
        self.name = tk.StringVar()
        self.name.set(name)
        self.path = path
        self.mod_time = None
        self.file_size = None
        self.checked = tk.BooleanVar(value=False)
        self.moved = False
        self.id = None

    def move(self) -> str:
        destpath = self.dest
        do_not_move_if_exists = True # This flag prevents overwriting of files in destination that have the same name as source.

        if destpath != "" and os.path.isdir(destpath):
            file_name = self.name.get()
            exists_already_in_destination = os.path.exists(os.path.join(destpath, file_name))
            if exists_already_in_destination:
                if do_not_move_if_exists:
                    logger.warning(f"File {self.name.get()} already exists at destination, file not moved or deleted from source.")
                    return ("") # Returns if 1. Would overwrite someone
            try:
                new_path = os.path.join(destpath, file_name)
                old_path = os.path.join(self.path, file_name)

                shutil.move(self.path, new_path) # Try to move, fails if 1. Locked

                self.moved = True
                self.show = False

                self.guidata["frame"].configure(
                    highlightbackground="green", highlightthickness=2)
                
                self.path = new_path
                returnstr = ("Moved:" + self.name.get() +
                             " -> " + destpath + "\n")
                destpath = ""
                self.dest = ""
                self.hasunmoved = False
                return returnstr
            
            except Exception as e:
                logger.warning(f"Error moving/deleting: %s . File: %s {e} {self.name.get()}")
                
                if os.path.exists(new_path) and os.path.exists(old_path): # shuti.move has copied a duplicate to destinations, but image couldn't be moved. This deletes the duplicate from destination.
                    os.remove(new_path)
                    logger.warning("Image was locked and the move was completed partially, deleting image from destination, leaving it in source")

                self.guidata["frame"].configure(
                    highlightbackground="red", highlightthickness=2)
                return ("Error moving: %s . File: %s", e, self.name.get())

    def setid(self, id):
        self.id = id

    def setguidata(self, data):
        self.guidata = data

    def setdest(self, dest):
        self.dest = dest["path"]
        logger.info("Set destination of %s to %s",
                      self.name.get(), self.dest)


class SortImages:
    imagelist = []
    destinations = []
    exclude = []

    def __init__(self) -> None:
        self.hasunmoved=False
        self.existingnames = set()
        self.duplicatenames=[]
        self.autosave=True
        self.threads = os.cpu_count()
        self.gui = GUIManager(self)

        self.loadprefs()
        self.gui.initialize()
        self.validate_data_dir_thumbnailsize()
        
        self.gui.mainloop()

    def validate_data_dir_thumbnailsize(self): #Deletes data directory if the first picture doesnt match the thumbnail size from prefs. (If user changes thumbnailsize, we want to generate thumbnails again)
        
        data_dir = self.data_dir
        if(os.path.exists(data_dir) and os.path.isdir(data_dir)):
            temp = os.listdir(data_dir)
            image_files = [f for f in temp if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', 'webp', '.bmp', '.tiff', '.pcx', 'psd'))]
            if image_files:
                first_image_path = os.path.join(data_dir, image_files[0])
                try:
                    image = pyvips.Image.new_from_file(first_image_path)
                    
                    width = image.width
                    height = image.height
                    
                    # The size doesnt match what is wanted in prefs
                    if max(width, height) != self.gui.thumbnailsize:
                        shutil.rmtree(data_dir)
                        logger.warning(f"Removing data folder, thumbnailsize changed")
                        os.mkdir(data_dir)
                        logger.warning(f"Re-created data folder.")
                except Exception as e:
                    logger.warning(f"Couldn't load first image in data folder")
            else:
                logger.warning(f"Data folder is empty")
                pass
            pass
        else:
            os.mkdir(data_dir)

    def loadprefs(self):

        # Figure out script and data directory locations
        if getattr(sys, 'frozen', False):  # Check if running as a bundled executable
            script_dir = os.path.dirname(sys.executable) 
            self.prefs_path = os.path.join(script_dir, "prefs.json")
        else:
            script_dir = os.path.dirname(os.path.abspath(__file__)) # Else if a ran as py script
            self.prefs_path = os.path.join(script_dir, "prefs.json") 
        self.data_dir = os.path.join(script_dir, "data")

        hotkeys = ""
        # todo: replace this with some actual prefs manager that isn't a shittone of ifs
        try:
            with open(self.prefs_path, "r") as prefsfile:

                jdata = prefsfile.read()
                jprefs = json.loads(jdata)

                #paths
                if "source" in jprefs:
                    self.gui.source_folder = jprefs["source"]
                if "destination" in jprefs:
                    self.gui.destination_folder = jprefs["destination"]
                if "lastsession" in jprefs:
                    self.gui.sessionpathvar.set(jprefs['lastsession'])
                if "exclude" in jprefs:
                    self.exclude = jprefs["exclude"]

                #Preferences
                if 'thumbnailsize' in jprefs:
                    self.gui.thumbnailsize = int(jprefs["thumbnailsize"])
                if 'hotkeys' in jprefs:
                    hotkeys = jprefs["hotkeys"]
                if "interactive_buttons" in jprefs:
                    self.gui.interactive_buttons = jprefs["interactive_buttons"]
                if "hideonassign" in jprefs:
                    self.gui.hideonassignvar.set(jprefs["hideonassign"])
                if "hidemoved" in jprefs:
                    self.gui.hidemovedvar.set(jprefs["hidemoved"])

                #Technical preferences
                if "throttle_time" in jprefs:
                    self.gui.throttle_time = jprefs["throttle_time"]
                if 'threads' in jprefs:
                    self.threads = jprefs['threads']
                if 'autosave_session' in jprefs:
                    self.autosave = jprefs['autosave_session']
                #Customization
                if "checkbox_height" in jprefs:
                    self.gui.checkbox_height = int(jprefs["checkbox_height"])
                if "gridsquare_padx" in jprefs:
                    self.gui.gridsquare_padx = int(jprefs["gridsquare_padx"])
                if "gridsquare_pady" in jprefs:
                    self.gui.gridsquare_pady = int(jprefs["gridsquare_pady"])
                if "text_box_thickness" in jprefs:
                    self.gui.text_box_thickness = int(jprefs["text_box_thickness"])
                if "image_border_thickness" in jprefs:
                    self.gui.image_border_thickness = int(jprefs["image_border_thickness"])
                if "text_box_colour" in jprefs:
                    self.gui.text_box_colour = jprefs["text_box_colour"]
                if "text_box_selection_colour" in jprefs:
                    self.gui.text_box_selection_colour = jprefs["text_box_selection_colour"]
                if "imageborder_default_colour" in jprefs:
                    self.gui.imageborder_default_colour = jprefs["imageborder_default_colour"]   
                if "imageborder_selected_colour" in jprefs:
                    self.gui.imageborder_selected_colour = jprefs["imageborder_selected_colour"]
                if "imageborder_locked_colour" in jprefs:
                    self.gui.imageborder_locked_colour = jprefs["imageborder_locked_colour"]

                #Window colours
                if "main_colour" in jprefs:
                    self.gui.main_colour = jprefs["main_colour"]
                if "square_colour" in jprefs:
                    self.gui.square_colour = jprefs["square_colour"]
                if "grid_background_colour" in jprefs:
                    self.gui.grid_background_colour = jprefs["grid_background_colour"]
                if "canvasimage_background" in jprefs:
                    self.gui.canvasimage_background = jprefs["canvasimage_background"]
                if "text_colour" in jprefs:
                    self.gui.text_colour = jprefs["text_colour"]
                if "pressed_text_colour" in jprefs:
                    self.gui.pressed_text_colour = jprefs["pressed_text_colour"]
                if "button_colour" in jprefs:
                    self.gui.button_colour = jprefs["button_colour"]
                if "button_press_colour" in jprefs:
                    self.gui.button_press_colour = jprefs["button_press_colour"]
                if "text_field_colour" in jprefs:
                    self.gui.text_field_colour = jprefs["text_field_colour"]
                if "text_field_text_colour" in jprefs:
                    self.gui.text_field_text_colour = jprefs["text_field_text_colour"]
                if "pane_divider_colour" in jprefs:
                    self.gui.pane_divider_colour = jprefs["pane_divider_colour"]            
                #GUI CONTROLLED PREFRENECES
                if "squaresperpage" in jprefs:
                    self.gui.squaresperpage.set(jprefs["squaresperpage"])
                if "sortbydate" in jprefs:
                    self.gui.sortbydatevar.set(jprefs["sortbydate"])
                #Window positions
                if "main_geometry" in jprefs:
                    self.gui.main_geometry = jprefs["main_geometry"]
                if "viewer_geometry" in jprefs:
                    self.gui.viewer_geometry = jprefs["viewer_geometry"]
                if "destpane_geometry" in jprefs:
                    self.gui.destpane_geometry = jprefs["destpane_geometry"]
                if "leftpane_width" in jprefs:
                    self.gui.leftpane_width = int(jprefs["leftpane_width"])

            if len(hotkeys) > 1:
                self.gui.hotkeys = hotkeys
        except Exception as e:
            logger.error(f"Error loading prefs.json: {e}")
    
    def saveprefs(self, gui):
        sdp = gui.sdpEntry.get() if os.path.exists(gui.sdpEntry.get()) else ""
        ddp = gui.ddpEntry.get() if os.path.exists(gui.ddpEntry.get()) else ""

        save = {
            #paths
            "--#--#--#--#--#--#--#---#--#--#--#--#--#--#--#--#--PATHS": "--#--",
            "source": sdp,
            "destination": ddp,
            "lastsession": gui.sessionpathvar.get(),
            "exclude": self.exclude,

            #Preferences
            "--#--#--#--#--#--#--#---#--#--#--#--#--#--#--#--#--USER PREFERENCES":"--#--",
            "thumbnailsize": gui.thumbnailsize,
            "hotkeys": gui.hotkeys,
            "hideonassign": gui.hideonassignvar.get(),
            "hidemoved": gui.hidemovedvar.get(),
            "interactive_buttons":gui.interactive_buttons,
            #Technical preferences
            "--#--#--#--#--#--#--#---#--#--#--#--#--#--#--#--#--TECHNICAL PREFERENCES": "--#--",
            "throttle_time": gui.throttle_time,
            "threads": self.threads, 
            "autosave_session":self.autosave,

            #Customization
            "--#--#--#--#--#--#--#---#--#--#--#--#--#--#--#--#--PADDING AND COLOR FOR IMAGE CONTAINER": "--#--",
            "checkbox_height":gui.checkbox_height,

            "gridsquare_padx":gui.gridsquare_padx,
            "gridsquare_pady":gui.gridsquare_pady,

            "text_box_thickness":gui.text_box_thickness,
            "image_border_thickness":gui.image_border_thickness,

            "text_box_colour":gui.text_box_colour,
            "text_box_selection_colour":gui.text_box_selection_colour,
            
            "imageborder_default_colour":gui.imageborder_default_colour,
            "imageborder_selected_colour":gui.imageborder_selected_colour,
            "imageborder_locked_colour":gui.imageborder_locked_colour,

            #Window colours
            "--#--#--#--#--#--#--#---#--#--#--#--#--#--#--#--#--CUSTOMIZATION FOR WINDOWS": "--#--",
            "main_colour":gui.main_colour,
            "square_colour":gui.square_colour,
            "grid_background_colour":gui.grid_background_colour,
            "canvasimage_background":gui.canvasimage_background,

            "text_colour":gui.text_colour,
            "pressed_text_colour":gui.pressed_text_colour,
            
            "button_colour":gui.button_colour,
            "button_press_colour":gui.button_press_colour,

            "text_field_colour":gui.text_field_colour,
            "text_field_text_colour":gui.text_field_text_colour,

            "pane_divider_colour":gui.pane_divider_colour,

            #GUI CONTROLLED PREFRENECES
            "--#--#--#--#--#--#--#---#--#--#--#--#--#--#--#--#--SAVE DATA FROM GUI" : "--#--",
            "squaresperpage": gui.squaresperpage.get(),
            "sortbydate": gui.sortbydatevar.get(),

            #Window positions
            "--#--#--#--#--#--#--#---#--#--#--#--#--#--#--#--#--SAVE DATA FOR WINDOWS": "--#--",
            "main_geometry": gui.winfo_geometry(),
            "viewer_geometry": gui.viewer_geometry, 
            "destpane_geometry":gui.destpane_geometry,
            "leftpane_width":gui.leftui.winfo_width(),

            }

        try: #Try to save the preference to prefs.json
            with open(self.prefs_path, "w+") as savef:
                json.dump(save, savef,indent=4, sort_keys=False)
                logger.debug(save)
        except Exception as e:
            logger.warning(("Failed to save prefs:", e))

        try: #Attempt to save the session if autosave is enabled
            if self.autosave:
                self.savesession(False)
        except Exception as e:
            logger.warning(("Failed to save session:", e))

    def moveall(self):
        loglist = []
        for x in self.imagelist:
            out = x.move()

            if isinstance(out, str):
                loglist.append(out)

        try:
            if len(loglist) > 0:
                with open("filelog.txt", "a") as logfile:
                    logfile.writelines(loglist)

        except Exception as e:
            logger.error(f"Failed to write filelog.txt: {e}")
        self.gui.hidemoved()

    def walk(self, src):
        duplicates = self.duplicatenames
        existing = self.existingnames
        supported_formats = {"png", "gif", "jpg", "jpeg", "bmp", "pcx", "tiff", "webp", "psd"}
        animation_support = {"gif", "webp"} # For clarity
        for root, dirs, files in os.walk(src, topdown=True):
            dirs[:] = [d for d in dirs if d not in self.exclude]
            for name in files:
                ext = os.path.splitext(name)[1][1:].lower()
                if ext in supported_formats:
                    imgfile = Imagefile(name, os.path.join(root, name))
                    if ext == "gif" or ext == "webp":
                        imgfile.isanimated = True
                    if name in existing:
                        duplicates.append(imgfile)
                        imgfile.dupename=True
                    else:
                        existing.add(name)
                    self.imagelist.append(imgfile)
                    
        # Sort by date modificated
        if self.gui.sortbydatevar.get():
            self.imagelist.sort(key=lambda img: os.path.getmtime(img.path), reverse=True)
        return self.imagelist

    def checkdupefilenames(self, imagelist):
        duplicates: list[Imagefile] = []
        existing: set[str] = set()

        for item in imagelist:
            if item.name.get() in existing:
                duplicates.append(item)
                item.dupename=True
            else:
                existing.add(item.name)
        return duplicates
        
    def setDestination(self, *args):
        self.hasunmoved = True
        marked = []
        dest = args[0]
        try:
            wid = args[1].widget
        except AttributeError:
            wid = args[1]["widget"]
        if isinstance(wid, tk.Entry):
            pass
        else:
            for x in self.imagelist:
                if x.checked.get():
                    marked.append(x)
            for obj in marked:
                obj.setdest(dest)
                obj.guidata["frame"]['background'] = dest['color']
                obj.guidata["canvas"]['background'] = dest['color']
                obj.checked.set(False)
            self.gui.hideassignedsquare(marked)

    def savesession(self,asksavelocation):
        print("Saving session, Goodbye!")
        if asksavelocation:
            filet=[("Javascript Object Notation","*.json")]
            savelocation=tkFileDialog.asksaveasfilename(confirmoverwrite=True,defaultextension=filet,filetypes=filet,initialdir=os.getcwd(),initialfile=self.gui.sessionpathvar.get())
        else:
            savelocation = self.gui.sessionpathvar.get()
        if len(self.imagelist) > 0:
            imagesavedata = []
            for obj in self.imagelist:
                if hasattr(obj, 'thumbnail'):
                    thumb = obj.thumbnail
                else:
                    thumb = ""
                imagesavedata.append({
                    "name": obj.name.get(),
                    "file_size": obj.file_size,
                    "id": obj.id,
                    "path": obj.path,
                    "dest": obj.dest,
                    "checked": obj.checked.get(),
                    "moved": obj.moved,
                    "thumbnail": thumb,
                    "dupename": obj.dupename,
                    })
            save = {"dest": self.ddp, "source": self.sdp,
                    "imagelist": imagesavedata,"thumbnailsize":self.gui.thumbnailsize,'existingnames':list(self.existingnames)}
            with open(savelocation, "w+") as savef:
                json.dump(save, savef, indent=4)
      
    def loadsession(self):
        sessionpath = self.gui.sessionpathvar.get()
        
        if os.path.exists(sessionpath) and os.path.isfile(sessionpath):
            with open(sessionpath, "r") as savef:
                sdata = savef.read()
                savedata = json.loads(sdata)
            gui = self.gui
            self.sdp = savedata['source']
            self.ddp = savedata['dest']
            self.setup(savedata['dest'])
            print("")
            print(f'Using session:  "{sessionpath}"')
            print(f'Source:   "{self.sdp}"')
            print(f'Target:   "{self.ddp}"')

            if 'existingnames' in savedata:
                self.existingnames = set(savedata['existingnames'])
            for line in savedata['imagelist']:
                if os.path.exists(line['path']):
                    obj = Imagefile(line['name'], line['path'])
                    obj.thumbnail = line['thumbnail']
                    obj.dest=line['dest']
                    obj.id=line['id']
                    obj.file_size=line['file_size']
                    obj.checked.set(line['checked'])
                    obj.moved = line['moved']
                    obj.dupename=line['dupename']
                    
                    self.imagelist.append(obj)

            self.gui.thumbnailsize=savedata['thumbnailsize']
            listmax = min(gui.squaresperpage.get(), len(self.imagelist))
            sublist = self.imagelist[0:listmax]
            gui.displaygrid(self.imagelist, range(0, min(gui.squaresperpage.get(),listmax)))
            gui.guisetup(self.destinations)
            gui.hidemoved()
            gui.hideassignedsquare(sublist)
        else:
            logger.warning("No Last Session!")

    def validate(self, gui):
        self.sdp = self.gui.sdpEntry.get()
        self.ddp = self.gui.ddpEntry.get()
        samepath = (self.sdp == self.ddp)

        if ((os.path.isdir(self.sdp)) and (os.path.isdir(self.ddp)) and not samepath):
            self.setup(self.ddp)
            gui.guisetup(self.destinations)
            gui.sessionpathvar.set(os.path.basename(
                self.sdp)+"-"+os.path.basename(self.ddp)+".json")
            print("")
            print(f'New session:  "{self.gui.sessionpathvar.get()}"')
            print(f'Source:   "{self.sdp}"')
            print(f'Target:   "{self.ddp}"')
            self.walk(self.sdp)
            listmax = min(gui.squaresperpage.get(), len(self.imagelist))
            sublist = self.imagelist[0:listmax]
            print(f'Loading: {len(sublist)}')
            self.generatethumbnails(sublist)
            gui.displaygrid(self.imagelist, range(0, min(len(self.imagelist), gui.squaresperpage.get())))
        elif samepath:
            self.gui.sdpEntry.delete(0, tk.END)
            self.gui.ddpEntry.delete(0, tk.END)
            self.gui.sdpEntry.insert(0, "PATHS CANNOT BE SAME")
            self.gui.ddpEntry.insert(0, "PATHS CANNOT BE SAME")
        else:
            self.gui.sdpEntry.delete(0, tk.END)
            self.gui.ddpEntry.delete(0, tk.END)
            self.gui.sdpEntry.insert(0, "ERROR INVALID PATH")
            self.gui.ddpEntry.insert(0, "ERROR INVALID PATH")

    def setup(self, dest): # scan the destination
        self.destinations = []
        self.destinationsraw = []
        with os.scandir(dest) as it:
            for entry in it:
                if entry.is_dir():
                    random.seed(entry.name)
                    self.destinations.append(
                        {'name': entry.name, 'path': entry.path, 'color': randomColor()})
                    self.destinationsraw.append(entry.path)

    def makethumb(self, imagefile):
            file_name1 = imagefile.path.replace('\\', '/').split('/')[-1]
            if not imagefile.file_size or not imagefile.mod_time:
                file_stats = os.stat(imagefile.path)
                imagefile.file_size = file_stats.st_size
                imagefile.mod_time = file_stats.st_mtime
            id = file_name1 + " " +str(imagefile.file_size)+ " " + str(imagefile.mod_time)

            #dramatically faster hashing.
            hash = md5()
            hash.update(id.encode('utf-8'))
            
            imagefile.setid(hash.hexdigest())

            thumbpath = os.path.join(self.data_dir, imagefile.id+os.extsep+"jpg")
            if(os.path.exists(thumbpath)):
                imagefile.thumbnail = thumbpath
                return

            try:
                im = pyvips.Image.thumbnail(imagefile.path, self.gui.thumbnailsize)
                im.write_to_file(thumbpath)
                imagefile.thumbnail = thumbpath
            except Exception as e:
                logger.error("Error in thumbnail generation: %s", e)

    def generatethumbnails(self, images):
        #logger.info("md5 hashing %s files", len(images))
        max_workers = max(1,self.threads)
        with concurrent.ThreadPoolExecutor(max_workers=max_workers) as executor:
            executor.map(self.makethumb, images)


    def clear(self, *args):
        if askokcancel("Confirm", "Really clear your selection?"):
            for x in self.imagelist:
                x.checked.set(False)

# Run Program
if __name__ == '__main__':
    mainclass = SortImages()
