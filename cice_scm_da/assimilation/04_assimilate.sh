#!/bin/bash -l
### Job Name
#PBS -N run_assimilations
### Charging account
#PBS -A UWAS0083
### Request one chunk of resources with 1 CPU and 10 GB of memory
#PBS -l select=1:ncpus=1:mem=4GB
### Allow job to run up to 30 minutes
#PBS -l walltime=00:15:00
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
conda activate cice-scm-da

### Run analysis script
python 04a_setup_da_case.py SIT_f101_BNRH_test spinup_test 101 BNRH atm
python 04b_cycle.py SIT_f101_BNRH_test free_test 101 BNRH 2011 1 2 2011 1 3
