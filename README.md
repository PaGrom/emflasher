emflasher
=========

Script for the base firmware embedded systems

Dependencies:
	sudo apt-get install python-serial

usage: emflasher.py [-h] [-p PORT] [-b BAUDRATE] [-t TIMEOUT] [-bs BYTESIZE]
                    [-ia IPADDR] [-si SERVERIP] [-tf TFTP_FOLDER]
                    [-ais AISFILE] [-k KERNEL] [-r ROOTFS] [-ns]

optional arguments:
  -h, --help            show this help message and exit
  -p PORT, --port PORT  Serial port
  -b BAUDRATE, --baudrate BAUDRATE
                        Serial baudrate
  -t TIMEOUT, --timeout TIMEOUT
                        Serial timeout
  -bs BYTESIZE, --bytesize BYTESIZE
                        Serial bytesize
  -ia IPADDR, --ipaddr IPADDR
                        TFTP IP addr
  -si SERVERIP, --serverip SERVERIP
                        TFTP Server IP addr
  -tf TFTP_FOLDER, --tftp_folder TFTP_FOLDER
                        TFTP folder addr
  -ais AISFILE, --aisfile AISFILE
                        AIS file of U-Boot
  -k KERNEL, --kernel KERNEL
                        Kernel Image
  -r ROOTFS, --rootfs ROOTFS
                        Rootfs file
  -ns, --not_by_symbols
                        write not by symbols
