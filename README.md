# Simple-Image-Sorter QOL fork

Sorts images into destination files.

Original author: Legendsmith https://github.com/Legendsmith/Simple-Image-Sorter 
(Assumed license is GNU AFFERO GENERAL PUBLIC LICENSE Version 3, 19 November 2007., though there is no clear current license, as author removed it) (MY code is free to use, but I assumed the fork itself is still under Original author's lisence, assumed to be the GNU AFFERO)

This fork attempts to add some new features like sorting by modification date, darkmode, and support for animated images. It also adds some other QOL stuff and experiments with threading and optimization.
Below is a mostly complete changelog:

    New main features:
      Ability to display animations (.gif and .webp, in all views) (Lazy loading, zooming is broken/not implemented, panning works)
      Ability to choose speed of animations (Config option + Checkbox in GUI) (The file's own frametimes or a "default_delay" (100 ms))
      Ability to customize colours (Dark mode, or whatever you want, change from .prefs, use hex codes or tkinter defaults white,black...)
      Better window handling (All windows save their position upon closing, also the divider in the main window saves it's position, too)
      Changed Imagefile hash to hash from header data instead of binary imagedata for lower latency
      If destination already has an identical image, it doesn't move it, otherwise it would OVERWRITE the one in destination! If image locked by image viewer or other processes, same thing.
      Attempted threading to make some stuff faster
      
      Tweaks to main GUI:
        Ability to sort by date modified. (Toggleable) (Config option + Checkbox in GUI)
        Better list view (Switchable) (Optionmenu in GUI)
        Image name truncation so long names don't overflow the gridbox, causing misalignment (Set "textlength" in prefs that works for your preferred thumbnailsize) (I couldn't automate it)
        Removed validation from add page button (It prevented removing all the text which was annoying, now if left empty, defaults to 1 or something)
        Added autodisplaying (Config option + Checkbox in GUI) (If you right click an image in the grid, it will turn blue, and any image that enters that index, will be automatically displayed in the imageviewer window.)
        It will also check the checkbox of the image framed in blue, so it works just like singleimageview.
        Destwindow and imageviewer windows use .transient to stay atop main window.
        
        
      Tweaks to canvasimage (The window that opens a big picture like a real imageviewer) (Zooming broken/not implemented):
        Larger images load faster by rendering a lower resolution image initially, then refreshes it to best quality. (Config option, default is "BILINEAR", so it isn't noticeable visually)
        Fast rendering size limit (Config option, "fast_render_size", it uses the above only for images that are larger than x MB (default 5))
        Better imageviewer window. (Correct scaling and Centering, removed scrollbars)
        Unlocked imageviewer panning (Allows panning and zooming while cursor not hovering over the image)
        Option to change where it centers (Config option, "viewer_y_centering")
        Changed Imageviewer window to always be on top.
        
      Tweaks to destination window:
        Better view for destination views (Auto-refreshes upon changes, saves position) (Optionmenu in GUI)

      Small stuff:
        You can run without compiling (Run sortimages_multiview.py, you need the .dll's, though. Take from a compiled copy, must be in same folder as the .py, check wiki for more info)
        Made building easier. (.spec file now points the .dll's to _internal. Prefs, session and data now saves outside of _internal next to the .exe for easy access)
        Some values changed in prefs
        It should use as many cores/threads as cpu reports

      Removed:
        Image renaming (Sorry! I removed it to make coding easier, and never readded it)

      For singleview:
        Buttons for different styles of Centering. (Optionmenu in GUI)
        Now remembers last location and size of the window.

Warnings:
  You may get duplicates, especially attempting to move pictures that are open in the image viewer. It will fail to remove the old one, but still move a copy to destination. You can use a tool like ANTIDUPL (github) to     remove them easily!
  No quarantee of working as intended, you may lose images using this. (Better to backup first! I haven't noticed any accidental deletions though.)
  Image zooming for animated images is not implemented. It could be done because we could lazy load image by image, but it's difficult to implement. Maybe someday.

Thanks to FooBar167 on stackoverflow for the advanced (and memory efficient!) Zoom and Pan tkinter class. Thank you for using this program.

End of file congratz!
