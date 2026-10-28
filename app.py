from flask import Flask, request, redirect, url_for, render_template_string, flash, Response
import sqlite3, os, csv, io
from datetime import date
app=Flask(__name__); app.secret_key=os.environ.get('TRAVELPRO_SECRET_KEY','change-this-before-deployment')
DB=os.path.join(os.path.dirname(__file__),'travel_agency.db')
def con():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON'); return c
with con() as c:
 c.executescript('''
 CREATE TABLE IF NOT EXISTS customers(id INTEGER PRIMARY KEY, code TEXT UNIQUE, name TEXT NOT NULL, phone TEXT,email TEXT,passport TEXT,nationality TEXT,address TEXT,created TEXT);
 CREATE TABLE IF NOT EXISTS bookings(id INTEGER PRIMARY KEY,ref TEXT UNIQUE,customer_id INTEGER,service TEXT,destination TEXT,travel_date TEXT,return_date TEXT,supplier TEXT,status TEXT DEFAULT 'Pending',total REAL DEFAULT 0,paid REAL DEFAULT 0,notes TEXT,FOREIGN KEY(customer_id) REFERENCES customers(id));
 CREATE TABLE IF NOT EXISTS transactions(id INTEGER PRIMARY KEY,txn_date TEXT,type TEXT,category TEXT,description TEXT,amount REAL,payment_method TEXT);
 CREATE TABLE IF NOT EXISTS packages(id INTEGER PRIMARY KEY,name TEXT,destination TEXT,duration TEXT,price REAL,description TEXT);
 ''')
STYLE='''<style>
:root{--navy:#12333d;--teal:#147d82;--gold:#d5a84b;--bg:#f3f6f8;--line:#dce5e8}*{box-sizing:border-box}body{margin:0;background:var(--bg);font:15px Arial;color:#18343c}header{background:linear-gradient(120deg,#12333d,#1c4a56);color:white;padding:20px 28px;font-size:23px;font-weight:bold}header span{color:var(--gold)}.shell{display:grid;grid-template-columns:220px 1fr;min-height:calc(100vh - 70px)}nav{background:#102f38;padding:15px}nav a{display:block;color:#e2eeee;padding:12px;text-decoration:none;border-radius:7px;font-weight:bold}nav a:hover{background:var(--teal)}main{padding:25px;min-width:0}h1{margin:0 0 7px}h2{font-size:18px}.muted{color:#617780}.panel,.metric{background:white;border:1px solid var(--line);border-radius:12px;padding:18px;margin:16px 0}.cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.metric strong{display:block;font-size:22px;margin-top:8px}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.field label{display:block;font-size:12px;font-weight:bold;color:#617780;margin-bottom:5px}.field input,.field select,.field textarea{width:100%;padding:10px;border:1px solid #ccd9dd;border-radius:7px;font:inherit}.field textarea{min-height:70px}button,.btn{background:var(--teal);color:white;border:0;border-radius:7px;padding:10px 14px;font-weight:bold;text-decoration:none;display:inline-block;cursor:pointer;margin-top:12px}.btn.gold{background:var(--gold);color:#18343c}.top{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap}.tablewrap{overflow:auto}table{border-collapse:collapse;width:100%;min-width:620px}th,td{text-align:left;padding:11px;border-bottom:1px solid #edf1f2}th{background:#f8fafb;color:#617780;font-size:12px;text-transform:uppercase}.pill{background:#e5f4f2;color:#12686c;border-radius:20px;padding:4px 8px;font-size:12px;font-weight:bold}.search{padding:10px;border:1px solid var(--line);border-radius:7px}.notice{background:#fff4d7;padding:12px;border-radius:8px;margin-bottom:12px}.empty{text-align:center;color:#617780;padding:24px}@media(max-width:850px){.shell{grid-template-columns:1fr}nav{display:flex;overflow:auto;padding:8px}nav a{white-space:nowrap}.cards{grid-template-columns:repeat(2,1fr)}.grid{grid-template-columns:repeat(2,1fr)}main{padding:14px}}@media(max-width:520px){.cards,.grid{grid-template-columns:1fr}header{padding:16px}}
</style>'''
def money(n): return 'UGX {:,.0f}'.format(float(n or 0))
def rows(sql,args=()):
 with con() as c:return c.execute(sql,args).fetchall()
