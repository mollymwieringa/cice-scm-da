###############################################################
## THIS CODE IS UNDER DEVELOPMENT! DO NOT USE! (10/13/2022   ##
###############################################################
# All we need to do to get started with assimilating is to 
# adjust the restart files from the corresponding free 
# ensemble and then use those restart files to intialize the 
# next forecast cycle.
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
import shutil

from datetime import datetime, timedelta
from time import sleep, perf_counter
import pandas as pd

###############################################################
## SET MANUAL INPUTS HERE                                    ##
###############################################################

case = 'da_1cycle_sit_ksno_dec'
free_case = 'free_ksno_pet'
dart_dir = '/glade/work/mollyw/dart_manhattan/'
filter_kind = 1
obs_type = 'SAT_SEAICE_AGREG_THICKNESS'
first_assim_date = datetime(int(sys.argv[1]),int(sys.argv[2]),int(sys.argv[3]))

###############################################################
## DEFINE HELPER FUNCTIONS                                   ##
###############################################################
def check_completion(file_string): 
    txt = open(file_string).readlines()
    if 'icepack' in file_string:
        check = 'ICEPACK COMPLETED SUCCESSFULLY\n'
    else:
        check = ' Finished ... at YYYY MM DD HH MM SS = \n'

    if  check not in txt:
      print('Process did not finish correctly')
      status = -1
    else:
    #   os.system('rm '+file_string)
      status = 0

    return status


