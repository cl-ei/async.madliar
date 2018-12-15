let WebSocketClient = require('websocket').client;
let request = require('request');


/* ***************************** */

function generatePacket (action, payload) {
    payload = payload || '';
    let packetLength = Buffer.byteLength(payload) + 16;
    let buff = new Buffer.alloc(packetLength);

    buff.writeInt32BE(packetLength, 0);
    // write consts
    buff.writeInt16BE(16, 4);
    buff.writeInt16BE(1, 6);
    buff.writeInt32BE(1, 12);
    // write action
    buff.writeInt32BE(action, 8);
    // write payload
    buff.write(payload, 16);
    return buff
}

function sendJoinRoom(ws, rid){
    let uid = 1E15 + Math.floor(2E15 * Math.random());
    let packet = JSON.stringify({uid: uid, roomid: rid});
    let joinedRoomPayload = generatePacket(7, packet);
    ws.send(joinedRoomPayload);
}

function parseMessage(buff, fn, room_id){
    if(buff.length < 21) {return}
    while (buff.length > 16){
        let length = (buff[0] << 24) + (buff[1] << 16) + (buff[2] << 8) + buff[3];
        let current = buff.slice(0, length);
        buff = buff.slice(length);
        if (current.length > 16 && current[16] !== 0){
            try{
                let msg = JSON.parse("" + current.slice(16));
                fn(msg, room_id);
            }catch (e) {
                console.log("e: " + current);
            }
        }
    }
}


let HEART_BEAT = generatePacket(2);
let MONITOR_URL = "ws://broadcastlv.chat.bilibili.com:2244/sub";
let MONITOR_ROOM_LIST = new Set();
let RESTARTING_CONNECTIONS = new Set();

/* ***************************** */
MESSAGE_COUNT = 0;
let NOTICE_BUFFER_1s = new Set();
let NOTICE_BUFFER_2s = new Set();
let NOTICE_BUFFER_3s = new Set();

let checkGType = ["摩天大楼", "小电视飞船", "嗨翻全城", "小金人"];
function procMessage(msg, room_id){
    if (msg.cmd === "NOTICE_MSG"){
        if (msg.msg_type !== 2) return;
        let real_roomid = msg.real_roomid;
        let message = msg.msg_common;

        let gtypeInfo = message.split("%>").pop();
        let count = parseInt(gtypeInfo);
        let realGType = "Unknown";
        for(let i = 0; i < checkGType.length; i++){
            if(gtypeInfo.indexOf(checkGType[i]) > -1){
                realGType = checkGType[i];
                break;
            }
        }
        // console.log("procMessage: ", JSON.stringify(msg));
        let finnalMsg = real_roomid + ":" + realGType + ":" + count + ":";
        if(NOTICE_BUFFER_1s.has(finnalMsg) || NOTICE_BUFFER_2s.has(finnalMsg) || NOTICE_BUFFER_3s.has(finnalMsg)) {
            // do nothing
        }else{
            console.log(finnalMsg);
        }
        NOTICE_BUFFER_1s.add(finnalMsg);
        NOTICE_BUFFER_2s.add(finnalMsg);
        NOTICE_BUFFER_3s.add(finnalMsg);
    }else if(msg.cmd === "SEND_GIFT"){
        if (msg.data.giftName !== "节奏风暴") return;
        let gtype = msg.data.giftName;
        let count = msg.data.num;
        console.log("gift: ", gtype, "*", count, " - ", room_id);
    }else if(msg.cmd === "GUARD_BUY"){
        let count = msg.data.num;
        let gid = msg.data.gift_id;
        let gname = msg.data.gift_name;
        console.log("gift: ", gname, "room_id", room_id, "c: ", count);
    }else if([
            "DANMU_MSG", "SEND_GIFT", "COMBO_END", "ENTRY_EFFECT",
            "WELCOME_GUARD", "WELCOME", "NOTICE_MSG", "COMBO_SEND",
            "ROOM_RANK", "ROOM_BLOCK_MSG", "WISH_BOTTLE", "LIVE",
            "SYS_MSG", "SPECIAL_GIFT", "GUARD_MSG", "PREPARING",
            "WELCOME_ACTIVITY", "TV_START", "GUARD_LOTTERY_START",
            "USER_TOAST_MSG", "RAFFLE_END", "PK_PROCESS", "RAFFLE_START",
            "room_admin_entrance", "ROOM_ADMINS", "TV_END", "PK_SETTLE",
            "PK_MIC_END",
        ].indexOf(msg.cmd) > -1
    ){
        MESSAGE_COUNT += 1;
        if(MESSAGE_COUNT % 1000 === 0){
            console.log(MESSAGE_COUNT, " messages received.")
        }
        if(MESSAGE_COUNT > 9999999999999){
            MESSAGE_COUNT = 0;
        }
    }else{
        console.log(msg.cmd, room_id, msg);
    }
}


