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

case = 'VIC_f1_NORM_catwise'
free_case = 'free_SHEBA'
dart_dir = '/glade/work/mollyw/dart_manhattan/'
filter_kind = 1
postprocessing = 'cice'
obs_type = ['SAT_SEAICE_VICE01','SAT_SEAICE_VICE02','SAT_SEAICE_VICE03','SAT_SEAICE_VICE04','SAT_SEAICE_VICE05']
# obs_type = ['SAT_SEAICE_AGREG_THICKNESS']#, 'SAT_SEAICE_AGREG_CONCENTR']
cat_assim = True 
first_assim_date = datetime(int(sys.argv[1]),int(sys.argv[2]),int(sys.argv[3]))
end_assim_date = datetime(int(sys.argv[4]),int(sys.argv[5]),int(sys.argv[6]) )

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

def unpack_categories(file):

    # data_vars = ['aicen','vicen','vsnon']
    ncat = 5
    encd = {'aice01': {'_FillValue': None},
            'aice02': {'_FillValue': None},
            'aice03': {'_FillValue': None},
            'aice04': {'_FillValue': None},
            'aice05': {'_FillValue': None},
            'vice01': {'_FillValue': None},
            'vice02': {'_FillValue': None},
            'vice03': {'_FillValue': None},
            'vice04': {'_FillValue': None},
            'vice05': {'_FillValue': None},
            'vsno01': {'_FillValue': None},
            'vsno02': {'_FillValue': None},
            'vsno03': {'_FillValue': None},
            'vsno04': {'_FillValue': None},
            'vsno05': {'_FillValue': None}}

    ds = xr.open_dataset(file)
    os.rename(file, file+'~')
    # ds = ds[data_vars]

    for n in range(1,ncat+1):
        ds['aice'+'{:02}'.format(n)]=ds.aicen.isel(ncat=n-1)
        ds['vice'+'{:02}'.format(n)]=ds.vicen.isel(ncat=n-1)
        ds['vsno'+'{:02}'.format(n)]=ds.vsnon.isel(ncat=n-1)
        
    # ds=ds.drop(data_vars)

    ds.to_netcdf(file, encoding=encd)  
    
    return len(ds.variables)

def repack_categories(file):

    ncat = 5
    expanded_vars=[]
    for n in range(1,ncat+1):
        expanded_vars.append('vice'+'{:02}'.format(n))
        expanded_vars.append('aice'+'{:02}'.format(n))
        expanded_vars.append('vsno'+'{:02}'.format(n))

    encd = {'aicen': {'_FillValue': None},
            'vicen': {'_FillValue': None},
            'vsnon': {'_FillValue': None}}
            
    ds = xr.open_dataset(file)
    os.rename(file, file+'~')
    aicen=np.zeros((ncat,4))
    vicen=np.zeros((ncat,4))
    vsnon=np.zeros((ncat,4))
    
    for n in range(1,ncat+1):
        aicen[n-1,:]=ds['aice'+'{:02}'.format(n)].values
        vicen[n-1,:]=ds['vice'+'{:02}'.format(n)].values
        vsnon[n-1,:]=ds['vsno'+'{:02}'.format(n)].values
    
    ds['aicen']=xr.DataArray(data=aicen, dims=['ncat','ni'])
    ds['vicen']=xr.DataArray(data=vicen, dims=['ncat','ni'])
    ds['vsnon']=xr.DataArray(data=vsnon, dims=['ncat','ni'])

    ds=ds.drop(expanded_vars)
    ds.to_netcdf(file, mode= 'w', encoding=encd)

    os.remove(file+'~')

    return len(ds.variables)


