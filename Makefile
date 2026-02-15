deploy-home:
	cp ./home.html /opt/homebrew/var/www/.
	chmod 644 /opt/homebrew/var/www/home.html

deploy-remote:
	unison m4pro-feeder -auto -batch
	ssh m4pro "cd ~/Documents/GitHub/ApproachingFeeder && make deploy-home"
