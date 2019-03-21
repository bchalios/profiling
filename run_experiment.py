import argparse
import json
import os
import sys
import itertools

from experiment import ExperimentClusters

def get_bsc_machine():
    """Returns a string with the BSC machine name"""
    return os.environ['BSC_MACHINE']

def create_results_directory(machine, experiment_type, prog_model):
    """Creates (if not existing) the results directory and returns the name"""
    
    resdir = 'results/{0}/{1}/{2}'.format(machine, experiment_type, prog_model)
    try:
        os.makedirs(resdir)
    except OSError:
        if not os.path.isdir(resdir):
            raise

    return resdir

def parse_json(json_file):
    """Parse the json file describing the experiment"""
    with open(json_file, "r") as fh:
        params = json.load(fh)
        return params

def create_experiment_ompss(path, arguments, repetitions, resdir, jobname, machine):
    """Create and return an ExperimentClusters object"""
    return ExperimentClusters(path, arguments, repetitions, resdir, jobname, machine)

def create_experiment(model, path, arguments, repetitions, resdir, jobname, machine):
    """Create the correct type of experiment object depending on the model"""
    if model == "ompss":
        return create_experiment_ompss(path, arguments, repetitions, resdir, jobname, machine)
    else:
        print("Programming model: {0} not supported".format(model))
        sys.exit(0)
    
def parse_cmd_line():
    """Setup command line parser and return object with parsed arguments"""
    parser = argparse.ArgumentParser(description="Automated job sumbission tool")
    parser.add_argument('--scheduler', default='cluster-locality', help='Nanos6 scheduler')
    parser.add_argument('--cpu-scheduler', default='default', help='Nanos6 CPU scheduler')
    parser.add_argument('--runtime', default='optimized', help='Nanos6 flavour')
    parser.add_argument('json', metavar='json_file', type=str)

    args = parser.parse_args()
    return args

def run_campaign(bench, conf, hw, exp_type, repetitions, debug, resdir, args):
    """Run an experiment campaign"""
    
    machine = get_bsc_machine()

    #Our hardware configuration is a tuple of nodes x CPUs
    nodes_cpus = []
    if hw['cartesian']:
        nodes_cpus = itertools.product(hw['nodes'], hw['cpus'])
    else:
        nodes_cpus = zip(hw['nodes'], hw['cpus'])
        
    for hw_conf in nodes_cpus:
        nodes = hw_conf[0]
        cpus = hw_conf[1]
        
        #prefix the binary with 'taskset', we need to fix that within the
        #Experiment module
        cmd = 'taskset -c 0-{0} {1}'.format(cpus - 1, bench['path'])
        
        # jobname is in the form: benchname_args_nrnodes
        jobname = '{0}_{1}_{2}'.format(bench['name'], '_'.join(conf['args']), nodes)
        experiment = create_experiment(bench['programming_model'], cmd,
                                conf["args"], repetitions, resdir, jobname,
                                machine) 
        
        #Setup the hardware-independent parameters of the experiment
        experiment.set_stdout('{0}/{1}.out'.format(resdir, jobname))
        experiment.set_stderr('{0}/{1}.err'.format(resdir, jobname))
        experiment.set_job_minutes(conf['time_limit_minutes'])
        experiment.set_mem_distributed(conf['distributed_memory'])
        experiment.set_mem_local(conf['local_memory'])
        experiment.set_debug_job(debug)
        experiment.set_runtime(args.runtime)
        experiment.set_scheduler(args.scheduler)
        experiment.set_cpu_scheduler(args.cpu_scheduler)
                
        """
        We have to hardcode this, because we do not have an easy way to
        define a proper cpuset from outside the job and we want to run
        exclusively.
        """
        experiment.set_cpus_per_task(48)
        
        # Setup hardware-specific parameters
        experiment.set_nrnodes(nodes)

        # At the moment we run with one process per node only 
        experiment.set_nrtasks(nodes)

        experiment.run_experiment()
        
def main():
    args = parse_cmd_line()
    params = parse_json(args.json)

    exp_conf = params['experiment']
    hw_conf = exp_conf['hardware']
    bench = params['benchmark']
    machine = get_bsc_machine()
    resdir = create_results_directory(machine, exp_conf['type'], bench['programming_model'])

    for conf in exp_conf['configurations'] :
        run_campaign(bench, conf, hw_conf, exp_conf['type'], exp_conf['repetitions'],
                    exp_conf['debug'], resdir, args)
        

if __name__ == "__main__":
    main()
