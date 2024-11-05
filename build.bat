cd %~dp0
pyinstaller --noconsole --add-data "libvips-cpp-42.dll;." --add-data "libvips-42.dll;." --add-data "libglib-2.0-0.dll;." --add-data "libgobject-2.0-0.dll;." sortimages_multiview.py
pyinstaller sortimages.py --noconfirm
pause