def fld(label,name,kind='text',required=False,options=None):
 req='required' if required else ''
 if options: ctrl='<select name="%s" %s>%s</select>'%(name,req,''.join('<option value="%s">%s</option>'%(v,l) for v,l in options))
 else: ctrl='<input name="%s" type="%s" %s>'%(name,kind,req)
 return '<div class="field"><label>%s</label>%s</div>'%(label,ctrl)
def render(title,body,active):
 nav=''.join('<a href="%s" style="background:%s">%s</a>'%(u,'#147d82' if active==k else 'transparent',label) for k,u,label in [('home','/','▦ Dashboard'),('customers','/customers','♙ Customers'),('bookings','/bookings','✈ Bookings'),('packages','/packages','◎ Tour packages'),('finance','/finance','▤ Finance'),('reports','/reports','▥ Reports'),('settings','/settings','⚙ Settings & backup')])
 return render_template_string('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+title+' | TravelPro Uganda</title>'+STYLE+'</head><body><header>✈ TravelPro <span>Uganda</span><div style="font-size:12px;font-weight:normal">Travel agency management · Currency UGX</div></header><div class="shell"><nav>'+nav+'</nav><main>{% with ms=get_flashed_messages() %}{% for m in ms %}<div class="notice">{{m}}</div>{% endfor %}{% endwith %}'+body+'</main></div><script>document.querySelectorAll("[data-search]").forEach(x=>x.oninput=()=>document.querySelectorAll(x.dataset.search+" tbody tr").forEach(r=>r.style.display=r.innerText.toLowerCase().includes(x.value.toLowerCase())?"":"none"))</script></body></html>')
@app.route('/')
def home():
 customers=rows('select count(*) n from customers')[0]['n']; bookings=rows('select count(*) n from bookings')[0]['n']
 inc=rows("select coalesce(sum(amount),0) n from transactions where type='Income'")[0]['n']; exp=rows("select coalesce(sum(amount),0) n from transactions where type='Expense'")[0]['n']
 outstanding=rows('select coalesce(sum(total-paid),0) n from bookings')[0]['n']
 recent=rows('select b.*,c.name customer from bookings b left join customers c on c.id=b.customer_id order by b.id desc limit 8')
 body=f'<div class="top"><div><h1>Dashboard</h1><div class="muted">Business overview · {date.today()}</div></div><a class="btn" href="/bookings">＋ New booking</a></div><div class="cards">'+''.join('<div class="metric"><span class="muted">%s</span><strong>%s</strong></div>'%x for x in [('Customers',customers),('Bookings',bookings),('Income received',money(inc)),('Net balance',money(inc-exp)),('Outstanding',money(outstanding)),('Expenses',money(exp))])+'</div><section class="panel"><h2>Recent bookings</h2>'+table(['Reference','Customer','Service','Destination','Travel date','Status','Balance'],[[r['ref'],r['customer'] or '—',r['service'],r['destination'],r['travel_date'] or '—',r['status'],money(r['total']-r['paid'])] for r in recent])+'</section>'
 return render('Dashboard',body,'home')
def table(headers,data):
 s='<div class="tablewrap"><table><thead><tr>'+''.join('<th>'+str(h)+'</th>' for h in headers)+'</tr></thead><tbody>'
 s+=''.join('<tr>'+''.join('<td>'+str(v if v is not None else '—')+'</td>' for v in row)+'</tr>' for row in data)
 return s+'</tbody></table></div>' if data else s+'<tr><td colspan="'+str(len(headers))+'" class="empty">No records yet.</td></tr></tbody></table></div>'
@app.route('/customers',methods=['GET','POST'])
def customers():
 if request.method=='POST':
  d=request.form
  try:
   with con() as c:c.execute('insert into customers(code,name,phone,email,passport,nationality,address,created) values(?,?,?,?,?,?,?,?)',(d.get('code') or None,d['name'],d.get('phone'),d.get('email'),d.get('passport'),d.get('nationality'),d.get('address'),str(date.today())))
   flash('Customer saved.')
  except sqlite3.IntegrityError:flash('Customer code already exists.')
  return redirect('/customers')
 rs=rows('select * from customers order by id desc')
 body='<h1>Customers</h1><p class="muted">Customer profiles and travel documents</p><section class="panel"><h2>Add customer</h2><form method="post"><div class="grid">'+fld('Customer code','code')+fld('Full name *','name',required=True)+fld('Phone','phone')+fld('Email','email','email')+fld('Passport / national ID','passport')+fld('Nationality','nationality')+fld('Address','address')+'</div><button>Save customer</button></form></section><section class="panel"><div class="top"><h2>Customer register</h2><input class="search" placeholder="Search…" data-search="#cust"></div><div id="cust">'+table(['Code','Name','Phone','Email','Passport / ID','Nationality'],[[r['code'],r['name'],r['phone'],r['email'],r['passport'],r['nationality']] for r in rs])+'</div></section>'
 return render('Customers',body,'customers')
@app.route('/bookings',methods=['GET','POST'])
def bookings():
 if request.method=='POST':
  d=request.form; ref=d.get('ref') or 'TP-'+date.today().strftime('%y%m%d')+'-'+str(__import__('time').time_ns())[-5:]
  try:
   with con() as c:c.execute('insert into bookings(ref,customer_id,service,destination,travel_date,return_date,supplier,status,total,paid,notes) values(?,?,?,?,?,?,?,?,?,?,?)',(ref,int(d['customer_id']) if d.get('customer_id') else None,d['service'],d['destination'],d.get('travel_date'),d.get('return_date'),d.get('supplier'),d['status'],float(d.get('total') or 0),float(d.get('paid') or 0),d.get('notes')))
   flash('Booking saved.')
  except (ValueError,sqlite3.IntegrityError):flash('Could not save booking. Check reference and amounts.')
  return redirect('/bookings')
 cs=rows('select id,name from customers order by name'); opts=[('', '— Select customer —')]+[(str(r['id']),r['name']) for r in cs]
 rs=rows('select b.*,c.name customer from bookings b left join customers c on c.id=b.customer_id order by b.id desc')
 body='<h1>Bookings</h1><p class="muted">Flights, safaris, visa assistance, hotels and transport</p><section class="panel"><h2>Create booking</h2><form method="post"><div class="grid">'+fld('Reference (optional)','ref')+fld('Customer','customer_id',options=opts)+fld('Service','service',required=True,options=[('Flight','Flight'),('Tour / Safari','Tour / Safari'),('Visa assistance','Visa assistance'),('Hotel','Hotel'),('Transport','Transport')])+fld('Destination / details','destination',required=True)+fld('Travel date','travel_date','date')+fld('Return date','return_date','date')+fld('Supplier','supplier')+fld('Status','status',options=[('Pending','Pending'),('Confirmed','Confirmed'),('In progress','In progress'),('Completed','Completed'),('Cancelled','Cancelled')])+fld('Total amount UGX','total','number')+fld('Amount paid UGX','paid','number')+fld('Notes','notes')+'</div><button>Save booking</button></form></section><section class="panel"><div class="top"><h2>Booking register</h2><input class="search" placeholder="Search…" data-search="#book"></div><div id="book">'+table(['Reference','Customer','Service','Destination','Travel date','Status','Total','Paid','Balance'],[[r['ref'],r['customer'],r['service'],r['destination'],r['travel_date'],r['status'],money(r['total']),money(r['paid']),money(r['total']-r['paid'])] for r in rs])+'</div></section>'
 return render('Bookings',body,'bookings')
@app.route('/finance',methods=['GET','POST'])
def finance():
 if request.method=='POST':
  d=request.form
  try:
   with con() as c:c.execute('insert into transactions(txn_date,type,category,description,amount,payment_method) values(?,?,?,?,?,?)',(d.get('txn_date') or str(date.today()),d['type'],d['category'],d.get('description'),float(d['amount']),d.get('payment_method')))
   flash('Transaction saved.')
  except ValueError:flash('Enter a valid amount.')
  return redirect('/finance')
 rs=rows('select * from transactions order by txn_date desc,id desc'); inc=sum(r['amount'] for r in rs if r['type']=='Income'); exp=sum(r['amount'] for r in rs if r['type']=='Expense')
 body='<h1>Finance</h1><p class="muted">Income and expenses · Ugandan Shillings</p><div class="cards">'+''.join('<div class="metric"><span>%s</span><strong>%s</strong></div>'%x for x in [('Income',money(inc)),('Expenses',money(exp)),('Net balance',money(inc-exp))])+'</div><section class="panel"><h2>Record transaction</h2><form method="post"><div class="grid">'+fld('Date','txn_date','date')+fld('Type','type',options=[('Income','Income'),('Expense','Expense')])+fld('Category','category',required=True,options=[('Booking payment','Booking payment'),('Flight','Flight'),('Tour / Safari','Tour / Safari'),('Visa','Visa'),('Hotel','Hotel'),('Transport','Transport'),('Office expense','Office expense'),('Supplier payment','Supplier payment'),('Other','Other')])+fld('Description','description')+fld('Amount UGX','amount','number',True)+fld('Payment method','payment_method',options=[('Cash','Cash'),('Bank transfer','Bank transfer'),('Mobile money','Mobile money'),('Card','Card'),('Other','Other')])+'</div><button>Save transaction</button></form></section><section class="panel"><h2>Transaction ledger</h2>'+table(['Date','Type','Category','Description','Payment method','Amount'],[[r['txn_date'],r['type'],r['category'],r['description'],r['payment_method'],money(r['amount'])] for r in rs])+'</section>'
 return render('Finance',body,'finance')
@app.route('/packages',methods=['GET','POST'])
def packages():
 if request.method=='POST':
  d=request.form
  with con() as c:c.execute('insert into packages(name,destination,duration,price,description) values(?,?,?,?,?)',(d['name'],d.get('destination'),d.get('duration'),float(d.get('price') or 0),d.get('description')))
  flash('Package saved.');return redirect('/packages')
 rs=rows('select * from packages order by id desc')
 body='<h1>Tour packages</h1><p class="muted">Safari and tour catalogue</p><section class="panel"><h2>Add package</h2><form method="post"><div class="grid">'+fld('Package name','name',required=True)+fld('Destination','destination')+fld('Duration','duration')+fld('Price per person UGX','price','number')+fld('Description','description')+'</div><button>Save package</button></form></section><section class="panel"><h2>Package catalogue</h2>'+table(['Package','Destination','Duration','Price','Description'],[[r['name'],r['destination'],r['duration'],money(r['price']),r['description']] for r in rs])+'</section>'
 return render('Tour packages',body,'packages')
@app.route('/reports')
def reports():
 rs=rows('select service,count(*) n,coalesce(sum(total),0) total,coalesce(sum(paid),0) paid from bookings group by service')
 body='<div class="top"><div><h1>Reports</h1><p class="muted">Booking summaries and CSV exports</p></div><a class="btn" href="/export/customers">Export customers</a><a class="btn" href="/export/bookings">Export bookings</a><a class="btn gold" href="/export/transactions">Export finance</a></div><section class="panel"><h2>Bookings by service</h2>'+table(['Service','Bookings','Total value','Paid','Outstanding'],[[r['service'],r['n'],money(r['total']),money(r['paid']),money(r['total']-r['paid'])] for r in rs])+'</section>'
 return render('Reports',body,'reports')
@app.route('/export/<kind>')
def export(kind):
 schema={'customers':('customers',['id','code','name','phone','email','passport','nationality','address','created']),'bookings':('bookings',['id','ref','customer_id','service','destination','travel_date','return_date','supplier','status','total','paid','notes']),'transactions':('transactions',['id','txn_date','type','category','description','amount','payment_method'])}
 if kind not in schema:return 'Not found',404
 tbl,cols=schema[kind]; rs=rows('select '+','.join(cols)+' from '+tbl); out=io.StringIO(); w=csv.writer(out);w.writerow(cols)
 for r in rs:w.writerow([r[x] for x in cols])
 return Response(out.getvalue(),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename=travelpro_'+kind+'.csv'})
@app.route('/settings')
def settings():
 body='<h1>Settings & backup</h1><section class="panel"><h2>Database backup</h2><p>Records are stored in <b>travel_agency.db</b> beside this application. Back it up regularly and secure it because it contains customer and passport-related information.</p><a class="btn" href="/backup">Download database backup</a></section><section class="panel"><h2>Deployment notes</h2><ul><li>Currency: UGX.</li><li>This app does not issue airline tickets, connect to live airline inventory, process mobile money automatically or submit visa applications.</li><li>Before public deployment, add authentication, role permissions, HTTPS and a strong secret key.</li></ul></section>'
 return render('Settings',body,'settings')
@app.route('/backup')
def backup():
 return Response(open(DB,'rb').read(),mimetype='application/octet-stream',headers={'Content-Disposition':'attachment; filename=travel_agency_backup.db'})
if __name__=='__main__': app.run(host='127.0.0.1',port=5000,debug=False)
