
.PHONY: rpm

web:
	(cd dino-web; /mw/dino/bin/paster serve --reload development.ini)

rpm: 
	rpmtools/rpmtool.py build

clean:
	rm -rf _buildroot build dino-web/build project.spec dino-web/data
	
