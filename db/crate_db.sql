CREATE TYPE ip_cam_status AS ENUM ('unchecked', 'offline', 'unauthorized', 'authorized', 'timeout', 'not_found', 'unexcepted');

CREATE TABLE ip_cam_hosts (
	hostname	character varying(32) PRIMARY KEY,
	status		ip_cam_status DEFAULT 'unchecked',
	updated		timestamp DEFAULT NULL
);

CREATE TABLE ip_cam_images (
	hostname        character varying(32) references ip_cam_hosts(hostname) PRIMARY KEY,
	username	character varying(8) references usernames(username),
	password	character varying(16) references passwords(password),
	image           bytea NOT NULL,
	country		character varying(128) DEFAULT 'Unknown'
);

CREATE TABLE usernames (
	username	character varying(8) PRIMARY KEY,
	priority        smallint NULL
);

CREATE TABLE passwords (
	password	character varying(16)  PRIMARY KEY,
	priority        smallint NULL
);
/*
CREATE TABLE hosts (
	hostname	character varying(32) PRIMARY KEY,
	checked		boolean DEFAULT FALSE
);
*/
CREATE TABLE credentials (
	id		serial PRIMARY KEY,
	username	character varying(8) NOT NULL,
	password	character varying(16) NOT NULL,
	priority	smallint NULL
);
/*
CREATE TABLE ip_cams_online (
	hostname	character varying(32) references hosts(hostname) PRIMARY KEY,
	last_update	timestamp DEFAULT now(),	
	url		character varying(255) NOT NULL
);

CREATE TABLE ip_cams_online_authed (
	hostname	character varying(32) references hosts(hostname) PRIMARY KEY,
	credentials_id	serial references credentials(id),
	image		bytea NULL
);
*/
CREATE TABLE uas (
	ua		character varying(255) PRIMARY KEY
);
	
/*
ORDER BY RANDOM()
character varying(n)
*/

-- UPDATE ip_cam_hosts
-- CREATE RULE update_time AS ON UPDATE TO ip_cam_hosts
-- select u.username, u.priority as uprio, p.password as pprio, p.priority, u.priority + p.priority as prio from usernames u, passwords p order by prio, RANDOM();
-- select username, password, count(*) as count from ip_cam_images group by username, password order by count desc;
-- select status, count(*) as count from ip_cam_hosts where status != 'unchecked' group by status order by count desc;
