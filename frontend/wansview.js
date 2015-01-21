var express = require('express');
var bodyParser = require('body-parser');
var app = express();
var net = require('net')

// soccket.io
var server = require('http').Server(app);
var io = require('socket.io')(server);

// gm
var gm = require('gm');


// vars
var HTTP_PORT = 8080;
var BIND_TO = '0.0.0.0';

var SERVICE_PORT = 5567;
var SERVICE_HOST = 'localhost';

// db
var DB_PASSWD = 'iez6so4B';

// image
var IMG_WIDTH = 160;
var IMG_HEIGHT = 120;

// no layouts
app.set("view options", {layout: false});
app.set('trust proxy', 1);
app.use(express.static(__dirname + '/public'));
app.use(bodyParser.urlencoded({ extended: false }));

// test
// pg client
var pg = require('pg');
var conString = 'postgres://wansview:' + DB_PASSWD + '@localhost/wansview';

var soc = new net.Socket();
soc.connect(SERVICE_PORT, SERVICE_HOST, function (err) {
	if (err) {
		console.log('Failed to connect to socket');
	}
});

var resizeImage = function (imageBuffer, size, callback) {
	gm(imageBuffer).resize(size).toBuffer(function (err, data) {
		if (err) {
			console.error('GM error: ', err);
			callback(err);
		}
		//console.log('Image processing done');
		callback(null, data);
	});
}

app.post('/getRandomImages', function (req, res) {
	console.log('got post');
	console.log('width: ' + req.body.width);
	console.log('height: ' + req.body.height);


	//var pgClient = new pg.Client(conString);
	//pgClient.connect(function (err) {
	pg.connect(conString, function(err, client, done) {
		if (err) {
			console.error('could not connect to database', err);
			res.json({error: 'could not connect to database ' + err});
		}
		client.query("SELECT count(*) as count FROM ip_cam_images", function (err, result) {
			done();
			if (err) {
				console.error('error running query', err);
				res.json({error: 'error running query ' + err});
			}
			var imgCountDB = result.rows[0].count;
			console.log('Images in DB: ' + imgCountDB);

			var new_img_width = IMG_WIDTH;
			var new_img_height = IMG_HEIGHT;
			var imgCount = 0;
			
			do {
				new_img_width = new_img_width - 1;
				new_img_height = Math.round(IMG_HEIGHT / IMG_WIDTH * new_img_width);
				imgCount = Math.floor(req.body.width / new_img_width) * Math.floor(req.body.height / new_img_height);
			} while (imgCount < imgCountDB);
			new_img_width = new_img_width + 1;
			new_img_height = Math.round(IMG_HEIGHT / IMG_WIDTH * new_img_width);
			imgCount = Math.floor(req.body.width / new_img_width) * Math.floor(req.body.height / new_img_height);
			
			console.log('Images: ' + imgCount);
			console.log('Width: ' + new_img_width + ' Height: ' + new_img_height);
			console.log('Loading images');
			client.query("SELECT replace(encode(image, 'base64'), '\n', '') as image FROM ip_cam_images ORDER BY RANDOM() LIMIT " + imgCount, function (err, result) {
				done();
			
				if (err) {
					console.error('error running query', err);
					res.json({error: 'error running query ' + err});
				}
				console.log('Got ' + result.rows.length + ' items');
				// get images
				console.log('calculating ...');
				imgs = new Array();
				for (i=0; i<result.rows.length; i++) {
					var buf = new Buffer(result.rows[i].image, 'base64');
					resizeImage(buf, new_img_width, function (err, data) {
						if (err) {
							console.error('Error in callback');
						}
						console.log('Callback');
						imgs.push(data.toString('base64'));
						if (imgs.length == result.rows.length) {
							console.log('All images done');
							console.log('Sending json');
							res.json({imagew: new_img_width, imageh: new_img_height,images: imgs});
						}
						else {
							console.log(imgs.length + ' proceeded');
						}
					});
			
				}
				//pgClient.end();
			
			});
			
		});
	});

});

app.get('/images/:count', function (req, res) {
	console.log('Getting ' + req.params.count + ' images');
	var pgClient = new pg.Client(conString);
	pgClient.connect(function (err) {
		if (err) {
			console.error('could not connect to database', err);
			res.json({error: 'could not connect to database ' + err});
		}
		// encode(byteaColumn,'base64')
		pgClient.query("SELECT replace(encode(image, 'base64'), '\n', '') as image FROM ip_cam_images ORDER BY RANDOM() LIMIT " + req.params.count *7, function (err, result) {
			if (err) {
				console.error('error running query', err);
				res.json({error: 'error running query ' + err});
			}
			console.log('Got ' + result.rows.length + ' items');
			// get images
			imgs = new Array();
			for (i=0; i<result.rows.length; i++) {
				var buf = new Buffer(result.rows[i].image, 'base64');
				resizeImage(buf, 60, function (err, data) {
					if (err) {
						console.error('Error in callback');
					}
					console.log('Callback');
					imgs.push(data.toString('base64'));
					if (imgs.length == result.rows.length) {
						console.log('All images done');
						console.log('Sending json');
						res.json({images: imgs});
					}
					else {
						console.log(imgs.length + ' proceeded');
					}
				});
			
			}
			/*
			console.log('imgs: ', imgs.length);
			console.log('Sending json');
			res.json({images: imgs});
			*/
			pgClient.end();
			
		});
	});
});

