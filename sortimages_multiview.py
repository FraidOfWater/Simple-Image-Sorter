import os
#Zooming for gif and webp? should we use pyramid?
#Just replace the picture with configure, dont create new? hmm? or make the main show use my pic to create a new one! yeah!.
#""" #comment when building
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
#"""
    

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
        self.mod_time = None
        self.file_size = None
        self.checked = tk.BooleanVar(value=False)
        self.destchecked = tk.BooleanVar(value=False)
        self.moved = False
        self.assigned = False
        self.isanimated = None
        self.isvisible = False
        self.isvisibleindestination = False
        self.lazy_loading = True
        self.frames = []
        self.frametimes = []
        self.framecount = 0
        self.index = 0
        self.delay = 100 #Default delay
        self.id = None
        self.truncated = self.name.get()[:50]
                        
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
            #combined_squarelist.remove(x)
            #self.gui.combined_squarelist.append(x)
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
        supported_formats = {"png", "gif", "jpg", "jpeg", "bmp", "pcx", "tiff", "webp", "psd"}
        animation_support = {"gif", "webp"}
        for root, dirs, files in os.walk(src, topdown=True):
            dirs[:] = [d for d in dirs if d not in self.exclude]
            for name in files:
                ext = os.path.splitext(name)[1][1:].lower()
                if ext in supported_formats:
                    full_path = f"{root}/{name}"
                    #full_path = os.path.join(root, name) #long time initializing
                    imgfile = Imagefile(name, full_path)

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

    #@profile
    def setDestination(self, *args):
        dest = args[0]
        marked = []
        current_list = []
        current_list = self.get_current_list()     
        #self.gui.render_refresh = []
        temp2 = []   
        try:
            wid = args[1].widget
        except AttributeError:
            wid = args[1]["widget"]

        if isinstance(wid, tk.Entry):
            pass
        
        else: #we could make marked list from check button adding it to the list or removing. ##OPTIMIZE
            if current_list:
                marked = [x for x in current_list if x.obj.checked.get()]

                for x in marked:
                    x.obj.setdest(dest)
                    x.obj.guidata["frame"]['background'] = dest['color']
                    x.obj.guidata["canvas"]['background'] = dest['color']
                    x.obj.checked.set(False)

                    #If we have the unassigned view, we want to move images from unassigned list to assigned list.
                    if self.gui.show_unassigned.get(): #Unassigned list to Assigned list, Assigned True
                        x.obj.assigned = True
                        if x.obj.assigned and x not in self.gui.assigned_squarelist:
                            self.gui.unassigned_squarelist.remove(x)
                            self.gui.assigned_squarelist.append(x) 

                            if x.obj.dest == dest['path']:
                                #self.gui.filtered_images.append(x.obj)
                                if hasattr(self.gui, 'destwindow'): # if we have new assigned.
                                    if self.gui.dest == dest['path']: #the path is here because we only want to append when path is the same as current dest
                                        self.gui.filtered_images.append(x.obj)
                                         #imageobject eventually
                                        self.gui.queue.append(x)

                            #self.gui.combined_squarelist.append(x)
                            try:
                                self.gui.running.remove(x)
                                self.gui.track_animated.remove(x)
                            except Exception as e:
                                pass

                    ##this is not enabled because we dont want placement to change here, it is too distracting.
                    elif self.gui.show_assigned.get(): #Assigned to Assigned, Assigned True, moved false
                        #self.gui.filtered_images = []
                        #obj.assigned = True
                        if hasattr(self.gui, 'destwindow'): # if we have the dest window open
                            #self.gui.filtered_images.remove(x.obj)
                            #self.gui.filtered_images.append(x.obj)
                            if self.gui.dest == dest['path']: # if the dest chosen and current dest window point to same dest
                                try:
                                    if x.obj not in self.gui.filtered_images:
                                        self.gui.filtered_images.append(x.obj) # this makes is refresh the pos. but now getting stuff out of dest win or new into it no working.
                                        self.gui.queue.append(x)
                                    else:
                                        x.obj.checked.set(True)
                                        #self.gui.destgrid_updateslist.append(x) # x in here?
                                        x.obj.destchecked.set(True)                                    

                                        #self.gui.filtered_images.remove(x.obj)
                                        #self.gui.filtered_images.append(x.obj)

                                except Exception as e:
                                    print(f"first {e}")
                            else:
                                try:
                                    self.gui.filtered_images.remove(x.obj)
                                except Exception as e:
                                    print(f"second {e}")
                                    pass
                    #If we have the moved view, we want to move images from moved list to assigned list.
                    elif self.gui.show_moved.get(): #Moved to Assigned, Assigned True, moved False
                        x.obj.assigned = True
                        x.obj.moved = True
                        if x.obj.assigned and x not in self.gui.assigned_squarelist:
                            self.gui.moved_squarelist.remove(x)
                            self.gui.assigned_squarelist.append(x)
                            if x.obj.dest == dest['path']:
                                #self.gui.filtered_images.append(x.obj)
                                if hasattr(self.gui, 'destwindow'): # if we have new assigned.
                                    if self.gui.dest == dest['path']:
                                        self.gui.filtered_images.append(x.obj)
                                        self.gui.queue.append(x)
                            #self.gui.combined_squarelist.remove(square)
                            #self.gui.combined_squarelist.append(square)
                            try:
                                self.gui.running.remove(x)
                                self.gui.track_animated.remove(x)
                            except Exception as e:
                                pass
                            

        #checks for click in destination windows, if seen, changes their colour.
        marked = []
        ##--could replace with normal marked list which is activated and removed from by athe checkbutton functioning. no need to filter the whole list!
        marked = [square for square in self.gui.dest_squarelist if square.obj.destchecked.get()]    
        
        #changes destination and the color regardless of whether it was active window or dest that this happened in.
        temp = self.gui.assigned_squarelist.copy()

        for square in marked:
            if self.gui.show_assigned.get():
                for gridsquare in self.gui.assigned_squarelist: ##OPTIMIZE change to the current displayedlist, but that has to not be dictionary.
                    if gridsquare.obj.id == square.obj.id:
                        if not(square.obj.destchecked.get() and square.obj.checked.get()):
                            self.gui.render_refresh.append(gridsquare) #need the other record.
                            break
             #we check against the main assigned list to find the key, then we remove it and add it again, so the order is saved.
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
                #self.gui.queue.append(square.obj) # when the image selected is not going to the same destination, #to remove?
                """
                elif item.obj.id == square.obj.id:
                    self.gui.combined_squarelist.remove(item)
                    self.gui.combined_squarelist.append(item)
                """ 
            
            square.obj.setdest(dest)
            square.obj.guidata["frame"]['background'] = dest['color']
            square.obj.guidata["canvas"]['background'] = dest['color']
            square.obj.destchecked.set(False)
        
        #Updates main and destination windows.
        
        self.gui.refresh_rendered_list()
        if hasattr(self.gui, 'destwindow'): #only refresh dest list if destwindow active.
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
                
                if obj.isanimated:
                    imagesavedata.append({
                        "name": obj.name.get(),
                        "path": obj.path,
                        "dest": obj.dest,
                        "checked": obj.checked.get(),
                        "moved": obj.moved,
                        "thumbnail": thumb,
                        "isanimated": obj.isanimated,

                    })
                else:
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
                    try:
                        n.isanimated=o['isanimated']
                    except Exception as e: #nonexistent
                        pass
                    self.imagelist.append(n)
            
            self.thumbnailsize=savedata['thumbnailsize']
            self.gui.thumbnailsize=savedata['thumbnailsize']
            listmax = min(gui.squaresperpage.get(), len(self.imagelist))
            gui.displaygrid(self.imagelist, range(0, min(gui.squaresperpage.get(),listmax)))
            gui.guisetup(self.destinations)
        else:
            logging.error("No Last Session!")

    def validate(self, gui):

        self.sdp = gui.sdpEntry.get()
        self.ddp = gui.ddpEntry.get()
        samepath = (self.sdp == self.ddp)

        print(f"{gui.sdpEntry.get()}, {self.ddp}")
        if ((os.path.isdir(self.sdp)) and (os.path.isdir(self.ddp)) and not samepath):

            
            #logging.info("main class setup")
            self.setup(self.ddp)
            #logging.info("GUI setup")
            gui.guisetup(self.destinations)
            gui.sessionpathvar.set(os.path.basename(
                self.sdp)+"-"+os.path.basename(self.ddp)+".json")
            #logging.info("displaying first image grid")
            self.walk(self.sdp)
            listmax = min(gui.squaresperpage.get(), len(self.imagelist))
            sublist = self.imagelist[0:listmax]
            self.generatethumbnails(sublist) #so the problem is that this doesnt check the existing stuff!
            gui.displaygrid(self.imagelist, range(0, min(len(self.imagelist), gui.squaresperpage.get())))

        elif samepath:
            self.sdp.delete(0, tk.END)
            self.ddp.delete(0, tk.END)
            self.sdp.insert(0, "PATHS CANNOT BE SAME")
            self.ddp.insert(0, "PATHS CANNOT BE SAME")
        else:
            self.sdp.delete(0, tk.END)
            self.ddp.delete(0, tk.END)
            self.sdp.insert(0, "ERROR INVALID PATH")
            self.ddp.insert(0, "ERROR INVALID PATH")


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
                print("Generated a thumbnail")
                im = pyvips.Image.thumbnail(imagefile.path, self.thumbnailsize)
                im.write_to_file(thumbpath)
                imagefile.thumbnail = thumbpath
            except Exception as e:
                logging.error("Error:: %s", e)
    
    def generatethumbnails(self, images):
        #logging.info("md5 hashing %s files", len(images))
        max_workers = max(1,self.threads)
        with concurrent.ThreadPoolExecutor(max_workers=max_workers) as executor:
            executor.map(self.makethumb, images)
        #logging.info("Finished making thumbnails")

    def clear(self, *args):
        if askokcancel("Confirm", "Really clear your selection?"):
            for x in self.imagelist:
                x.checked.set(False)
    
    def load_frames(self, gridsquare):
        try:            
            with Image.open(gridsquare.obj.path) as img:

                with pyvips.Image.new_from_file(gridsquare.obj.path, access='sequential') as image:
                    image = pyvips.Image.new_from_file(gridsquare.obj.path, access='sequential')
                    gridsquare.obj.framecount = image.get('n-pages')
                gridsquare.obj.delay = img.info.get('duration', 20)

                #print(f"test {gridsquare.obj.framecount}")
                for i in range(gridsquare.obj.framecount):
                    img.seek(i)  # Move to the ith frame
                    frame = img.copy()
                    gridsquare.obj.frametimes.append(frame.info.get('duration',gridsquare.obj.delay))
                    frame.thumbnail((self.thumbnailsize, self.thumbnailsize), Image.Resampling.LANCZOS)
                    tk_image = ImageTk.PhotoImage(frame)
                    gridsquare.obj.frames.append(tk_image)
            
                gridsquare.obj.lazy_loading = False
                print(f"All frames loaded for: {gridsquare.obj.truncated}")
        except Exception as e: #fallback to static.
            print(f"Fallback to static, {gridsquare.obj.truncated}: {e}")
            gridsquare.obj.isanimated = False
            
# Run Program
if __name__ == '__main__':
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(
        format=format, level=logging.WARNING, datefmt="%H:%M:%S")
    mainclass = SortImages()
