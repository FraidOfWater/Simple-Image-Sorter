# -*- coding: utf-8 -*-
# Advanced zoom for images of various types from small to huge up to several GB
import os
import math
import warnings
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from autoscrollbar import AutoScrollbar

class CanvasImage:
	""" Display and zoom image """
	def __init__(self, master, path, imagewindowgeometry, background_colour):
		""" Initialize the ImageFrame """
		self.background_colour = background_colour
		self.imscale = 1.0  # scale for the canvas image zoom, public for outer classes
		self.__delta = 1.15  # zoom magnitude
		self.__filter = Image.Resampling.LANCZOS  # could be: NEAREST, BILINEAR, BICUBIC and ANTIALIAS
		self.__previous_state = 0  # previous state of the keyboard
		self.path = path  # path to the image, should be public for outer classes

				#relating to animation
		self.is_animated = False
		self.frames = []
		self.original_frames = []
		self.index = 0
		self.delay = 100
  
		#Check if gif or not
		try:
			self.image = Image.open(path)
			print("Image open.")
			
			if self.image.format in ['GIF', 'WEBP']:
				print(f"The image is in {self.image.format} format.")
				self.is_animated = True
			else:
				print(f"The image is in {self.image.format} format, which is not WEBP or GIF.")
		except FileNotFoundError:
			print(f"File not found: {path}")
			return
		except Exception as e:
			print(f"An error occurred: {e}")
			return

		#Load frames if animated
		if self.is_animated:
			try:
				for i in range(self.image.n_frames):
					self.image.seek(i)  # Move to the ith frame
					frame = ImageTk.PhotoImage(self.image.copy())
					self.frames.append(frame)
					self.original_frames.append(self.image.copy())
					self.delay = self.image.info.get('duration', 100)
					print(f"{self.delay}")
					print("Load frames.")
			except Exception as e:
				print(f"Error loading frames: {e}")
				return
   
  		# Create ImageFrame in master widget
		self.__imframe = ttk.Frame(master)  # This is the ttk.frame for the main window.
  
 		# Vertical and horizontal scrollbars for __imframe
		hbar = AutoScrollbar(self.__imframe, orient='horizontal')
		vbar = AutoScrollbar(self.__imframe, orient='vertical')
		hbar.grid(row=1, column=0, sticky='we')
		vbar.grid(row=0, column=1, sticky='ns')
  
		# Create canvas and bind it with scrollbars. Public for outer classes
		#Avoids using update_idletasks()
		geometry_width, geometry_height = imagewindowgeometry.split('x',1)
  
		# Set canvas dimensions to remove scrollbars
		self.canvas = tk.Canvas(self.__imframe, bg=self.background_colour, highlightthickness=0, xscrollcommand=hbar.set, yscrollcommand=vbar.set, width=geometry_width, height = geometry_height)
		self.canvas.grid(row=0, column=0, sticky='nswe') #Bind to __imframe grid.(not set? set here?)
		self.canvas.update()  # wait till canvas is created
  
		if self.frames:
			self.image_id = self.canvas.create_image(0, 0, anchor='nw', image=self.frames[0])
			self.canvas.after(self.delay, self.animate_image)
  
		# bind scrollbars to the canvas
		hbar.configure(command=self.__scroll_x)  
		vbar.configure(command=self.__scroll_y)
  
		# Bind events to the Canvas
		self.canvas.bind('<Configure>', lambda event: self.__show_image())  # canvas is resized / updated
		self.canvas.bind('<ButtonPress-1>', self.__move_from)  # remember canvas position / panning
		self.canvas.bind('<B1-Motion>',	 self.__move_to)  # move canvas to the new position / panning
		self.canvas.bind('<MouseWheel>', self.__wheel)  # zoom for Windows and MacOS, but not Linux / zoom pyramid.
		self.canvas.bind('<Button-5>',   self.__wheel)  # zoom for Linux, wheel scroll down
		self.canvas.bind('<Button-4>',   self.__wheel)  # zoom for Linux, wheel scroll up
  
		# Handle keystrokes in idle mode, because program slows down on a weak computers,
		# when too many key stroke events in the same time
  
		self.canvas.focus_set()
		self.canvas.bind('<Key>', lambda event: self.canvas.after_idle(self.__keystroke, event))
  
		# Decide if this image huge or not
		self.__huge = False  # huge or not
		self.__huge_size = 14000  # define size of the huge image
		self.__band_width = 1024  # width of the tile band
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
  
		# Create image pyramid
		self.__pyramid = [self.smaller()] if self.__huge else [Image.open(self.path)]

		# Set ratio coefficient for image pyramid
		self.__ratio = max(self.imwidth, self.imheight) / self.__huge_size if self.__huge else 1.0
		self.__curr_img = 0  # current image from the pyramid
		self.__scale = self.imscale * self.__ratio  # image pyramide scale
		self.__reduction = 2  # reduction degree of image pyramid
		w, h = self.__pyramid[-1].size
		while w > 512 and h > 512:  # top pyramid image is around 512 pixels in size
			w /= self.__reduction  # divide on reduction degree
			h /= self.__reduction  # divide on reduction degree
			self.__pyramid.append(self.__pyramid[-1].resize((int(w), int(h)), self.__filter))
   
		# Put image into container rectangle and use it to set proper coordinates to the image
		self.container = self.canvas.create_rectangle((0, 0, self.imwidth, self.imheight), width=0)

		#self.__show_image()  # show image on the canvas
		self.__image.close()
  
	def animate_image(self):
		self.index = (self.index + 1) % len(self.frames)
		self.canvas.itemconfig(self.image_id, image=self.frames[self.index])  # Update the image
		self.canvas.after(self.delay, self.animate_image)
		
	def smaller(self):
		""" Resize image proportionally and return smaller image """
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

	# noinspection PyUnusedLocal
	def __scroll_x(self, *args, **kwargs):
		""" Scroll canvas horizontally and redraw the image """
		self.canvas.xview(*args)  # scroll horizontally
		self.__show_image()  # redraw the image

	# noinspection PyUnusedLocal
	def __scroll_y(self, *args, **kwargs):
		""" Scroll canvas vertically and redraw the image """
		self.canvas.yview(*args)  # scroll vertically
		self.__show_image()  # redraw the image

	def __show_image(self):
		if self.is_animated:
			pass
		else:
			print(f"afuckup")
			""" Show image on the Canvas. Implements correct image zoom almost like in Google Maps """
			box_image = self.canvas.coords(self.container)  # get image area
			box_canvas = (self.canvas.canvasx(0),  # get visible area of the canvas
						  self.canvas.canvasy(0),
						  self.canvas.canvasx(self.canvas.winfo_width()),
						  self.canvas.canvasy(self.canvas.winfo_height()))
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
				else:  # show normal image
					image = self.__pyramid[max(0, self.__curr_img)].crop(  # crop current img from pyramid
										(int(x1 / self.__scale), int(y1 / self.__scale),
										 int(x2 / self.__scale), int(y2 / self.__scale)))
				
				imagetk = ImageTk.PhotoImage(image.resize((int(x2 - x1), int(y2 - y1)), self.__filter))
				imageid = self.canvas.create_image(max(box_canvas[0], box_img_int[0]),
												   max(box_canvas[1], box_img_int[1]),
												anchor='nw', image=imagetk)
				self.canvas.lower(imageid)  # set image into background
				self.canvas.imagetk = imagetk  # keep an extra reference to prevent garbage-collection
   

	def __move_from(self, event):
		""" Remember previous coordinates for scrolling with the mouse """
		self.canvas.scan_mark(event.x, event.y)

	def __move_to(self, event):
		""" Drag (move) canvas to the new position """
		self.canvas.scan_dragto(event.x, event.y, gain=1)
		self.__show_image()  # zoom tile and show it on the canvas

	def outside(self, x, y):
		""" Checks if the point (x,y) is outside the image area """
		bbox = self.canvas.coords(self.container)  # get image area
		if bbox[0] < x < bbox[2] and bbox[1] < y < bbox[3]:
			return False  # point (x,y) is inside the image area
		else:
			return True  # point (x,y) is outside the image area

	def __wheel(self, event):
		""" Zoom with mouse wheel """
		x = self.canvas.canvasx(event.x)  # get coordinates of the event on the canvas
		y = self.canvas.canvasy(event.y)
  
		#re-enable this if you dont want scrolling outside the image
		#if self.outside(x, y): return  # zoom only inside image area
		scale = 1.0
  
		# Respond to Linux (event.num) or Windows (event.delta) wheel event
		if event.num == 5 or event.delta == -120:  # scroll down, smaller
			if round(self.__min_side * self.imscale) < 30: return  # image is less than 30 pixels
			self.imscale /= self.__delta
			scale		/= self.__delta
		if event.num == 4 or event.delta == 120:  # scroll up, bigger
			i = min(self.canvas.winfo_width(), self.canvas.winfo_height()) >> 1
			if i < self.imscale: return  # 1 pixel is bigger than the visible area
			self.imscale *= self.__delta
			scale		*= self.__delta
   
		# Take appropriate image from the pyramid
		k = self.imscale * self.__ratio  # temporary coefficient
		self.__curr_img = min((-1) * int(math.log(k, self.__reduction)), len(self.__pyramid) - 1) #presumably changes the displayed image. Yes. We need pyramid to change the iterated frames.
		self.__scale = k * math.pow(self.__reduction, max(0, self.__curr_img)) #positioning dont change
  
		self.canvas.scale('all', x, y, scale, scale)  # rescale all objects
  
		# Redraw some figures before showing image on the screen
		self.redraw_figures()	# method for child classes
		self.__show_image()

	def __keystroke(self, event):
		""" Scrolling with the keyboard.
			Independent from the language of the keyboard, CapsLock, <Ctrl>+<key>, etc. """
		if event.state - self.__previous_state == 4:  # means that the Control key is pressed
			pass  # do nothing if Control key is pressed
		else:
			self.__previous_state = event.state	# remember the last keystroke state
			# Up, Down, Left, Right keystrokes
			if event.keycode in [68, 39, 102]:	# scroll right, keys 'd' or 'Right'
				self.__scroll_x('scroll',  1, 'unit', event=event)
			elif event.keycode in [65, 37, 100]:	# scroll left, keys 'a' or 'Left'
				self.__scroll_x('scroll', -1, 'unit', event=event)
			elif event.keycode in [87, 38, 104]:	# scroll up, keys 'w' or 'Up'
				self.__scroll_y('scroll', -1, 'unit', event=event)
			elif event.keycode in [83, 40, 98]:	# scroll down, keys 's' or 'Down'
				self.__scroll_y('scroll',  1, 'unit', event=event)

	def crop(self, bbox):
		""" Crop rectangle from the image and return it """
		if self.__huge:	# image is huge and not totally in RAM
			band = bbox[3] - bbox[1]	# width of the tile band
			self.__tile[1][3] = band	# set the tile height
			self.__tile[2] = self.__offset + self.imwidth * bbox[1] * 3	# set offset of the band
			self.__image.close()
			self.__image = Image.open(self.path)	# reopen / reset image
			self.__image.size = (self.imwidth, band)	# set size of the tile band
			self.__image.tile = [self.__tile]
			return self.__image.crop((bbox[0], 0, bbox[2], band))
		else:	# image is totally in RAM
			return self.__pyramid[0].crop(bbox)

	def destroy(self):
		""" ImageFrame destructor """
		self.__image.close()
		map(lambda i: i.close, self.__pyramid)  # close all pyramid images
		del self.__pyramid[:]  # delete pyramid list
		del self.__pyramid  # delete pyramid variable
		self.canvas.destroy()
		self.__imframe.destroy()
	
	def rescale(self, scale):
		""" Rescale the Image without doing anything else """
		self.__scale=scale
		self.imscale=scale

		self.canvas.scale('all', self.canvas.winfo_width(), 0, scale, scale)  # rescale all objects
		print(f"Rescaled")
		#self.redraw_figures()
		#self.__show_image()
  
	def center_image(self):
		""" Center the image on the canvas """
		canvas_width = self.canvas.winfo_width()
		canvas_height = self.canvas.winfo_height()
  
		# Calculate scaled image dimensions
		scaled_image_width = self.imwidth * self.imscale
		scaled_image_height = self.imheight * self.imscale
  
		# Calculate offsets to center the image
		x_offset = (canvas_width - scaled_image_width) // 2
		y_offset = (canvas_height - scaled_image_height) // 2
  
		# Update the position of the image container
		self.canvas.coords(self.container, x_offset, y_offset, x_offset + scaled_image_width, y_offset + scaled_image_height)

		print(f"Centered")
  
		self.__show_image()
			

def main():
	""" Main function to run the application """
	root = tk.Tk() 				#Create main window
	root.title("Image Viewer")	#Rename main window
	root.rowconfigure(0, weight=1)		#Expanding to content
	root.columnconfigure(0, weight=1)	#Expanding to content
	geometry = "800x600" #dummy
	root.geometry("800x600+2000+100")  # Set initial window size (dummy, should be done from sortimages_multiview from prefs.json)
	#Files
	script_dir = os.path.dirname(os.path.abspath(__file__))
	image_path = os.path.join(script_dir, "test3.png")
 
	#Window->Frame->Canvas->canvas.create_image
	#Initialize Frame Add to main window grid

	__imframe = CanvasImage(root, image_path, geometry, 'black')
	__imframe.grid(sticky='nswe')

	__imframe.rescale(min(root.winfo_width()/__imframe.imwidth, root.winfo_height()/__imframe.imheight))
	__imframe.center_image()
	#__imframe.auto_scroll()
	#print(f"{root.winfo_width()}:{__imframe.imwidth}:{root.winfo_height()}:{__imframe.imheight}")

 
	root.mainloop() #Start the main window loop

if __name__ == "__main__":
	main()
