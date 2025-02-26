#! /bin/bash

# Given a subject ID, session, and tgz directory:
#   1) Copy all tgzs to compute node's disk
#   2) Unpack tgzs
#   3) Convert dcms to niftis in BIDS
#   4) Select the best SEFM
#   5) Rename and move Eprime files
#   6) Copy back to Lustre

## Necessary dependencies
# dcm2bids (https://github.com/DCAN-Labs/Dcm2Bids)
# microgl_lx (https://github.com/rordenlab/dcm2niix)
# pigz-2.4 (https://zlib.net/pigz)
# run_order_fix.py (in this repo)
# sefm_eval_and_json_editor.py (in this repo)

# If output folder is given as a command line arg, get it; otherwise use
# ./data as the default. Added by Greg 2019-06-06
if [ "x$4" = "x" ]; then
    ROOT_BIDSINPUT=./data
else
    ROOT_BIDSINPUT=$4
fi

# If temp files folder is given as a command line arg, get it; otherwise use
# ./temp as the default. Added by Greg 2019-06-07
if [ "x$5" = "x" ]; then
    ScratchSpaceDir=./temp
else
    ScratchSpaceDir=$5
fi

# Get FSL and MRE directory paths from command line; added by Greg Conan on
# 2019-06-10
if [[ ! "x$6" = "x" && ! "x$7" = "x" ]]; then
    FSL_DIR=$6
    MRE_DIR=$7
fi

SUB=$1 # Full BIDS formatted subject ID (sub-SUBJECTID)
VISIT=$2 # Full BIDS formatted session ID (ses-SESSIONID)
TGZDIR=$3 # Path to directory containing all .tgz for this subject's session

ABCD2BIDS_DIR="$(dirname `dirname $0`)"

participant=`echo ${SUB} | sed 's|sub-||'`
session=`echo ${VISIT} | sed 's|ses-||'`

date
hostname
echo ${SLURM_JOB_ID}
echo Running under group: `id -g`

# Setup scratch space directory
if [ ! -d ${ScratchSpaceDir} ]; then
    mkdir -p ${ScratchSpaceDir}
    # chown :fnl_lab ${ScratchSpaceDir} || true 
    chmod 770 ${ScratchSpaceDir} || true
fi
RandomHash=`cat /dev/urandom | tr -cd 'a-f0-9' | head -c 16`
TempSubjectDir=${ScratchSpaceDir}/${RandomHash}
mkdir -p ${TempSubjectDir}
# chown :fnl_lab ${TempSubjectDir} || true

########################### orignal code ############################
# # copy all tgz to the scratch space dir
# echo `date`" :COPYING TGZs TO SCRATCH: ${TempSubjectDir}"
# cp ${TGZDIR}/image03/* ${TempSubjectDir}

# # unpack tgz to ABCD_DCMs directory
# mkdir ${TempSubjectDir}/DCMs/${SUB}/${VISIT}
# echo `date`" :UNPACKING DCMs: ${TempSubjectDir}/DCMs/${SUB}/${VISIT}"
# for tgz in ${TempSubjectDir}/*.tgz; do
#     echo $tgz
#     tar -xzf ${tgz} -C ${TempSubjectDir}/DCMs
# done
########################################################################

