# ABCD DICOM to BIDS

Written by the OHSU ABCD site for selectively downloading ABCD Study imaging DICOM data QC'ed as good by the ABCD DAIC site, converting it to BIDS standard input data, selecting the best pair of spin echo field maps, and correcting the sidecar JSON files to meet the BIDS Validator specification. 
For information on [Collection 3165, see here](https://github.com/ABCD-STUDY/nda-abcd-collection-3165).

## Installation

Clone this repository, install the dependencies listed below ***and*** the requirements listed in `src/requirements.txt`.

### Dependencies

1. [Python 3.6.8](https://www.python.org/downloads/release/python-368/)+
1. [jq](https://stedolan.github.io/jq/download/) version 1.6 or higher
1. [MathWorks MATLAB Runtime Environment (MRE) version 9.1 (R2016b)](https://www.mathworks.com/products/compiler/matlab-runtime.html)
1. [cbedetti Dcm2Bids version 2.1.4](https://github.com/cbedetti/Dcm2Bids) (`export` into your BASH `PATH` variable) (WARNING: versions >=3.0.0 are not compatible with code written for previous versions)
1. [Rorden Lab dcm2niix version v1.0.20201102](https://github.com/rordenlab/dcm2niix) (`export` into your BASH `PATH` variable) (WARNING: older versions of dcm2niix have failed to properly convert DICOMs)
1. [dcmdump version 3.6.5 or higher](https://dicom.offis.de/dcmtk.php.en) (`export` into your BASH `PATH` variable)
1. Singularity or Docker (see documentation for [Docker Community Edition for Ubuntu](https://docs.docker.com/install/linux/docker-ce/ubuntu/))
1. [FMRIB Software Library (FSL) v5.0](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/FslInstallation)

### Requirements

We recommend creating a virtual environment for Python by running:

```
python3 -m venv env
source env/bin/activate
```

Then install the specified versions of all required python packages by running:

```
pip install -r src/requirements.txt
```

If encountering errors during the package download process, try running `pip install --upgrade setuptools`. Then check to see if this fixed any download errors by rerunning `pip install -r src/requirements.txt`

## Usage
```
usage: abcd2bids.py [-h] [-d DOWNLOAD] [-o OUTPUT]
                    [-q QC] [-y {00A,02A...} [{00A,02A,...} ...]] 
                    [-m {anat,func,dwi} [{anat,func,dwi} ...]] [-r]
                    [-s {reformat_fastqc_spreadsheet,download_s3_data,unpack_and_setup,correct_jsons,validate_bids}] 
                    [-t TEMP] [-z DOCKER_CMD] [-x SIF_PATH] [-c S3_CONFIG] 
                    fsl_dir mre_dir -l SUBJECT_LIST -s3 S3_BUCKET

Wrapper to download, parse, and validate QC'd ABCD data.

positional (and required) arguments:
  fsl_dir               Required: Path to FSL directory. This positional
                        argument must be a valid path to an existing folder.
  mre_dir               Required: Path to directory containing MATLAB Runtime
                        Environment (MRE) version 9.1 or newer. This is used
                        to run a compiled MATLAB script. This positional
                        argument must be a valid path to an existing folder. 
                        Note: MRE will ouput cached files into INSERT PATH in 
                        your home directory. This will need to be cleared out 
                        regularly in order to avoid filling up the system you 
                        are running abcd2bids.py on.
  -q QC, --qc QC        Path to Quality Control (QC) spreadsheet file
                        Given by UCSD or downloaded by LASSO.
  -l SUBJECT_LIST, --subject-list SUBJECT_LIST
                        Path to a .txt file containing a list of subjects to
                        download. Subjects should appear as 'sub-NDAID' without
                        quotations.
 -s3 S3_BUCKET, --s3bucket S3_BUCKET
                        Path to UCSD S3 bucket to download the dicoms.
 -c S3_CONFIG, --s3config S3_CONFIG
                        Path to config file with S3 Bucket credentials.
optional arguments:
  -h, --help            show this help message and exit
  -d DOWNLOAD, --download DOWNLOAD
                        Path to folder which NDA data will be downloaded into.
                        By default, data will be downloaded into the
                        ~/abcd-dicom2bids/raw folder. A folder will be created 
                        at the given path if one does not already exist.
  -o OUTPUT, --output OUTPUT
                        Folder path into which NDA data will be unpacked and
                        setup once downloaded. By default, this script will
                        put the data into the ~/abcd-dicom2bids/data folder. 
                        A folder will be created at the given path if one does 
                        not already exist.
  -y {00A,02A..} [{00A,02A} ...], --sessions {00A,02A} [{00A,02A} ...]
                        List of sessions for each subject to download. The
                        default is to download all sessions for each subject.
                        The possible selections are ['00A',
                        '02A']
  -m {anat,func,dwi} [{anat,func,dwi} ...], --modalities {anat,func,dwi} [{anat,func,dwi} ...]
                        List of the imaging modalities that should be
                        downloaded for each subject. The default is to
                        download all modalities. The possible selections are
                        ['anat', 'func', 'dwi']
  -r, --remove          After each subject's data has finished conversion,
                        removed that subject's unprocessed data.
  -s {reformat_fastqc_spreadsheet,download_s3_data,unpack_and_setup,correct_jsons,validate_bids}, --start_at {reformat_fastqc_spreadsheet,download_s3_data,unpack_and_setup,correct_jsons,validate_bids}
                        Give the name of the step in the wrapper to start at,
                        then run that step and every step after it. Here are
                        the names of all of the steps, in order from first to
                        last: reformat_fastqc_spreadsheet, download_s3_data,
                        unpack_and_setup, correct_jsons, validate_bids
  -t TEMP, --temp TEMP  Path to the directory to be created and filled with
                        temporary files during unpacking and setup. By
                        default, the folder will be created at
                        ~/abcd-dicom2bids/temp and deleted once the script finishes.
                        A folder will be created at the given path if one
                        doesn't already exist. 
  -z DOCKER_CMD, --docker-cmd DOCKER_CMD
                        A necessary docker command replacement on HPCs like
                        the one at OHSU, which has it's own special wrapper
                        fordocker for security reasons. Example:
                        '/opt/acc/sbin/exadocker'
  -x SIF_PATH, --singularity SIF_PATH
                        Use singularity and path the .sif file
```


The DICOM to BIDS process can be done by running the `abcd2bids.py` wrapper from within the directory cloned from this repo. `abcd2bids.py` requires five positional arguments and can take several optional arguments. Those positional arguments are file paths to the FSL directory, the MATLAB Runtime Environment, the list of subjects to download, S3 bucket path where the raw DICOM files live and the path to the QC file. Here is an example of a valid call of this wrapper:
```
python3 abcd2bids.py <FSL directory> <Matlab2016bRuntime v9.1 compiler runtime directory> -q <Path to QC spreadsheet file from UCSD> -l <Path to a .txt file containing a list of subjects to download> -o <Path to where you want the final file output to be placed> -s3 <Path to UCSD S3 bucket to download the dicoms> -c <Path to config file with S3 creendials to acces the S3 bucket>
```
Example contents of SUBJECT_LIST file (not using any ABCC subject IDs):
```
sub-01
sub-02
```

### Disk Space Usage Warnings

This wrapper will download DICOM data (into the `raw/` subdirectory by default) and then copy it (into the `data/` subdirectory by default) to convert it, without deleting the downloaded data unless the `--remove` flag is added. The downloaded and converted data will take up a large amount of space on the user's filesystem, especially for converting many subjects. About 3 to 7 GB of data or more will be produced by downloading and converting one subject session, not counting the temporary files in the `temp/` subdirectory.

This wrapper will create a temporary folder (`temp/` by default) with hundreds of thousands of files (about 7 GB or more) per subject session. These files are used in the process of preparing the BIDS data. The wrapper will delete that temporary folder once it finishes running, even if it crashes. Still, it is probably a good idea to double-check that the temporary folder has no subdirectories before and after running this wrapper. Otherwise, this wrapper might leave an extremely large set of unneeded files on the user's filesystem.

### Optional Arguments

`--start_at`: By default, this wrapper will run every step listed below in that order. Use this flag to start at one step and skip all of the previous ones. To do so, enter the name of the step. E.g. `--start-at correct_jsons` will skip every step before JSON correction.

1. reformat_fastqc_spreadsheet
2. download_s3_data
3. unpack_and_setup
4. correct_jsons
5. validate_bids

`--temp`: By default, the temporary files will be created in the `temp/` subdirectory of the clone of this repo. If the user wants to place the temporary files anywhere else, then they can do so using the optional `--temp` flag followed by the path at which to create the directory containing temp files, e.g. `--temp /usr/home/abcd2bids-temporary-folder`. A folder will be created at the given path if one does not already exist.

`--sessions`: By default, the wrapper will download all sessions from each subject. This is equivalent to `--sessions ['00A', '02A']`. If only a specific year should be download for a subject then specify the year within list format, e.g. `--sessions ['00A']` for just "year 1" data.

`--modalities`: By default, the wrapper will download all modalities from each subject. This is equivalent to `--modalities ['anat', 'func', 'dwi']`. If only certain modalities should be downloaded for a subject then provide a list, e.g. `--modalities ['anat', 'func']`

`--download`: By default, the wrapper will download the ABCD data to the `raw/` subdirectory of the cloned folder. If the user wants to download the ABCD data to a different directory, they can use the `--download` flag, e.g. `--download ~/abcd-dicom2bids/ABCD-Data-Download`. A folder will be created at the given path if one does not already exist.

`--remove`: By default, the wrapper will download the ABCD data to the `raw/` subdirectory of the cloned folder. If the user wants to delete the raw downloaded data for each subject after that subject's data is finished converting, the user can use the `--remove` flag without any additional parameters.

`--output`: By default, the wrapper will place the finished/converted data into the `data/` subdirectory of the cloned folder. If the user wants to put the finished data anywhere else, they can do so using the optional `--output` flag followed by the path at which to create the directory, e.g. `--output ~/abcd-dicom2bids/Finished-Data`. A folder will be created at the given path if one does not already exist.

For more information including the shorthand flags of each option, use the `--help` command: `python3 abcd2bids.py --help`.

Here is the format for a call to the wrapper with more options added:

```
python3 abcd2bids.py <FSL directory> <Matlab2016bRuntime v9.1 compiler runtime directory> -q <Path to QC spreadsheet file downloaded from the NDA> -l <Path to a .txt file containing a list of subjects to download> --download <Folder to place raw data in> --output <Folder to place converted data in> --temp <Directory to hold temporary files> --remove -s <Any one of the stages to start from> -s3 <Path to S3 bucket to download the raw dicoms> -c <Path to config file with s3 credentials to access the S3 bucket>
```

*Note: DWI has been added to the list of modalities that can be downloaded. This has resulted in a couple important changes to the scripts included here and the output BIDS data. Most notably, fieldmaps now include an acquisition field in their filenames to differentiate those used for functional images and those used for DWI (e.g. ..._acq-func_... or ..._acq-dwi_...). Data uploaded to [Collection 3165](https://github.com/ABCD-STUDY/nda-abcd-collection-3165), which was created using this repository, does not contain this identifier.*

## Explanation of Process

`abcd2bids.py` is a wrapper for 4 distinct scripts, which previously needed to be run on their own in sequential order:

1. (Python) `s3_downloader_revised.py`
2. (BASH) `unpack_and_setup.sh`
3. (Python) `correct_jsons.py`
4. (Docker) Official BIDS validator

The DICOM 2 BIDS conversion process can be done by running `python3 abcd2bids.py <FSL directory> <MRE directory> -l <Path to a .txt file containing a list of subjects to download> -q <Path to QC spreadsheet file from UCSD> -s3 <Path to UCSD S3 bucket to download the dicoms> -c <Path to config file with s3 credentials to access the S3 bucket>` without any other options. First, the wrapper will produce a download list for the Python & BASH portion to download, convert, select, and prepare. The QC spreadsheet referenced above are used to create the `abcd_fastqc01_reformatted.csv` which gets used to actually download the images. If successful, this script will create the file `abcd_fastqc01_reformatted.csv` in the `spreadsheet/` subdirectory. This step was previously done by a compiled MATLAB script called `data_gatherer`, but now the wrapper has its own functionality to replace that script.

### 1. (Python) `s3_downloader_revised.py`

Once `abcd_fastqc01_reformatted.csv` is successfully created, the wrapper will run `src/s3_downloader_revised.py` with this repository's cloned folder as the present working directory to download the ABCD data which passes the QC from the specified S3 bucket. It requires the `abcd_fastqc01_reformatted.csv` spreadsheet under a `spreadsheet/` subdirectory of this repository's cloned folder.
```sh
--qc-csv # Reformatted QC spreadsheet used for selecting data
--s3-bucket # Path to the S3 bucket containing the data
--s3-config # Configuration file with credentials for accessing the S3 bucket
--subject-list # A text file containing a list of subjects to download
--download-dir # Directory to store downloaded files. Defaults to raw/ subdirectory if not specified
--modalities # modalities specifies by the user in the wrapper. Defaults to downlaod all the modailities ['anat', 'func', 'dwi']
--sessions # List of sessions to download Defaults to download all the sessions. 
```

`src/s3_downloader_revised.py` will download the ABCD data from the s3 bucket into the `raw/` subdirectory of the clone of this repo or the directory specified by `--download flag`. If the download crashes and shows errors about `awscli`, try making sure you have the [latest AWS CLI installed](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html), and that the [`aws` executable is in your BASH `PATH` variable](https://docs.aws.amazon.com/cli/latest/userguide/install-linux.html#install-linux-path).

### 2. (BASH) `unpack_and_setup.sh`

The wrapper will call `unpack_and_setup.sh` in a loop to do the DICOM to BIDS conversion and spin echo field map selection, taking seven arguments:

```sh
SUB=$1 # Full BIDS formatted subject ID (sub-SUBJECTID)
VISIT=$2 # Full BIDS formatted session ID (ses-SESSIONID)
TGZDIR=$3 # Path to directory containing all TGZ files for SUB/VISIT
ROOTBIDSINPUT=$4 Path to output folder which will be created to store unpacked/setup files
ScratchSpaceDir=$5 Path to folder which will be created to store temporary files that will be deleted once the wrapper finishes
FSL_DIR=$6 # Path to FSL directory
MRE_DIR=$7 # Path to MATLAB Runtime Environment (MRE) directory
```

This script performs these tasks in the following order :
1. Copy all the tgz to `temp/` subdirectory or the one specified via `--temp flag` and unpack them
2. Convert DICOM to BIDS using [dcm2bids](https://github.com/DCAN-Labs/Dcm2Bids)
3. Replace bvals and bvecs with files supplied by the DIAC
4. Select best func fieldmap based on those with the least variance from the registered group average and update sidecar jsons with all anatomical and functional runs in the IntendedFor field
5. If DWI fieldmaps exist, update the sidecar JSON files by setting the `IntendedFor` field of each fieldmap to include the path of the corresponding DWI run.  
6. Rename all the ERI ( `*EventRelatedInformation.txt` ) files to make them bids complaint
7. Finally copy over the `data/` subdirectory or the path specified via `--output flag`

   
By default, the wrapper will put the unpacked/setup data in the `data/` subdirectory of this repository's cloned folder. This step will also create and fill the `temp/` subdirectory of the user's home directory containing temporary files used for the download. If the user enters other locations for the temp directory or output data directory as optional command line args, then those will be used instead.

### 3. (Python) `correct_jsons.py`

Next, the wrapper runs `correct_jsons.py` on the whole BIDS directory (`data/` by default) to correct/prepare all BIDS sidecar JSON files to comply with the BIDS specification standard version 1.2.0. `correct_jsons.py` will derive fields that are important for the abcd-hcp-pipeline that are hardcoded in scanner specific details.

### 4. (Docker) Run Official BIDS Validator

Finally, the wrapper will run the [official BIDS validator](https://github.com/bids-standard/bids-validator) using Docker to validate the final dataset created by this process in the `data/` subdirectory.

## Inside the `data` subdirectory

The following files belong in the `data` subdirectory to run `abcd2bids.py`:

1. `CHANGES`
2. `dataset_description.json`
3. `task-MID_bold.json`
4. `task-nback_bold.json`
5. `task-rest_bold.json`
6. `task-SST_bold.json`

Without these files, the output of `abcd2bids.py` will fail BIDS validation. They should be downloaded from the GitHub repo by cloning it.

`data` is where the output of `abcd2bids.py` will be placed by default. So, after running `abcd2bids.py`, this folder will have subdirectories for each subject session. Those subdirectories will be correctly formatted according to the [official BIDS specification standard v1.2.0](https://github.com/bids-standard/bids-specification/releases/tag/v1.2.0).

The resulting ABCD Study dataset here is made up of all the ABCD Study participants' BIDS imaging data that passed initial acquisition quality control (MRI QC) for the subjects and sessions originally provide in the SUBJECT_LIST. 


## Attributions

This wrapper relies on the following other projects:
- [cbedetti Dcm2Bids](https://github.com/cbedetti/Dcm2Bids)
- [Rorden Lab dcm2niix](https://github.com/rordenlab/dcm2niix)
- [Official BIDS validator](https://github.com/bids-standard/bids-validator) 


## Meta

Documentation last updated by Tanya Pandhi on 2025-02-18.
