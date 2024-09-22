cd %~dp0
pyinstaller sortimages_multiview.py --noconfirm
copy .\libglib-2.0-0.dll .\dist\sortimages_multiview\_internal\libglib-2.0-0.dll
copy .\libgobject-2.0-0.dll .\dist\sortimages_multiview\_internal\libgobject-2.0-0.dll
copy .\libvips-42.dll .\dist\sortimages_multiview\_internal\libvips-42.dll
copy .\libvips-cpp-42.dll .\dist\sortimages_multiview\_internal\libvips-cpp-42.dll
copy .\prefs.json .\dist\sortimages_multiview\prefs.json
pause
