# External data provenance

All **nine canonical data copies** match their official upstream files byte-for-byte. They are four unique assets. No canonical input was edited or replaced. Exact URLs, hashes, file mappings, attribution, and separate license-evidence fields are in [DATA-PROVENANCE.json](DATA-PROVENANCE.json).

| Asset | Copies | Size of each payload | Verified SHA-256 |
| --- | ---: | ---: | --- |
| Adult `a9a` | 2 | 2,329,875 | `f5d5ffd8d865ff41328e7ee043e4b020816914ff6843ff15b98905ddbedce906` |
| Adult `a9a.t` | 2 | 1,164,628 | `1f448a153f0320399a7e40836eb207655b0bde0f21fc941cc472193daa9f5de9` |
| MPAS `x1.10242.grid.nc` | 3 | 14,014,372 | `729a77fddd829ad5206661a9478d8473454552e3b3c5a1af768f4128e188295c` |
| ICON `icon_grid_0013_R02B04_G.nc` | 2 | 17,889,372 | `31821695d5d98c1c5a1d77c4d07deccf579f92e9127c89cdd300a2343e57db51` |

## Adult / LIBSVM

The two files match the official LIBSVM downloads, including their 32,561 training and 16,281 test records. LIBSVM identifies Adult as their source and documents its binary feature conversion; no additional conversion was applied to the bundled files. Preserve attribution to Becker and Kohavi's Adult dataset and to the LIBSVM distribution. [Official LIBSVM dataset description](https://www.csie.ntu.edu.tw/~cjlin/libsvmtools/datasets/binary.html#a9a).

UCI identifies Adult as CC BY 4.0 and supplies the dataset citation: Becker, B. and Kohavi, R. (1996), *Adult*, DOI 10.24432/C5XW20. Applying these data terms to the identified LIBSVM representation is recorded explicitly; the LIBSVM software license is not substituted for the data license. [UCI Adult dataset and license](https://archive.ics.uci.edu/dataset/2/adult).

## MPAS mesh

The frozen grid exactly matches `x1.10242.grid.nc` in the official 240-km, 10,242-cell mesh tarball. The downloaded tarball SHA-256 is `4dde31932bc45aaf467e2717d17ec8e5e54d73c3ebbeea027087bfdb8b98ab56`. The benchmark's `make_case.py` copies that base grid and may rotate a case-local copy; this is distinct from modifying the bundled upstream asset. [Official MPAS mesh repository](https://mpas-dev.github.io/atmosphere/atmosphere_meshes.html).

UCAR's repository policy assigns CC BY 4.0 to copyrighted data-repository material unless stated otherwise, and permits lawful use of material not protected by copyright. We apply that general policy to this official UCAR-hosted mesh, with attribution to MPAS-Atmosphere developers / NSF NCAR / UCAR. This applicability is an explicit inference: the tarball has no separate mesh-specific license notice, and the MPAS code license is not used as its data license. [UCAR data-repository terms](https://www.ucar.edu/terms-of-use/data).

## ICON grid

The bundled NetCDF identifies MPI-M / DWD, grid 0013 / R02B04, and UUID `c8481318-398c-11e8-a225-05e6d8b4e7ef`. Its `ICON_grid_file_uri` points to the official grid service; downloading that file produced exactly the frozen SHA-256 above. The model documentation independently directs users to this service. [Official ICON grid documentation](https://docs.icon-model.org/2025.04/buildrun/buildrun_running.html#grid-files), [exact official grid file](http://icon-downloads.mpimet.mpg.de/grids/public/mpim/0013/icon_grid_0013_R02B04_G.nc).

The inspected grid metadata and service do not state an explicit redistribution grant for this separate data file. This is a terms-evidence gap, not an unknown origin or a finding of infringement. The public-source preparation therefore includes an exact-download recipe for both canonical destinations, instead of assigning the ICON code's BSD terms to the grid. The canonical manifest records both expected copies.

## Fetch and hydrate without changing task inputs

[fetch_external_data.py](fetch_external_data.py) obtains assets from their official URLs, verifies download and payload SHA-256/size, and optionally fills missing paths in a derivative staging tree. It refuses to overwrite different existing files. `--offline` verifies a populated cache without accessing the network.

```sh
# Fetch only the externally delivered ICON grid and fill its two missing paths.
python3 public-release/fetch_external_data.py \
  --only icon-grid-0013 \
  --cache ./asset-cache \
  --hydrate ./canonical/tasks

# Or fetch and verify all four unique data assets.
python3 public-release/fetch_external_data.py \
  --cache ./asset-cache \
  --hydrate ./canonical/tasks
```

The official ICON documentation and stored URI use HTTP; that endpoint succeeded and matched the pinned source hash. Its HTTPS endpoint did not negotiate successfully during this check. The hash pin is retained in the manifest.

An isolated offline hydration test produced all nine expected destination files with their canonical hashes. Run the full 3,706-file source verifier after assembling the complete staging tree. A source checkout requiring asset hydration is not described as immediately runnable before hydration.
