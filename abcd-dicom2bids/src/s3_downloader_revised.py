#! /usr/bin/env python3


import pandas as pd
import csv
import subprocess
import os
import sys
import argparse

#######################################
# Read in ABCD_good_and_bad_series_table.csv (renamed to ABCD_operator_QC.csv) that is continually updated
#   Create a log of all subjects that have been checked
#   If they are not able to be processed report what is wrong with them
#
#######################################

prog_descrip='AWS downloader'

QC_CSV = os.path.join(os.path.dirname(os.path.dirname(
                    os.path.abspath(__file__))), "spreadsheets",
                    "abcd_fastqc01_reformatted.csv") 
YEARS = ['baseline_year_1_arm_1', '2_year_follow_up_y_arm_1',  '00A', '02A', '04A', '06A', '08A']
MODALITIES = ['anat', 'func', 'dwi']

def generate_parser(parser=None):

    if not parser:
        parser = argparse.ArgumentParser(
            description=prog_descrip
        )
    parser.add_argument(
        '-q', 
        '--qc-csv', 
        dest='qc_csv',
        default=QC_CSV,
        help='Path to the csv file containing aws paths and operator QC info'
)
    parser.add_argument(
        '-d',
        '--download-dir',
        dest='download_dir',
        default='./new_download',
        help='Path to where the subjects should be downloaded to.'
)
    parser.add_argument(
        '-s', 
        '--subject-list', 
        dest='subject_list',
        required=True,
        help='Path to a text file containing a list of subject IDs'
)
    parser.add_argument(
        '-y', 
        '--sessions', 
        dest='year_list',
        default=YEARS,
        help='List the years that images should be downloaded from'
)
    parser.add_argument(
        '-m', 
        '--modalities',
#        choices=MODALITIES,
#        nargs='+',
        dest='modalities',
        default=MODALITIES,
        help="List the modalities that should be downloaded. Default: ['anat', 'func', 'dwi']"
)
    parser.add_argument(
        '--s3-bucket',
        dest='s3_bucket',
        default='s3://midb-abcd-ucsd-main-pr-upload/release/bids/sourcedata',
        help="UCSD S3 Bucket . Default: s3://midb-abcd-ucsd-main-pr-upload/release/bids/sourcedata"
)

    return parser

