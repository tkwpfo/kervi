// Copyright (c) 2016, Tim Wentzlau
// Licensed under MIT

export class  KerviSpineBase {

    public isConnected = false;
    public doAuthenticate = false;

    sessionId = null;
    queryHandlers = [];
    commandHandlers = [];
    eventHandlers = [];
    streamHandlers = [];
    rpcQueue = {};
    ready = false;
    messageId = 0;
    sensors = {};
    controllers = {};
    sensorTypes = [];
    controllerTypes = [];
    visionRegions = [];
    application = null;
    allowAnonymous = true;
    firstOnOpen = true;
    messageCount = 0;
    mpsTime = new Date;
    mps = 0;

    protected websocket = null;

    public options: any = {
            userName: 'anonymous',
            password: null,
            address: null,
            onOpen: null,
            onClose: null,
            onAuthenticate: null,
            onAuthenticateFailed: null,
            onAuthenticateStart: null,
            onLogOff: null,
            onMPS: null,
            autoConnect: true,
            targetScope: null,
            protocol: 'ws',
            apiToken: null
    }

    constructor(public constructorOptions) {
        console.log('Kervi base spine init', this.options, constructorOptions);
        this.options = this.extend(this.options, constructorOptions);
        console.log('kbo', this.options);
        this.connect();
        const self = this;
        setInterval(
            function() {
                var hangingNodes = []
                for(let id in self.rpcQueue) {
                    var query = self.rpcQueue[id];
                    if (query['callbackTimeout']) {
                        if (Date.now() - query['ts'] > query['timeout']){
                            var callback = query['callbackTimeout']; 
                            hangingNodes.push(id);
                            callback.call(self.options.targetScope);
                        }
                    }
                }
                for(let id of hangingNodes) {
                    delete self.rpcQueue[id];
                }
            }
        , 1);
    }

    protected extend(...p: any[])
    {
        for (let i = 1; i < p.length; i++) {
            for(let key in p[i]) {
                if(p[i].hasOwnProperty(key)) {
                    p[0][key] = p[i][key];
                }
            }
        }
        return p[0];
    }

    protected addRPCCallback(id: string, callback, callbackTimeout, timeout) {
        if (callback) {
            this.rpcQueue[id] = {
                'callback': callback,
                'callbackTimeout': callbackTimeout,
                'timeout': timeout,
                'ts': Date.now(),
             };
        }
    }

    protected handleRPCResponse(message){
        if (message.id in this.rpcQueue){
            var callback = this.rpcQueue[message.id]['callback'];
            if (callback){
                delete this.rpcQueue[message.id];
                callback.call(this.options.targetScope,message.response,message.response);
            }
        }
    }

    protected handleEvent(message){
        // console.log('ev', message)
        const eventName = message.event;
        const id = message.id;

        let eventPath=eventName;
        if (id) {
            eventPath += '/' + id;
        }

        let value = null;
        if(message.args && message.args.length) {
            value = message.args[0];
        }
        for(var n = 0; (n < this.eventHandlers.length); n++)
        {
            let h = this.eventHandlers[n];
            if (h.eventName === eventPath)
                h.callback.call(value,id,value);
            else if (h.eventName === eventName)
                h.callback.call(value,id,value);
        }
    }

    protected handleStream(message, streamBlob) {
        const streamTag = message.streamId + '/' + message.streamEvent ;
        for (let n = 0; (n < this.streamHandlers.length); n++) {
            const h = this.streamHandlers[n];
            if (h.streamTag === streamTag) {
                h.callback.call(message.streamId, message.streamId, message.streamEvent, streamBlob);
            } else if (h.streamTag === message.streamId) {
                h.callback.call(message.streamId, message.streamId, message.streamEvent, streamBlob);
            }
        }
    }

    protected handleCommand(message){
        console.log('cmd',this,message);
        var command=message.command
        
        var args=null;
        if(message.args && message.args.length){
            args=message.args[0];
        }
        
        for(var n=0;(n<this.commandHandlers.length);n++)
        {
            var c=this.commandHandlers[n];
            if (c.command==command)
                c.callback.call(this,args);
        }
    }

    protected connect() {

    }

    protected onOpen(evt) {
        console.log('Kervi open', this, evt);

        this.isConnected = true;
        this.eventHandlers = [];
        this.streamHandlers = [];
        this.commandHandlers = [];
        this.queryHandlers = [];
        console.log('Kervi spine ready');

    }

    protected onClose(evt) {
        console.log('Kervi spine on close', evt);
        this.isConnected = false;
        const self = this;
        if (this.options.onClose)
            this.options.onClose.call(this.options.targetScope,evt);
        this.firstOnOpen = true;
        if (this.options.autoConnect) {
            setTimeout(function() {
                self.connect();
            }, 1000);
        }
    }

    public authenticate(userName, password) {

    }

    public logoff() {

    }

    protected onMessage(evt) {

    }

    protected onError(evt) {
        console.log('Kervi on error', evt);
    }

    public addCommandHandler (command: string, callback) {

    }

    public addQueryHandler(query: string, callback) {

    }

    public addEventHandler = function(eventName: string, id: string, callback) {

    };

    public addStreamHandler = function(streamId: string, streamEvent: string[], callback) {

    }

    public removeStreamHandler = function(streamId: string, streamEvent: string[], callback) {

    }

    public sendCommand(command: string, ...p: any[]) {

    }

    public sendQuery(query, ...p: any[]) {

    }

    public triggerEvent(eventName: string, id: string) {

    }

    public streamData(stream_id: string, event: string , data: any) {

    }
}
