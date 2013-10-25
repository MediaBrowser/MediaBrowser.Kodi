Okay, like I said this is a total hack right now. 

But... If you want to play, download and install PleXBMC. 

Go into the plugin settings and turn auto discover off, specify your MB3 ip and port.

Then go to my repository here:

https://github.com/xnappo/plugin.video.plexbmc

Replace default.py with the one in my repo.

Search for any occurrences of: 81452d964095cf6c18af19ac559f08c5 and replace with the 'id' found here: http://localhost:8096/Mediabrowser/Users
Search for any occurrences of: 4a9b8f589564a0bb2dc7fbe54c1e3ff1 and replace with the 'id' found here: http://localhost:8096/Mediabrowser/Users/{id from above}/Items/Root

If all goes well, you will be able to browse your library (in a very boring way).

I am totally booked this weekend, I hope to spend some more time on it next weekend and make more progress since I sort-of understand what is needed now Smile.

A quick and easy thing to help with is to grab that id stuff automatically. The MB3 API docs have more info...