def cycle_da(case, free_case, dart_dir, filter_kind, assim_date):

    case_dir  = '/glade/scratch/mollyw/ICEPACK_RUNS/'+case+'/'
    assim_dir = '/glade/scratch/mollyw/ICEPACK_RUNS/assim_dir/'+case+'/'
    free_dir  = '/glade/scratch/mollyw/ICEPACK_RUNS/'+free_case+'/'
    obs_dir = '/glade/work/mollyw/DA_obs/ICEPACK_OBS/'+free_case+'/brhf_exps/'

    truth_member = 24

    # Get date information
    year = assim_date.year
    mon = assim_date.month
    day = assim_date.day
    date_str = '{0}'.format('%04d'%year) + '-{0}'.format('%02d'%mon) + '-{0}'.format('%02d'%day)
    next_day = assim_date + timedelta(days = 1)
    next_day_str = '{0}'.format('%04d'%next_day.year) + '-{0}'.format('%02d'%next_day.month) + '-{0}'.format('%02d'%next_day.day) 

    # Move to assimilation directory
    if os.path.exists(assim_dir) is False:
        os.makedirs(assim_dir)
    else: 
        print('Assimilation directory already exists!')      
    os.chdir(assim_dir)
    shutil.copy(dart_dir + '/models/cice-scm2/work/filter', '.')
    shutil.copy(dart_dir + '/models/cice-scm2/input.nml.template', 'input.nml')
    shutil.copy(dart_dir + '/models/cice-scm2/work/cice.r.nc', '.')
    shutil.copy(dart_dir + '/models/cice-scm2/work/dart_to_cice', '.')
    shutil.copy(dart_dir + '/assimilation_code/programs/gen_sampling_err_table/work/sampling_error_correction_table.nc', '.')
    restarts_in_list = open(assim_dir + 'cice_restarts_in.txt', 'w')
    restarts_out_list = open(assim_dir + 'cice_restarts_out.txt', 'w')

    # Set up directory
    ensemble_size = len(glob.glob('/glade/scratch/mollyw/ICEPACK_RUNS/'+free_case+'/mem*'))
    mem = 1
    while mem <= ensemble_size:
    
        # make a subdirectory for each ensemble member
        inst_string = '{0}'.format('%04d'%mem)
        if os.path.exists(assim_dir + '/mem'+inst_string+'/') is False: 
            os.makedirs(assim_dir + '/mem'+inst_string+'/')

        os.chdir(assim_dir + '/mem'+inst_string+'/')

        if mem == truth_member:
            comd = 'cp ' + case_dir + '/mem'+inst_string+'/restart/iced.'+date_str+'-00000.nc truth_data.nc'
        else:
            restarts_in_list.writelines('mem'+inst_string+'/dart_restart.nc \n')
            restarts_out_list.writelines('mem'+inst_string+'/restart_state.nc \n')
            comd = 'cp ' + case_dir + '/mem'+inst_string+'/restart/iced.'+date_str+'-00000.nc dart_restart.nc'
        
        os.system(comd)
        os.chdir('../')
        mem += 1

    restarts_in_list.close()
    restarts_out_list.close()
    os.symlink(obs_dir + '/obs_seq.{0}{1}{2}'.format('%04d'%year, '%02d'%mon, '%02d'%day), 'obs_seq.out')

    # Set filter namelist settings 
    nml_file = f90nml.read('input.nml')
    nml_file['filter_nml']['ens_size'] = ensemble_size-1
    nml_file['filter_nml']['num_output_state_members'] = ensemble_size-1
    nml_file['filter_nml']['num_output_obs_members'] = ensemble_size-1
    nml_file['obs_kind_nml']['assimilate_these_obs_types'] = obs_type
    nml_file['assim_tools_nml']['filter_kind'] = filter_kind
    nml_file['assim_tools_nml']['cutoff'] = 100000.0
    nml_file.write('input.nml', force=True)

    # Run the filter
    print('Running the filter for '+date_str+'...')
    comd = './filter > output.filter'
    os.system(comd)
    filt_status = check_completion('output.filter')
    if filt_status < 0:
        print('filter did not complete correctly. Process stopping.')
        sys.exit()

    # Move filter output to case directory
    os.makedirs(case_dir + '/analyses/'+date_str+'/')
    os.makedirs(case_dir + '/forecasts/'+date_str+'/')
    os.makedirs(case_dir + '/output_files/'+date_str+'/')
    shutil.move('output.filter', case_dir + '/output_files/'+date_str+'/')
    # shutil.move('regression_data.txt', case_dir + '/output_files/'+date_str+'/')
    # shutil.move('obs_inc_data.txt', case_dir + '/output_files/'+date_str+'/')
    os.remove('obs_seq.out')

    comd = 'mv input_*.nc ' + case_dir+ '/output_files/'+date_str+'/'
    os.system(comd)
    sleep(2)
    comd = 'mv preassim_*.nc ' + case_dir+ '/output_files/'+date_str+'/'
    os.system(comd)
    sleep(2)
    comd = 'mv analysis_*.nc ' + case_dir+ '/output_files/'+date_str+'/'
    os.system(comd)
    sleep(2)
    comd = 'mv output_*.nc ' + case_dir+ '/output_files/'+date_str+'/'
    os.system(comd)
    sleep(2)
    comd = 'mv *_forward_ope_errors* ' + case_dir+ '/output_files/'+date_str+'/'
    os.system(comd)
    shutil.move('obs_seq.final', case_dir+ '/output_files/'+date_str+'/')

    # Do manual post assimilation processes
    mem = 1
    while mem <= ensemble_size:
        inst_string = '{0}'.format('%04d'%mem) 

        # Do everything assimilation related in the assim_dir member directories 
        os.chdir(assim_dir+'/mem'+inst_string+'/')
        if mem == truth_member:
            # print('Formatting truth member file...')
            # Save the truth data
            shutil.copy('truth_data.nc', case_dir+'/analyses/'+date_str+'/truth_data_'+inst_string+'.nc' )
            # Put the truth restart back into the case directory
            shutil.move('truth_data.nc', case_dir+'/mem'+inst_string+'/restart/iced.'+date_str+'-00000.nc')
        else:
            # print('Handling member number '+inst_string)
            # Save the restart and state files from the assimilation
            shutil.copy('dart_restart.nc', case_dir+'/analyses/'+date_str+'/dart_restart_'+inst_string+'.nc')
            shutil.copy('restart_state.nc', case_dir+'/analyses/'+date_str+'/restart_state_'+inst_string+'.nc')
            shutil.copy('../input.nml', '.')
    
            # Run dart_to_cice postprocessing
            # os.symlink(assim_dir+'/dart_to_cice','dart_to_cice')
            comd = assim_dir + '/dart_to_cice > output.dart_to_cice'
            os.system(comd)
            upst_status = check_completion('output.dart_to_cice')
            if upst_status < 0:
                print('dart_to_cice did not finish correctly. Process stopping.')
                sys.exit()
        
            # Save the post-processed restart file in the analyses folder
            shutil.copy('dart_restart.nc', case_dir+'/analyses/'+date_str+'/iced.'+date_str+'-00000_'+inst_string+'.nc')
            # Replace the restart file in the case directory 
            shutil.move('dart_restart.nc', case_dir+'/mem'+inst_string+'/restart/iced.'+date_str+'-00000.nc')

            # Remove process-specific files 
            os.remove('restart_state.nc')
            os.remove('output.dart_to_cice')
    
        # Move to the case directory member folder to run the model forward 
        os.chdir(case_dir+'/mem'+inst_string+'/')

        # Edit the namelist file in order to run a forecast with icepack
        icepack_nml = f90nml.read('icepack_in')
        icepack_nml['setup_nml']['ice_ic'] = case_dir + '/mem'+inst_string+'/restart/iced.'+date_str+'-00000.nc'
        icepack_nml['setup_nml']['npt'] = 24
        icepack_nml['setup_nml']['runtype_startup'] = False
        icepack_nml.write('icepack_in', force=True)

        # Run Icepack
        comd = './icepack > icepack.out'
        os.system(comd)
        sleep(2)

        if os.path.exists('restart/iced.'+next_day_str+'-00000.nc') is False:
            print('icepack did not create necessary restart file! Process stopping.')
            sys.exit()

        # Clean up 
        shutil.copy('history/icepack.h.{0}{1}{2}'.format('%04d'%year, '%02d'%mon, '%02d'%day)+'.nc', case_dir+'/forecasts/'+date_str+'/icepack.h.'+date_str+'_'+inst_string+'.nc')
        shutil.move('ice_diag.full_ITD', case_dir+'/forecasts/'+date_str+'/ice_diag.full_ITD_'+inst_string)
        os.remove('icepack.out')
        comd = 'rm ice_diag.*'
        os.system(comd)

        # Advance to the next member
        mem += 1 

    print('Done cycling '+case+' for '+date_str+'...')
    # end = perf_counter()

    # print(f'Execution time was {end - start:0.4f} seconds')
    return

