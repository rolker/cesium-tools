out/layer.json: srtm2qmesh.py
	./srtm2qmesh.py data/topo15.grd out

clean:
	rm -rf out/*