Random notes on the Raspberry Pi tools to pull, convert, and push data
files from the Trimble NetRS receiver.

1.  The "runpkr00" package is statically linked using a proprietary library
provided by Trimble.  It is an i386 32 bit program, but will run on the
rasperry pi if you have the "qemu-user" and "binfmt-support" packages
installed.

2.  The "teqc" program is the *statically* linked version for the Raspberry
Pi as the dynamically linked one doesn't seem to work.  It was downloaded
from https://www.unavco.org/software/data-processing/teqc/teqc.html

3.  The "gnsscal" module is from https://pypi.org/project/gnsscal/
You could install this via pip, but then you have to deal with the "break
system files" hoohaw that Debian now puts you through.

4.  Install paramiko for sftp: "sudo apt install python3-maramiko"

5.  The code assumes that the NetRS "system name" is the same as the
hostname.  This needs to be correct in order for file downloads to work
properly.

