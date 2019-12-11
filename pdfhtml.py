import shlex
import subprocess
import os
import platform

def run(command):
    if platform.system() != 'Windows':
        args = shlex.split(command)
    else:
        args = command
    s = subprocess.Popen(args,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    output, errors = s.communicate()
    return s.returncode == 0, output, errors

# Change this to your PDF file base directory
base_directory = 'C:\\Users\\Admin\\Desktop\\learningpython\\PROJECT'
if not os.path.isdir(base_directory):
    print "%s is not a directory" % base_directory
    exit(1)
# Change this to your pdf2htmlEX executable location
bin_path = 'C:\\Python27\\pdf2htmlEX-master\\pdf2htmlEX.exe'
if not os.path.isfile(bin_path):
    print "Could not find %s" % bin_path
    exit(1)
for dir_path, dir_name_list, file_name_list in os.walk(base_directory):
    for file_name in file_name_list:
        # If this is not a PDF file
        if not file_name.endswith('.pdf'):
            # Skip it
            continue
        file_path = os.path.join(dir_path, file_name)
        # Convert your PDF to HTML here
        args = (bin_path, dir_path, file_path)
        success, output, errors = run("%s --dest-dir %s %s" % args)
        if not success:
            print "Could not convert %s to HTML" % file_path
            print "%s" % errors