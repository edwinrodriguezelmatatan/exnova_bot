import telebot, cv2, numpy as np
from PIL import Image
import io, os, time, threading
from flask import Flask
TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)
ultima_alerta = 0
def leer_mercado(foto_bytes):
 try:
  img = Image.open(io.BytesIO(foto_bytes)).convert("RGB")
  arr = np.array(img)
  h,w,_ = arr.shape
  grafico = arr[int(h*0.1):int(h*0.85), int(w*0.05):int(w*0.95)]
  hsv = cv2.cvtColor(grafico, cv2.COLOR_RGB2HSV)
  mask_v = cv2.inRange(hsv, np.array([35,50,50]), np.array([85,255,255]))
  mask_r = cv2.inRange(hsv, np.array([0,50,50]), np.array([10,255,255])) + cv2.inRange(hsv, np.array([160,50,50]), np.array([180,255,255]))
  verdes = cv2.countNonZero(mask_v)
  rojos = cv2.countNonZero(mask_r)
  if verdes+rojos < 500:
   return None,0,"Foto muy lejos, acerca al grafico"
  gw = grafico.shape[1]
  cols=5
  anchos=gw//cols
  fuerza=[]
  for i in range(cols):
   col=grafico[:,i*anchos:(i+1)*anchos]
   hsv_col=cv2.cvtColor(col,cv2.COLOR_RGB2HSV)
   v=cv2.countNonZero(cv2.inRange(hsv_col, np.array([35,50,50]), np.array([85,255,255])))
   r=cv2.countNonZero(cv2.inRange(hsv_col, np.array([0,50,50]), np.array([10,255,255])) + cv2.inRange(hsv_col, np.array([160,50,50]), np.array([180,255,255])))
   if v>r: fuerza.append(1)
   elif r>v: fuerza.append(-1)
   else: fuerza.append(0)
  ultimas3=fuerza[-3:]
  gray=cv2.cvtColor(grafico,cv2.COLOR_RGB2GRAY)
  edges=cv2.Canny(gray,50,150)
  densidad=np.sum(edges>0)/edges.size*100
  if densidad>9:
   return "LATERAL",0,"LATERAL - No operar"
  if ultimas3==[1,1,1] and verdes>rojos*1.6:
   conf=88+min((verdes/rojos)*2,6)
   return "ALCISTA FUERTE",conf,"Rompiendo resistencia"
  elif ultimas3==[-1,-1,-1] and rojos>verdes*1.6:
   conf=88+min((rojos/verdes)*2,6)
   return "BAJISTA FUERTE",conf,"Rompiendo soporte"
  elif sum(ultimas3)>=2 and verdes>rojos*1.2:
   conf=75+(verdes/(verdes+rojos))*10
   return "ALCISTA",conf,"Tendencia alcista"
  elif sum(ultimas3)<=-2 and rojos>verdes*1.2:
   conf=75+(rojos/(verdes+rojos))*10
   return "BAJISTA",conf,"Tendencia bajista"
  else:
   return "DUDOSO",50,"Sin tendencia clara"
 except Exception as e:
  return None,0,str(e)
@bot.message_handler(commands=['start'])
def start(m): bot.reply_to(m,"✅ LECTOR 86%+ ACTIVO\nManda captura 1M")
@bot.message_handler(content_types=['photo'])
def foto(m):
 global ultima_alerta
 try:
  if time.time()-ultima_alerta<120: return
  file_id=m.photo[-1].file_id
  data=bot.download_file(bot.get_file(file_id).file_path)
  tendencia,confianza,motivo=leer_mercado(data)
  if tendencia is None:
   bot.reply_to(m,f"⚠️ {motivo}");return
  if confianza<86:
   bot.reply_to(m,f"❌ {tendencia} {confianza:.0f}%\n{motivo}\nSolo aviso 86%+");return
  ultima_alerta=time.time()
  entrada="CALL 📈" if "ALCISTA" in tendencia else "PUT 📉"
  bot.reply_to(m,f"✅ {tendencia}\n🎯 {entrada}\n🔥 {confianza:.0f}%\n{motivo}\n⏱️ 2 MIN")
 except: pass
app=Flask(__name__)
@app.route('/')
def home(): return "Bot vivo"
def run_flask():
 port=int(os.environ.get("PORT",10000))
 app.run(host="0.0.0.0",port=port)
threading.Thread(target=run_flask,daemon=True).start()
threading.Thread(target=lambda:bot.infinity_polling(timeout=30),daemon=True).start()
while True: time.sleep(1)
