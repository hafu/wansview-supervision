# wansview supervision

This project was developed at the Hacker Art class at the University of Applied Sciences (HTW), Berlin, Germany.

It demonstrates the insecurity of cheap IP Cameras, especially wansview devices. But also other manufacturers maybe affected.

**The project status shows what is possible and is not stable**

## concept

You become the observer of thousends IP Cameras, mostly private ones. The thousends of IP Camera images will be displayed as a mosaic and the images get updated slowly. Theoretically all the images / IP Cameras could be updated live, but this would need massive of bandwith (~1Gbps+). It is like the position of a securty guy with all his monitors, but you got thousends of them! If you can see people on an image, they don't know that they are watched! 

So, think about your devices, which are connected to the internet - not only IP Cameras may be insecure by default! Also think about surveillance techniques!

## implementation

The implementation is very beta. It works, but needs a lot of improvements.

* crawler, written in python
 * "crawler" which uses generic hostnames
 * try to login with default username/password
 * save the status of every crawled host
 * scale the image down (160x120) and save it for caching
 * comminicates with the frontend via sockets
* frontend, written in nodejs
 * displays the mosaic and some statistics
 * uses the resolution of the client to show as mouch images as possible (but limited to 2000)
 * scales the images down for the client (uses a lot of memory and CPU power)

## TODOs

* performance improvements
* code cleanup
* frontend rewrite (maybe other language)
* async image processing suboptimal, for every image one task!

## Screenshots

![screenshot without stats](/screenshots/screenshot_nostats_low.png)

![screenshot with stats](/screenshots/screenshot_stats_low.png)
