# Simple-Image-Sorter QOL fork
Sorts images into destinations

I have assumed the licence to be GNU AFFERO GENERAL PUBLIC LICENSE Version 3, 19 November 2007. (Removed from author's source)

This is a fork of Simple-Image-Sorter by Legendsmith https://github.com/Legendsmith/Simple-Image-Sorter.

This fork is a hobby, it adds new features and other tweaks, and removes some others. Light experimenting with threading and optimization. Adding animatinos and customizations. An introduction to python.

Below is a mostly up-to-date changelog:

      Tweaks to main GUI:
        Added "sort by date modified" - In GUI, In Prefs.json
        Added View optionbox
        Added Docked image viewer
        Added Show next - Upon assigning the current image in view, shows the next one - In GUI, In Prefs.json
        Added Assigning from viewer - You can view an image and press your hotkey to move it, less clicking, singleview style - Cancels automatically upon interacting with other images in the grid
        Added name truncation - No longer overflows and misaligns the grid. - In prefs.json
        Added transien windows - Windows spawned by main GUI now stay on top
        Added support for .gif and .webp
        Added Default speed - Overrides animation speed - (Toggle) in GUI, (Toggle) In Prefs.json
        Added theme customization - Main theme is now darkmode, use hex codes - In Prefs.json
        Added last window positions - Saves most positions and size adjustments by user - In Prefs.json
        Added dock view - Choose between docked and standalone image viewer- In Prefs.json, In GUI
        Added dock side button - Change the side the viewer uses! - In prefs, In GUI
        Added scrollbar override - Disable the white scrollbar - In prefs "Force_scrollbar = False"
        
        Removed squaresperpage entryfield annoying validation

      Tweaks to performance:
        Added imagefile header hashing - Faster than reading all of the binary imagedata, lowers latency
        Added safeguards against overwrites - If image is locked or would overwrite someone else, it cancels
        Added threading - Threads and lazy loads images and gifs/webps to image viewer
        Added buffering - Images above a set size are buffered to lower latency - In prefs "filter_mode" and "fast_render_size" (MB) - Filter modes "NEAREST, "BILINEAR", "BICUBIC", "LANCZOS"
        
      Tweaks to image viewer:
        Added auto scaling - Scales to the window automatically
        Added centering - Centers to the window automatically
        Added centering options - Tweak how the image is centered - In prefs "viewer_x_centering" and "viewer_y_centering"
        Added centering button - In prefs, In GUI (Toggle "extra_buttons")
        Added free imageviewer zooming - No longer have to hover over the picture to zoom
        
        Removed scrollbars - Messed with scaling and centering
        Removed image renaming - Messed with scaling and centering - I was too noob at the start
        
        Caution: Zooming not implemented for gifs and webps

      Misc:
        Added running without compiling - Just download the .dll's from compiled copy, put into same folder as .py, and run from main script "sortimages_multiview.py" - More info in wiki
        Added dll's to .spec file - It knows to put them into _internal
        Added Prefs, sessiondata and data folder outside _internal (These are user files, ease of access)
        Added value tweaks for Prefs.json
        Added automatic utilisation of cores based on cores reported by OS

      Tweaks to singleview:
        Added centering buttons - In Prefs.json, In GUI
        Added last window positions - Saves most positions and size adjustments by user - In Prefs.json

Warnings and other info:
  You can use a tool like ANTIDUPL (github) to remove duplicates easily!
  No quarantee of working as intended, you may lose images using this. (Better to backup first! I haven't noticed any accidental deletions though.)
  Gifs and Webps fail to zoom, it is not implemented.
    
  Reason for this is because its complicated -,_,- How I'd do it is
  1. Get the zoom pyramid to do it for me. It will do the zooming for us, then it will pass the image to the lazy frame loader, which loads slowly frame by frame, as to not slow down. It will pass it everytime we zoom.
  2. Sounds easy, but there is a lot of cropping and other logic involved, so its very confusing at times.

  Other things to add?
  1. Navigation using arrow keys?
  
Thanks to FooBar167 on stackoverflow for the advanced (and memory efficient!) Zoom and Pan tkinter class. Thank you for using this program.
# Requirements #
SW = Singleview
MW = Multiview


Building SW/MW:
Install Python
You need to pip install like this:

      (pip install pyvips, tkinter-tooltip, pillow, pyinstaller)

Building MW:
You need these dlls in this folder:
(Take from a compiled copy, in _internal)

      libglib-2.0, libgobject-2.0, libvips-42, libvips-cpp-42

Building:

      Finished copy can hopefully be found in "dist" folder.

      #Note, if you edit any source files, you must delete build and dist folders, otherwise you will build from outdated files.

      You can also add --noconsole and --onefile in fron ot pyinstaller to disable console or to not have _internal folder

Running without building:

      Run the script from via python sortimages_multiview.py

However, you must uncomment this block of code at the very start:

      #""" # This can/should be commented if you build.
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
      #"""
      
End of file congratz!
