# ApproachingFeeder
When Momo, the cutest kitten, approaches the wet feeder, open it; after he's gone for a while, close it

<!-- <video src='./example/example.mp4' width=360/> -->
![](https://github.com/user-attachments/assets/f6990f78-17a3-46dd-bc3b-a53d67fecad4)

## Usage

Start a local server in the local network:

```sh
tmux new -s feeder
python3 approach_feeder.py --plate=1  # logging goes to approach_feed.log
```

When you would like to take a look at the food tray, you can manually open or close the plate using

```sh
DEBUG=1 python3 wet_feeder.py close
DEBUG=1 python3 wet_feeder.py feed --plate=1
```

You can visit the webpage to see real-time video feed: <http://192.168.0.91:8080/video>.
Note that the video is only available for internal network.
To visit it from remote machines, use SSH tunneling: `ssh -N -L 8223:192.168.0.91:8080 m4pro` and then visit <http://localhost:8223/video> should work normally.
