###############################################################
## IMPORT NECESSARY LIBRARIES                                ##
###############################################################
# This tool MUST be run with an environment in which f90nml exists
import f90nml 
import glob
import os
import xarray as xr
import numpy as np
import sys

###############################################################
## SET MANUAL INPUTS HERE                                    ##
###############################################################

# set the case name 
case_name = sys.argv[1]

# set relevant directory names 
# where is this project repo located on your system?
project_dir = '/glade/work/mollyw/Projects/cice-scm-da/'
# where is the Icepack installation located on your system?
icepack_dir = '/glade/work/mollyw/Icepack_DART/Icepack'
# where is the scratch directory Icepack will write output to?
scratch_dir = '/glade/scratch/mollyw/'

# set machine name and compiler
machine = 'cheyenne'
compiler = 'intel'

# choose a spinup length and ensemble size (limited at this 
# time to 30 or less)
spinup_length = 10
ensemble_size = 30

# This code comes equipped with the ability to perturb param-
# eters in the sea ice code. To do so, you must specify the 
# parameter(s) you wish to perturb as a single or list of 
# arguements to the script. For example, if you wish to
# perturb the snow thermal conductivity and the ice strength,
# you would run the script as follows:
# python3 step1_spinup_ensemble.py case_name ksno Cf

# The code currently supports the following perturbation options:
# R_snw: Snow grain radius tuning parameter (unitless)
# ksno: Snow thermal conductivity (W/m/K)
# dragio: Ice-ocean drag coefficient (unitless)
# hi_ssl: Ice surface scattering layer thickness (m)
# hs_ssl: Snow surface scattering layer thickness (m)
# rsnw_mlt: Snow melt rate (kg/m^2/s)
# rhoi: Ice density (kg/m^3)
# rhos: Snow density (kg/m^3)
# Cf: ratio of ridging work to PE change in ridging (unitless)
# atm: atmospheric forcing 
# ocn: oceanic forcing

###############################################################
## BEGIN LAUNCH- DO NOT EDIT BELOW THIS LINE                 ##
###############################################################
#-----------------------------------------#
# 0. Read parameter inputs
#-----------------------------------------#
if len(sys.argv) > 2:
    perturb = [sys.argv[i] for i in range(2, len(sys.argv))]
else:
    perturb = []

#-----------------------------------------#
# 1. Set parameter details
#-----------------------------------------#
# Defaults
dR_snw = -2.0
dksno = 0.3
dCf = 17
ddragio = 0.00536
dhi_ssl = 0.05
dhs_ssl = 0.04
drsnw_mlt = 1500.0
drhoi = 917.0
drhos = 330.0

# Perturbed
parameters = xr.open_dataset(project_dir+ '/data/forcings/ICE_PERTS/parameters_30_cice5.nc')
zeros = np.zeros(ensemble_size)

if 'R_snw' in perturb:
    R_snw = list(parameters.R_snw.values)
else:
    R_snw = list(zeros+dR_snw)

if 'ksno' in perturb:
    ksno = list(parameters.ksno.values)
else:
    ksno = list(zeros+dksno)

if 'dragio' in perturb:
    dragio = list(parameters.dragio.values)
else:
    dragio = list(zeros+ddragio)

if 'hi_ssl' in perturb:
    hi_ssl = list(parameters.hi_ssl.values)
else:
    hi_ssl = list(zeros+dhi_ssl)

if 'hs_ssl' in perturb:
    hs_ssl = list(parameters.hs_ssl.values)
else:
    hs_ssl = list(zeros+dhs_ssl)

if 'rsnw_mlt' in perturb:
    rsnw_mlt = list(parameters.rsnw_melt.values)
else:
    rsnw_mlt = list(zeros+drsnw_mlt)

if 'rhoi' in perturb:
    rhoi = list(parameters.rhoi.values)
else:
    rhoi = list(zeros+drhoi)

if 'rhos' in perturb:
    rhos = list(parameters.rhos.values)
else:
    rhos = list(zeros+drhos)

if 'Cf' in perturb:
    Cf = list(parameters.Cf.values)
else:
    Cf = list(zeros+dCf)

#-----------------------------------------#
# 2. Set up an Icepack case
#-----------------------------------------#
# go to the Icepack directory
os.chdir(icepack_dir)

# setup a new case 
comd = './icepack.setup -c '+case_name+' -m '+machine+' -e '+compiler
os.system(comd)

#-----------------------------------------#
# 3. Build the case 
#-----------------------------------------#
# got into the case directory 
os.chdir(case_name)

# build the case 
comd = './icepack.build'
os.system(comd)

# check that the case was built correctly
storage_dir = scratch_dir + '/ICEPACK_RUNS/'+case_name
if os.path.exists(storage_dir) is False:
    AssertionError('Model did not build correctly! Please rebuild model or check your directory setups in the Icepack installation.')
else:
    print('Model with following perturbations has been built:', perturb)

