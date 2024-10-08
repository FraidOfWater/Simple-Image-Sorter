# Simple-Image-Sorter (This is not intended as a replacement, it is for testing purposes only, and there is no quarantee of stability. If you wish, you can copy specific changes like sorting by date modification or centering buttons for singleview.) (The build released is a showcase, I will try to merge useful additions back to to Main instance once I know they're stable, but you may do so also)
Original author: Legendsmith https://github.com/Legendsmith/Simple-Image-Sorter

Sorts images into destination files. Written in python.

This is a WIP fork. You can do whatever you want with "My" portions of the code. Most is Legendsmith's. Check wiki on how to build, or run without building.
- Ability to sort by date modified. (Toggleable)
- Better view for destination views
- Better lists to show views (Show unassigned, Show assigned, Show moved)
- Better imageviewer window. (Scales and centers seamlessly now) (Removed the scrollbars that made it weird)
- Unlocked imageviewer panning (can pan/zoom without having the cursors on the image.)
- Less buttons
- Fixed the add page button being annoying. (Now less "validation!")
- Text truncation so long names don't overflow the gridbox.
- Can run without building.
- Building now easier.
- Preference saving now better.

- Image renaming broken.


  For singleview:
  - Centering button.
  - Now remembers last location and size of the window.

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

The journey is night complete. Just have to solve a few performance problems with the animation support.
