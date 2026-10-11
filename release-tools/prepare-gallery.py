"""Publish real guest screenshots; no generated screen mockups."""
import pathlib,base64,html,zipfile,re
root=pathlib.Path('dist');folder=root/'gallery';images=sorted(folder.glob('*.png'))
if len(images)!=62:raise RuntimeError(f'Expected 62 actual guest captures, found {len(images)}')
report=(folder/'guest-report.txt').read_text()
if 'GITM_GALLERY_ERROR|' in report:raise RuntimeError('A gallery page failed: inspect guest-report.txt')
report=re.sub(r'\x1b\[[0-9;]*m','',report)
order=[line.split('GITM_GALLERY_FRAME|',1)[1].strip().split()[0] for line in report.splitlines() if 'GITM_GALLERY_FRAME|' in line]
positions={name:i for i,name in enumerate(order)}
images.sort(key=lambda p:positions.get(p.stem,999))
captions={'dock-revealed':'الشريط السفلي — ظاهر','desktop-light':'سطح المكتب — نهاري','appearance-light':'المظهر — نهاري', 'desktop':'سطح المكتب','control-center':'مركز التحكم','control-center-light':'مركز التحكم — نهاري','volume-popup':'قائمة الصوت','wifi':'شبكات Wi-Fi','bluetooth':'أجهزة Bluetooth','battery-power':'البطارية والطاقة','search':'البحث','sync':'تحديث الحالة','settings':'الإعدادات','updates':'التحديثات','appearance':'المظهر','app-files':'مدير الملفات','app-browser':'المتصفح','app-photos':'الصور','app-media':'الوسائط','app-calculator':'الحاسبة','app-install':'المثبت — طلب صلاحية المسؤول','app-documents':'قارئ PDF','network':'إدارة الشبكات','bluetooth-manager':'مدير Bluetooth','audio':'الصوت','screen-power':'إعدادات الشاشة والطاقة','keyboard':'لوحة المفاتيح','processes':'مراقبة العمليات','accounts':'الحسابات','system-updates':'تحديث حزم Ubuntu','airplane-confirm':'وضع الطيران — تأكيد فقط','suspend-confirm':'التعليق — تأكيد فقط','reboot-confirm':'إعادة التشغيل — تأكيد فقط','shutdown-confirm':'إيقاف التشغيل — تأكيد فقط','autodiag-home':'الصفحة الرئيسية للتشخيص','split-screen':'تقسيم الشاشة'}
names=['التشخيص الذكي','اختيار السيارة','وظائف الصيانة','التشخيص المحلي','TPMS','تحديثات البرنامج','سجل التشخيص','المساعد الذكي','محلل CAN','التقارير','التغطية','الإعدادات','قاعدة أكواد الأعطال','مخطط VCI','البيانات الحية','إدارة البيانات','أوسيلوسكوب','مراجع الإصلاح','بوابات OEM','تعريفات ECU']
for i,name in enumerate(names,1):captions['autodiag-'+str(i).zfill(2)]=name
for key,name in [('customers','العملاء'),('invoices','الفواتير'),('invoice_history','سجل الفواتير'),('camera','الكاميرا'),('pdf','قارئ PDF المدمج'),('media','الوسائط المدمجة'),('calculator','الحاسبة المدمجة')]:captions['workshop-'+key.replace('_','-')]=name
page=['<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8"><title>GITM OS — لقطات النظام الفعلية</title><style>body{background:#0c1b30;color:#eff6ff;font:18px sans-serif;margin:24px auto;max-width:1280px;padding:20px}figure{margin:28px 0;border:1px solid #375779;border-radius:16px;padding:16px}img{width:100%;height:auto;border-radius:8px}figcaption{padding:12px}a{color:#77c2ff}</style><h1>GITM OS — لقطات النظام الفعلية</h1><p>62 لقطة فعلية من اختبارات ISO نفسه، تشمل لقطة إضافية للشريط السفلي ظاهرًا، تشمل المظهر الداكن والنهاري وإعدادات التخصيص. تم فتح التطبيقات وصفحات الأزرار. لم تُنفذ أوامر تغيير السيارة أو التثبيت أو الإيقاف. العتاد اللاسلكي والكاميرا والمحول غير متوفر في هذا الاختبار؛ الصفحات تعرض حالتها الفعلية. فتح الصفحة لا يثبت نجاح وظيفتها على عتاد حقيقي.</p>']
page.append('<nav>'+ ' · '.join('<a href="#'+image.stem+'">'+html.escape(captions.get(image.stem,image.stem))+'</a>' for image in images)+'</nav>')
for image in images:
 label=html.escape(captions.get(image.stem,image.stem));data=base64.b64encode(image.read_bytes()).decode()
 page.append(f'<figure id="{image.stem}"><figcaption>{label} · {image.name}</figcaption><img loading="lazy" src="data:image/png;base64,{data}" alt="{label}"></figure>')
page.append('</html>');(root/'gallery.html').write_text('\n'.join(page))
with zipfile.ZipFile(root/'gallery.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
 for f in folder.iterdir():
  if f.is_file():z.write(f,'gallery/'+f.name)
 z.write(root/'gallery.html','gallery.html')
print(f'Published {len(images)} real screenshots')

from PIL import Image,ImageDraw,ImageFont,ImageStat
for path in images:
 if sum(ImageStat.Stat(Image.open(path).convert('RGB')).stddev)/3<8:raise RuntimeError('Inactive or blank screenshot: '+path.name)
columns=6;cellw=360;cellh=250;rows=(len(images)+columns-1)//columns
sheet=Image.new('RGB',(columns*cellw,rows*cellh),'#0c1b30');draw=ImageDraw.Draw(sheet)
for i,image in enumerate(images):
 thumb=Image.open(image).convert('RGB');thumb.thumbnail((350,218))
 x=(i%columns)*cellw+5;y=(i//columns)*cellh+5
 sheet.paste(thumb,(x,y));draw.text((x,y+222),image.stem,fill='#d8eaff')
sheet.save(root/'gallery-overview.png')

