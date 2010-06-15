
.PHONY: rpm

serve:
	(cd web; /mw/app/dino/bin/paster serve --reload development.ini)

put:
	(/mw/app/dino/bin/python web/dinoweb/probe-tools/probe-put.py http://127.0.0.1:5000 example.yaml)
rpm: 
	@barpm all

clean:
	rm -rf _buildroot src/build web/build project.spec web/data
	
