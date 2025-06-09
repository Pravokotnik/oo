# Prerequisites

### Image collection

Download the wikiart collection from this link:
https://github.com/cs-chan/ArtGAN/blob/master/WikiArt%20Dataset/README.md

After downloading, put the "wikiart" folder into the main repository folder, so the structure should be:
```
OO
|- assets
|- details
|- ...
|- wikiart
   |- Abstract_Expressionism
   |- Action_painting
   |- ...
   ```

### Python dependencies
To have access to every part of this project, including the precomputing, install the dependencies in "requirements.txt".

# How to run

Wait for full execution:
`python precompute_annoy.py`

Run:
`python wwwwpreprocess.py`

**Then simoultaneously:**
One terminal:
`python hough_server.py`

Second terminal:
python poses_backend.py

Third terminal:
`python main.py`

Lastly, visit:
http://127.0.0.1:8000

# Do note
This version isn't fully web-based yet, so the viewers for "poses" and "facial emotions" open a python script in the background.
