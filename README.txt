Basic Movie functinality is working now.

If you want to play, download and install PleXBMC. 

Go into the plugin settings and turn auto discover off, specify your MB3 ip and port.
Replace default.py with the one in my repo.

Search for any occurrences of: 81452d964095cf6c18af19ac559f08c5 and replace with the 'id' found here: http://localhost:8096/Mediabrowser/Users
Search for any occurrences of: 4a9b8f589564a0bb2dc7fbe54c1e3ff1 and replace with the 'id' found here: http://localhost:8096/Mediabrowser/Users/{id from above}/Items/Root

If all goes well, you will be able to browse your library and play movies (TV not working yet). 

NOTE: When first going into your library it will take a long time as it needs to cache all images locally right now.  Only an issue on first entry.

To do list (in no particular order):

[ ] Grab user ID automatically
[ ] Grab root directory automatically
[ ] Support multiple users
[ ] Support passwords
[ ] Fix TV browsing
[ ] Add item description metadata
[ ] Add item details metadata (file type, resolution, playtime, etc)
[ ] Add tracking of partial playback
[ ] Add tracking of played items
[ ] De-plexify code (remove all references to PLEXBMC, other than thanks to Hippojay)
[ ] MB3-ify - add MB3 artwork collateral etc
[ ] Document how to to root entry points from main menu to the add-on
[ ] Add 'recently added' support
[ ] Add sorting support
[ ] Add delete support

