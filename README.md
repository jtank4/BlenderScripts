# BlenderScripts
A collection of standalone scripts I've written for Blender modeling software. These have been tested in Blender 3.1.2.

# How to use
Open a Text Editor window in Blender (https://docs.blender.org/manual/en/latest/editors/text_editor.html). Either download the scripts from this repo and open them in the text editor, or copy and paste their code into the editor (just the one you want, not multiple at once). Make sure you are in object mode, not edit mode (if you run the script in edit mode, you will get a "Python script failed, check the message in the system console" error, or in the console "ValueError: to_mesh(): Mesh 'x' is in editmode"). Click the play button to the right of the group of buttons in the top-middle of the text editor. If an error occurs, the only way to see the full output is to start blender from a terminal, the output will show up there.

# About the different scripts
These scripts were tested on this model, the before and after pictures feature it as well: https://sketchfab.com/3d-models/space-station-x-326e55c4cb40425593114993db5e6ac4
# Delete Small Faces (deleteSmallFaces.py)
This script will iterate through each face in the model and delete it if its area is less than the MINAREA variable defined at the top, .5 by default.

# Delete Z Fighting Faces (deleteZFighters.py)
This script will delete faces that are occupying the same space. It has O(n^2) efficiency so be careful running it on models with many faces. On a model with 2,639 faces it took 3.6 seconds to run.
