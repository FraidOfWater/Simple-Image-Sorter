import os

""" #comment when building
import ctypes
try: #presumably for building only?
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dll_path1 = os.path.join(script_dir, 'libvips-cpp-42.dll')
    dll_path2 = os.path.join(script_dir, 'libvips-42.dll')
    dll_path3 = os.path.join(script_dir, 'libglib-2.0-0.dll')
    dll_path4 = os.path.join(script_dir, 'libgobject-2.0-0.dll')
except FileNotFoundError:
    print("The file was not found.")
    
ctypes.CDLL(dll_path1)
ctypes.CDLL(dll_path2)
ctypes.CDLL(dll_path3)
ctypes.CDLL(dll_path4)
"""
    

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

class Imagefile:
    path = ""
    dest = ""

    def __init__(self, name, path) -> None:
        self.name = tk.StringVar()
        self.name.set(name)
        self.path = path
        self.checked = tk.BooleanVar(value=False)
        self.moved = False
        self.assigned = False
        self.isanimated = False
        self.isvisible = False
        self.frames = []
        self.index = 0
        self.delay = 29
        self.truncated = self.name.get()[:10]
        self.isanimating = False
        self.isrunning = False
                        
    def move(self) -> str:
        destpath = self.dest
        if destpath != "" and os.path.isdir(destpath):
            try:
                shmove(self.path, os.path.join(destpath, self.name.get()))
                self.moved = True
                self.show = False
                self.guidata["frame"].configure(
                    highlightbackground="green", highlightthickness=2)
                self.path = os.path.join(destpath, self.name.get())
                returnstr = ("Moved:" + self.name.get() +
                             " -> " + destpath + "\n")
                destpath = ""
                return returnstr
            except Exception as e:
                logging.error("Error moving: %s . File: %s",
                              e, self.name.get())
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
        
        self.existingnames = set()
        self.duplicatenames=[]
        self.autosave=True
        self.gui = GUIManager(self)
        
        # Determine the correct directory for prefs.json
        if getattr(sys, 'frozen', False):  # Check if running as a bundled executable
            script_dir = os.path.dirname(sys.executable)  # Get the directory of the executable
            prefs_path = os.path.join(script_dir, "prefs.json")
        else:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            prefs_path = os.path.join(script_dir, "prefs.json") 
            
        #script_dir = os.path.dirname(os.path.abspath(__file__))
        #prefs_path = os.path.join(script_dir, "prefs.json")
        self.threads = os.cpu_count()
        hotkeys = ""

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
            if len(hotkeys) > 1:
                self.gui.hotkeys = hotkeys
        except Exception as e:
            logging.error("Error loading prefs.json, it is possibly corrupt, try deleting it, or else it doesn't exist and will be created upon exiting the program.")
            logging.error(e)
        self.gui.leftui.configure(width=self.gui.toppane_width)

        self.data_dir = os.path.join(script_dir, "data")
        if(os.path.exists(self.data_dir) and os.path.isdir(self.data_dir)):
            temp = os.listdir(self.data_dir)
            image_files = [f for f in temp if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', 'webp', '.bmp', '.tiff', '.pcx', 'psd'))]
            if image_files:
                first_image_path = os.path.join(self.data_dir, image_files[0])
                try:
                    image = pyvips.Image.new_from_file(first_image_path)
                    width = image.width
                    height = image.height
                    
                    if max(width, height) != self.thumbnailsize:
                        shutil.rmtree(self.data_dir)
                        print(f"Removing data folder, thumbnailsize changed")
                        os.mkdir(self.data_dir)
                        print(f"Re-created data folder.")
                except Exception as e:
                    print(f"Coudln't load first image in data folder")
                    pass
            else:
                print(f"Data folder is empty")
                pass
            pass
        else:
            os.mkdir(self.data_dir)
        self.gui.mainloop()
        

    def moveall(self):
        loglist = []
        temp1 = list(self.gui.assigned_squarelist)
        for x in temp1:
            temp = []
            image_obj = x.obj
            temp.append(image_obj) #store imageobj
            self.gui.assigned_squarelist.remove(x)
            self.gui.moved_squarelist.append(x)
            for obj in temp:
                out = obj.move()
                obj.dest = ""
                obj.assigned = False
                obj.moved = True
                
            if isinstance(out, str):
                loglist.append(out)
        self.gui.refresh_rendered_list()
        self.gui.refresh_destinations()
        try:
            if len(loglist) > 0:
                with open("filelog.txt", "a") as logfile:
                    logfile.writelines(loglist)
        except:
            logging.error("Failed to write filelog.txt")
        

    def walk(self, src):
        duplicates = self.duplicatenames
        existing = self.existingnames
        for root, dirs, files in os.walk(src, topdown=True):
            dirs[:] = [d for d in dirs if d not in self.exclude]
            for name in files:
                ext = os.path.splitext(name)[1][1:].lower()
                if ext == "png" or ext == "gif" or ext == "jpg" or ext == "jpeg" or ext == "bmp" or ext == "pcx" or ext == "tiff" or ext == "webp" or ext == "psd":
                    imgfile = Imagefile(name, os.path.join(root, name))
                    if ext == "gif" or ext == "webp":
                        imgfile.isanimated = True
                    if name in existing:
                        duplicates.append(imgfile)
                    else:
                        existing.add(name)
                    self.imagelist.append(imgfile)
                    
        #Default sorting is based on name. This sorts by date modified.
        if self.gui.sortbydatevar.get():
            self.imagelist.sort(key=lambda img: os.path.getmtime(img.path), reverse=True)
        return self.imagelist
    
    #This tells the setDestination method the current list being viewed.
    #Picture selection checkboxes aren't cleared when switching views
    #Assigning will only happen to selected in the current view, or in the focused destination window.
    def get_current_list(self):
        if self.gui.show_unassigned.get():
            unassign = self.gui.unassigned_squarelist
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
        else:
            for x in current_list[:]:
                image_obj = x.obj
                if image_obj.checked.get():
                    marked.append(image_obj)
            for obj in marked:
                obj.setdest(dest)
                obj.guidata["frame"]['background'] = dest['color']
                obj.guidata["canvas"]['background'] = dest['color']
                obj.checked.set(False)
                
                if self.gui.show_unassigned.get(): #Unassigned list to Assigned list, Assigned True
                    obj.assigned = True
                    for square in current_list:
                        if square.obj.assigned and square not in self.gui.assigned_squarelist:
                            self.gui.unassigned_squarelist.remove(square)
                            self.gui.assigned_squarelist.append(square)
                            try:
                                self.gui.running.remove(square)
                            except Exception as e:
                                pass
                
                #elif self.gui.show_assigned.get(): #Assigned to Assigned, Assigned True, moved false
                #    print("test")
                #    obj.assigned = True
                #    for square in current_list:
                #        if square.obj.assigned and square in self.gui.assigned_squarelist:
                #            self.gui.assigned_squarelist.remove(square)
                #            self.gui.assigned_squarelist.append(square)
                            
                elif self.gui.show_moved.get(): #Moved to Assigned, Assigned True, moved False
                    obj.assigned = True
                    obj.moved = True
                    for square in current_list:
                        if square.obj.assigned and square not in self.gui.assigned_squarelist:
                            self.gui.moved_squarelist.remove(square)
                            self.gui.assigned_squarelist.append(square)
                            try:
                                self.gui.running.remove(square)
                            except Exception as e:
                                pass
            
                            

        marked = []
        for x in self.gui.active_dest_squarelist:
            image_obj = x.obj
            if image_obj.checked.get():
                marked.append(image_obj)
                
        for obj in marked:
            obj.setdest(dest)
            obj.guidata["frame"]['background'] = dest['color']
            obj.guidata["canvas"]['background'] = dest['color']
            obj.checked.set(False)
        

        #Updates main and destination windows.
        
        self.gui.refresh_rendered_list()
        self.gui.refresh_destinations()

    def savesession(self,asksavelocation):
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
                    "path": obj.path,
                    "dest": obj.dest,
                    "checked": obj.checked.get(),
                    "moved": obj.moved,
                    "thumbnail": thumb,
                })
            save = {"dest": self.ddp, "source": self.sdp,
                    "imagelist": imagesavedata,"thumbnailsize":self.thumbnailsize,'existingnames':list(self.existingnames)}
            with open(savelocation, "w+") as savef:
                json.dump(save, savef)

    def loadsession(self):
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
            for o in savedata['imagelist']:
                if os.path.exists(o['path']):
                    n = Imagefile(o['name'], o['path'])
                    n.checked.set(o['checked'])
                    n.moved = o['moved']
                    n.thumbnail = o['thumbnail']
                    n.dest=o['dest']
                    self.imagelist.append(n)
            self.thumbnailsize=savedata['thumbnailsize']
            self.gui.thumbnailsize=savedata['thumbnailsize']
            listmax = min(gui.squaresperpage.get(), len(self.imagelist))
            gui.displaygrid(self.imagelist, range(0, min(gui.squaresperpage.get(),listmax)))
            gui.guisetup(self.destinations)
        else:
            logging.error("No Last Session!")

    def validate(self, gui):
        samepath = (gui.sdpEntry.get() == gui.ddpEntry.get())
        print(f"{gui.sdpEntry.get()}{gui.ddpEntry.get()}")
        if ((os.path.isdir(gui.sdpEntry.get())) and (os.path.isdir(gui.ddpEntry.get())) and not samepath):
            self.sdp = gui.sdpEntry.get()
            self.ddp = gui.ddpEntry.get()
            logging.info("main class setup")
            self.setup(self.ddp)
            logging.info("GUI setup")
            gui.guisetup(self.destinations)
            gui.sessionpathvar.set(os.path.basename(
                self.sdp)+"-"+os.path.basename(self.ddp)+".json")
            logging.info("displaying first image grid")
            self.walk(self.sdp)
            listmax = min(gui.squaresperpage.get(), len(self.imagelist))
            sublist = self.imagelist[0:listmax]
            self.generatethumbnails(sublist)
            gui.displaygrid(self.imagelist, range(0, min(len(self.imagelist), gui.squaresperpage.get())))
        elif gui.sdpEntry.get() == gui.ddpEntry.get():
            gui.sdpEntry.delete(0, len(gui.sdpEntry.get()))
            gui.ddpEntry.delete(0, len(gui.ddpEntry.get()))
            gui.sdpEntry.insert(0, "PATHS CANNOT BE SAME")
            gui.ddpEntry.insert(0, "PATHS CANNOT BE SAME")
        else:
            gui.sdpEntry.delete(0, len(gui.sdpEntry.get()))
            gui.ddpEntry.delete(0, len(gui.ddpEntry.get()))
            gui.sdpEntry.insert(0, "ERROR INVALID PATH")
            gui.ddpEntry.insert(0, "ERROR INVALID PATH")

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
        im = pyvips.Image.new_from_file(imagefile.path,)
        hash = md5()
        hash.update(im.write_to_memory())
        imagefile.setid(hash.hexdigest())
        thumbpath = os.path.join(self.data_dir, imagefile.id+os.extsep+"jpg")
        if os.path.exists(thumbpath):
            imagefile.thumbnail = thumbpath
        else:
            try:
                im = pyvips.Image.thumbnail(imagefile.path, self.thumbnailsize)
                im.write_to_file(thumbpath)
                imagefile.thumbnail = thumbpath
            except Exception as e:
                logging.error("Error:: %s", e)

    def generatethumbnails(self, images):
        logging.info("md5 hashing %s files", len(images))
        max_workers = self.threads
        with concurrent.ThreadPoolExecutor(max_workers=max_workers) as executor:
            executor.map(self.makethumb, images)
        logging.info("Finished making thumbnails")

    def clear(self, *args):
        if askokcancel("Confirm", "Really clear your selection?"):
            for x in self.imagelist:
                x.checked.set(False)
                


# Run Program
if __name__ == '__main__':
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(
        format=format, level=logging.WARNING, datefmt="%H:%M:%S")
    mainclass = SortImages()