def main(argv=sys.argv):
    parser = generate_parser()
    args = parser.parse_args()

    # Logging variables
    num_sub_visits = 0
    num_t1 = 0
    num_rsfmri = 0
    num_sst = 0
    num_mid = 0
    num_nback = 0
    num_t2 = 0
    num_dti = 0


    series_csv = args.qc_csv
    if args.subject_list:
        f = open(args.subject_list, 'r')
        x = f.readlines()
        f.close
        subject_list = [sub.strip() for sub in x]
        log = os.path.join(os.path.dirname(args.subject_list), os.path.splitext(os.path.basename(args.subject_list))[0] + "_download_log.csv")
    year_list = args.year_list
    if isinstance(year_list, str):
        year_list = year_list.split(',')
    modalities = args.modalities
    if isinstance(modalities, str):
        modalities = modalities.split(',')
    download_dir = args.download_dir

    print("s3_downloader.py command line arguments:")    
    print("     QC spreadsheet      : {}".format(series_csv))
    print("     Number of Subjects  : {}".format(len(subject_list)))
    print("     Year                : {}".format(year_list))
    print("     Modalities          : {}".format(modalities))

    with open(log, 'w') as f:
        writer = csv.writer(f)

        # Read csv as pandas dataframe, drop duplicate entries, sort, and group by subject/visit
        series_header = pd.read_csv(series_csv, nrows=0).columns.tolist()
        series_df = pd.read_csv(series_csv, usecols=list(range(0,len(series_header))))

        # If subject list is provided
        # Get list of all unique subjects if not provided
        # subject_list = series_df.pGUID.unique()
        # year_list = ['baseline_year_1_arm_1']
        # Get list of all years if not provided
        # year_list = series_df.EventName.unique()
        uid_start = "INV"
        for sub in subject_list:
            # uid = sub.split(uid_start, 1)[1]
            # pguid = 'NDAR_INV' + ''.join(sub)
            bids_id = 'sub-' + ''.join(sub)
            subject_df = series_df[series_df['pGUID'] == bids_id]
            for bids_year in year_list:
                year = 'ses-' + ''.join(bids_year)
                # if bids_year == '06A':
                #     year='6_year_follow_up_y_arm_1'
                # elif bids_year == '00A':
                #     year='baseline_year_1_arm_1'
                # elif bids_year == '02A':
                #     year='2_year_follow_up_y_arm_1'
                # elif bids_year == '04A':
                #     year='4_year_follow_up_y_arm_1'
                # elif bids_year == '08A':
                #     year='8_year_follow_up_y_arm_1'
                # else:
                #     print("Wrong choice of session")
                #     sys.exit(1)
                sub_ses_df = subject_df[subject_df['EventName'] == year]
                sub_pass_QC_df = sub_ses_df[sub_ses_df['usable'] != 0.0] #changed this line back to be able to filter based on QC from fast track
                file_paths = []
                ### Logging information
                # initialize logging variables
                has_t1 = 0
                has_t2 = 0
                has_sefm = 0
                has_rsfmri = 0
                has_mid = 0
                has_sst = 0
                has_nback = 0
                has_dti = 0

                num_sub_visits += 1
                tgz_dir = os.path.join(download_dir, bids_id, f'ses-{bids_year}')
                print("Checking QC data for valid images for {} {}.".format(bids_id, year))
                os.makedirs(tgz_dir, exist_ok=True)
                                
                if 'anat' in modalities:
                    (file_paths, has_t1, has_t2) = add_anat_paths(sub_pass_QC_df, file_paths)
                if 'func' in modalities:
                    (file_paths, has_sefm, has_rsfmri, has_mid, has_sst, has_nback) = add_func_paths(sub_ses_df, sub_pass_QC_df, file_paths)
                if 'dwi' in modalities:
                    (file_paths, has_dti) = add_dwi_paths(sub_ses_df, sub_pass_QC_df, file_paths)
                    
            
        
                # TODO: log subject level information
                print(' t1=%s, t2=%s, sefm=%s, rsfmri=%s, mid=%s, sst=%s, nback=%s, has_dti=%s' % (has_t1, has_t2, has_sefm, has_rsfmri, has_mid, has_sst, has_nback, has_dti))
                writer.writerow([bids_id, year, has_t1, has_t2, has_sefm, has_rsfmri, has_mid, has_sst, has_nback, has_dti])
                
                if has_t1 != 0:
                    num_t1 += 1
                if has_t2 != 0:
                    num_t2 += 1
                if has_rsfmri != 0 and has_rsfmri != 10000:
                    num_rsfmri += 1
                if has_mid != 0 and has_mid != 10000:
                    num_mid += 1
                if has_sst != 0 and has_sst != 10000:
                    num_sst += 1
                if has_nback != 0 and has_nback != 10000:
                    num_nback += 1
                if has_dti != 0:
                    num_dti += 1

                
                missing_files_log = '/home/midb-ig/shared/projects/ABCD/dicom2bids/abcd-dicom2bids/temp/missing_files.txt'
                # Create the log file if it doesn't exist
                if not os.path.exists(missing_files_log):
                    with open(missing_files_log, 'w') as log_file:
                        log_file.write("Missing files log:\n")
                    os.chmod(missing_files_log, 0o664)
                
                for file_path in file_paths:
                    #ensure file_path is string type
                    file_path = str(file_path)
                    # Split the file_path by ';' and process each value
                    for split_value in file_path.split(';'):
                        # full_file_path = f"{args.s3_bucket}/{bids_id}/ses-{bids_year}/{split_value.strip()}"
                        full_file_path = f"{args.s3_bucket}/{split_value.strip()}"
                        print("Trying to Download",full_file_path)
                        # Check if the file exists in the S3 bucket
                        result = subprocess.run(['s3cmd', 'ls', full_file_path, '-c', '/spaces/ngdr/workspaces/hendr522/ABCC/code/s3cfgs/msi_loris_abcd_midb_s3.s3cfg'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        print(result.stdout.decode())
                        print(result.stderr.decode())
                        print(result.returncode)

                        if result.returncode == 0:
                            # Extract the second last directory (e.g., "anat" from the full path)
                            second_last_dir = full_file_path.split('/')[-2]
                            file_name = full_file_path.split('/')[-1]
                            
                            # Construct the destination directory
                            destination_dir = os.path.join(tgz_dir, second_last_dir,file_name)
                            # os.makedirs(destination_dir, exist_ok=True)  # Create the destination directory if it doesn't exist
                            try:
                                subprocess.run(['s3cmd', 'get', full_file_path, destination_dir, '-c', '/spaces/ngdr/workspaces/hendr522/ABCC/code/s3cfgs/msi_loris_abcd_midb_s3.s3cfg'], check=True)
                                print(f"Downloaded: {full_file_path} to {destination_dir}")
                            except subprocess.CalledProcessError as e:
                                # File does not exist, log the missing file
                                with open(missing_files_log, 'a') as log_file:
                                    log_file.write(f"{bids_id}; {bids_year}; {full_file_path}\n")
                                print(f"Missing: {full_file_path}")
                                print(f"Error syncing {full_file_path} to {destination_dir}: {e}")
                        else:
                            # File does not exist, log the missing file
                            try:
                                with open(missing_files_log, 'a') as log_file:
                                    log_file.write(f"{bids_id}; {bids_year}; {full_file_path}; \n")
                            except OSError as e:
                                print(f"Error writing to log file: {e}")

                
    print("There are %s subject visits" % num_sub_visits)
    print("number of subjects with a T1 : %s" % num_t1)
    print("number of subjects with a T2 : %s" % num_t2)
    print("number of subjects with rest : %s" % num_rsfmri)
    print("number of subjects with mid  : %s" % num_mid)
    print("number of subjects with sst  : %s" % num_sst)
    print("number of subjects with nBack: %s" % num_nback)
    print("number of subjects with dti  : %s" % num_dti)


def add_anat_paths(passed_QC_group, file_paths):
    ##  If T1_NORM exists, only download that file instead of normal T1
    T1_df = passed_QC_group[passed_QC_group['SeriesType'] == 'ABCD-T1-NORM']
    if T1_df.empty:
        T1_df = passed_QC_group[passed_QC_group['SeriesType'] == 'ABCD-T1']
        if T1_df.empty:
            has_t1 = 0 # No T1s. Invalid subject
        else:
            for file_path in T1_df['filename']:
                file_paths += [file_path]
            has_t1 = T1_df.shape[0]
    else:
        for file_path in T1_df["filename"]:
            file_paths += [file_path]
        has_t1 = T1_df.shape[0]

    ##  If T2_NORM exists, only download that file instead of normal T2
    T2_df = passed_QC_group[passed_QC_group['SeriesType'] == 'ABCD-T2-NORM']
    if T2_df.empty:
        T2_df = passed_QC_group[passed_QC_group['SeriesType'] == 'ABCD-T2']
        if T2_df.empty:
            has_t2 = 0 # No T1s. Invalid subject
        else:
            for file_path in T2_df['filename']:
                file_paths += [file_path]
            has_t2 = T2_df.shape[0]
    else:
        for file_path in T2_df["filename"]:
            file_paths += [file_path]
        has_t2 = T2_df.shape[0]

    return (file_paths, has_t1, has_t2)

def add_func_paths(all_group,passed_QC_group, file_paths):
    #convert func files only if any one task or rest func file exists
    if passed_QC_group['SeriesType'].isin(['ABCD-rsfMRI', 'ABCD-MID-fMRI', 'ABCD-nBack-fMRI', 'ABCD-SST-fMRI']).any():

        ## Pair SEFMs and only download if both pass QC
        #   Check first if just the FM exists
        FM_df = passed_QC_group[passed_QC_group['SeriesType'] == 'ABCD-fMRI-FM']
        if FM_df.empty:
            ## Pair SEFMs first based on all fmaps available using the all_group def i.e. sub_ses_df before filtering for QC
            FM_AP_df = all_group[all_group['SeriesType'] == 'ABCD-fMRI-FM-AP']
            FM_PA_df = all_group[all_group['SeriesType'] == 'ABCD-fMRI-FM-PA']
            # if FM_AP_df.shape[0] != FM_PA_df.shape[0] or FM_AP_df.empty:
            if FM_AP_df.empty:
                has_sefm = 0 # No SEFMs. Invalid subject
            else:
                # If there are a different number of AP and PA fmaps, then figure out which has fewer to use for upper_range value to iterate through
                if FM_AP_df.shape[0] <= FM_PA_df.shape[0]:
                    upper_range=FM_AP_df.shape[0]
                elif FM_AP_df.shape[0] > FM_PA_df.shape[0]:
                    upper_range=FM_PA_df.shape[0]

                #for i in range(0, FM_AP_df.shape[0]):
                for i in range(0, upper_range):
                    if FM_AP_df.iloc[i]['usable'] != 0.0 and FM_PA_df.iloc[i]['usable'] != 0.0:
                        FM_df = FM_df.append(FM_AP_df.iloc[i])
                        FM_df = FM_df.append(FM_PA_df.iloc[i])
        if FM_df.empty:
            has_sefm = 0 # No SEFMs. Invalid subject
            return (file_paths, has_sefm, 10000 , 10000, 10000, 10000)########### added to not download any func even if qc==1, if they dont have any pair of fmap i.e. has_sefm=0
        else:
            for file_path in FM_df['filename']:
                file_paths += [file_path]
            has_sefm = FM_df.shape[0]


        ## List all rsfMRI scans that pass QC
        RS_df = passed_QC_group.loc[passed_QC_group['SeriesType'] == 'ABCD-rsfMRI']
        if RS_df.empty:
            has_rsfmri = 0
        else:
            for file_path in RS_df['filename']:
                file_paths += [file_path]
            has_rsfmri = RS_df.shape[0]

        ## List only download task if and only if there is a pair of scans for the task that passed QC
        MID_df = passed_QC_group.loc[passed_QC_group['SeriesType'] == 'ABCD-MID-fMRI']

        if MID_df.empty:
            has_mid = 0
        else:
            for file_path in MID_df['filename']:
                file_paths += [file_path]
            has_mid = MID_df.shape[0]
        SST_df = passed_QC_group.loc[passed_QC_group['SeriesType'] == 'ABCD-SST-fMRI']
        if SST_df.empty:
            has_sst = 0
        else:
            for file_path in SST_df['filename']:
                file_paths += [file_path]
            has_sst = SST_df.shape[0]
        nBack_df = passed_QC_group.loc[passed_QC_group['SeriesType'] == 'ABCD-nBack-fMRI']
        if nBack_df.empty:
            has_nback = 0
        else:
            for file_path in nBack_df['filename']:
                file_paths += [file_path]
            has_nback = nBack_df.shape[0]


        return (file_paths, has_sefm, has_rsfmri, has_mid, has_sst, has_nback)
    else:
        return(file_paths, 0, 0, 0, 0, 0)


def add_dwi_paths(all_group, passed_QC_group, file_paths):
    DTI_df = passed_QC_group.loc[passed_QC_group['SeriesType'] == 'ABCD-DTI']
    if DTI_df.shape[0] >= 1:
        # If a DTI exists then download all passing DTI fieldmaps
        DTI_FM_df = passed_QC_group.loc[passed_QC_group['SeriesType'] == 'ABCD-Diffusion-FM']
        # If not present, next search and sort AP/PA fmaps
        if DTI_FM_df.empty:
            DTI_FM_AP_df = all_group[all_group['SeriesType'] == 'ABCD-Diffusion-FM-AP']
            DTI_FM_PA_df = all_group[all_group['SeriesType'] == 'ABCD-Diffusion-FM-PA']
            DTI_FM_df = pd.DataFrame()
            
            # if DTI_FM_AP_df.shape[0] != DTI_FM_PA_df.shape[0] or DTI_FM_AP_df.empty:
            if DTI_FM_AP_df.empty:
                return (file_paths, 0)
            else:
                # If there are a different number of AP and PA fmaps, then figure out which has fewer to use for upper_range value to iterate through
                if DTI_FM_AP_df.shape[0] <= DTI_FM_PA_df.shape[0]:
                    upper_range=DTI_FM_AP_df.shape[0]
                elif DTI_FM_AP_df.shape[0] > DTI_FM_PA_df.shape[0]:
                    upper_range=DTI_FM_PA_df.shape[0]
                
                for i in range(0, upper_range):
                    if DTI_FM_AP_df.iloc[i]['usable'] != 0.0 and DTI_FM_PA_df.iloc[i]['usable'] != 0.0:
                        DTI_FM_df = DTI_FM_df.append(DTI_FM_AP_df.iloc[i])
                        DTI_FM_df = DTI_FM_df.append(DTI_FM_PA_df.iloc[i])
        if not DTI_FM_df.empty:
            for file_path in DTI_df['filename']:
                file_paths += [file_path]
            for file_path in DTI_FM_df['filename']:
                file_paths += [file_path]
        has_dti = DTI_df.shape[0]
    else:
        has_dti = DTI_df.shape[0]

    return (file_paths, has_dti)

if __name__ == "__main__":
    main()
