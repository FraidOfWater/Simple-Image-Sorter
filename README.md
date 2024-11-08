# Simple-Image-Sorter QOL Fork
This is a fork of Simple-Image-Sorter by Legendsmith https://github.com/Legendsmith/Simple-Image-Sorter. If author reads this, feel free to merge this?
I have assumed the licence to be GNU AFFERO GENERAL PUBLIC LICENSE Version 3, 19 November 2007. (Removed from author's source)

# Sorts images into destinations #
This fork is a hobby, it adds new features and other tweaks, and removes some others. Light experimenting with threading and optimization. Tried to make it very customizable! Now supports animations!

# Changelog: #

      GUI Enhancements

    Sorting Options: Added "Sort by date modified" in GUI and Prefs.json.
    View Options: Introduced an option box to show unassigned, assigned, moved, or animations.
    Docked Image Viewer: Choose between integrated or free-floating viewer.
    Auto Next: Automatically shows the next image upon assigning the current one.
    Single View Assigning: Assign images directly from the viewer with a hotkey.
    Name Truncation: Prevents overflow and misalignment in the grid / fixed root problem auto resizing gridboxes..
    Transient Windows: Windows spawned by the main GUI now stay on top.
    File Format Support: Added support for .gif and .webp.
    Navigator: Use arrow keys or WASD to navigate the grid; lock images for zooming with enter or clicking.
    Theme Customization: Main theme is now dark mode; customize using hex codes; prefs.json.
    Window Position Saving: Remembers user-adjusted positions and sizes.
    Scrollbar Override: Option to disable the white scrollbar.

      Performance Improvements

    Image Header Hashing: Faster image loading by reading headers instead of full binary data.
    Overwrite Safeguards: Prevents overwriting locked images or those assigned to others.
    Threading: Implements threading for lazy loading of images and GIFs/WebPs.
    Buffering: Buffers large images to reduce latency; configurable in Prefs.json.

      Image Viewer Enhancements

    Auto Scaling and Centering: Images automatically scale and center within the viewer.
    Centering Options: Customize centering behavior.
    Free Zooming: Zoom functionality no longer requires hovering over the image.

      Miscellaneous

    Run Without Compiling: Copy over required DLLs and run the script directly.
    User File Accessibility: Prefs, session data, and data folders are now outside _internal
    Core Utilization: Automatically utilizes available CPU cores.
    Fixed Bugs: That appeared in the original
    Logging: Added logging for better debugging.

      Single View Enhancements

    Centering Buttons: Added in Prefs.json and GUI.
    Window Position Saving: Remembers user-adjusted positions and sizes.

# Warnings #

    Use tools like ANTIDUPL to remove duplicates.
    No guarantees of functionality; backup images before use.
    GIFs and WebPs do not support zooming due to implementation complexity.
    Image renaming and dupe checking removed/not supported.
# Requirements For Building #

##  How to build: ##
Install Python; You need pip, then install dependencies like this:

      pip install pyvips, tkinter-tooltip, pillow, pyinstaller

You need these DLLs; (Take from a compiled copy, in _internal)

      libglib-2.0, libgobject-2.0, libvips-42, libvips-cpp-42

Put the DLLs in the same folder as the .py and .bat scripts:
Run the .bat file (try restarting if it doesn't work)

      Finished copy can hopefully be found in "dist" folder.

      #Note, if you edit any source files, you must delete build and dist folders, otherwise you will build from outdated files.

      You can also add --noconsole and --onefile to the pyinstaller command to disable console or to not have the _internal folder.

# How to run as a script#
##Running without building:##

Edit sortimages_multiview.py, delete this code, save:

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
      
Open terminal

      python sortimages_multiview.py

Or make a shortcut, this should work if all files are in the same folder. You can remove the pause, if there are no errors.

      start.bat
            cd %~dp0
            python sortimages_multiview.py
            pause
      
End of file congratz!
