"""Static UI concepts only. No application code is changed."""
from pathlib import Path
import json
from PIL import Image,ImageDraw,ImageFont
P=Path(__file__).parent
DATA=json.loads((P/'source_result.json').read_text(encoding='utf-8'))['rows']
INK='#203747';MUTED='#657785';BLUE='#2367A0';EDGE='#DDE4E9';BG='#F5F7F9'
def font(s,b=False):return ImageFont.truetype('C:/Windows/Fonts/'+('segoeuib.ttf' if b else 'segoeui.ttf'),s)
def text(x,y,s,size=18,c=INK,b=False):d.text((x,y),s,font=font(size,b),fill=c)
def box(x,y,w,h,fill='white',outline=EDGE,r=9):d.rounded_rectangle((x,y,x+w,y+h),r,fill=fill,outline=outline,width=1)
def button(x,y,w,label,active=False):
    box(x,y,w,38,'#EAF2F9' if active else 'white',BLUE if active else EDGE,6);text(x+13,y+8,label,15,BLUE if active else INK,active)
def field(x,y,w,label,value):
    text(x,y,label,14,MUTED);box(x,y+25,w,38);text(x+11,y+33,value,15);d.line([(x+w-24,y+42),(x+w-19,y+47),(x+w-14,y+42)],fill=MUTED,width=2)
def chart(x,y,w,h,small=False):
    text(x,y,'Fall enrollment at Mount Holyoke and Smith',22 if small else 25,b=True)
    text(x,y+38,'Total students · Fall 2015–2024',15,MUTED)
    left=x+53;right=x+w-(175 if small else 200);top=y+99;bottom=y+h-93
    for tick in [0,1000,2000,3000,4000]:
        yy=bottom-(bottom-top)*tick/4000;d.line((left,yy,right,yy),fill=EDGE,width=1);text(left-49,yy-11,f'{tick:,}',12,MUTED)
    for yr in range(2015,2025):
        xx=left+(right-left)*(yr-2015)/9;text(xx-16,bottom+13,str(yr),11 if small else 13,MUTED)
    text((left+right)/2-16,bottom+40,'Year',13,MUTED)
    for name,color in [('Smith College','#84939F'),('Mount Holyoke College',BLUE)]:
        rr=sorted([r for r in DATA if r['institution']==name],key=lambda r:r['observation_year'])
        pts=[(left+(right-left)*(r['observation_year']-2015)/9,bottom-(bottom-top)*r['value']/4000) for r in rr]
        d.line(pts,fill=color,width=3)
        for xx,yy in pts:d.ellipse((xx-3,yy-3,xx+3,yy+3),fill=color)
        xx,yy=pts[-1];text(xx+13,yy-19,'Mount Holyoke' if name.startswith('Mount') else 'Smith College',13 if small else 15,color,True);text(xx+13,yy+3,f"{rr[-1]['value']:,.0f} students",13 if small else 15,color)
    text(x,y+h-27,'Source: IPEDS · Fall Enrollment · EF2015A–EF2024A',12,MUTED)
def base():
    global im,d
    im=Image.new('RGB',(1600,1120),BG);d=ImageDraw.Draw(im)
    d.rectangle((0,0,1600,77),fill='white');text(47,20,'IPEDS Research Companion',24,b=True);text(376,26,'Local prototype',14,MUTED)
    text(1010,28,'Ask & Analyze',17,BLUE,True);text(1190,28,'Explore IPEDS',17,MUTED);text(1420,28,'Tools',17,MUTED)
    d.line((1008,75,1140,75),fill=BLUE,width=3)
    text(125,104,'What would you like to learn?',29,b=True);text(125,151,'Build an extract or look up a definition.',16,MUTED);text(1360,128,'Hide Menu',15,MUTED);d.line([(1443,141),(1448,136),(1453,141)],fill=MUTED,width=2)
    d.line((125,192,1475,192),fill=EDGE,width=1)
    box(640,219,835,55,'#EAF1F7',None);text(660,234,"Compare Mount Holyoke’s total enrollment with Smith College.",18)
    text(126,300,'IPEDS Research Companion',15,BLUE,True)
    text(126,333,'Here is total fall enrollment for both institutions from 2015 through 2024.',18)