function create_monitor(room_id){
    function on_message(message){
        parseMessage(message.binaryData, procMessage, room_id);
    }

    let client = new WebSocketClient();
    function on_error(e){
        console.log('Connect Error: ' + e.toString(), "room_id: ", room_id);
        try{
            client.close();
        }catch (e) {
            // console.log("Try stop: ", e.toString())
        }
        if (RESTARTING_CONNECTIONS.has(room_id)){return;}
        RESTARTING_CONNECTIONS.add(room_id);
        setTimeout(function(){
            if (MONITOR_ROOM_LIST.has(room_id)){
                create_monitor(room_id);
            }
        }, 1000);
    }

    client.on('connectFailed', on_error);
    client.on('connect', function(connection) {
        connection.on('error', on_error);
        connection.on('close', on_error);
        connection.on('message', on_message);
        sendJoinRoom(connection, room_id);
        function sendHeartBeat() {
            if(!MONITOR_ROOM_LIST.has(room_id)){
                connection.close();
            }
            if (connection.connected) {
                connection.send(HEART_BEAT);
                setTimeout(sendHeartBeat, 10000);
            }
        }
        sendHeartBeat();
        console.log("Connected: ", room_id);
        RESTARTING_CONNECTIONS.delete(room_id);
    });
    client.connect(MONITOR_URL);
}


let scan_url = "https://api.live.bilibili.com/room/v1/room/get_user_recommend?page=";
let headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36'
};

function startMonitor(){
    console.log("Start monitor: ", MONITOR_ROOM_LIST.size);
    MONITOR_ROOM_LIST.forEach(function(room_id) {
        setTimeout(function () {
            create_monitor(room_id);
        }, parseInt(Math.random()*10000));
    });

    setInterval(function () {
        NOTICE_BUFFER_1s.clear();
    }, 1000);
    setInterval(function () {
        NOTICE_BUFFER_2s.clear();
    }, 2300);
    setInterval(function () {
        NOTICE_BUFFER_3s.clear();
    }, 4000);
}

let MONITOR_ROOM_COUNT_LIMIT = 300;
function roomScaner(index){
    index = index || 0;
    console.log("Req times: ", index);
    request({
        url: scan_url + index,
        method: "get",
        headers: headers,
        timeout: 10000,
    }, function (err, res, body) {
        if (err) {
            setTimeout(function () {
                roomScaner(index);
            }, 500);
        } else {
            let r = JSON.parse(body).data || [];
            for (let i = 0; i < r.length; i++){
                let roomid = r[i].roomid;
                MONITOR_ROOM_LIST.add(roomid);
            }
            if (MONITOR_ROOM_LIST.size > MONITOR_ROOM_COUNT_LIMIT){
                startMonitor();
            }else{
                setTimeout(function () {
                    roomScaner(index + 1);
                }, 500);
            }
        }
    });
}

roomScaner();
console.log("Started.");
