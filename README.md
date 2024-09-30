# Simple-Image-Sorter
Original author: Legendsmith

Sorts images into destination files. Written in python.

This is a WIP fork. You can modify and use *MY* portions of the code freely.
- Ability to sort by modified date. (Toggleable)
- Better destination window view
- Better lists to show views (Show unassigned, Show assigned, Show moved)
- Better imageviewer window. (Scales and centers seamlessly now) (Removed the scrollbars that made it weird)
- Unlocked imageviewer panning (can pan/zoom without having the cursors on the image.)
- Fixed the add page button being annoying. (Now less "validation!")
- Text truncation so long names don't overflow the gridbox.
- Code to run using only python
- Some "performance" tweaks (though I don't know if my implementation overall is more or less costly)
- Building puts all binaries inside _internal folder now, easy to build.
- Prefs.json is automatically created now in the same directory as .exe if not already there.
- Small UI tweaks and fixes
- Changed some names to reflect more the function, but made more some that don't make sense!
- WIP (dark mode?)
- WIP (image renaming) (I hacked this together knowing nothing of python, soo some features were sadly lost in the process)
- WIP (dynamic hotkey setting?)

## USE
1. Select source directory filled with images to sort (Will scan recursively -> scans all folders inside your folder)
2. Select destination directory to sort to
3. Press ready!

-- Designate images by clicking on them, then assign them to destinations with the corresponding destination button. When you're ready, click "move all" to move everything at once.
-- Within a new or existing folder, create your new organisational structure, _for example:_

```
Pictures (Destination folder)
├ Family
├ Holiday
├ Wedding
├ My stuff
├ Misc
```

-- (There is an 'exclusions' function where you can list folder names to ignore.
-- Source and destination folders must *cannot* be the same folder.


For performance, only a set amount is loaded at first. Press the "Add Files" button to make it load another chunk. You can configure how many it adds and loads at once in the program.
- Right-click on Destination Buttons to show which images are assigned to them.
- Right-click on Thumbnails to show a zoomable full view. You can also **rename** (work in progress in this version) images from this view.
- You can configure the size of thumbnails in prefs.json. Default is 256px. (work in progress in this version)
- The program will save your session automatically on exit with the name of source and destination folders, this WILL overwrite.
- You can save your session manually too with a filename, and load it later to resume where you last left off.
- You can customize hotkeys by opening `prefs.json` and editing the hotkeys entry. There is no GUI editor or hotkeys at this time. (work in progress in this version?)

Thanks to FooBar167 on stackoverflow for the advanced (and memory efficient!) Zoom and Pan tkinter class. Thank you for using this program.
