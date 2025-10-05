# ApproachingFeeder
When Momo, the cutest kitten, approaches the wet feeder, open it; after he's gone for a while, close it

## Usage

Start a local server in the local network:

```sh
tmux new -s feeder
DEBUG=1 python3 motion_detector.py --plate=1
```

When you would like to take a look at the food tray, you can manually open or close the plate using

```sh
DEBUG=1 python3 wet_feeder.py close
```
