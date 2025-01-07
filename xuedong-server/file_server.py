import os
import time
import uuid
from fastapi import FastAPI, File, Form, UploadFile
from datetime import datetime, timedelta
from uvicorn import run
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import base64
import hashlib
import hmac
import websocket
import json
from urllib.parse import urlencode
from wsgiref.handlers import format_date_time
import ssl
import _thread as thread
import wave
from time import mktime
import shutil
import subprocess

# Initialize FastAPI app
app = FastAPI()

# 配置文件存储路径
UPLOAD_FOLDER = "uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# 定义请求体模型
class TTSRequest(BaseModel):
    text: str

class WsParam:
    def __init__(self, APPID, APIKey, APISecret, Text):
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret
        self.Text = Text
        
        self.CommonArgs = {"app_id": self.APPID}
        self.BusinessArgs = {"aue": "raw", "auf": "audio/L16;rate=16000", "vcn": "xiaoyan", "tte": "utf8"}
        self.Data = {"status": 2, "text": str(base64.b64encode(self.Text.encode('utf-8')), "UTF8")}

    def create_url(self):
        url = 'wss://tts-api.xfyun.cn/v2/tts'
        now = datetime.now()
        date = format_date_time(time.mktime(now.timetuple()))

        signature_origin = "host: " + "ws-api.xfyun.cn" + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + "/v2/tts " + "HTTP/1.1"
        
        signature_sha = hmac.new(self.APISecret.encode('utf-8'), signature_origin.encode('utf-8'),
                                digestmod=hashlib.sha256).digest()
        signature_sha = base64.b64encode(signature_sha).decode(encoding='utf-8')

        authorization_origin = f'api_key="{self.APIKey}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha}"'
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')
        
        v = {
            "authorization": authorization,
            "date": date,
            "host": "ws-api.xfyun.cn"
        }
        return url + '?' + urlencode(v)

def pcm2wav(pcm_file, wav_file, channels=1, bits=16, sample_rate=16000):
    with open(pcm_file, 'rb') as pcmf:
        pcmdata = pcmf.read()
    
    with wave.open(wav_file, 'wb') as wavfile:
        wavfile.setnchannels(channels)
        wavfile.setsampwidth(bits // 8)
        wavfile.setframerate(sample_rate)
        wavfile.writeframes(pcmdata)


@app.post("/uploadfile")
async def upload_file(file: UploadFile = File(...)):
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"filename": file.filename, "url": f"http://10.65.1.110:8002/files/{file.filename}"}

@app.get("/files/{filename}")
async def get_file(filename: str):
    file_path = os.path.join("uploads", filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return {"error": "File not found"}

@app.post("/api/tts")
async def text_to_speech(request: TTSRequest):
    try:
        text = request.text
        if not text:
            return JSONResponse(
                status_code=400,
                content={'error': 'No text provided'}
            )

        # 生成唯一文件名
        filename = f"{uuid.uuid4()}"
        pcm_file = os.path.join(UPLOAD_FOLDER, f"{filename}.pcm")
        wav_file = os.path.join(UPLOAD_FOLDER, f"{filename}.wav")

        # 初始化讯飞参数
        ws_param = WsParam(
            APPID='a9468b3d',  # 需要从环境变量或配置文件读取
            APIKey='3d5e9910b46311ea048dabd3748ae2e2',
            APISecret='MzM3M2JlMmZmNTEwODA2OGVmMjFlMTk5',
            Text=text
        )

        # 用于存储音频数据
        audio_data = []

        def on_message(ws, message):
            try:
                message = json.loads(message)
                code = message["code"]
                if code != 0:
                    print(f"Error: {message['message']}")
                    return
                
                audio = base64.b64decode(message["data"]["audio"])
                with open(pcm_file, 'ab') as f:
                    f.write(audio)

                if message["data"]["status"] == 2:
                    ws.close()
            except Exception as e:
                print(f"Error processing message: {str(e)}")

        def on_open(ws):
            def run(*args):
                data = {
                    "common": ws_param.CommonArgs,
                    "business": ws_param.BusinessArgs,
                    "data": ws_param.Data,
                }
                ws.send(json.dumps(data))
            thread.start_new_thread(run, ())

        # 创建WebSocket连接
        websocket.enableTrace(False)
        ws_url = ws_param.create_url()
        ws = websocket.WebSocketApp(
            ws_url,
            on_message=on_message,
            on_open=on_open
        )
        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

        # 转换PCM到WAV
        pcm2wav(pcm_file, wav_file)
        
        # 清理PCM文件
        if os.path.exists(pcm_file):
            os.remove(pcm_file)

        return {
            'success': True,
            'message': 'Text to speech conversion successful',
            'file_url': f"http://10.65.1.110:8002/files/{filename}.wav"
        }

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'message': str(e)
            }
        )

STATUS_FIRST_FRAME = 0  # 第一帧的标识
STATUS_CONTINUE_FRAME = 1  # 中间帧标识
STATUS_LAST_FRAME = 2  # 最后一帧的标识

