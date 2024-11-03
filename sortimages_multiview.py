import os
import sys
from shutil import move as shmove
import tkinter as tk
from tkinter.messagebox import askokcancel
import json
import random
from math import floor, sqrt
from tkinter import filedialog as tkFileDialog
import concurrent.futures as concurrent
import logging
from hashlib import md5
import pyvips
from gui import GUIManager, randomColor
import shutil
from PIL import Image, ImageTk

""" # This can/should be commented if you build.
import ctypes
try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dll_path1 = os.path.join(script_dir, 'libvips-cpp-42.dll')
    dll_path2 = os.path.join(script_dir, 'libvips-42.dll')
    dll_path3 = os.path.join(script_dir, 'libglib-2.0-0.dll')
    dll_path4 = os.path.join(script_dir, 'libgobject-2.0-0.dll')
except FileNotFoundError:
    logging.error("The file was not found. (You are missing .dlls)")
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
        self.destchecked = tk.BooleanVar(value=False)
        self.moved = False
        self.assigned = False
        self.isanimated = False
        self.isvisible = False
        self.isvisibleindestination = False
        self.lazy_loading = True
        self.frames = []
        self.frametimes = []
        self.framecount = 0
        self.index = 0
        self.delay = 100 #Default delay
        self.id = None
    
    def move(self, x, assigned, moved) -> str:
        destpath = self.dest
        do_not_move_if_exists = True # This flag prevents overwriting of files in destination that have the same name as source.

        if destpath != "" and os.path.isdir(destpath):
            file_name = self.name.get()
            exists_already_in_destination = os.path.exists(os.path.join(destpath, file_name))
            if exists_already_in_destination:
                if do_not_move_if_exists:
                    logging.error(f"File {self.name.get()} already exists at destination, file not moved or deleted from source.")
                    return ("") # Returns if 1. Would overwrite someone
            try:
                new_path = os.path.join(destpath, file_name)
                old_path = os.path.join(self.path, file_name)

                shmove(self.path, new_path) # Try to move, fails if 1. Locked

                # If above functons and checks fail, these below won't get set. As designed
                assigned.remove(x)
                moved.append(x) # Moves from assigned to moved ?
                
                self.moved = True
                self.show = False

                self.guidata["frame"].configure(
                    highlightbackground="green", highlightthickness=2)
                
                self.path = new_path
                returnstr = ("Moved:" + self.name.get() +
                             " -> " + destpath + "\n")
                destpath = ""
                self.dest = ""
                self.assigned = False
                self.moved = True
                return returnstr
            
            except Exception as e:
                logging.error("Error moving/deleting: %s . File: %s",
                              e, self.name.get())
                
                if os.path.exists(new_path) and os.path.exists(old_path): # Shmove has copied a duplicate to destinations, but image couldn't be moved. This deletes the duplicate from destination.
                    os.remove(new_path)
                    print("Image was locked and the move was completed partially, deleting image from destination, leaving it in source")

                self.guidata["frame"].configure(
                    highlightbackground="red", highlightthickness=2)
                return ("Error moving: %s . File: %s", e, self.name.get())

    def setid(self, id):
        self.id = id

    def setguidata(self, data):
        self.guidata = data

    def setdest(self, dest):
        self.dest = dest["path"]
        logging.debug("Set destination of %s to %s",
                      self.name.get(), self.dest)




class SortImages:
    imagelist = []
    destinations = []
    exclude = []
    thumbnailsize = 256

    def __init__(self) -> None:
        logging.info("Starting main program")
        self.existingnames = set()
        self.duplicatenames=[]
        self.autosave=True
        self.gui = GUIManager(self)
        
        logging.info("Loading preferences")

        # Determine the correct directory for prefs.json
        if getattr(sys, 'frozen', False):  # Check if running as a bundled executable
            script_dir = os.path.dirname(sys.executable)  # Get the directory of the executable
            prefs_path = os.path.join(script_dir, "prefs.json")
        else: # Assumes we are running from script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            prefs_path = os.path.join(script_dir, "prefs.json") 
            self.data_dir = os.path.join(script_dir, "data")
            data_dir = self.data_dir
            
        self.threads = os.cpu_count()
        hotkeys = ""
        # Loads preferences
        try:
            with open(prefs_path, "r") as prefsfile:
                jdata = prefsfile.read()
                jprefs = json.loads(jdata)
                if 'hotkeys' in jprefs:
                    hotkeys = jprefs["hotkeys"]
                if 'thumbnailsize' in jprefs:
                    self.gui.thumbnailsize = int(jprefs["thumbnailsize"])
                    self.thumbnailsize = int(jprefs["thumbnailsize"])
                if 'threads' in jprefs:
                    self.threads = jprefs['threads']
                if "hideonassign" in jprefs:
                    self.gui.hideonassignvar.set(jprefs["hideonassign"])
                if "hidemoved" in jprefs:
                    self.gui.hidemovedvar.set(jprefs["hidemoved"])
                if "sortbydate" in jprefs:
                    self.gui.sortbydatevar.set(jprefs["sortbydate"])
                self.exclude = jprefs["exclude"]
                self.gui.sdpEntry.delete(0, len(self.gui.sdpEntry.get()))
                self.gui.ddpEntry.delete(0, len(self.gui.ddpEntry.get()))
                self.gui.sdpEntry.insert(0, jprefs["srcpath"])
                self.gui.ddpEntry.insert(0, jprefs["despath"])
                if "squaresperpage" in jprefs:
                    self.gui.squaresperpage.set(int(jprefs["squaresperpage"]))
                if "imagewindowgeometry" in jprefs:
                    self.gui.imagewindowgeometry = jprefs["imagewindowgeometry"]
                if "geometry" in jprefs:
                    self.gui.geometry(jprefs["geometry"])
                if "lastsession" in jprefs:
                    self.gui.sessionpathvar.set(jprefs['lastsession'])
                if "autosavesession" in jprefs:
                    self.autosave = jprefs['autosave']
                if "toppane_width" in jprefs:
                    self.gui.toppane_width = jprefs['toppane_width']
                if "middlepane_width" in jprefs:
                    self.gui.middlepane_width = jprefs['middlepane_width']
                if "destinationwindow" in jprefs:
                    self.gui.save = jprefs['destinationwindow']
                if "background_colour" in jprefs:
                    self.gui.background_colour = jprefs['background_colour']
                if "button_colour" in jprefs:
                    self.gui.button_colour = jprefs['button_colour']
                if "text_colour" in jprefs:
                    self.gui.text_colour = jprefs['text_colour']
                if "canvas_colour" in jprefs:
                    self.gui.canvas_colour = jprefs['canvas_colour']
                if "active_background_colour" in jprefs:
                    self.gui.active_background_colour = jprefs['active_background_colour']
                if "grid_background_colour" in jprefs:
                    self.gui.grid_background_colour = jprefs['grid_background_colour']
                if "active_foreground_colour" in jprefs:
                    self.gui.active_foreground_colour = jprefs['active_foreground_colour']
                if "selectcolour" in jprefs:
                    self.gui.selectcolour = jprefs['selectcolour']
                if "divider_colour" in jprefs:
                    self.gui.divider_colour = jprefs['divider_colour']
                if "textlength" in jprefs:
                    self.gui.textlength = jprefs['textlength']
                if "gridsquare_padx" in jprefs:
                    self.gui.gridsquare_padx = jprefs['gridsquare_padx']
                if "gridsquare_pady" in jprefs:
                    self.gui.gridsquare_pady = jprefs['gridsquare_pady']
                if "checkbox_height" in jprefs:
                    self.gui.checkbox_height = jprefs['checkbox_height']
                    
            if len(hotkeys) > 1:
                self.gui.hotkeys = hotkeys
        except Exception as e:
            logging.error("Error loading prefs.json, it is possibly corrupt, try deleting it, or else it doesn't exist and will be created upon exiting the program.")
            logging.error(e)

        # Adjusts some window positions and sizes to user preferred after creation
        self.gui.leftui.configure(width=self.gui.toppane_width)
        self.gui.image_display_frame.configure(width = self.gui.middlepane_width)

        logging.info("Checking data folder")

        #This deletes the data directory if the first picture doesnt match the thumbnail size from prefs. (If user changes thumbnailsize, we want to generate thumbnails again)
        
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
                    if max(width, height) != self.thumbnailsize:
                        shutil.rmtree(data_dir)
                        logging.info(f"Removing data folder, thumbnailsize changed")
                        os.mkdir(data_dir)
                        logging.info(f"Re-created data folder.")
                except Exception as e:
                    logging.error(f"Couldn't load first image in data folder")
            else:
                logging.info(f"Data folder is empty")
                pass
            pass
        else:
            os.mkdir(self.data_dir)
        self.gui.mainloop()

    def moveall(self):
        logging.info("Moving items")

        flag = False
        check_if_window_open = hasattr(self.gui, 'second_window') and self.gui.second_window and self.gui.second_window.winfo_exists()

        # If an imageviewer window is open, close it. (It locks move operations)
        if check_if_window_open and len(self.gui.assigned_squarelist) > 0:
            self.gui.saveimagewindowgeo()
            # This is needed ? testing
            #self.gui.Image_frame.closing = False
            #self.gui.Image_frame.close_window()
            #del self.gui.Image_frame
            flag = True

        loglist = []

        assigned = self.gui.assigned_squarelist
        moved = self.gui.moved_squarelist

        for x in self.gui.assigned_squarelist:
            out = x.obj.move(x, assigned, moved) # Pass functionality to happen in move so it can fail removing from the sorted lists when shmove fails.
            
            if isinstance(out, str): # May report images that were failed ?
                loglist.append(out)

        self.gui.refresh_rendered_list()
        self.gui.refresh_destinations()

        try:
            if len(loglist) > 0:
                with open("filelog.txt", "a") as logfile:
                    logfile.writelines(loglist)

        except Exception as e:
            logging.error(f"Failed to write filelog.txt: {e}")

        if len(self.gui.displayedlist) > 0 and flag: # Reopen image viewer now that moves are completed
            self.gui.displayimage(self.gui.displayedlist[self.gui.last_viewed_image_pos].obj)

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
    
    # Communicates what list is selected
    def get_current_list(self):
        if self.gui.show_unassigned.get():
            unassign = self.gui.unassigned_squarelist
            if self.gui.show_animated.get():
                unassigned_animated = [item for item in unassign if item.obj.isanimated]
                return unassigned_animated
            else:
                return unassign
        
        elif self.gui.show_assigned.get():
            assign = self.gui.assigned_squarelist
            return assign
        
        elif self.gui.show_moved.get():
            moved = self.gui.moved_squarelist
            return moved
        
    def setDestination(self, *args):
        dest = args[0]
        marked = []
        current_list = []
        current_list = self.get_current_list()

        try:
            wid = args[1].widget
        except AttributeError:
            wid = args[1]["widget"]
        if isinstance(wid, tk.Entry):
            pass
        # Return all images whose checkbox is checked (And currently in view by image viewer, so you can just press a hotkey and not have to check a checkbox everytime) (If interacting with other squares, it will cancel itself out. This is so user wont accidentally move anything.)
        else:
            marked = [x for x in current_list if x.obj.checked.get()]
            #if self.gui.show_next.get():
            if self.gui.current_selection_obj and self.gui.current_selection_obj_flag: # to see if we have clicked elsewhere as to not move the displayed image anymore.
                for x in current_list:
                    if self.gui.current_selection_obj.id == x.obj.id:
                        if x not in marked:
                            marked.append(x)
                            
            for x in marked:
                x.obj.setdest(dest)
                x.obj.guidata["frame"]['background'] = dest['color']
                x.obj.guidata["canvas"]['background'] = dest['color']
                x.obj.checked.set(False)
                
                # Move from unasssigned to assigned
                if self.gui.show_unassigned.get():
                    x.obj.assigned = True
                    if x.obj.assigned and x not in self.gui.assigned_squarelist:
                        self.gui.unassigned_squarelist.remove(x)
                        self.gui.assigned_squarelist.append(x) 

                        # Destination view different behaviour
                        if x.obj.dest == dest['path']:
                            if hasattr(self.gui, 'destwindow'): # if we have new assigned.
                                if self.gui.dest == dest['path']: #the path is here because we only want to append when path is the same as current dest
                                    self.gui.filtered_images.append(x.obj)
                                     #imageobject eventually
                                    self.gui.queue.append(x)

                        # Stop animations
                        if x in self.gui.running:
                            self.gui.running.remove(x)
                        if x in self.gui.track_animated:
                            self.gui.track_animated.remove(x)

                # Moving from assigned to assigned
                elif self.gui.show_assigned.get():

                    # Different behaviour for destination view
                    if hasattr(self.gui, 'destwindow'): # if we have the dest window open
                        if self.gui.dest == dest['path']: # if the dest chosen and current dest window point to same dest
                            if x.obj not in self.gui.filtered_images:
                                self.gui.filtered_images.append(x.obj) # this makes is refresh the pos. but now getting stuff out of dest win or new into it no working.
                                self.gui.queue.append(x)
                            else:
                                x.obj.checked.set(True)
                                x.obj.destchecked.set(True)                                    

                        else:
                            if x.obj in self.gui.filtered_images:
                                self.gui.filtered_images.remove(x.obj)

                # Moving from moved to assigned
                elif self.gui.show_moved.get():
                    x.obj.assigned = True
                    x.obj.moved = True
                    if x.obj.assigned and x not in self.gui.assigned_squarelist:
                        self.gui.moved_squarelist.remove(x)
                        self.gui.assigned_squarelist.append(x)
                        if x.obj.dest == dest['path']:
                            if hasattr(self.gui, 'destwindow'): # if we have new assigned.
                                if self.gui.dest == dest['path']:
                                    self.gui.filtered_images.append(x.obj)
                                    self.gui.queue.append(x)

                        # Stop animations
                        if x in self.gui.running:
                            self.gui.running.remove(x)
                        if x in self.gui.track_animated:
                            self.gui.track_animated.remove(x)
        
        # Check for destination view changes separately. Note, We use destchecked here, not checked.
        marked = []
        marked = [square for square in self.gui.dest_squarelist if square.obj.destchecked.get()]    
        temp = self.gui.assigned_squarelist.copy()

        # Returns all images that are marked, but who are already assigned
        # Why? IDK. It has to do with the behaviour of how items add to the list.
        # Likely so we can update their positions in the list!
        for square in marked:
            if self.gui.show_assigned.get():
                for gridsquare in self.gui.assigned_squarelist:
                    if gridsquare.obj.id == square.obj.id:
                        if not(square.obj.destchecked.get() and square.obj.checked.get()):
                            self.gui.render_refresh.append(gridsquare)
                            break
        
            #we check against the main assigned list to find the key, then we remove it and add it again, so the order is saved.
            # What the fuck is this? I think it had something to do with how I couldnt use the same gridsquare for dest and imagegrid, so this has to match them.
            for item in temp:
                if item.obj.id == square.obj.id and dest['path'] == square.obj.dest:
                    if not (square.obj.destchecked.get() and square.obj.checked.get()):
                        self.gui.assigned_squarelist.remove(item)
                        self.gui.assigned_squarelist.append(item)
                    square.obj.checked.set(False)
                    self.gui.destgrid_updateslist.append(square)
                    self.gui.filtered_images.remove(square.obj)
                    self.gui.filtered_images.append(square.obj) # going to the same destnation, just refresh, update pos.
                    break
                elif item.obj.id == square.obj.id:
                    self.gui.assigned_squarelist.remove(item)
                    self.gui.assigned_squarelist.append(item)
                    self.gui.filtered_images.remove(square.obj)
                    
                    break
            
            square.obj.setdest(dest)
            square.obj.guidata["frame"]['background'] = dest['color']
            square.obj.guidata["canvas"]['background'] = dest['color']
            square.obj.destchecked.set(False) #Not .checked for purposes of having different actions take place independent of current view. So
            #For example... I dont remember
            #Very helpful!

        #Updates main and destination windows.
        self.gui.refresh_rendered_list()
        if hasattr(self.gui, 'destwindow'): #only refresh dest list if destwindow active.
            self.gui.refresh_destinations()
        
        # This attempts to display the item in the current index after setdestination has completed.
        #Should only run if something is already displayed. If nothing is displayed, user wouldn't want a new image displayed.
        image_viewer_is_open = hasattr(self.gui, 'second_window') and self.gui.second_window and self.gui.second_window.winfo_exists()
        if (image_viewer_is_open or self.gui.dock_view) and self.gui.show_next.get():
            #If second window OPEN. We should display the next image in the displayed list. We should also reset the border colour to normal.
            try:
                if self.gui.current_selection: # try to restore old's border colour.
                    self.gui.current_selection[0].canvas.configure(highlightcolor=self.gui.image_border_selection_colour, highlightbackground = self.gui.image_border_colour) #reset to default

                # always add colour to the selected indexe's gridsquare.
                self.gui.displayedlist[self.gui.last_viewed_image_pos].canvas.configure(highlightbackground = "blue", highlightcolor = "blue") #Modify new pics border colour in the index.
                self.gui.templist = []
                self.gui.templist.append(self.gui.displayedlist[self.gui.last_viewed_image_pos].obj) # records square that's checkbox was set by this function

                #if gridsquare is same as gridsquare from current_selection, dont run this
                if not self.gui.current_selection[0] == self.gui.displayedlist[self.gui.last_viewed_image_pos]:
                    self.gui.displayimage(self.gui.displayedlist[self.gui.last_viewed_image_pos].obj) # Open the new picture that has entered the index.
                self.gui.current_selection = []

                self.gui.current_selection.append(self.gui.displayedlist[self.gui.last_viewed_image_pos]) #adds modified to current list

                self.gui.leftui.focus_set()
            except Exception as e:
                logging.error(f"Error show_next: {e}")

    def savesession(self,asksavelocation):
        logging.info("Saving session, Goodbye!")
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
                    if obj.isanimated:
                        imagesavedata.append({
                        "name": obj.name.get(),
                        "file_size": obj.file_size,
                        "id": obj.id,
                        "path": obj.path,
                        "dest": obj.dest,
                        "checked": obj.checked.get(),
                        "moved": obj.moved,
                        "thumbnail": thumb,
                        "isanimated": obj.isanimated, 
                        "dupename": obj.dupename,
                        
                    })
                    else:
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
                    "imagelist": imagesavedata,"thumbnailsize":self.thumbnailsize,'existingnames':list(self.existingnames)}
            with open(savelocation, "w+") as savef:
                json.dump(save, savef, indent=4)
      
    def loadsession(self):
        logging.info("Loading session")
        sessionpath = self.gui.sessionpathvar.get()
        if os.path.exists(sessionpath) and os.path.isfile(sessionpath):
            with open(sessionpath, "r") as savef:
                sdata = savef.read()
                savedata = json.loads(sdata)
            gui = self.gui
            self.ddp = savedata['dest']
            self.sdp = savedata['source']
            self.setup(savedata['dest'])
            if 'existingnames' in savedata:
                self.existingnames = set(savedata['existingnames'])
            for line in savedata['imagelist']:
                if os.path.exists(line['path']):
                    obj = Imagefile(line['name'], line['path'])
                    obj.checked.set(line['checked'])
                    obj.moved = line['moved']
                    obj.thumbnail = line['thumbnail']
                    obj.dupename=line['dupename']
                    obj.dest=line['dest']
                    obj.id=line['id']
                    obj.file_size=line['file_size']
                    try:
                        obj.isanimated=line['isanimated']
                    except Exception as e:
                        logging.debug(f"No value isanimated: {e}")
                    self.imagelist.append(obj)
            
            self.thumbnailsize=savedata['thumbnailsize']
            self.gui.thumbnailsize=savedata['thumbnailsize']
            listmax = min(gui.squaresperpage.get(), len(self.imagelist))
            gui.displaygrid(self.imagelist, range(0, min(gui.squaresperpage.get(),listmax)))
            gui.guisetup(self.destinations)
        else:
            logging.error("No Last Session!")
      
    def validate(self, gui):

        self.sdp = self.gui.sdpEntry.get()
        self.ddp = self.gui.ddpEntry.get()
        samepath = (self.sdp == self.ddp)

        logging.info(f"Using source: {self.gui.sdpEntry.get()}, and destination: {self.ddp}")
        if ((os.path.isdir(self.sdp)) and (os.path.isdir(self.ddp)) and not samepath):

            logging.info("Setting up GUI")
            self.setup(self.ddp)
            gui.guisetup(self.destinations)
            gui.sessionpathvar.set(os.path.basename(
                self.sdp)+"-"+os.path.basename(self.ddp)+".json")
            logging.info("Scanning folders")
            self.walk(self.sdp)
            listmax = min(gui.squaresperpage.get(), len(self.imagelist))
            sublist = self.imagelist[0:listmax]
            logging.info("Generating thumbnails")
            self.generatethumbnails(sublist)
            logging.info("Displaying images")
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


    def setup(self, dest):
        # scan the destination
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
                im = pyvips.Image.thumbnail(imagefile.path, self.thumbnailsize)
                im.write_to_file(thumbpath)
                imagefile.thumbnail = thumbpath
                logging.debug("Generated a thumbnail")
            except Exception as e:
                logging.error("Error in thumbnail generation: %s", e)
    
    def generatethumbnails(self, images):
        #logging.info("md5 hashing %s files", len(images))
        max_workers = max(1,self.threads)
        with concurrent.ThreadPoolExecutor(max_workers=max_workers) as executor:
            executor.map(self.makethumb, images)
        logging.info("Finished making thumbnails")

    def clear(self, *args):
        if askokcancel("Confirm", "Really clear your selection?"):
            for x in self.imagelist:
                x.checked.set(False)

    # Creates frames and frametimes for gifs and webps
    def load_frames(self, gridsquare):
        logging.info("Loading frames")
        try:            
            with Image.open(gridsquare.obj.path) as img:
                gridsquare.obj.framecount = img.n_frames

                if gridsquare.obj.framecount == 1: #Only one frame, cannot animate
                    raise Exception(f"Found static: {gridsquare.obj.name.get()}")
                                
                logging.debug(f"Found animated: {gridsquare.obj.name.get()} with {gridsquare.obj.framecount} frames. {gridsquare.obj.delay}")
                for i in range(gridsquare.obj.framecount):
                    img.seek(i)  # Move to the ith frame
                    frame = img.copy()
                    frame_frametime = frame.info.get('duration',gridsquare.obj.delay)
                    if frame_frametime == 0:
                        frame_frametime = gridsquare.obj.delay # Replace with default_delay
                    gridsquare.obj.frametimes.append(frame_frametime)
                    frame.thumbnail((self.thumbnailsize, self.thumbnailsize), Image.Resampling.LANCZOS)
                    tk_image = ImageTk.PhotoImage(frame)
                    gridsquare.obj.frames.append(tk_image)
                gridsquare.obj.lazy_loading = False
                logging.debug(f"frametimes {gridsquare.obj.frametimes}")
                logging.info(f"All frames loaded for: {gridsquare.obj.name.get()[:30]}")
        except Exception as e: #fallback to static.
            logging.error(f"Error in load_frames: {e}")
            gridsquare.obj.isanimated = False
            
            
# Run Program
if __name__ == '__main__':
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(
        format=format, level=logging.WARNING, datefmt="%H:%M:%S")
    mainclass = SortImages()
