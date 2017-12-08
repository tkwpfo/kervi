# Copyright (c) 2016, Tim Wentzlau
# Licensed under MIT

""" Handles multiprocessing functionality in Kervi """

from multiprocessing import Process #, Array, Value, Manager, freeze_support
import time
import kervi.spine as spine
from kervi.utility.process_spine import _ProcessSpine
#import sys
import kervi.kervi_logging as k_logging

MAIN_SPINE = None
def _start_root_spine(settings, reset_log=False):
    global MAIN_SPINE
    k_logging.init_process_logging("kervi-main", settings["log"])
    k_logging.KerviLog("kervi main")
    spine._init_spine("kervi-main", settings["network"]["IPCRootPort"])
    #MAIN_SPINE = _ProcessSpine(settings["network"]["IPCRootPort"], settings, is_root=True)

def _stop_root_spine():
    #MAIN_SPINE.close_all_connections()
    pass

class _KerviProcess(object):
    def __init__(self, name, settings, ipcPort):
        self.name = name
        self.do_terminate = False
        self.port = ipcPort
        self.settings = settings
        spine._init_spine(name, ipcPort, "tcp://" + settings["network"]["IPRootAddress"] + ":" + str(settings["network"]["IPCRootPort"]))
        self.spine = spine.Spine()
        #self.process_spine = _ProcessSpine(ipcPort, settings)
        #self.spine.send_command("startThreads", scope="process")
        #time.sleep(1)
        self.spine.register_command_handler("terminateProcess", self.terminate)
        self.spine.register_query_handler("getProcessInfo", self.get_process_info)
        self.init_process()
        self.spine.run()
        self.spine.send_command("startThreads", scope="process")
        

    def __del__(self):
        print("pd", self.name)

    def get_process_info(self):
        return {"id": self.name}

    def terminate(self):
        print("terminate process", self.name)
        self.spine.log.debug("do terminate:{0}", self.port)
        #print("terminate:", self.port)
        self.do_terminate = True

    def init_process(self):
        self.spine.log.error("abstract init_process called in KerviProcess")

    def _terminate_process(self):
        self.terminate_process()
        self.spine.trigger_event("processTerminating", None, scope="process")
        #time.sleep(5)
        #self.process_spine.close_all_connections()
        self.spine.log.info("process terminated:{0}", self.port)
        self.spine.stop()

    def terminate_process(self):
        pass

    def process_step(self):
        pass

def _launch(name, process_class, settings, ipc_port):
    k_logging.init_process_logging(name, settings["log"])
    log = k_logging.KerviLog(name)
    log.info('create process:{0} ipc port:{1}:', process_class.__name__, ipc_port)
    process = process_class(name, settings, ipc_port)
    try:
        while not process.do_terminate:
            process.process_step()

    except KeyboardInterrupt:
        pass
    except:
        log.exception("error in process loop")
        pass
    print("ot", name)
    process._terminate_process()


def _start_process(name, settings, port_idx, process_class):
    process = Process(target=_launch, args=(name, process_class, settings, port_idx))
    process.start()
    return process

def _stop_processes():
    spine.Spine().send_command("terminateProcess")
