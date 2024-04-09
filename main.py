import os
import time
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import threading
from models.main import Rtsp
from services.main import cleanup_folder, convert_to_hls, cut_ip_address, thread_exists

load_dotenv()
secret_url_api = os.environ.get('SECURITY_URL_API')

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/videos", StaticFiles(directory="videos"), name="videos")

@app.post("/convert")
async def start_conversion(rtsp: Rtsp):
        ip_cam = cut_ip_address(rtsp.rtsp)
        print("ip_cam",ip_cam)
        if not thread_exists(ip_cam):
            cleanup_folder(ip_cam)
            conversion_thread = threading.Thread(target=convert_to_hls, args=(rtsp.rtsp,""), name=ip_cam)
            conversion_thread.start()
        else:
            print("Thread đã tồn tại, không tạo mới.")
        while not os.path.exists(os.path.join("videos",ip_cam,"output.m3u8")):
            time.sleep(1)
        return {"hls_url": f"{secret_url_api}/videos/{ip_cam}/output.m3u8"}

@app.get("/active_threads")
async def active_threads():
    active = threading.enumerate()
    thread_names = [t.name for t in active]
    return {"active_threads": thread_names}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)