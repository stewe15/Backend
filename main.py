from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import sqlalchemy as sq
import sqlalchemy.orm
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session
import uvicorn
app = FastAPI()
connected_clients = []
class Messages_queue():
    name = ''
    msgs = ''
engine = sq.create_engine('sqlite:///UsersDb')
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = sqlalchemy.orm.declarative_base()
session = Session(bind=engine)
class ModelUsers(Base):
    __tablename__ = 'users'
    id = sq.Column(sq.Integer, primary_key=True, index=True)
    name = sq.Column(sq.String(256), index=True)
    password = sq.Column(sq.String(256), index=True)
Base.metadata.create_all(bind=engine)
messages_queue = []
class ConnectedUser():
    ws = ''
    name = ''
@app.websocket("/ws/admin")
async def import_to_db(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        data_parsed = data.split('\t')
        if data_parsed[0] != '' and data_parsed[1] != '':
            item = ModelUsers()
            item.name = data_parsed[0]
            item.password = data_parsed[1]
            db = SessionLocal()
            try:
                db.add(item)
                db.commit()
                db.refresh(item)
                await websocket.send_text(f"Сохранено в базе: {data}")
            except Exception as e:
                await websocket.send_text(f"Ошибка: {str(e)}")
            finally:
                db.close()
        else:
            await websocket.send_text("Ошибка: имя или пароль были нулевыми")
@app.websocket("/ws/auth")
async def authoristion(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        data_splited = data.split('\t')
        try:
            obj = session.query(ModelUsers).all()
            for i in range(len(obj)):
                if data_splited[0] == obj[i].name and data_splited[1] == obj[i].password:
                    await websocket.send_text("True")
        except:
            await websocket.send_text("False")
@app.websocket("/ws/getusers")
async def get_users(websocket: WebSocket):
    await websocket.accept()
    db = SessionLocal()
    try:
        users = db.query(ModelUsers).all()
        for user in users:
            await websocket.send_text(user.name)
    finally:
        db.close()
@app.websocket("/ws/chatUser/{username}/{to}")
async def chat(websocket: WebSocket, username: str, to: str):
    await websocket.accept()
    flag = False
    obj2 = ConnectedUser()
    obj2.ws = websocket
    obj2.name = username
    connected_clients.append(obj2)
    for ms in messages_queue:
        if ms.name == username:
            await websocket.send_text(ms.msgs)
            ms.name = ''
            ms.msgs = ''

    try:
        while True:
            data = await websocket.receive_text()
            message = f"{username}: {data}"
            msageforuser = f"Вы: {data}"

            for i in connected_clients:
                if i.name == to:
                    await i.ws.send_text(message)
                    flag = True
                    break
            for i in connected_clients:
                if i.name == username:
                    await i.ws.send_text(msageforuser)
                    break
            if not flag:
                obj = Messages_queue()
                obj.name = to
                obj.msgs = message
                messages_queue.append(obj)
                await websocket.send_text(
                        f"Пользователь {to} не подключён ваше сообщение ({message}) добавлено в очередь")

    except Exception as e:
        print(f"Error: {e}")