def composer():
    text(1328,1000,'Clear conversation',14,MUTED)
    box(125,1033,1350,57,'white',EDGE,10);text(145,1049,'Ask a follow-up or describe a chart change…',17,MUTED)
    box(1424,1044,36,35,BLUE,BLUE,7);text(1435,1049,'↑',21,'white')
def actions(y=895):
    text(144,y+9,'○  Display table',15,MUTED);button(350,y,148,'Format chart');button(511,y,164,'Download chart')
    button(144,y+51,208,'Definitions & sources');button(365,y+51,159,'Download Data')

base();box(125,376,1350,500);chart(150,395,1296,466);actions();composer()
text(47,1100,'CONCEPT 01 · Conversation view · Formatting controls stay tucked away until needed',12,MUTED)
im.save(P/'ui-01-conversation.png')

base();box(125,376,935,500);chart(149,395,887,466,True)
text(145,908,'○  Display table',15,MUTED);button(335,897,145,'Format chart',True);button(492,897,164,'Download chart')
button(145,948,208,'Definitions & sources');button(365,948,159,'Download Data')
box(1084,376,391,604);text(1106,397,'Format chart',21,b=True);text(1438,399,'×',23,MUTED)
for xx,label,active in [(1106,'Layout',False),(1200,'Text',False),(1274,'Style',True),(1360,'Axes',False)]:
    text(xx,445,label,16,BLUE if active else MUTED,active)
d.line((1273,475,1314,475),fill=BLUE,width=3)
text(1106,496,'Series colors',15,b=True)
for yy,label,color in [(532,'Mount Holyoke College',BLUE),(572,'Smith College','#84939F')]:
    box(1108,yy,25,25,color,color,4);text(1145,yy+1,label,15)
field(1106,623,345,'Value labels','Latest year only')
field(1106,713,345,'Legend','Direct labels at line ends')
text(1106,803,'●  Show point markers',15);text(1106,837,'○  Show vertical gridlines',15,MUTED)
button(1106,894,100,'Undo');button(1216,894,100,'Reset')
text(1107,945,'Changes update the chart immediately.',12,MUTED)
composer();text(47,1100,'CONCEPT 02 · Format panel · The chart remains visible while you adjust its appearance',12,MUTED)
im.save(P/'ui-02-format-panel.png')

base();composer()
shade=Image.new('RGBA',im.size,(24,40,54,95));im=Image.alpha_composite(im.convert('RGBA'),shade).convert('RGB');d=ImageDraw.Draw(im)
box(100,90,1400,944,'#F5F7F9','#CCD5DD',12)
text(130,112,'Presentation preview',24,b=True);text(1454,110,'×',27,MUTED)
text(130,154,'Preview the complete figure, including its title and source note.',16,MUTED)
field(132,209,231,'Layout','Full slide · 16:9');field(387,209,185,'File type','PNG image');field(596,209,219,'Resolution','2400 × 1350 px')
button(1180,234,278,'Download chart')
box(228,335,1144,644,'white',EDGE,1)
preview=Image.open(P/'02-focus-direct-labels.png')
# Remove the concept label and explanatory subtitle from the export preview.
pd=ImageDraw.Draw(preview);pd.rectangle((0,0,preview.width,130),fill='white');pd.rectangle((0,230,preview.width,315),fill='white')
preview=preview.resize((1142,642),Image.Resampling.LANCZOS);im.paste(preview,(229,336));d=ImageDraw.Draw(im)
text(131,997,'Export contains the figure only. Formatting controls and conversation are excluded.',14,MUTED)
text(47,1100,'CONCEPT 03 · Presentation preview · A fixed canvas makes the downloaded result predictable',12,MUTED)
im.save(P/'ui-03-presentation-preview.png')
print('Created three static interface mockups.')
