out/layer.json: srtm2qmesh.py params.json
	./srtm2qmesh.py params.json

clean:
	rm -rf out/*