#-----------------------------------------#
# 4. Begin cycling over each year 
#-----------------------------------------#
simulation_length = 8760
spinup_year = 1
while spinup_year <= spinup_length:
    spinup_year_str ='{0}'.format('%02d' % spinup_year) 
    print('Working on spinup year '+ spinup_year_str+'...')

    #-------------------------------------#
    # 5. Begin cycling through ensemble   
    #-------------------------------------#
    mem = 1
    while mem <= ensemble_size:
        inst_string ='{0}'.format('%04d' % mem) 
        print('Running member '+inst_string+'...')

        if spinup_year == 1:
            #create history and restart directories for the run
            os.chdir(storage_dir)
            os.makedirs('mem' + inst_string + '/history/')
            os.makedirs('mem' + inst_string + '/restart/')

            # link the model executable for each member to the main one built for the case
            os.symlink(storage_dir+'/icepack','mem' + inst_string+'/icepack')

            # set restart flag
            restart_flag = False
        else:
            restart_flag = True
            restart_file ='restart/iced.2012-01-01-00000.year'+spinup_year_str_prev+'.nc'
    
        # begin working on an individual ensemble member
        os.chdir(storage_dir+'/mem' + inst_string)

        # read namelist template
        namelist = f90nml.read(project_dir + '/data/templates/ICEPACK_input.nml.template')

        # set case settings 
        namelist['setup_nml']['year_init'] = 2011
        namelist['setup_nml']['npt'] = simulation_length
        namelist['setup_nml']['restart'] = restart_flag
        namelist['setup_nml']['runtype_startup'] = True
        namelist['setup_nml']['dumpfreq'] = 'y'
        if restart_flag is not True:
            namelist['setup_nml']['ice_ic'] = 'default'
        else:
            namelist['setup_nml']['restart_dir'] = './restart/'
            namelist['setup_nml']['ice_ic'] = restart_file

        # change namelist parameters of note
        namelist['thermo_nml']['ksno'] = ksno[mem-1]
        namelist['thermo_nml']['rhoi'] = rhoi[mem-1]
        namelist['shortwave_nml']['r_snw'] = R_snw[mem-1]
        namelist['shortwave_nml']['hi_ssl'] = hi_ssl[mem-1]
        namelist['shortwave_nml']['hs_ssl'] = hs_ssl[mem-1]
        namelist['shortwave_nml']['rsnw_mlt'] = rsnw_mlt[mem-1]
        namelist['snow_nml']['rhos']= rhos[mem-1]
        namelist['dynamics_nml']['Cf'] = Cf[mem-1]
        namelist['dynamics_nml']['dragio'] = dragio[mem-1]

        # set namelist forcing options
        namelist['forcing_nml']['data_dir'] = project_dir + '/data/forcings/'
        if 'atm' in perturb:
            namelist['forcing_nml']['atm_data_file'] = 'ATM_FORCING_'+inst_string+'.txt'
        else:
            namelist['forcing_nml']['atm_data_file'] = 'ATM_FORCING_0001.txt'
        if 'ocn' in perturb:
            namelist['forcing_nml']['ocn_data_file'] = 'OCN_FORCING_PERT_'+inst_string+'.txt'
        else:
            namelist['forcing_nml']['ocn_data_file'] = 'OCN_FORCING_'+inst_string+'.txt'
           
        # write namelist to needed file
        namelist.write('icepack_in',force=True)

        # run the member instance and dump output 
        comd = './icepack > icepack.out'
        os.system(comd)

        # check the output file for successful model completion
        check_finished = 'ICEPACK_COMPLETED SUCCESSFULLY'
        txt = open('icepack.out').readlines()
        if check_finished not in txt:
            AssertionError('Icepack did not run correctly! Process stopped.')
        else:
            print('Icepack ran successfully!')
    
        # check for restart files 
        files = glob.glob('restart/iced.2012-01-01-00000.nc')
        if len(files) == 0:
            AssertionError('Icepack did not correctly generate restart file! Process stopped.')
        else:
            comd = 'mv ./restart/iced.2012-01-01-00000.nc ./restart/iced.2012-01-01-00000.year'+spinup_year_str+'.nc'
            os.system(comd)
            comd = 'mv ./history/icepack.h.20110101.nc ./history/icepack.h.20110101.year'+spinup_year_str+'.nc'
            os.system(comd)
            print('restarts and history files renamed!')
    
        # advance to the next ensemble member 
        mem += 1
    
    # save the spinup_year_str to access the restart during the next spinup year
    spinup_year_str_prev = spinup_year_str
    
    # advance to the next spinup year
    spinup_year += 1

check_spinup = glob.glob(storage_dir + '/mem*/restart/iced.2012-01-01-00000.year'+spinup_year_str+'.nc')
# print(check_spinup)
if len(check_spinup) != ensemble_size:
    AssertionError('Spinup did not complete as expected. Some restarts are missing. Processed stopped.')
else:   
    print('PROCESS COMPLETE. Please check member directories.')