# 添加 Ws_Param_ASR 类（语音识别参数类）
class Ws_Param_ASR(object):
    # 初始化
    def __init__(self, APPID, APIKey, APISecret, AudioFile):
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret
        self.AudioFile = AudioFile

        # 公共参数(common)
        self.CommonArgs = {"app_id": self.APPID}
        # 业务参数(business)，更多个性化参数可在官网查看
        self.BusinessArgs = {"domain": "iat", "language": "zh_cn", "accent": "mandarin", "vinfo":1,"vad_eos":10000}

    # 生成url
    def create_url(self):
        url = 'wss://ws-api.xfyun.cn/v2/iat'
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        signature_origin = "host: " + "ws-api.xfyun.cn" + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + "/v2/iat " + "HTTP/1.1"

        signature_sha = hmac.new(self.APISecret.encode('utf-8'), signature_origin.encode('utf-8'),
                               digestmod=hashlib.sha256).digest()
        signature_sha = base64.b64encode(signature_sha).decode(encoding='utf-8')

        authorization_origin = f'api_key="{self.APIKey}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha}"'
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')
        
        v = {
            "authorization": authorization,
            "date": date,
            "host": "ws-api.xfyun.cn"
        }
        return url + '?' + urlencode(v)

# 添加语音识别接口
@app.post("/api/asr")
async def speech_to_text(file: UploadFile = File(...)):
    try:
        # 保存上传的文件
        original_file = os.path.join(UPLOAD_FOLDER, file.filename)
        with open(original_file, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 生成转换后的PCM文件路径
        pcm_file = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}.pcm")
        
        try:
            # 使用ffmpeg将AMR-WB转换为PCM
            # -ar 16000：设置采样率为16kHz
            # -ac 1：设置为单声道
            # -f s16le：设置格式为16位小端PCM
            cmd = [
                'ffmpeg', '-i', original_file,
                '-ar', '16000',
                '-ac', '1',
                '-f', 's16le',
                pcm_file
            ]
            subprocess.run(cmd, check=True)
            
            # 使用转换后的PCM文件进行识别
            wsParam = Ws_Param_ASR(
                APPID='a9468b3d',
                APISecret='MzM3M2JlMmZmNTEwODA2OGVmMjFlMTk5',
                APIKey='3d5e9910b46311ea048dabd3748ae2e2',
                AudioFile=pcm_file
            )
            
            # 用于存储识别结果
            final_result = ""

            def on_message(ws, message):
                nonlocal final_result
                try:
                    code = json.loads(message)["code"]
                    sid = json.loads(message)["sid"]
                    if code != 0:
                        errMsg = json.loads(message)["message"]
                        print(f"sid:{sid} call error:{errMsg} code is:{code}")
                    else:
                        data = json.loads(message)["data"]["result"]["ws"]
                        result = ""
                        for i in data:
                            for w in i["cw"]:
                                result += w["w"]
                        final_result += result
                except Exception as e:
                    print(f"receive msg,but parse exception:{str(e)}")

            def on_error(ws, error):
                print(f"### error:{error}")

            def on_close(ws, a, b):
                print("### closed ###")

            def on_open(ws):
                def run(*args):
                    frameSize = 8000  # 每一帧的音频大小
                    intervel = 0.04  # 发送音频间隔(单位:s)
                    status = STATUS_FIRST_FRAME

                    with open(pcm_file, "rb") as fp:
                        while True:
                            buf = fp.read(frameSize)
                            if not buf:
                                status = STATUS_LAST_FRAME
                            if status == STATUS_FIRST_FRAME:
                                d = {
                                    "common": wsParam.CommonArgs,
                                    "business": wsParam.BusinessArgs,
                                    "data": {
                                        "status": 0,
                                        "format": "audio/L16;rate=16000",
                                        "audio": str(base64.b64encode(buf), 'utf-8'),
                                        "encoding": "raw"
                                    }
                                }
                                d = json.dumps(d)
                                ws.send(d)
                                status = STATUS_CONTINUE_FRAME
                            elif status == STATUS_CONTINUE_FRAME:
                                d = {
                                    "data": {
                                        "status": 1,
                                        "format": "audio/L16;rate=16000",
                                        "audio": str(base64.b64encode(buf), 'utf-8'),
                                        "encoding": "raw"
                                    }
                                }
                                ws.send(json.dumps(d))
                            elif status == STATUS_LAST_FRAME:
                                d = {
                                    "data": {
                                        "status": 2,
                                        "format": "audio/L16;rate=16000",
                                        "audio": str(base64.b64encode(buf), 'utf-8'),
                                        "encoding": "raw"
                                    }
                                }
                                ws.send(json.dumps(d))
                                time.sleep(1)
                                break
                            time.sleep(intervel)
                    ws.close()
                thread.start_new_thread(run, ())

            # 开始语音识别
            websocket.enableTrace(False)
            wsUrl = wsParam.create_url()
            ws = websocket.WebSocketApp(
                wsUrl,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )
            ws.on_open = on_open
            ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

        finally:
            # 清理临时文件
            if os.path.exists(original_file):
                os.remove(original_file)
            if os.path.exists(pcm_file):
                os.remove(pcm_file)

        return {
            'success': True,
            'text': final_result
        }

    except subprocess.CalledProcessError as e:
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'message': f'音频转换失败: {str(e)}'
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'message': str(e)
            }
        )

if __name__ == '__main__':
    run(app, host='0.0.0.0', port=8002)