def cycle_da(case, free_case, dart_dir, filter_kind, assim_date, cat_obs = False):

    case_dir  = '/glade/scratch/mollyw/ICEPACK_RUNS/'+case+'/'
    assim_dir = '/glade/scratch/mollyw/ICEPACK_RUNS/assim_dir/'+case+'/'
    free_dir  = '/glade/scratch/mollyw/ICEPACK_RUNS/'+free_case+'/'

    if cat_obs is False:
        obs_dir = '/glade/work/mollyw/DA_obs/ICEPACK_OBS/'+free_case+'/eakf_vs_brhf/mem_14/bc_obs/'
        state_variables = ['aicen', 'QTY_SEAICE_CONCENTR'       , 'UPDATE',
                           'vicen', 'QTY_SEAICE_VOLUME'         , 'UPDATE',
                           'vsnon', 'QTY_SEAICE_SNOWVOLUME'     , 'UPDATE'] 
    else:
        obs_dir = '/glade/work/mollyw/DA_obs/ICEPACK_OBS/'+free_case+'/eakf_vs_brhf/mem_14/bc_obs/itd/'
        state_variables = ['vice01', 'QTY_SEAICE_VICE01'        , 'UPDATE',
                           'vice02', 'QTY_SEAICE_VICE02'        , 'UPDATE',
                           'vice03', 'QTY_SEAICE_VICE03'        , 'UPDATE',
                           'vice04', 'QTY_SEAICE_VICE04'        , 'UPDATE',
                           'vice05', 'QTY_SEAICE_VICE05'        , 'UPDATE',
                           'vsno01', 'QTY_SEAICE_VSNO01'        , 'UPDATE',
                           'vsno02', 'QTY_SEAICE_VSNO02'        , 'UPDATE',
                           'vsno03', 'QTY_SEAICE_VSNO03'        , 'UPDATE',
                           'vsno04', 'QTY_SEAICE_VSNO04'        , 'UPDATE',
                           'vsno05', 'QTY_SEAICE_VSNO05'        , 'UPDATE',
                           'aice01', 'QTY_SEAICE_AICE01'        , 'UPDATE',
                           'aice02', 'QTY_SEAICE_AICE02'        , 'UPDATE',
                           'aice03', 'QTY_SEAICE_AICE03'        , 'UPDATE',
                           'aice04', 'QTY_SEAICE_AICE04'        , 'UPDATE',
                           'aice05', 'QTY_SEAICE_AICE05'        , 'UPDATE']

    truth_member = 14

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
    shutil.copy(dart_dir + '/models/cice-scm2/cross_correlations.txt', 'cross_correlations.txt')
    # shutil.copy(dart_dir + '/models/cice-scm2/control_impact_runtime.txt', 'control_impact_runtime.txt')  
    shutil.copy(dart_dir + '/models/cice-scm2/work/cice.r.nc', '.')
    shutil.copy(dart_dir + '/models/cice-scm2/work/dart_to_cice', '.')
    shutil.copy(dart_dir + '/assimilation_code/programs/gen_sampling_err_table/work/sampling_error_correction_table.nc', '.')
    restarts_in_list = open(assim_dir + 'cice_restarts_in.txt', 'w')
    restarts_out_list = open(assim_dir + 'cice_restarts_out.txt', 'w')

    # if necessary, unpack cice.r.nc
    if cat_obs is True:
        null = unpack_categories('cice.r.nc')

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
            restarts_in_list.writelines('mem'+inst_string+'/pre_filter_restart.nc \n')
            restarts_out_list.writelines('mem'+inst_string+'/post_filter_restart.nc \n')
            comd = 'cp ' + case_dir + '/mem'+inst_string+'/restart/iced.'+date_str+'-00000.nc pre_filter_restart.nc'

        os.system(comd)

        # unpack categories if necessary
        if cat_obs is True:
            if mem != truth_member:
                null = unpack_categories('pre_filter_restart.nc')
        
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
    nml_file['model_nml']['model_state_variables'] = state_variables
    nml_file['dart_to_cice_nml']['postprocess'] = postprocessing
    nml_file['obs_impact_tool_nml']['input_filename'] = 'cross_correlations.txt'
    nml_file['obs_impact_tool_nml']['output_filename'] = 'control_impact_runtime.txt'
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
            # Save the restart and state files from the assimilation
            shutil.copy('pre_filter_restart.nc', case_dir+'/analyses/'+date_str+'/pre_filter_restart_'+inst_string+'.nc')
            shutil.copy('post_filter_restart.nc', case_dir+'/analyses/'+date_str+'/post_filter_restart_'+inst_string+'.nc')
            shutil.copy('../input.nml', '.')

            # generate a copy of the pre_filter file that will become the postprocessed file 
            shutil.copy('pre_filter_restart.nc', 'postprocessed_restart.nc')

            # repack the post_filter_restart.nc file if necessary
            if cat_obs is True:
                null = repack_categories('post_filter_restart.nc')
            
            # Run dart_to_cice postprocessing
            # os.symlink(assim_dir+'/dart_to_cice','dart_to_cice')
            comd = assim_dir + '/dart_to_cice > output.dart_to_cice'
            os.system(comd)
            upst_status = check_completion('output.dart_to_cice')
            if upst_status < 0:
                print('dart_to_cice did not finish correctly. Process stopping.')
                sys.exit()
        
            # Save the post-processed restart file in the analyses folder
            shutil.copy('postprocessed_restart.nc', case_dir+'/analyses/'+date_str+'/postprocessed_restart_'+inst_string+'.nc')
            # Replace the restart file in the case directory 
            shutil.move('postprocessed_restart.nc', case_dir+'/mem'+inst_string+'/restart/iced.'+date_str+'-00000.nc')

            # Remove process-specific files 
            os.remove('pre_filter_restart.nc')
            os.remove('post_filter_restart.nc')
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

datelist = pd.date_range(start = first_assim_date, end = end_assim_date).to_pydatetime()
start = perf_counter()

for date in datelist:
    cycle_da(case, free_case, dart_dir, filter_kind, date, cat_obs=cat_assim)

end = perf_counter()
print(f'Execution time was {(end - start)/60:0.4f} minutes')
    