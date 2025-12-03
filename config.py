ADDRESS = 'USB0::1510::9782::4399155\x00::0::INSTR'

TSP_DIR = 'TSP-scripts/'

def set_address(addr: str):
    global ADDRESS
    ADDRESS = addr

def set_tsp_dir(dir: str):
    global TSP_DIR
    TSP_DIR = dir