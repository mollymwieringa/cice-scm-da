#!/bin/bash -l
### Job Name
#PBS -N run_assimilations
### Charging account
#PBS -A UWAS0083
### Request one chunk of resources with 1 CPU and 10 GB of memory
#PBS -l select=1:ncpus=1:mem=4GB
### Allow job to run up to 30 minutes
#PBS -l walltime=10:00:00
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
python 04a_setup_da_case.py CAT_f1_NORM_opt3 spinup_test 1 NORM null atm
python 04b_cycle.py CAT_f1_NORM_opt3 free_test 1 NORM 2011 1 2 2011 12 31 SAT_SEAICE_AICE01 SAT_SEAICE_VICE01 SAT_SEAICE_AICE02 SAT_SEAICE_VICE02 SAT_SEAICE_AICE03 SAT_SEAICE_VICE03 SAT_SEAICE_AICE04 SAT_SEAICE_VICE04 SAT_SEAICE_AICE05 SAT_SEAICE_VICE05
