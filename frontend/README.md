# wansview supervision - frontend
This is the "frontend" for the crawled IP Camera images. It connects to the DB to get the maximum of 2000 random images and displays them as a mosaic. It also recalculates every image size to reduce the data send to the client (browser)

## requirements
* nodejs

## configuration
* see vars in wansview.py

## setup
* just run `npm install` and all required packeges should be installed
* start with `nodejs wansview.js`
