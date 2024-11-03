# Simple-Image-Sorter QOL fork
Sorts images into destinations

I have assumed the licence to be GNU AFFERO GENERAL PUBLIC LICENSE Version 3, 19 November 2007. (Removed from author's source)

This is a fork of Simple-Image-Sorter by Legendsmith https://github.com/Legendsmith/Simple-Image-Sorter.

This fork is a hobby, it adds new features and other tweaks, and removes some others. Light experimenting with threading and optimization. An introduction to python.

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
  1. Switching from standalone viewer to dock, scroll the last selection to center - not implemetned - location -> the button
  2. View button has a white border, get rid of it (Most likely activation related)
  3. Navigation using arrow keys?
  4. Help text under destination buttons?
  5. Consolidate code into methods. Alot of spaghetti out there, cowboy
  
Thanks to FooBar167 on stackoverflow for the advanced (and memory efficient!) Zoom and Pan tkinter class. Thank you for using this program.

End of file congratz!
