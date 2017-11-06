#!/usr/bin/env /usr/bin/python

import sys
import os
import commands
import subprocess
import sys
import shutil
import time
import tarfile
import argparse
import logging

#set up the menu of options - only two in this case
parser = argparse.ArgumentParser(description='Backup all logs, indexes, and configuration for Archiware P5')
parser.add_argument('-d','--destination',dest='backup_path',metavar="PATH",type=str,help="Directory to backup to",required=True)
parser.add_argument('-p','--p5',dest='aw_path',metavar="PATH",type=str,help="Path to P5 directory (if left unset, /usr/local/aw will be used)",default="/usr/local/aw")
args = parser.parse_args()
aw_path = args.aw_path
backup_path = args.backup_path

#set up our logging.  This script only uses INFO level logging
logging.basicConfig(filename="/var/log/p5_index_backup.log", level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

#function to copy and overwrite old backup
def copy_and_overwrite(from_path, to_path):
    if os.path.exists(to_path):
        shutil.rmtree(to_path)
    shutil.copytree(from_path, to_path,symlinks=True)


#check if p5 cli is installed where we expect it
if not os.path.isfile(aw_path + "/bin/nsdchat"):
	logging.error("Could not find P5 CLI at " + str(aw_path) + "/bin/nsdchat, exiting")
	sys.exit(1)

#if our backup path doesn't exist, make it
if not os.path.exists(backup_path):
	os.makedirs(backup_path)

#if our backup path has a trailing slash, kill it so tar works
if backup_path[-1:] == "/":
	backup_path = backup_path[:-1]
	
#function to tar and gzip up our backup for easier movement
def make_tarfile(output_filename, source_dir):
	with tarfile.open(output_filename, "w:gz") as tar:
		tar.add(source_dir, arcname=os.path.basename(source_dir))

# check to see if nsd is already running, if it is lets throw a flag
nr = 0 # our flag
if(commands.getoutput('pgrep nsd') == ""):
	logging.info("P5 is not running")
	nr = 1
	
# if P5 is running, lets check and make sure no jobs are running
if(nr != 1):
	# get all the running jobs
	jobs_str = subprocess.Popen([aw_path + "/bin/nsdchat","-c","Job","names"],stdout=subprocess.PIPE).communicate()[0]
	jobs_str.rstrip()
	jobs = jobs_str.split()

	# figure out which are running and which are stopped.  We only care about running jobs
	i = 0
	for job in jobs:
		status = subprocess.Popen([aw_path + "/bin/nsdchat","-c","Job",job,"status"],stdout=subprocess.PIPE).communicate()[0].rstrip()
		if status == "running":
			i = i +1
			
	# if there is a running job, don't stop the service
	if i > 0:
		logging.error("There are " + str(i) + " job(s) running, can't shut down service!")
		sys.exit(1)
	#if we can shut down P5, lets do it
	logging.info("Shutting down P5")
	output = subprocess.Popen([aw_path + "/stop-server"],stdout=subprocess.PIPE).communicate()[0]
	logging.info(output)

# Lets make a backup of the files now, first we make a stamp so we know how long it took
time_start = time.time()
	
# After we make sure we can make a new copy, we copy the proper files	
new_backup_file = backup_path + "/" + "p5-backup-" + time.strftime("%Y%m%d%H%M%S") + ".tar.gz"
logging.info("Making backup copy")
copy_and_overwrite(aw_path + "/config/index",backup_path + "/aw/config/index")
copy_and_overwrite(aw_path + "/config/customerconfig",backup_path + "/aw/config/customerconfig")
copy_and_overwrite(aw_path + "/log",backup_path + "/aw/log")	
try:
	logging.info("Starting to create tgz file")
	make_tarfile(new_backup_file,backup_path + "/aw")
except:
	logging.error("Could not tgz backup, will not delete")
else:
	logging.info("Removing temporary backup")
	try:
		shutil.rmtree(backup_path + "/aw/")
	except:
		logging.error("Could not remove temporary backup")

time_stop = time.time()

# Then we let you know how long it took
logging.info("Backup took " + str(time_stop - time_start) + " seconds")
logging.info("Backup is located at " + new_backup_file)
# Last, we start up the server
output = subprocess.Popen([aw_path + "/start-server"],stdout=subprocess.PIPE).communicate()[0]
logging.info(output)
sys.exit(0)