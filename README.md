Allows simple browsing and renaming of FITS images based on header information

Explanation
====================

The header of a FITS image can contain all sorts of useful information about
the time the image was taken, exposure time, filters used, etc. Often the images
are just named sequentially, and it can be very tedious to open up each image
in a program and view its header to determine if it is the one you want.

This program simplifies that procedure, allowing one to sort a large number of files
at once based on any number of FITS header tokens. The files can be renamed based on the
value of token(s) to make the filenames more readable, and can even be moved to a separate
directory by prepending it to the rename mask.

It's a beast with many headers. Right?

Using/Installing FITS Hydra
====================
FITS Hydra can be run using the Python (2.7) interpreter. Required python libraries are:
- wxpython
- pyfits

If the python interpreter is in the path the script can be run from any location.

FITS Hydra has also been compiled into standalone executables for some systems using the
PyInstaller program. These are found in the exec/ folder and can be run on a system
without the necessary libraries or even a python interpreter.

To compile standalone executables for other systems using PyInstaller, obtain
the program from https://github.com/pyinstaller/pyinstaller (additional information
at http://www.pyinstaller.org ), download this repository, and run the command

      pyinstaller fits_hydra.py -F -i <icon_file>

where <icon_file> is the appropriate icon file found in icons/, if desired.



MIT License
