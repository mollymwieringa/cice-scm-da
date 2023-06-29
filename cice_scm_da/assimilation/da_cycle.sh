#!/bin/bash -l
### Job Name
#PBS -N postprocess_icepack_da
### Charging account
#PBS -A UWAS0083
### Request one chunk of resources with 1 CPU and 10 GB of memory
#PBS -l select=1:ncpus=1:mem=4GB
### Allow job to run up to 30 minutes
#PBS -l walltime=09:00:00
### Route the job to the casper queue
#PBS -q economy
### Join output and error streams into single file
#PBS -j oe
#PBS -m ae
#PBS -M mmw906@uw.edu

export TMPDIR=/glade/scratch/$USER/temp
mkdir -p $TMPDIR

### Load Python module and activate NPL environment
module load ncarenv python
conda activate icepack

### Run analysis script
python step4b_cycle.py 2011 1 2 2011 12 31

### 2011 12 31