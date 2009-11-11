
.PHONY: rpm

web:
	(cd dino-web; /mw/app/dino/bin/paster serve --reload development.ini)

rpm: 
	rpmtools/rpmtool.py build

clean:
	rm -rf _buildroot src/build web/build project.spec web/data
	