var statsnsp = io.of('/stats-socket');
statsnsp.on('connection', function (socket) {
	console.log('New connection');

	pg.connect(conString, function(err, client, done) {
		if (err) {
			console.error('could not connect to database', err);
			socket.emit('error', 'could not connect to database ' + err);
		}
		client.query("select country, count(*) as count from ip_cam_images group by country order by count desc", function (err, result) {
			done();
			if (err) {
				console.error('query error', err);
				socket.emit('error', 'querry error ' + err);
			}
			socket.emit('stats', result.rows);
		});
	});


	socket.on('disconnect', function () {
		console.log('Connection closed');
	});
});

var imgnsp = io.of('/image-socket');
imgnsp.on('connection', function (socket) {
	console.log('New connection');
	var new_img_width = IMG_WIDTH;
	var new_img_height = IMG_HEIGHT;
	
	socket.on('resolution', function (msg) {
		console.log('Got resolution: ' + msg.width);

		//socket.emit('loading', 'connecting to database');
		pg.connect(conString, function(err, client, done) {
			if (err) {
				console.error('could not connect to database', err);
				//res.json({error: 'could not connect to database ' + err});
				socket.emit('error', 'could not connect to database ' + err);
			}
			client.query("SELECT count(*) as count FROM ip_cam_images", function (err, result) {
				done();
				if (err) {
					console.error('error running query', err);
					//res.json({error: 'error running query ' + err});
					socket.emit('error', 'error running query ' + err);
				}
				var imgCountDB = result.rows[0].count;
				console.log('Images in DB: ' + imgCountDB);
	
				var imgCount = 0;
				
				do {
					new_img_width = new_img_width - 1;
					new_img_height = Math.round(IMG_HEIGHT / IMG_WIDTH * new_img_width);
					imgCount = Math.floor(msg.width / new_img_width) * Math.floor(msg.height / new_img_height);
				} while (imgCount < imgCountDB);
				new_img_width = new_img_width + 1;
				new_img_height = Math.round(IMG_HEIGHT / IMG_WIDTH * new_img_width);
				imgCount = Math.floor(msg.width / new_img_width) * Math.floor(msg.height / new_img_height);
			
				console.log('Images: ' + imgCount);
				console.log('Width: ' + new_img_width + ' Height: ' + new_img_height);
				console.log('Loading images');
				socket.emit('loading', 'loading ' + imgCount + ' images');
				client.query("SELECT replace(encode(image, 'base64'), '\n', '') as image FROM ip_cam_images ORDER BY RANDOM() LIMIT " + imgCount, function (err, result) {
					done();
			
					if (err) {
						console.error('error running query', err);
						//res.json({error: 'error running query ' + err});
						socket.emit('error', 'error running query ' + err);
					}
					console.log('Got ' + result.rows.length + ' items');
					// get images
					socket.emit('loading', 'got images, calculating new size - this can take some time');
					console.log('calculating ...');
					imgs = new Array();
					var perc = 0;
					var parc_now;
					for (i=0; i<result.rows.length; i++) {
						perc_now = Math.round((i/imgCount)*100);
						if (perc != perc_now) {
							perc = perc_now;
							console.log(perc);
							socket.emit('progress', perc);
						}
						var buf = new Buffer(result.rows[i].image, 'base64');
						resizeImage(buf, new_img_width, function (err, data) {
							if (err) {
								console.error('Error in callback');
							}
							//console.log('Callback');
							imgs.push(data.toString('base64'));
							if (imgs.length == result.rows.length) {
								console.log('All images done');
								console.log('Sending json');
								//res.json({imagew: new_img_width, imageh: new_img_height,images: imgs});
								socket.emit('images', {imagew: new_img_width, imageh: new_img_height,images: imgs});
							}
							else {
								//console.log(imgs.length + ' proceeded');
							}
						});
				
					}
					//pgClient.end();
			
				});
			
			});
		});

	});

	soc.on('data', function (data) {
		if (data == 'ping') {
			console.log('just a ping');
		}
		else {
			//console.log('other data: ' + data);
			var jsonData = JSON.parse(data);
			//console.log('JS obj: ' + obj.newImage);
			if (jsonData.newImage) {
				var buf = new Buffer(jsonData.newImage, 'base64');
				resizeImage(buf, new_img_width, function (err, data) {
					if (err) {
						console.error('Error in callback');
					}
					socket.emit('newImage', {image: data.toString('base64')});
				});
			}
		}
		// resize image
		/*
		ar buf = new Buffer(data.newImage, 'base64');
		resizeImage(buf, new_img_width, function (err, data) {
			if (err) {
				console.error('Error in callback');
			}
			socket.emit('newImage', {image: data.toString('base64')});
		});
		*/
	});

	socket.on('disconnect', function () {
		console.log('Connection closed');
	});

});
// test end


server.listen(HTTP_PORT, BIND_TO);
console.log('Server is listening on ' + BIND_TO + ':' + HTTP_PORT);
