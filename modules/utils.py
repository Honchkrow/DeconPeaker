#!/usr/bin/env python
#title       : utils.py
#description : Helpful utilities for building analysis pipelines
#author      : Huamei Li
#date        : 29/05/2018
#type        : module
#version     : 2.7

#-----------------------------------------------------
# load python modules
   
import os
import sys
import pdb
import logging
import numpy as np
import pandas as pd
from scipy import stats
from collections import defaultdict
from operator    import itemgetter
from distutils.spawn import find_executable
from rpy2.robjects import r, pandas2ri

#----------------------------------------------------
# global setting

pandas2ri.activate()
pd.options.mode.chained_assignment = None # ignore warning generated by pandas
np.warnings.filterwarnings("ignore")
INFOS = defaultdict(lambda : defaultdict())
NARROWS_NAMES = ['chrom', 'start', 'end', 'name', 'score', \
        'strand', 'foldChange', 'pValue', 'qValue', 'summit2PeakDist']
UPDATE_NARROW_NAMES = NARROWS_NAMES + ['cellName', 'rawWidth']
CHROMS = [ 'chr{}'.format(x) for x in range(1, 23) ] 

#----------------------------------------------------

def log_infos():
    '''
    create a log to record the status of the program during operation
    :return: logging [object]

    '''
    logging.basicConfig(
            level    = 20,
            format   = '%(levelname)-5s @ %(asctime)s: %(message)s ',
            datefmt  = '%a, %d %b %Y %H:%M:%S',
            stream   = sys.stderr,
            filemode = 'w'
        )
           
    logging.warn  = logging.warning # function alias
    return logging

def create_tmp_files(fil_names=None, delete=False, fixnames=False, mode='w', tmpdir='tmp.deconPeaker'):
    '''
    create temporary files
    :param fil_names: [list] temporary file names, default: None
    :param delete: [bool] delete temporary file when closed
    :param mode: [str] write mode, default: w
    :param fixnames: [bool] random names generate by tempfile module or give fix name of the temporary files
    :param tmpdir: [str/dir] suffix name of temporary directory, default: .deconPeaker
    :reuturn: _fps [hanles in list] handles of temporary files
     
    '''
    import tempfile
    fil_names = fil_names if fil_names else ''
    names  = fil_names if isinstance(fil_names, list) else [ fil_names ]
    randon = [''.join(itemgetter(*np.random.choice(51, 25))(__import__('string').letters)) \
            for idx in xrange(len(names)) ]
    names  = [rand + name for name, rand in zip(names, randon) ]
    tmpdir = os.path.join(tempfile.gettempdir(), tmpdir)
    0 if os.path.exists(tmpdir) else os.mkdir(tmpdir) 
    if fixnames:
        _fps = [open(os.path.join(tmpdir, fil), 'w') for fil in names]
    else:
        _fps = [ tempfile.NamedTemporaryFile(suffix=fil, mode=mode, dir=tmpdir, delete=delete) for fil in names ]
    return _fps

def split_bins(tasks, nth):
    '''
    split the size of data into sections for multi-processes
    :param tasks: [list] total tasks of multi-processes
    :param nth: [int] number of threads
    :return: sub_tasks [list in list] the amount of tasks performed by each child process
     
    '''
    length = len(tasks)
    bin_size, sub_tasks = int(length / nth), []
    if length % nth: bin_size += 1
    for idx in xrange(nth):
        if idx != nth - 1:
            start, end = idx * bin_size, (idx + 1) * bin_size
        else:
            start, end = idx * bin_size, length
 
        if end > length: end = length
        tmp = tasks[start : end]
        sub_tasks.append(tmp if isinstance(tmp, list) else [ tmp ])
        if end >= length: break
    return sub_tasks

def multi_process(data_lst, func, nth, **kargs):
    '''
    multiple processing to handle data list
    :param data_lst: data list
    :param func: unified approach to the processing of various processes
    :param nth: processor number
    :return: tag_infos [list] returned results for all processors
      
    '''
    if nth > 1:
        sub_tasks = split_bins(data_lst, nth)
        pools = __import__('multiprocessing').Pool(nth)
        _func = __import__('functools').partial(func, **kargs)
        tag_infos = pools.map(_func, sub_tasks) # multiple processing
        pools.close(); pools.join()
        tag_infos = [subline for line in tag_infos for subline in line]
    else:
        tag_infos = func(data_lst, **kargs)
    return tag_infos

