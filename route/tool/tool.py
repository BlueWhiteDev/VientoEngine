import datetime
import hashlib
import json
import re
import secrets
import binascii

import aiosqlite
from sanic_ipware import get_client_ip
from sanic_session import Session

async def date_time():
    return str(datetime.datetime.today().strftime("%Y-%m-%d %H:%M:%S"))

async def user_name(request):
    if not request.ctx.session.get('id') or request.ctx.session.get('id') == 0:
        if not request.remote_addr:
            ip = "Error:ip"
        else:
            ip = request.remote_addr
        return ip
    else:
        return request.ctx.session['id']

async def user_link(name):
    if re.sub('\.([^.]*)\.([^.]*)$', '.*.*', name):
        return '<a href="/contribution/' + name + '/changes">' + name + '</a>'
    elif (':([^:]*):([^:]*)$', ':*:*', name):
        return '<a href="/contribution/' + name + '/changes">' + name + '</a>'
    else:
        return '<a href="/w/사용자:' + name + '">' + name + '</a>' 

async def namespace_check(data):
    return 0

async def wiki_set(data):
    setting_data = json.loads(open('data/setting.json', encoding = 'utf8').read())
    db = await aiosqlite.connect(setting_data['db_name'] + '.db')

    data_footer = await db.execute("select data from wiki_set where name = 'license'")
    footer = await data_footer.fetchall()

    data_wiki = await db.execute("select data from wiki_set where name = 'name'")
    wiki = await data_wiki.fetchall()

    date = ''

    if data != 0:
        data_edit = await db.execute("select date from doc_his where title = ? order by date desc", [data])
        date = await data_edit.fetchall()

    footer = footer[0][0] if footer else 'ARR'
    wiki = wiki[0][0] if wiki else 'Wiki'
    date = date[0][0] if date else 0

    return footer, wiki, date

async def check_user():
    return 0

async def check_admin(data):
    return 0

async def check_acl(data):
    return 0

async def history_add(title, data, date, ip, send, leng):
    setting_data = json.loads(open('data/setting.json', encoding = 'utf8').read())
    db = await aiosqlite.connect(setting_data['db_name'] + '.db')

    history_id = await db.execute("select id from doc_his where title = ? order by id + 0 desc limit 1", [title])
    history_id = await history_id.fetchall()

    send = re.sub('\(|\)|<|>', '', send)

    if len(send) > 128:
        send = send[:128]

    if history_id:
        id = str(int(history_id[0][0]) + 1) 
    else:
        id = '1'

    await db.execute("insert into doc_his (id, title, data, date, ip, send, leng) values (?, ?, ?, ?, ?, ?, ?)", [id, title, data, date, ip, send, leng])
    await db.commit()

async def password_encode(data, name):
    setting_data = json.loads(open('data/setting.json', encoding = 'utf8').read())
    db = await aiosqlite.connect(setting_data['db_name'] + '.db')

    encode_type = await db.execute('select data from wiki_set where name = "encode"')
    encode_type = await encode_type.fetchall()

    if encode_type[0][0] == 'sha256':
        return hashlib.sha256(bytes(data, 'utf-8')).hexdigest()

    elif encode_type[0][0] == 'sha3':
        return hashlib.sha3_256(bytes(data, 'utf-8')).hexdigest()

    elif encode_type[0][0] == 'pbkdf2-sha512':
        #TODO : Need slow password hash algorithm
        return CreateAuth(name, data)

async def _hashpass(username: str, password: str, salt: str):
    hashsalt = (salt + username).encode('utf-8')
    password = password.encode('utf-8')
    curhash = hashlib.pbkdf2_hmac('sha512',password,hashsalt,100000,dklen=256)
    curhash = binascii.hexlify(curhash)
    curhash = str(curhash)
    #print(curhash)
    return curhash[2:-1]

async def CreateAuth(username: str, password: str):
    #min: 16+
    SALT_LEN=16
    salt = secrets.token_hex(SALT_LEN)
    curhash = await _hashpass(username,password,salt)
    return str(salt+'$'+curhash)

async def VerifyAuth(username:str,password:str,authstr:str):
    setting_data = json.loads(open('data/setting.json', encoding = 'utf8').read())
    db = await aiosqlite.connect(setting_data['db_name'] + '.db')

    encode_type = await db.execute('select data from wiki_set where name = "encode"')
    encode_type = await encode_type.fetchall()

    if encode_type[0][0] == 'sha256':
        check_password = await db.execute('select pw from mbr where id = ?', [username])
        check_password = await check_password.fetchall()

        if hashlib.sha256(bytes(password, 'utf-8')).hexdigest() == check_password[0][0]:
            return 1
        else:
            return 0

    elif encode_type[0][0] == 'sha3':
        check_password = await db.execute('select pw from mbr where id = ?', [username])
        check_password = await check_password.fetchall()

        if hashlib.sha3_256(bytes(password, 'utf-8')).hexdigest() == check_password[0][0]:
            return 1
        else:
            return 0

    elif encode_type[0][0] == 'pbkdf2-sha512':
        salt = authstr.split('$')[0]
        hashdata = authstr.split('$')[1]
        if await _hashpass(username,password,salt) == hashdata:
            return 1
        else:
            return 0