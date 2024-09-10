#!/bin/bash --login

#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --time=50:00:00
#SBATCH --partition=blanca-shirts
#SBATCH --qos=blanca-shirts
#SBATCH --account=blanca-shirts
#SBATCH --gres=gpu
#SBATCH --job-name=sfe_test_mix1_test6
#SBATCH --output=slurm_codes/sfe_test_mix1_test6.log

module purge
module avail
ml anaconda
conda activate old-evaluator-test7

python sfe_test.py
echo "It finished"

sacct --format=jobid,jobname,cputime,elapsed