###############################################################
## PERFORM CYCLING- DO NOT EDIT BELOW THIS LINE              ##
###############################################################

start = perf_counter()

# cycle da for the date in question
cycle_da(case, free_case, dart_dir, filter_kind, first_assim_date)

# forecast icepack forward from there
forecast_date = first_assim_date + timedelta(days=1)
year = forecast_date.year
month = forecast_date.month
day = forecast_date.day
simulation_length = 8760-1
ensemble_size = 30

mem = 1
while mem <= ensemble_size:
    inst_string ='{0}'.format('%04d' % mem) 
    print('Running member '+inst_string+'...')
    os.chdir('/glade/scratch/mollyw/ICEPACK_RUNS/'+case+'/mem' + inst_string)
    
    restart_file = '/glade/scratch/mollyw/ICEPACK_RUNS/'+case+'/mem'+inst_string+'/restart/iced.{0}-{1}-{2}-00000.nc'.format('%04d'%year, '%02d'%month, '%02d'%day)
    
    # read namelist template
    namelist = f90nml.read('icepack_in')

    # set case settings 
    namelist['setup_nml']['npt'] = simulation_length
    namelist['setup_nml']['dumpfreq'] = 'd'
    namelist['setup_nml']['ice_ic'] = restart_file
  
    # write namelist to needed file
    namelist.write('icepack_in',force=True)

    # run the member instance and dump output 
    comd = './icepack > icepack.out'
    os.system(comd)

    # check the output file for successful model completion
    check_finished = 'ICEPACK COMPLETED SUCCESSFULLY'
    txt = open('icepack.out').readlines()
    if check_finished not in txt:
        AssertionError('Icepack did not run correctly! Process stopped.')
    else:
        print('Icepack ran successfully!')
    
    # advance to the next ensemble member 
    mem += 1

end = perf_counter()
print(f'Execution time was {(end - start)/60:0.4f} minutes')
    