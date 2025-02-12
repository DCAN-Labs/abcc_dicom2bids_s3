# `src` folder

This folder contains all of the scripts used by the `abcd2bids.py` wrapper. There should be 13 files in this folder, as well as a `bin` subdirectory.

## Files belonging in this folder

#### Metadata:
1. `__init__.py`
1. `README.md`

#### Scripts used to download raw DICOM data:
1. `s3_downloader_revised.py`

#### Scripts used to unpack and setup NDA data:
1. `eta_squared`
1. `run_eta_squared.sh`
1. `run_order_fix.py`
1. `sefm_eval_and_json_editor.py`
1. `unpack_and_setup.sh`
2. `remove_RawDataStorage_dcms.py`

#### Scripts used to make data meet BIDS standards:
1. `correct_jsons.py`