def doublecheck_files(filepaths):
    '''
    double check the file path is correct or not
    :param filepaths: [list] It is a list containing the file path to be detected
    :return: True/False [bool]
    
    '''
    filepaths = filepaths if isinstance(filepaths, list) else [ filepaths ]
    nonexists = [ path for path in filepaths if not os.path.exists(path) ]
    status = 1 if len(nonexists) else 0
    return status, nonexists

def create_dirs(dirpaths):
    '''
    create directory if if does not exist
    :param dirpaths: [str/list] directory pathes which neeo to be double check
    :return: 0

    '''
    status, nonexistdirs = doublecheck_files(dirpaths)
    if status:
        [ os.makedirs(path) for path in nonexistdirs ]
    return 0

def decomp_gzfile(filpathes):
    '''
    decompressed the files if gz as the suffix name
    :param filpathes: [list/str] file pathes
    :return: result_fils [list] decompressed file names
    
    '''
    result_fils = []
    filpathes   = filpathes if isinstance(filpathes, list) else [ filpathes ]
    for fil in filpathes:
        if not fil.endswith('.gz'):
            result_fils.append(fil)
            continue
        tmp_fil = create_tmp_files(fil.split(os.sep)[-1].rsplit('.gz', 1)[0], delete=False)[0].name
        cmd = 'gunzip -c {} > {}'.format(fil, tmp_fil)
        syscmd_run(cmd)
        result_fils.append(tmp_fil)
    return result_fils

def syscmd_run(cmd, rm=None):
    '''
    run system commands and check the status of the operation results
    :param cmd: [str] system command
    :param rm: [str] remove temporary file
    :return: 0
    
    '''
    ret = os.system(cmd)
    if ret: sys.exit(log_infos().error('{} excute error, exting....'.format(cmd)))
    if rm:
        os.remove(rm)
    return 0

def remove_files(*kargs):
    '''
    remove files
    :param kargs: [str] file path, variable parameter
    :return: 0
    
    '''
    [os.remove(kg) for kg in kargs]
    return 0

def catfiles(fil1, fil2, rm=None):
    '''
    append the contents of file1 to file2
    :param fil1: [str/file] file path
    :param fil2: [str/file] file path
    :param rm: [str/file] remove temporary file
    :return: 0
    
    '''
    cmd = 'cat {} >> {}'.format(fil1, fil2)
    syscmd_run(cmd, rm=rm)
    return 0

def sortfiles(fil1, fil2, rm=None, tbidx=True):
    '''
    sort the file contents and save the results into file2
    :param fil1: [str/file] file path
    :param fil2: [str/file] file path
    :param rm: [str/file] remove temporary file
    :param txidx: [bool] tab index the sorted file
    :return: 0
    
    '''
    cmd = 'sort -k1V -k2n -k3n {0} > {1}'.format(fil1, fil2)
    syscmd_run(cmd, rm=rm)
    return 0

def detect_gzip(filename):
    '''
    detect gzip compressed file
    :param filename: [str/file] the name of the file to be detected
    :return: func [function] open function

    '''
    func = __import__('gzip').open if filename.endswith('.gz') else open
    return func

def mk_dir(dirpath, subpath=None):
    '''
    make directory if not exists
    :param dirpath: [str] directory path
    :param subpath: [str] sub directory path, default: None
    :return: outdir [str] finally directory path
    
    '''
    outdir = os.path.join(dirpath, subpath) if subpath else dirpath
    0 if os.path.exists(outdir) else os.makedirs(outdir)
    return outdir

def rewrite_yaml(peaks, counts=None, outdir=None):
    '''
    re-write mixture sample infos as YAML format file
    :param peaks: [list] non-redundant peak list files
    :param counts: [list] read counts of each mixture sample of peaks, default: None
    :param outdir: [str/dir] output directory, default: None
    :return: 0
    
    '''
    counts = counts if counts else ['None'] * len(peaks)
    assert len(counts) == len(peaks)

    infos_hash = { 'Sample_{}'.format(idx) : {'peak': [], 'count': [], 'label': None} for idx in xrange(len(peaks)) }
    for idx, sn in enumerate(infos_hash):
        label = os.path.basename(peaks[idx]).split('mixed_profile.xls')[0]
        infos_hash[sn]['peak']  = peaks[idx]
        infos_hash[sn]['count'] = counts[idx]
        infos_hash[sn]['label'] = label
    
    outfile = os.path.join(outdir, 'mixture_yaml_preprocessed.yaml')
    with open(outfile, 'w') as fp:
        __import__('yaml').dump(infos_hash, fp, default_flow_style=False)
    return 0

