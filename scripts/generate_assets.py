"""Original deterministic RuneForge pixel art and synthesized sound; CC0."""
from pathlib import Path
from PIL import Image, ImageDraw
import random, math, wave, struct
ROOT = Path(__file__).resolve().parents[1] / 'game/assets'
ROOT.mkdir(parents=True, exist_ok=True)
rng = random.Random(7331)
def canvas(w,h):
 im=Image.new('RGBA',(w,h)); return im,ImageDraw.Draw(im)
def save(im,name): im.save(ROOT/f'{name}.png')
def sprite(kind,frame):
 im,d=canvas(40,48); bob=[0,-1,0,1][frame]; y=bob
 # Silhouette, shadows, and several layers of armor rather than primitive placeholders.
 if kind=='boss':
  d.polygon([(7,43),(9,19),(3,15),(11,14),(12,8),(16,12),(24,12),(29,6),(28,15),(36,18),(30,24),(34,44)],fill='#121522',outline='#4e4367')
  d.polygon([(12,23),(20,18),(28,23),(30,43),(10,43)],fill='#382d51')
  for xx in (12,23): d.rectangle((xx,26,xx+5,41),fill='#574264'); d.line((xx,28,xx+4,40),fill='#927596')
  d.polygon([(14,11),(20,7),(26,11),(25,22),(20,26),(15,22)],fill='#514963',outline='#aaa0b5')
  d.polygon([(10,10),(9,2),(16,12),(24,12),(31,1),(29,13)],fill='#85758d')
  d.line((15,16,24,16),fill='#6fe4e2',width=2); d.rectangle((19,19,21,23),fill='#171d2b')
  d.rectangle((3,24,6,44),fill='#88849e');d.polygon([(1,25),(4,12),(7,25)],fill='#bcb4cf'); d.line((4,18,4,42),fill='#a9f4ed')
 elif kind=='mage':
  d.polygon([(8,44),(12,23),(12,14),(20,4),(28,14),(27,25),(33,44)],fill='#191828',outline='#6f4f86')
  d.polygon([(13,23),(20,28),(27,23),(29,43),(11,43)],fill='#594172')
  d.line((19,29,18,42),fill='#9b77ac',width=2); d.rectangle((15,15,25,23),fill='#111c27')
  d.rectangle((16,18,18,19),fill='#92eddf');d.rectangle((22,18,24,19),fill='#92eddf')
  d.line((32,17,32,43),fill='#936f56',width=2); d.polygon([(32,8),(28,14),(32,19),(36,14)],fill='#94e9d8'); d.point((32,12),fill='white')
 else:
  palette={'player':('#a0b7bc','#4d6671','#a6424d','#d8c8a0'),'skeleton':('#d3ccb0','#7c8074','#575c61','#efe5bf'),'goblin':('#91ab68','#4b694e','#694b3c','#bbc581'),'elder':('#b39a72','#666650','#355b62','#e1cda7')}
  light,mid,cloth,skin=palette[kind]
  step=[0,2,0,-2][frame]
  d.polygon([(11,21+y),(27,21+y),(31,40),(22,37),(11,42)],fill=cloth,outline='#18232b')
  d.rectangle((13,34,18,43+step//2),fill='#202d35');d.rectangle((22,34,27,43-step//2),fill='#202d35')
  d.rectangle((11,42+step//2,18,45+step//2),fill=mid);d.rectangle((22,42-step//2,29,45-step//2),fill=mid)
  d.rectangle((12,22+y,28,34+y),fill=mid,outline='#151d28'); d.rectangle((15,22+y,24,30+y),fill=light)
  d.line((18,23+y,18,29+y),fill='#e0dbbf'); d.rectangle((12,32+y,28,34+y),fill='#302c2d');d.rectangle((19,32+y,22,34+y),fill='#d2ab64')
  d.rectangle((9,23+y,13,31+y),fill=light);d.rectangle((28,23+y,31,31+y),fill=light)
  d.rectangle((14,9+y,26,21+y),fill=skin,outline='#1b2228')
  if kind=='player':
   d.polygon([(12,10+y),(16,5+y),(25,5+y),(29,10+y),(28,20+y),(25,19+y),(25,13+y),(14,13+y),(14,20+y),(12,19+y)],fill=light,outline=mid)
   d.line((15,15+y,24,15+y),fill='#142832',width=2);d.line((19,6+y,19,13+y),fill='#eef0d4')
   d.polygon([(17,5+y),(20,1+y),(25,1+y),(24,7+y)],fill='#b55656')
  elif kind=='skeleton':
   d.rectangle((15,13+y,18,16+y),fill='#222d34');d.rectangle((22,13+y,25,16+y),fill='#222d34');d.line((17,20+y,23,20+y),fill='#222d34');
   for j in range(3):d.line((14,24+j*3+y,26,24+j*3+y),fill='#29383b')
  elif kind=='goblin':
   d.polygon([(14,12+y),(6,9+y),(12,19+y)],fill=mid);d.polygon([(26,12+y),(34,9+y),(28,19+y)],fill=mid)
   d.line((15,14+y,18,15+y),fill='#e9d59d',width=2);d.line((22,15+y,25,14+y),fill='#e9d59d',width=2)
   d.polygon([(15,9+y),(19,4+y),(25,8+y)],fill='#503c32')
  else:
   d.polygon([(12,14+y),(14,7+y),(25,7+y),(28,14+y)],fill='#c9bfa8'); d.polygon([(15,17+y),(25,17+y),(21,28+y)],fill='#d5c8ac')
  if kind!='elder':
   d.line((33,20+y,33,39+y),fill='#c6d1cc',width=2);d.polygon([(31,21+y),(33,15+y),(35,21+y)],fill='#edf0d9');d.line((29,32+y,36,32+y),fill='#bca46a',width=2)
  else:d.line((32,19,32,44),fill='#b78b61',width=2)
 return im
for kind in ['player','skeleton','goblin','mage','boss','elder']:
 sheet=Image.new('RGBA',(160,48))
 for f in range(4):sheet.paste(sprite(kind,f),(40*f,0))
 save(sheet,kind)
for kind in ['floor','earth','path','wall','water']:
 sheet=Image.new('RGBA',(24*6,24))
 for v in range(6):
  im,d=canvas(24,24)
  colors={'floor':('#262e38','#313b46','#1d252e'),'earth':('#283733','#33453d','#202f2d'),'path':('#49463e','#555349','#393c36'),'wall':('#414554','#555b68','#202733'),'water':('#122c38','#1a414d','#285360')}
  a,b,c=colors[kind];d.rectangle((0,0,23,23),fill=a)
  if kind in ('floor','path'):
   d.line((0,0,23,0),fill=b);d.line((0,0,0,23),fill=b);d.line((0,23,23,23),fill=c);d.line((23,0,23,23),fill=c)
   if v%2==0:d.line((8,0,9,5,7,7,10,12),fill=c)
  if kind=='wall':
   for y in (0,8,16):
    d.line((0,y,24,y),fill=c,width=2)
    for x in range(-12 if y==8 else 0,24,12):d.line((x,y,x,y+8),fill=c);d.line((x+2,y+2,x+10,y+2),fill=b)
  for _ in range(26):
   x,y=rng.randrange(24),rng.randrange(24);d.point((x,y),fill=rng.choice([b,c]))
  if kind=='earth':
   for _ in range(4):
    x,y=rng.randrange(22),rng.randrange(19);d.line((x,y+4,x+1,y,x+2,y+3),fill=b)
  sheet.paste(im,(v*24,0))
 save(sheet,kind)
# Environment props, deliberately taller than a tile for depth and overlap.
im,d=canvas(64,96)
d.polygon([(26,87),(29,43),(38,43),(39,86),(48,93),(33,90),(19,94)],fill='#4f4036',outline='#172827')
for y,w in [(51,29),(37,26),(22,20),(9,13)]:
 d.polygon([(32,y-9),(32-w,y+22),(24,y+18),(32-w+4,y+29),(32+w,y+26),(32+w-9,y+17)],fill='#182f32',outline='#38504b')
 d.line((32,y-4,32-w+8,y+20),fill='#496157',width=2)
save(im,'tree')
im,d=canvas(128,112)
d.rectangle((15,52,112,102),fill='#544b49',outline='#151e29');d.rectangle((20,57,107,99),fill='#756354')
for x in (22,61,103):d.rectangle((x,53,x+4,102),fill='#352e32')
for y in (69,85):d.line((20,y,107,y),fill='#433b39',width=2)
d.polygon([(4,55),(61,5),(124,55)],fill='#2e3744',outline='#111b29')
for y in range(18,55,6):
 half=int((y-5)*1.2);d.line((61-half,y,61+half,y),fill='#56616b',width=2)
d.rectangle((51,71,72,104),fill='#292d33');d.arc((51,60,72,82),180,360,fill='#a89870',width=3)
for x in (29,85):
 d.rectangle((x,67,x+13,82),fill='#d49d58',outline='#2a2a32');d.line((x+6,67,x+6,82),fill='#513d35');d.line((x,74,x+13,74),fill='#513d35')
d.rectangle((90,7,101,37),fill='#64585c');d.rectangle((87,5,104,10),fill='#8a7a77')
save(im,'house')
im,d=canvas(40,40)
d.ellipse((3,26,36,38),fill='#19242d');d.rectangle((5,13,34,33),fill='#67452f',outline='#17242b');d.pieslice((5,3,34,23),180,360,fill='#90603a',outline='#d1a968')
for x in (9,27):d.rectangle((x,8,x+3,32),fill='#bc985b')
d.line((6,20,33,20),fill='#201e25',width=2);d.rectangle((18,17,23,25),fill='#efcb74');d.point((20,21),fill='#423833');save(im,'chest')
im,d=canvas(40,48)
d.ellipse((4,34,36,46),fill='#484653',outline='#8a7a75');d.ellipse((10,36,31,43),fill='#242c35')
d.line((11,39,28,34),fill='#a37d57',width=3);d.line((12,34,28,40),fill='#705441',width=3)
for f,c in [(0,'#da613d'),(4,'#efab59'),(8,'#ffe6a1')]:d.polygon([(13+f//2,35),(10+f,23),(18,26-f),(21,8+f),(30-f//2,26),(27-f//2,36)],fill=c)
save(im,'fire')
im,d=canvas(40,64)
d.polygon([(6,60),(9,14),(15,7),(28,7),(32,14),(34,60)],fill='#414957',outline='#76818a');d.rectangle((13,16,27,48),fill='#263742');d.line((20,20,20,42),fill='#81c1bd',width=2);d.line((14,27,25,27),fill='#81c1bd',width=2);d.rectangle((2,56,38,62),fill='#555b66');save(im,'shrine')
im,d=canvas(40,48)
d.rectangle((8,15,31,43),fill='#383d49',outline='#131f29');d.ellipse((8,5,31,26),fill='#464e59',outline='#82908a');d.line((20,12,20,28),fill='#80958f',width=2);d.line((15,18,25,18),fill='#80958f',width=2);save(im,'grave')
im,d=canvas(24,48)
d.rectangle((8,19,16,43),fill='#746458');d.rectangle((5,36,19,44),fill='#414451');d.polygon([(5,19),(7,10),(10,14),(13,3),(19,16),(16,23),(8,23)],fill='#f1b768');d.polygon([(9,20),(12,12),(15,21)],fill='#fff0b0');save(im,'torch')
for kind,c in [('sword','#d3ded6'),('fang','#74c1b0'),('rune','#9e8ed3'),('legendary','#ebc878'),('potion','#ce6062'),('armor','#7e9aa6'),('gold','#d6b16a')]:
 im,d=canvas(32,32)
 if kind in ('sword','fang','legendary'):
  d.polygon([(10,24),(23,4),(27,2),(27,8),(14,27)],fill=c,outline='#29313b');d.line((14,23,25,5),fill='#fff2cb');d.line((7,19,17,28),fill='#c39b61',width=3);d.line((7,27,11,23),fill='#927258',width=3)
 elif kind=='potion':
  d.rectangle((12,3,20,7),fill='#bca27a');d.rectangle((12,8,20,14),fill='#9bb4b5');d.ellipse((7,11,25,29),fill='#adc5c0');d.ellipse((9,16,23,27),fill=c);d.line((11,17,11,23),fill='#ffd7b8',width=2)
 elif kind=='rune':
  d.polygon([(16,2),(27,16),(16,30),(5,16)],fill='#3c354d',outline=c);d.line((16,7,11,16,20,16,16,25),fill=c,width=2)
 elif kind=='armor':
  d.polygon([(8,6),(12,8),(20,8),(24,6),(30,14),(24,18),(24,29),(8,29),(8,18),(2,14)],fill=c,outline='#d0d7be');d.line((15,10,15,27),fill='#394d5d',width=2)
 else:
  d.ellipse((6,7,26,27),fill='#8e653b',outline=c);d.ellipse((6,4,26,24),fill=c,outline='#f3d898');d.line((17,8,12,15,20,15,15,21),fill='#926d3a',width=2)
 save(im,kind)
im,d=canvas(64,64);d.rounded_rectangle((1,1,62,62),8,fill='#131f2b',outline='#c6a66d',width=2);d.polygon([(32,8),(49,30),(32,55),(15,30)],outline='#7ec9bc',fill='#263d47');d.line((34,17,24,32,39,32,29,46),fill='#f1d292',width=4);save(im,'icon')
# Soft light used additively over the pixel world.
im=Image.new('RGBA',(128,128));pix=im.load()
for y in range(128):
 for x in range(128):
  a=max(0,1-math.hypot(x-63.5,y-63.5)/64)**2;pix[x,y]=(255,223,161,int(a*110))
save(im,'glow')
for kind in ['hit','slash','loot','roll','hurt','bell']:
 duration={'bell':.8,'loot':.4}.get(kind,.18); samples=[]
 for i in range(int(22050*duration)):
  t=i/22050;env=(1-t/duration)**2
  freq={'hit':95,'slash':700,'loot':720,'roll':180,'hurt':65,'bell':440}[kind]
  val=math.sin(2*math.pi*(freq*t+(180*t*t if kind=='loot' else 0)))
  if kind in ('hit','slash','roll'):val=.5*val+.5*rng.uniform(-1,1)
  samples.append(int(val*env*6500))
 with wave.open(str(ROOT/f'{kind}.wav'),'wb') as w:w.setparams((1,2,22050,0,'NONE','not compressed'));w.writeframes(struct.pack('<'+'h'*len(samples),*samples))
print('Generated',len(list(ROOT.glob('*'))),'original assets')
# Secondary art pass: architectural detail, weathering and environmental storytelling.
im,d=canvas(32,64)
d.line((2,4,29,4),fill='#baa078',width=3);d.rectangle((6,6,25,46),fill='#653c51',outline='#352d3c');d.polygon([(6,45),(15,58),(25,45)],fill='#653c51',outline='#352d3c')
d.line((9,9,9,44),fill='#996076');d.line((22,9,22,44),fill='#452f44')
d.polygon([(16,14),(22,28),(16,40),(11,28)],outline='#ceaf79');d.line((17,20,14,28,19,28,15,34),fill='#dfc793');save(im,'banner')
im,d=canvas(48,72)
d.rectangle((9,61,39,69),fill='#515b65',outline='#202c37');d.rectangle((14,10,34,62),fill='#48535f',outline='#222d39')
for x,c in [(17,'#6f7b80'),(21,'#576670'),(28,'#323d4d')]:d.line((x,14,x,59),fill=c,width=2)
d.rectangle((10,6,38,14),fill='#6e787d',outline='#293541');d.rectangle((7,2,41,7),fill='#8d9693');d.line((12,63,36,63),fill='#98a19b');save(im,'pillar')
im,d=canvas(48,40)
for x,y,w in [(3,24,15),(18,20,13),(30,27,15),(13,31,12),(34,14,9)]:
 d.polygon([(x,y),(x+w//2,y-5),(x+w,y-1),(x+w-1,y+7),(x+2,y+8)],fill='#46515a',outline='#26333b');d.line((x+2,y,x+w//2,y-3,x+w-2,y),fill='#77817e')
save(im,'rubble')
im,d=canvas(32,28)
d.ellipse((3,5,16,17),fill='#b0b1a1',outline='#36474c');d.rectangle((5,10,8,13),fill='#35424a');d.rectangle((11,10,14,13),fill='#35424a')
d.line((17,12,26,24),fill='#a0a797',width=2);d.line((18,24,28,14),fill='#a0a797',width=2);save(im,'bones')
im,d=canvas(48,38)
for i in range(35):
 x=rng.randrange(5,44);y=rng.randrange(10,35);d.line((x,y,x+rng.randrange(-5,6),y-rng.randrange(3,12)),fill=rng.choice(['#476255','#68816a','#344b46']))
for i in range(9):
 x=rng.randrange(8,40);y=rng.randrange(9,23);d.rectangle((x,y,x+2,y+2),fill=rng.choice(['#bb9765','#b5b28a','#867f97']))
save(im,'bush')
# A repeating woven runner for the inner sanctum.
im,d=canvas(48,48);d.rectangle((0,0,47,47),fill='#513344')
for x in (3,7,40,44):d.line((x,0,x,48),fill='#9e7d66' if x in (3,44) else '#302c38')
d.polygon([(24,8),(34,24),(24,40),(14,24)],outline='#8e6a65');d.line((24,14,20,24,28,24,24,34),fill='#bb9a78')
for _ in range(70):
 x,y=rng.randrange(48),rng.randrange(48);d.point((x,y),fill='#483241')
save(im,'carpet')
print('Secondary art pass complete')
