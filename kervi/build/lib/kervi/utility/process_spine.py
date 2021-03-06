#MIT License
#Copyright (c) 2017 Tim Wentzlau

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

""" Module that handles IPC between python processes  """
import uuid
from multiprocessing.connection import Listener, Client
import time
import threading
import kervi.spine as spine
#import sys
#import traceback
import kervi.utility.nethelper as nethelper

class _ConnCommandHandler(object):
    def __init__(self, command, conn, src):
        self.conn = conn
        self.command = command
        self.spine = spine.Spine()
        self.src = src
        self.spine.register_command_handler(command, self.on_command, injected="processSpine")

    def on_command(self, *args, **kwargs):
        try:
            injected = kwargs.get("injected", "")
            scope = kwargs.get("scope", "global")
            session = kwargs.get("session", None)
            if not injected == "processSpine":
                self.conn.send({"messageType":"command", "command":self.command, "args":args, "session":session})
        except IOError:
            self.spine.log.debug("IOError ConnCommandHandler:{0}", self.src)
        except:
            self.spine.log.exception("ConnCommandHandler")

class _ConnQueryHandler(object):
    id_count = 0
    uuid_handler = uuid.uuid4().hex
    def __init__(self, query, conn, process_spine, src):
        self.conn = conn
        self.query = query
        self.process_spine = process_spine
        self.spine = spine.Spine()
        self.src = src
        self.spine.register_query_handler(query, self.on_query, injected="processSpine")

    def on_query(self, *args, **kwargs):
        try:
            injected = kwargs.get("injected", "")
            scope = kwargs.get("scope", "global")
            session = kwargs.get("session", "session")
            if not injected == "processSpine":
                self.id_count += 1
                query_id = self.uuid_handler + "-" + str(self.id_count)
                event = threading.Event()
                event_data = {
                    "id":query_id,
                    "eventSignal":event,
                    "response":None,
                    "processed":False
                }
                self.process_spine.add_response_event(event_data)
                
                self.conn.send(
                    {"id":query_id, "messageType":"query", "query":self.query, "args":args, "session":session}
                )
                event.wait()
                res = event_data["response"]
                event_data["processed"] = True
                return res
        except IOError:
            self.spine.log.debug("IOError in ConnQueryHandler:{0}", self.src)
        except:
            self.spine.log.exception("ConnQueryHandler")

class _ConnEventHandler(object):
    def __init__(self, event, id_event, conn, src):
        self.conn = conn
        self.event = event
        self.id_event = id_event
        self.src = src
        self.spine = spine.Spine()
        self.spine.register_event_handler(event, self.on_event, id_event, injected="processSpine")

    def on_event(self, id_event, *args, **kwargs):
        try:
            injected = kwargs.get("injected", "")
            scope = kwargs.get("scope", "global")
            if not injected == "processSpine":
                self.spine.log.debug("trigger event: {0} on:{1} ", self.event, self.src)
                self.conn.send(
                    {"messageType":"event", "event":self.event, "id":id_event, "args":args}
                )
        except IOError:
            self.spine.log.debug("IOError ConnEventHandler:", self.src)
        except:
            self.spine.log.exception("ConnEventHandler")
            pass

class _ClientConnectionThread(threading.Thread):
    def __init__(self, process_spine):
        threading.Thread.__init__(self, None, None, "process spine clientconnection")
        self.daemon = True
        self.process_spine = process_spine
        self.terminate = False
    def run(self):
        try:
            self.process_spine.spine.log.debug("Listen on: {0}", self.process_spine.address)
            while not self.terminate:
                conn = self.process_spine.listener.accept()
                self.process_spine.spine.log.debug(
                    'connection accepted from {0}',
                    self.process_spine.listener.last_accepted
                )
                self.process_spine.add_process_connection(
                    conn,
                    self.process_spine.listener.last_accepted
                )
                if self.process_spine.is_root:
                    conn.send(
                        {"messageType":"processList", "list":self.process_spine.get_ipc_processes()}
                    )
        except IOError:
            self.process_spine.spine.log.debug("IOError in ClientConnectionThread")
        except:
            self.process_spine.spine.log.exception("ClientConnectionThread")

