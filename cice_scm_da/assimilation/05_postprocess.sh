#!/bin/bash -l
### Job Name
#PBS -N postprocess_assimilation
### Charging account
#PBS -A UWAS0083
### Request one chunk of resources with 1 CPU and 10 GB of memory
#PBS -l select=1:ncpus=1:mem=4GB
### Allow job to run up to 30 minutes
#PBS -l walltime=00:40:00
### Route the job to the economy queue
#PBS -q economy
### Join output and error streams into single file
#PBS -j oe
#PBS -m ae
#PBS -M mmw906@uw.edu

export TMPDIR=/glade/scratch/$USER/temp
mkdir -p $TMPDIR

### Load Python module and activate NPL environment
module load ncarenv python
conda activate cice-scm-da

### Run analysis script
python 05_postprocess.py CAT_f101_NORM_opt1 all