#################### modified code for ucsd bucket - tanya ######################
# Loop through each subdirectory in TGZDIR
for subdir in "${TGZDIR}"/*; do
    if [ -d "${subdir}" ]; then  # Check if it's a directory
        SUB_dir=$(basename "${subdir}")  # Get the name of the subdirectory
            
        # Create the destination directory
        dest_dir="${TempSubjectDir}/DCMs/${SUB}/${VISIT}/${SUB_dir}"
        mkdir -p "${dest_dir}"

        # Copy all files from the visit directory to the destination
        echo "$(date) :COPYING TGZs TO SCRATCH: ${dest_dir}"
        echo "${subdir}"
        cp -R "${subdir}"/* "${dest_dir}/"

        # Unpack tgz files in the destination directory
        echo "$(date) :UNPACKING DCMs: ${dest_dir}"
        for tgz in "${dest_dir}"/*.tgz; do
            if [ -f "${tgz}" ]; then  # Ensure it's a file
                echo "Unpacking ${tgz}"
                tar -xzf "${tgz}" -C "${dest_dir}/"
                # Move the unpacked files back to TempSubjectDir
                mv "${tgz}" "${TempSubjectDir}/"
            fi
        done
    fi
done
#################################################################################

if [ -e ${TempSubjectDir}/DCMs/${SUB}/${VISIT}/func ]; then
    ${ABCD2BIDS_DIR}/src/remove_RawDataStorage_dcms.py ${TempSubjectDir}/DCMs/${SUB}/${VISIT}/func
fi


# # IMPORTANT PATH DEPENDENCY VARIABLES AT OHSU IN SLURM CLUSTER
# export PATH=.../anaconda2/bin:${PATH} # relevant Python path with dcm2bids
# export PATH=.../mricrogl_lx/:${PATH} # relevant dcm2niix path
# export PATH=.../pigz-2.4/:${PATH} # relevant pigz path for improved (de)compression


# convert DCM to BIDS and move to ABCD directory
mkdir ${TempSubjectDir}/BIDS_unprocessed
cp ${ABCD2BIDS_DIR}/dataset_description.json ${TempSubjectDir}/BIDS_unprocessed/
echo ${participant}
echo `date`" :RUNNING dcm2bids"
dcm2bids -d ${TempSubjectDir}/DCMs/${SUB} -p ${participant} -s ${session} -c ${ABCD2BIDS_DIR}/abcd_dcm2bids.conf -o ${TempSubjectDir}/BIDS_unprocessed --forceDcm2niix --clobber


# replace bvals and bvecs with files supplied by the NDA
if [ -e ${TempSubjectDir}/DCMs/${SUB}/${VISIT}/dwi ]; then
    first_dcm=`ls ${TempSubjectDir}/DCMs/${SUB}/${VISIT}/dwi/*/*.dcm | head -n1`
    echo "Replacing bvals and bvecs with files supplied by the NDA"
    for dwi in ${TempSubjectDir}/BIDS_unprocessed/${SUB}/${VISIT}/dwi/${SUB}_${VISIT}*.nii.gz; do
        orig_bval=`echo $dwi | sed 's|.nii.gz|.bval|'`
        orig_bvec=`echo $dwi | sed 's|.nii.gz|.bvec|'`
        
        if [[ `dcmdump --search 0008,0070 ${first_dcm} 2>/dev/null` == *GE* ]]; then 
            if dcmdump --search 0018,1020 ${first_dcm} 2>/dev/null | grep -q DV25; then
                echo "Replacing GE DV25 bvals and bvecs"
                echo cp `dirname $0`/ABCD_Release_2.0_Diffusion_Tables/GE_bvals_DV25.txt ${orig_bval}
                cp `dirname $0`/ABCD_Release_2.0_Diffusion_Tables/GE_bvals_DV25.txt ${orig_bval}
                echo cp `dirname $0`/ABCD_Release_2.0_Diffusion_Tables/GE_bvecs_DV25.txt ${orig_bvec}
                cp `dirname $0`/ABCD_Release_2.0_Diffusion_Tables/GE_bvecs_DV25.txt ${orig_bvec}
            elif dcmdump --search 0018,1020 ${first_dcm} 2>/dev/null | grep -q -e DV26 -e RX26 -e DV27 -e RX27 -e DV28 -e RX28; then
                # Don Hagler at UCSD said GE software versions between DV (and RX) 26 and 28 needed to be replaced by the DV26 BVAL/BVEC files
                echo "Replacing GE bvals and bvecs for software version after DV25 and before DV29"
                cp `dirname $0`/ABCD_Release_2.0_Diffusion_Tables/GE_bvals_DV26.txt ${orig_bval}
                cp `dirname $0`/ABCD_Release_2.0_Diffusion_Tables/GE_bvecs_DV26.txt ${orig_bvec}
            fi
        elif [[ `dcmdump --search 0008,0070 ${first_dcm} 2>/dev/null` == *SIEMENS* ]]; then
            # Siemens BVAL and BVEC files should be good directly from dcm2niix
            echo "Found Siemens data, not replacing BVAL or BVEC files"
        elif [[ `dcmdump --search 0008,0070 ${first_dcm} 2>/dev/null` == *Philips* ]]; then
            # Philips BVAL and BVEC files should be good directly from dcm2niix
            echo "Found Philips data, not replacing BVAL or BVEC files"
        else
            echo "ERROR setting up DWI: Manufacturer not recognized"
            exit
        fi
    done
fi


if [[ -e ${TempSubjectDir}/BIDS_unprocessed/${SUB}/${VISIT}/func ]]; then
    echo `date`" :CHECKING BIDS ORDERING OF EPIs"
    i=0
    while [ "`${ABCD2BIDS_DIR}/src/run_order_fix.py ${TempSubjectDir}/BIDS_unprocessed ${TempSubjectDir}/bids_order_error.json ${TempSubjectDir}/bids_order_map.json --all --subject ${SUB} --session ${VISIT}`" != ${SUB} ] && [ $i -ne 3 ]; do
        ((i++))
        echo `date`" :  WARNING: BIDS functional scans incorrectly ordered. Attempting to reorder. Attempt #$i"
    done        
    if [ "`${ABCD2BIDS_DIR}/src/run_order_fix.py ${TempSubjectDir}/BIDS_unprocessed ${TempSubjectDir}/bids_order_error.json ${TempSubjectDir}/bids_order_map.json --all --subject ${SUB} --session ${VISIT}`" == ${SUB} ]; then
        echo `date`" : BIDS functional scans correctly ordered"
    else
        echo `date`" :  ERROR: BIDS incorrectly ordered even after running run_order_fix.py"
        exit
    fi
fi
# select best fieldmap and update sidecar jsons
echo `date`" :RUNNING SEFM SELECTION AND EDITING SIDECAR JSONS"
if [ -d ${TempSubjectDir}/BIDS_unprocessed/${SUB}/${VISIT}/fmap ]; then
    ${ABCD2BIDS_DIR}/src/sefm_eval_and_json_editor.py ${TempSubjectDir}/BIDS_unprocessed ${FSL_DIR} ${MRE_DIR} --participant-label=${participant} --output_dir $ROOT_BIDSINPUT
fi

# Fix all json extra data errors
for j in ${TempSubjectDir}/BIDS_unprocessed/${SUB}/${VISIT}/*/*.json; do
    mv ${j} ${j}.temp
    # print only the valid part of the json back into the original json
    jq '.' ${j}.temp > ${j}
    rm ${j}.temp
done


rm ${TempSubjectDir}/BIDS_unprocessed/${SUB}/${VISIT}/fmap/*dir-both* 2> /dev/null || true

# rename EventRelatedInformation
srcdata_dir=${TempSubjectDir}/BIDS_unprocessed/sourcedata/${SUB}/${VISIT}/func
if ls ${TempSubjectDir}/DCMs/${SUB}/${VISIT}/func/*EventRelatedInformation.* > /dev/null 2>&1; then
    echo `date`" :COPY AND RENAME SOURCE DATA"
    mkdir -p ${srcdata_dir}

    tasks=(MID SST nBack)

    for task in "${tasks[@]}"; do
        envs=$(ls ${TempSubjectDir}/DCMs/${SUB}/${VISIT}/func/*${task}*EventRelatedInformation.*)
        echo "Task ERI files found:" ${envs}

        i=1
        for ev in ${envs}; do
            if [[ "${ev}" == *"nBack"* ]]; then
                task=nback
            fi
            extension="${ev##*.}"
            cp ${ev} ${srcdata_dir}/${SUB}_${VISIT}_task-${task}_run-0${i}_bold_EventRelatedInformation.${extension}
            ((i++)) # Maybe needs a dollar sign in front 
        done
    done
fi

echo `date`" :COPYING BIDS DATA BACK: ${ROOT_BIDSINPUT}"

TEMPBIDSINPUT=${TempSubjectDir}/BIDS_unprocessed/${SUB}
if [ -d ${TEMPBIDSINPUT} ] ; then
    echo `date`" :CHMOD BIDS INPUT"
    chmod g+rw -R ${TEMPBIDSINPUT} || true
    #Delete unneccsary .bval and .bvec files from fmap 
    echo `date`" :DELETING .bval and .bvec FILES"
    find ${TEMPBIDSINPUT}/${VISIT}/fmap/ -type f \( -name '*.bval' -o -name '*.bvec' \) -delete || true
    echo `date`" :COPY BIDS INPUT"
    mkdir -p ${ROOT_BIDSINPUT}
    cp -r ${TEMPBIDSINPUT} ${ROOT_BIDSINPUT}/
    # Copy everything except .bval and .bvec files in the specific fmap directory

fi

ROOT_SRCDATA=${ROOT_BIDSINPUT}/sourcedata
TEMPSRCDATA=${TempSubjectDir}/BIDS_unprocessed/sourcedata/${SUB}
if [ -d ${TEMPSRCDATA} ] ; then
    echo `date`" :CHMOD SOURCEDATA"
    chmod g+rw -R ${TEMPSRCDATA} || true
    echo `date`" :COPY SOURCEDATA"
    mkdir -p ${ROOT_SRCDATA}
    cp -r ${TEMPSRCDATA} ${ROOT_SRCDATA}/
fi

echo `date`" :UNPACKING AND SETUP COMPLETE: ${SUB}/${VISIT}"