class _ConnectionMessageThread(threading.Thread):
    def __init__(self, process_spine, conn, src, is_root_connection=False):
        threading.Thread.__init__(self, None, None, "ConnectionMessage")
        self.daemon = True
        self.process_spine = process_spine
        self.connection = conn
        self.terminate = False
        self.is_root_connection = is_root_connection
        self.src = src

    def run(self):
        try:
            while not self.terminate:
                message = self.connection.recv()
                self.process_spine.handle_message(message, self.connection, self.src)
                time.sleep(0.001)
            print("connection closed:", self.src)
            self.connection.close()
        except EOFError:
            self.process_spine.spine.log.debug("connection messageThread eof from:{0}", self.src)
            self.process_spine.connection_terminated(self)
        except IOError:
            self.process_spine.spine.log.debug(
                "connection messageThread disconnected from:{0}",
                self.src
            )
            self.process_spine.connection_terminated(self)
        except:
            self.process_spine.spine.log.exception("connectionMessageThread", self.src)

class _ProcessSpine(object):
    def __init__(self, port, settings, **kwargs):
        self.is_root = kwargs.get("is_root", False)
        self.spine = spine.Spine()
        self.settings = settings
        self.port = port
        self.address = (self.settings["network"]["IPAddress"], port)
        #print("listen to:",self.address,self.settings["network"]["IPCSecret"])
        self.listener = Listener(self.address, authkey=self.settings["network"]["IPCSecret"])
        self.response_list = []
        self.process_list = []
        self.process_connections = []
        self.handlers = {"command":[], "query":[], "event":[]}


        self.spine.add_linked_spine(self)
        self.client_connection_thread = _ClientConnectionThread(self)
        self.client_connection_thread.start()
        self.register_at_root()


    def get_ipc_processes(self, *args, **kwargs):
        return self.process_list

    def register_at_root(self):
        if self.is_root:
            return

        root_address = (
            self.settings["network"]["IPRootAddress"],
            self.settings["network"]["IPCRootPort"]
        )

        conn = None
        reconnect = False
        while conn is None:
            try:
                if reconnect:
                    print("Try to connect to root:")
                conn = Client(
                    root_address,
                    authkey=self.settings["network"]["IPCSecret"]
                )
            except IOError:
                self.spine.log.debug("root not found")
                reconnect = True
                print("root not found", self.address)
                time.sleep(1)
        if reconnect:
            print("root found and connected")
        conn.send({"messageType":"registerProcess", "address":self.address})
        self.add_process_connection(conn, root_address, True)

    def register_process(self, process):
        self.process_list += [process]

    def add_process_connections(self, process_list):
        for process in process_list:
            if process != self.address:
                try:
                    conn = Client(process, authkey=self.settings["network"]["IPCSecret"])
                    self.add_process_connection(conn, process)
                    print("ok connection to:", process, "from:", self.address)
                except:
                    self.spine.log.exception("error add_process_connection")
                    print("error connection to:", process, "from:", self.address)

    def connection_terminated(self, connection):
        try:
            self.process_connections.remove(connection)
        except:
            pass

        for a in self.handlers:
            for h in self.handlers[a]:
                if h.src == connection.src:
                    try:
                        h.stop()
                        self.handlers[a].remove(connection)
                        break
                    except:
                        pass

        if connection.is_root_connection:
            self.register_at_root()

    def send_message(self, port, message):
        print ("SM")
        #self.client_connections[port].send(message)

    def add_process_connection(self, conn, src, is_root_connection=False):
        conn_thread = _ConnectionMessageThread(self, conn, src, is_root_connection)
        self.process_connections += [conn_thread]
        conn_thread.start()

        self.spine.log.debug("send rq to {1} clist:{0}", self.spine.get_commands(), src)
        for command in self.spine.get_commands():
            injected_count = 0
            handlers = self.spine.get_command_handlers(command)

            for handler in handlers:
                self.spine.log.debug("send rq handlers:{0}", handler)
                for ijc in self.handlers["command"]:
                    if ijc.on_command == handler:
                        injected_count += 1

            if injected_count < len(handlers):
                conn.send({"messageType":"registerCommandHandler", "command":command})

        self.spine.log.debug("send rq to {1} qlist:{0}", self.spine.get_queries(), src)
        for query in self.spine.get_queries():
            injected_count = 0
            handlers = self.spine.get_query_handlers(query)

            for handler in handlers:
                self.spine.log.debug("send rq handlers:{0}",handler)
                for ijq in self.handlers["query"]:
                    if ijq.on_query == handler:
                        injected_count += 1
            
            if injected_count < len(handlers):
                conn.send({"messageType":"registerQueryHandler", "query":query})

        # injected_events = []
        # for ije in self.handlers["event"]:
        #     injected_events += [{"id":ije.id_event, "event":ije.event, "matched":False, "src": ije.src}]

        # for event in self.spine.get_events():
        #     path = event.split("/")
        #     event_name = path[0]
        #     event_id = None
        #     if len(path) > 1:
        #         event_id = path[1]
        #     found = False
        #     for ie in injected_events:
        #         if ie["id"] == event_id and ie["event"] == event_name and not ie["matched"]:
        #             found = True
        #             ie["matched"] = True

        #     if not found:
        #         conn.send(
        #             {"messageType":"registerEventHandler", "eventId":event_id, "event":event_name}
        #         )
        self.spine.log.debug("send rq to {1} elist:{0}", self.spine.get_events(), src)
        for event in self.spine.get_events():
            path = event.split("/")
            event_name = path[0]
            event_id = None
            if len(path) > 1:
                event_id = path[1]

            injected_count = 0
            handlers = self.spine.get_event_handlers(event_name, event_id)

            for handler in handlers:
                self.spine.log.debug("send rq handlers:{0}",handler)
                for ije in self.handlers["event"]:
                    if ije.on_event == handler:
                        injected_count += 1

            if injected_count < len(handlers):
                conn.send({"messageType":"registerEventHandler", "eventId":event_id, "event":event_name})

    def close_all_connections(self):
        self.listener.close()
        for conn_thread in self.process_connections:
            conn_thread.terminate = True
            #conn_thread.join()
        self.client_connection_thread.terminate = True
        self.client_connection_thread.join()
        #time.sleep(1)

    def add_command_handler(self, command, connection, src):
        found = False
        for ch in self.handlers["command"]:
            if ch.command == command and ch.conn == connection:
                found = True
        if not found:
            self.handlers["command"] += [_ConnCommandHandler(command, connection, src)]

    def add_linked_command_handler(self, name, **kwargs):
        injected = kwargs.get("injected", "")
        if not injected == "processSpine":
            for conn_thread in self.process_connections:
                conn_thread.connection.send(
                    {"messageType":"registerCommandHandler", "command":name}
                )

    def add_query_handler(self, query, connection, src):
        found = False
        for qh in self.handlers["query"]:
            if qh.query == query and qh.conn == connection:
                found = True
        if not found:
            self.handlers["query"] += [_ConnQueryHandler(query, connection, self, src)]

    def add_linked_query_handler(self, name, **kwargs):
        injected = kwargs.get("injected", "")
        if not injected == "processSpine":
            for conn_thread in self.process_connections:
                conn_thread.connection.send({"messageType":"registerQueryHandler", "query":name})

    def add_linked_event_handler(self, name, id_event, **kwargs):
        injected = kwargs.get("injected", "")
        if not injected == "processSpine":
            for conn_thread in self.process_connections:
                conn_thread.connection.send(
                    {"messageType":"registerEventHandler", "event":name, "eventId":id_event}
                )

    def add_event_handler(self, event, id_event, connection, src):
        found = False
        for eh in self.handlers["event"]:
            if eh.event == event and eh.id_event == id_event and eh.conn == connection:
                found = True
        if not found:
            self.handlers["event"] += [_ConnEventHandler(event, id_event, connection, src)]

    def add_response_event(self, event):
        self.response_list += [event]

    def resolve_response(self, message):
        for event in self.response_list:
            if event["id"] == message["id"]:
                event["response"] = message["response"]
                event["eventSignal"].set()

    def handle_message(self, message, connection, src):
        try:
            self.spine.log.debug("message from:{0} on:{1} message:{2}", src, self.port, message)
            if message["messageType"] == "query":
                #print("query:", src, self.port,message["query"])
            
                res = self.spine.send_query(
                    message["query"],
                    *message["args"],
                    injected="processSpine",
                    session=message["session"]
                )
                #print("query:result", res)
                connection.send({"messageType":"queryResponse", "id":message["id"], "response":res})

            elif message["messageType"] == "queryResponse":
                self.resolve_response(message)
            elif message["messageType"] == "registerQueryHandler":
                self.add_query_handler(message["query"], connection, src)
            elif message["messageType"] == "command":
                self.spine.send_command(
                    message["command"],
                    *message["args"],
                    injected="processSpine",
                    session=message["session"]
                )
            elif message["messageType"] == "registerCommandHandler":
                self.add_command_handler(message["command"], connection, src)
            elif message["messageType"] == "event":
                self.spine.trigger_event(
                    message["event"],
                    message["id"],
                    *message["args"],
                    injected="processSpine"
                )
            elif message["messageType"] == "registerEventHandler":
                self.add_event_handler(message["event"], message["eventId"], connection, src)
            elif message["messageType"] == "processList":
                self.add_process_connections(message["list"])
            elif message["messageType"] == "registerProcess":
                self.register_process(message["address"])
        except:
            self.spine.log.exception("on process message")