def dict2pd(dtahash, indexes, transpose=True):
    '''
    convert dictionary into pandas dataframe
    :param dtahash: [dict] dictionary data struct
    :param indexes: [list] index names
    :param transpose: [bool] transpose dataframe or not, default: True
    :return: df [pd.dataframe]
    
    '''
    columns, df = dtahash.keys(), []
    for sn, values in dtahash.iteritems():
        if not df: df = [ [] for idx in  xrange(len(values)) ]
        for idx, label in enumerate(indexes):
            vv = values[label]
            tmp = str(vv) if not isinstance(vv, list) else ','.join(map(str, vv))
            df[idx].append(tmp)
    df = pd.DataFrame(df, columns=columns, index=indexes)
    return df.T if transpose else df

def merge_bams(bams, prefix, outdir='./', threads=4):
    '''
    merge bam files into one and then sort
    :param bams: [list] bam files which need to be merged
    :param prefix: [str] prefix name of the merged file
    :param outdir: [str/dir] output directory, default: ./
    :param threads: [int] number of threads, default: 4
    :return: merged_bam [str/file]
    
    '''
    mk_dir(outdir)	
    merged_bam = os.path.join(outdir, prefix + '.bam')
    cmd_merge  = 'samtools merge -f {} -@ {} {}'.format(merged_bam, threads,' '.join(bams))
    cmd_sort   = 'samtools index {}'.format(merged_bam)
    syscmd_run(cmd_merge); syscmd_run(cmd_sort)
    return merged_bam

def countspd2dict(df, phenotype):
    '''
    parse replicate lables and return positions
    :param df: [pd.DataFrame] readcounts of peaks
    :param phenotype: [pd.DataFrame] phenotype classes of all samples
    :return dfhash [dict] && cellpos [list]
    
    '''
    dfhash, colnames, cellpos = defaultdict(), df.columns, defaultdict()
    for cell in phenotype.index:
        positions = np.where(phenotype.loc[cell] == 1)[0]
        dfhash[cell]  = df[colnames[positions]]
        cellpos[cell] = positions
    return dfhash, cellpos

def write_phenotype_file(sninfos, outfile):
    '''
    write phenotype informative into file
    :param sninfos: [pd.DataFrame] sample info dataframe
    :param outfile: [str/file] output file name
    :return: 0
    
    '''
    (nrows, ncols), results = sninfos.shape, []
    cellnames = sninfos['CELL'].unique()
    
    for cell in cellnames:
        subclass = np.ones(nrows) * 2
        postions = np.where(sninfos['CELL'] == cell)[0]
        subclass[postions] = 1
        results.append(subclass)
    
    df = pd.DataFrame(results, index=cellnames).astype(int)
    df.to_csv(outfile, sep='\t', header=False, index=True)
    return 0

def merged_replicates(profile, phenotype, method='mean'):
    '''
    merge replicates profile of pure cells
    :parma profile: [pd.DataFrame] pure sample profile
    :param phenotype: [pd.DataFrame] Phenotype classes file
    :param method: [str] merge method, default: mean
    :return: merged_profile [pd.DataFrame] merged profile
     
    '''
    colnames = profile.columns
    fields, merged_profile = profile.columns[3 : ], []

    for cell, row in phenotype.iterrows():
        idx  = np.where(row == 1)[0] + 3
        func = np.mean if method == 'mean' else np.median
        merged_profile.append(func(profile[colnames[idx]], axis=1))
    
    merged_profile = pd.DataFrame(
            np.array(merged_profile).T, 
            columns=phenotype.index, 
            index=profile.index
        )
    merged_profile = pd.concat([profile[['chrom', 'start', 'end']], merged_profile], axis=1)
    return merged_profile

def is_logscale(X):
    '''
    check log2 transform or not
    :param X: [pd.DataFrame] data need to be check
    :return: logc [bool]
    
    '''
    X = X.values.flatten()
    qx = np.percentile(X, [0, 25, 50, 75, 99, 100])
    logc = qx[4] >= 100 or (qx[5] - qx[0] >= 50 and qx[1] >= 0) or (qx[1] >= 0 and qx[1] <= 1 and qx[3] >= 1 and qx[3] <= 2)
    return (not logc)

