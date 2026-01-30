import io
import logging
import struct
import gzip
import json
from dataclasses import dataclass
from enum import IntEnum
from typing import Callable, List, Union

logger = logging.getLogger(__name__)

class MsgType(IntEnum):
    Invalid = 0
    FullClientRequest = 0b1
    AudioOnlyClient = 0b10
    FullServerResponse = 0b1001
    AudioOnlyServer = 0b1011
    FrontEndResultServer = 0b1100
    Error = 0b1111

class MsgTypeFlagBits(IntEnum):
    NoSeq = 0
    PositiveSeq = 0b1
    LastNoSeq = 0b10
    NegativeSeq = 0b11
    WithEvent = 0b100

class SerializationBits(IntEnum):
    Raw = 0
    JSON = 0b1

class CompressionBits(IntEnum):
    None_ = 0
    Gzip = 0b1

class EventType(IntEnum):
    None_ = 0
    StartConnection = 1
    FinishConnection = 2
    ConnectionStarted = 50
    ConnectionFailed = 51
    ConnectionFinished = 52
    StartSession = 100
    CancelSession = 101
    FinishSession = 102
    SessionStarted = 150
    SessionFinished = 152
    SessionFailed = 153
    TaskRequest = 200
    UpdateConfig = 201
    TTSSentenceStart = 350
    TTSSentenceEnd = 351
    TTSResponse = 352
    ChatTTS = 500
    TextInput = 501

@dataclass
class DoubaoMessage:
    version: int = 1
    header_size: int = 1
    type: MsgType = MsgType.Invalid
    flag: MsgTypeFlagBits = MsgTypeFlagBits.WithEvent
    serialization: SerializationBits = SerializationBits.JSON
    compression: CompressionBits = CompressionBits.Gzip
    event: Union[EventType, int] = EventType.None_
    session_id: str = ""
    payload: bytes = b""
    error_code: int = 0
    sequence: int = 0

    @classmethod
    def from_bytes(cls, data: bytes) -> "DoubaoMessage":
        if len(data) < 4: raise ValueError("Data too short")
        
        msg = cls()
        msg.version = data[0] >> 4
        msg.header_size = data[0] & 0x0F
        msg.type = MsgType(data[1] >> 4)
        msg.flag = MsgTypeFlagBits(data[1] & 0x0F)
        msg.serialization = SerializationBits(data[2] >> 4)
        msg.compression = CompressionBits(data[2] & 0x0F)
        
        ptr = msg.header_size * 4
        
        # Sequence number handling (Demo logic)
        if msg.type in [MsgType.FullClientRequest, MsgType.FullServerResponse, 
                       MsgType.FrontEndResultServer, MsgType.AudioOnlyClient, MsgType.AudioOnlyServer]:
            if msg.flag in [MsgTypeFlagBits.PositiveSeq, MsgTypeFlagBits.NegativeSeq]:
                msg.sequence = int.from_bytes(data[ptr:ptr+4], 'big', signed=True)
                ptr += 4

        # Error code handling
        if msg.type == MsgType.Error:
            msg.error_code = int.from_bytes(data[ptr:ptr+4], 'big')
            ptr += 4

        # Event number handling
        if msg.flag & MsgTypeFlagBits.WithEvent:
            event_val = int.from_bytes(data[ptr:ptr+4], 'big')
            try: msg.event = EventType(event_val)
            except ValueError: msg.event = event_val
            ptr += 4
            
            # Session ID (Demo logic: certain events don't have session_id)
            if msg.event not in [EventType.StartConnection, EventType.FinishConnection,
                               EventType.ConnectionStarted, EventType.ConnectionFailed,
                               EventType.ConnectionFinished]:
                s_size = int.from_bytes(data[ptr:ptr+4], 'big')
                ptr += 4
                if s_size > 0:
                    msg.session_id = data[ptr:ptr+s_size].decode('utf-8')
                    ptr += s_size
        
        # Payload handling
        if len(data) >= ptr + 4:
            p_size = int.from_bytes(data[ptr:ptr+4], 'big')
            ptr += 4
            msg.payload = data[ptr:ptr+p_size]
        
        if msg.compression == CompressionBits.Gzip and msg.payload:
            try: msg.payload = gzip.decompress(msg.payload)
            except: pass
            
        return msg

    def marshal(self) -> bytes:
        header = bytes([
            (self.version << 4) | self.header_size,
            (self.type << 4) | self.flag,
            (self.serialization << 4) | self.compression,
            0x00 # Reserved
        ])
        
        body = bytearray()
        
        # Sequence
        if self.type in [MsgType.FullClientRequest, MsgType.AudioOnlyClient]:
             if self.flag in [MsgTypeFlagBits.PositiveSeq, MsgTypeFlagBits.NegativeSeq]:
                 body.extend(self.sequence.to_bytes(4, 'big', signed=True))

        # Error
        if self.type == MsgType.Error:
            body.extend(self.error_code.to_bytes(4, 'big'))

        # Event & SessionID
        if self.flag & MsgTypeFlagBits.WithEvent:
            body.extend(int(self.event).to_bytes(4, 'big'))
            
            if self.event not in [EventType.StartConnection, EventType.FinishConnection,
                                EventType.ConnectionStarted, EventType.ConnectionFailed,
                                EventType.ConnectionFinished]:
                s_bytes = self.session_id.encode('utf-8')
                body.extend(len(s_bytes).to_bytes(4, 'big'))
                body.extend(s_bytes)
            
        p_bytes = self.payload
        if self.compression == CompressionBits.Gzip and p_bytes:
            p_bytes = gzip.compress(p_bytes)
            
        body.extend(len(p_bytes).to_bytes(4, 'big'))
        if p_bytes: body.extend(p_bytes)
        
        return header + body

def parse_response(data: bytes) -> dict:
    if isinstance(data, str): return {"raw_str": data}
    try:
        msg = DoubaoMessage.from_bytes(data)
        result = {
            "message_type": str(msg.type),
            "event": int(msg.event),
            "session_id": msg.session_id,
            "payload_msg": msg.payload,
            "payload_size": len(msg.payload)
        }
        if msg.type == MsgType.Error:
            result["code"] = msg.error_code
        return result
    except Exception as e:
        return {"error": str(e)}

def generate_header(message_type=MsgType.FullClientRequest, flag=MsgTypeFlagBits.WithEvent, serialization=SerializationBits.JSON, compression=CompressionBits.Gzip, **kwargs):
    ser = kwargs.get('serial_method', serialization)
    comp = kwargs.get('compression_type', compression)
    return DoubaoMessage(type=message_type, flag=flag, serialization=ser, compression=comp).marshal()[:4]

# Backward compatibility
CLIENT_FULL_REQUEST = MsgType.FullClientRequest
CLIENT_AUDIO_ONLY_REQUEST = MsgType.AudioOnlyClient
SERVER_FULL_RESPONSE = MsgType.FullServerResponse
SERVER_ACK = MsgType.AudioOnlyServer
SERVER_ERROR_RESPONSE = MsgType.Error
NO_SERIALIZATION = SerializationBits.Raw
JSON = SerializationBits.JSON
NO_COMPRESSION = CompressionBits.None_
GZIP = CompressionBits.Gzip
