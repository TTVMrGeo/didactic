## For scrobbling and Discord RPC use pano scrobbler (Discord RPC is dumb, this works well, scrobbling is slow, this saves time for my prgram and only uses 500mb of ram)

### For Arch:
```
yay -S pano-scrobbler-bin
```

### For other systems
```diff
cd ~/Documents/Pano-Scrobbler # For example, you can put this anywhere
! If on a x64 system:
curl -L "https://github.com/kawaiiDango/pano-scrobbler/releases/latest/download/pano-scrobbler-linux-x64.tar.gz" --output Pano-Scrobbler.tar.gz
! If on a arm64 system:
curl -L "https://github.com/kawaiiDango/pano-scrobbler/releases/latest/download/pano-scrobbler-linux-arm64.tar.gz" --output Pano-Scrobbler.tar.gz
tar -xzvf Pano-Scrobbler.tar.gz && rm Pano-Scrobbler.tar.gz
```

### IF YOU WANT A DESKTOP ENTRY
```
nano pano-scrobbler.desktop
# Modify these 2 lines
Exec=~/Documents/Pano-Scrobbler/pano-scrobbler #Replace with your install location
Icon=~/Documents/Pano-Scrobbler/pano-scrobbler.svg
# Then run
mv ~/Documents/Pano-Scrobbler/pano-scrobbler.desktop ~/Desktop
```
### Final .desktop file should look something like:
```
[Desktop Entry]
Type=Application
Name=Pano Scrobbler
Comment=Feature packed music tracker
StartupWMClass=pano-scrobbler
Exec=~/Documents/Pano-Scrobbler/pano-scrobbler
Icon=~/Documents/Pano-Scrobbler/pano-scrobbler.svg
Categories=AudioVideo;Audio;
Terminal=false
StartupNotify=true
NoDisplay=false
```


## Todo list:
```
#TODO Add profiles for different local servers (eg, 0.0.0.0 and 10.0.0.103)
#TODO Add song to back of queue
#TODO Song progress bar
#TODO Song volume controlls
#TODO Play specific song with searching
#FIXME Add/Replace comments with some actual ones XD
```