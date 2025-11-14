# rtorrent-webclient
A Backend + WebInterface to download torrents onto a remote server using the magnet link

## Pre-Installation
To download torrents remotely, you must install a transmission RPC server. once installed run:
`sudo systemctl start transmission-daemon`
This daemon needs to be running to make the app work.
It is recommended to test the rpc server a few times manually to ensure it is working correctly.
The transmission settings should be updated to your own liking. Configure the download directory. I did not configure auth as my server is on my local network but feel free to play around with it. If you want to download the files unto an external drive not managed by transmission user, it is recommended to use a post-download script. post-torrent.sh acheives this. Please update it to your own needs and configure it in transmission settings

## Execution
run `Python3 api.py` (preferrably in a virtual environment) default port is 5000