def load_profile(tablefiles, lib_strategy):
    '''
    load profile based on specified library strategy
    :param tablefiles: [list/files] data file names that need to be loaded
    :param lib_strategy: [str] a string indicating the type of the profile measurements
    :return: loaded data [pd.DataFrame]
    
    '''
    loaded_data, labels, pesudo_infos = [], ['chrom', 'start', 'end'], ['-', 999, 999]
    tablefiles = tablefiles if isinstance(tablefiles, list) else [tablefiles]    
    
    if lib_strategy == 'ATAC-Seq':
        loaded_data = [ pd.read_csv(fil, sep='\t', header=0) for fil in tablefiles ]
    else:
        for fil in tablefiles:
            df = pd.read_csv(fil, sep='\t', header=0, index_col=0)
            [ df.insert(idx, value=pesudo_infos[idx], column=name) for idx, name in enumerate(labels) ]
            loaded_data.append(df)
    
    for idx, data in enumerate(loaded_data):
        fields = data.columns[3 : ]
        loaded_data[idx][fields] = loaded_data[idx][fields].fillna(0)
        logc = is_logscale(data[fields])
        if logc: loaded_data[idx][fields] = 2 ** data[fields]
        loaded_data[idx] = loaded_data[idx][~loaded_data[idx].index.duplicated(keep='first')]
    return loaded_data if len(loaded_data) > 1 else loaded_data[0]

def load_phenotypes(phenotypes_file):
    '''
    load phnotype classes and check each pure cell samples has replicates or not
    :param phenotypes_file: [pd.DataFrame] phenotype classes file
    :return: phenotypes [pd.DataFrame]
    
    '''
    phenotypes = pd.read_csv(phenotypes_file, sep='\t', header=0, index_col=0)
    colnames   = phenotypes.columns
    if '1' in colnames and '2' in colnames:
        phenotypes = pd.read_csv(phenotypes_file, sep='\t', header=None, index_col=0)
    else:
        pass
    
    tmpsum = (np.sum(phenotypes == 1, axis=1) >= 2).all()
    if not tmpsum:
        log_infos.error('Each pure cell samples require replicates, exiting......')
    else:
        return phenotypes

def intersect(mixprofile, sigprofile, lib_strategy):
    '''
    take the intersection of the mixed profile and the pure cell profile peaks/genes/probes
    :param mixprofile: [pd.DataFrame] mixed samples profile
    :param sigprofile: [pd.DataFrame] signature peaks/genes/probes profile
    :param lib_strategy: [str] a string indicating the type of the profile measurements
    :return: sub_intersect_data

    '''
    if lib_strategy == 'ATAC-Seq':
        mix_first3cols, sig_first3cols = mixprofile.columns[0 : 3], sigprofile.columns[0 : 3]
        mixprofile.index = mixprofile[mix_first3cols[0]].str.cat(mixprofile[mix_first3cols[1 : ]].astype(str), sep='_')
        sigprofile.index = sigprofile[sig_first3cols[0]].str.cat(sigprofile[sig_first3cols[1 : ]].astype(str), sep='_')
    
    commom_index = set(mixprofile.index) & set(sigprofile.index)
    mixprofile, sigprofile = mixprofile.loc[commom_index], sigprofile.loc[commom_index]
    return [mixprofile, sigprofile]

def get_line_number(fil):
    '''
    get line number of the file
    :param fil: [str/file] target file name
    :return: counts [int]
		
    '''
    with open(fil, 'rb') as fp:
	for count, line in enumerate(fp): pass
    return count

def matlab_engine():
    '''
    check matlab engine exists or not
    :return: 0

    '''
    mat_path = find_executable('matlab')
    if not mat_path:
        sys.exit(log_infos.error('Matlab cannot be detected in the system, exiting...'))
    else:
        try:
            import matlab.engine
        except ImportError:
            engine_path = os.path.join(mat_path.rsplit(os.sep, 2)[0], 'extern/engines/python/')
            os.system('cd {} && python setup.py install'.format(engine_path))
        finally:
            try:
                import matlab.engine
            except ImportError:
                sys.exit(log_infos.error('metlab.engine cannot be imported, exiting...'))
    return matlab.engine

