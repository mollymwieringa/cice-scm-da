#!/bin/bash -l
### Job Name
#PBS -N run_icepack_ensemble
### Charging account
#PBS -A UWAS0083
### Request one chunk of resources with 1 CPU and 10 GB of memory
#PBS -l select=1:ncpus=1:mem=8GB
### Allow job to run up to 30 minutes
#PBS -l walltime=1:00:00
### Route the job to the economy queue
#PBS -q economy
### Join output and error streams into single file
#PBS -j oe
### send emails on abort and exit
#PBS -m ae
#PBS -M mmw906@uw.edu

export TMPDIR=/glade/scratch/$USER/temp
mkdir -p $TMPDIR

### Load Python module and activate NPL environment
module load ncarenv python
conda activate icepack

### Run analysis script
python step2_run_free_ensemble.py 'SHEBA' 'SHEBA' 'atm'

