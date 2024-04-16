import glob
import os
import time
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import threading
from models.main import Rtsp
from services.main import cleanup_folder, convert_to_hls, cut_ip_address, stop_ffmpeg_by_ip, thread_exists
from motor.motor_asyncio import AsyncIOMotorClient
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

load_dotenv()
secret_url_api = os.environ.get('SECURITY_URL_API')
secret_url_mongo_rtsp = os.environ.get('SECURITY_URL_MONGO_RTSP')
secret_url_api_cxview = os.environ.get('SECURITY_URL_API_CXVIEW')

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Kết nối tới MongoDB
client = AsyncIOMotorClient(secret_url_mongo_rtsp)
db = client["rtsp-camera"]
collect_camera = db["camera"]

# Tạo thư mục chứa video
if not os.path.exists('./videos'):
    os.mkdir('./videos')
app.mount("/videos", StaticFiles(directory="videos"), name="videos")

# Dictionary to store running processes
running_processes = {}

# get
@app.get("/active-threads")
def get_active_threads():
    active = threading.enumerate()
    thread_names = [t.name for t in active]
    return {"active_threads": thread_names}

@app.get("/list-process")
def get_list_process():
    if running_processes:
        print("Running Processes:")
        for rtsp_url, process in running_processes.items():
            print(f"  RTSP URL: {rtsp_url}, PID: {process.pid}")
    else:
        print("No running processes.")

@app.get("/list-rtsp")
async def get_list_rtsp(request: Request):
    token = request.headers.get("Authorization")
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    data_user = requests.get(f"{secret_url_api_cxview}/prod/api/v1/user-management/get-profile", headers={"Authorization": token},verify=False)
    data_rtsp = await collect_camera.find_one({"email": data_user.json()["data"]["email"]})
    if data_rtsp == None:
        return {"data":{}}
    return {"data":data_rtsp}

# post
@app.post("/stop-ffmpeg")
async def post_stop_ffmpeg(rtsp: Rtsp,request: Request):
    ip_cam = cut_ip_address(rtsp.rtsp)
    url_image = stop_ffmpeg_by_ip(ip_cam,running_processes)
    if url_image:
        token = request.headers.get("Authorization")
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
        data_user = requests.get(f"{secret_url_api_cxview}/prod/api/v1/user-management/get-profile", headers={"Authorization": token},verify=False)
        data_rtsp = await collect_camera.find_one({"email": data_user.json()["data"]["email"]})
        for rtsp_item in data_rtsp["rtsp"]:
            if rtsp_item["link"] == rtsp.rtsp:
                rtsp_item["image_lastest"] = url_image
                break
        await collect_camera.update_one({"email": data_user.json()["data"]["email"]}, {"$set": data_rtsp})
        return {"url_image":url_image}

@app.post("/convert")
def post_start_conversion(rtsp: Rtsp):
        ip_cam = cut_ip_address(rtsp.rtsp)
        if not thread_exists(ip_cam, running_processes):
            cleanup_folder(ip_cam)
            conversion_thread = threading.Thread(target=convert_to_hls, args=(rtsp.rtsp,running_processes), name=ip_cam)
            conversion_thread.start()
        else:
            print("Thread đã tồn tại, không tạo mới.")
        while not glob.glob(os.path.join("videos", ip_cam, "*.ts")):
            time.sleep(1)  # Đợi 1 giây trước khi kiểm tra lại
        return {"hls_url": f"{secret_url_api}/videos/{ip_cam}/output.m3u8"}

@app.post("/add-rtsp")
async def post_add_rtsp(rtsp: Rtsp, request: Request):
    token = request.headers.get("Authorization")
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    data_user = requests.get(f"{secret_url_api_cxview}/prod/api/v1/user-management/get-profile", headers={"Authorization": token},verify=False)
    data_rtsp = await collect_camera.find_one({"email": data_user.json()["data"]["email"]})
    if data_rtsp == None:
        data_rtsp = {
            "email": data_user.json()["data"]["email"],
            "rtsp": [rtsp.rtsp]
        }
        await collect_camera.insert_one(data_rtsp)
    else:
        for rtsp_item in data_rtsp["rtsp"]:
            if rtsp_item["link"] == rtsp.rtsp:
                raise HTTPException(status_code=400, detail="RTSP đã tồn tại.")
        rtsp_new = {
            "id": len(data_rtsp["rtsp"]) + 1,
            "link": rtsp.rtsp,
            "status": False,
            "image_lastest": "https://dfstudio-d420.kxcdn.com/wordpress/wp-content/uploads/2019/06/digital_camera_photo-1080x675.jpg"
        }
        data_rtsp["rtsp"].append(rtsp_new)
        await collect_camera.update_one({"email": data_user.json()["data"]["email"]}, {"$set": data_rtsp})
    return {"message": "Thêm RTSP thành công."}
        

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)