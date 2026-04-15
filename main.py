from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
#from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, ForeignKey
from pydantic import BaseModel
from jose import JWTError, jwt
from typing import List
import shutil
import os
import uuid
from supabase import create_client, Client

import models, schemas, auth_utils, database

# ==========================================
# CONFIGURACIÓN DE SUPABASE STORAGE
# ==========================================
# 🌟 REEMPLAZA estas variables con tus datos reales de Supabase:
SUPABASE_URL = "https://ezdpfgcychysiqehknrw.supabase.co" 
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV6ZHBmZ2N5Y2h5c2lxZWhrbnJ3Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTY3NDA4NywiZXhwIjoyMDkxMjUwMDg3fQ.XdxcWZxXCrIFgqbwzvUs7nIcSvJR5Xkb1WO9hIVWoOA"

# Creamos el cliente que hablará con el disco duro de Supabase
supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================
# NUEVO MODELO DE BASE DE DATOS (Solicitudes)
# ==========================================
class Request(models.Base):
    __tablename__ = "requests"
    id = Column(Integer, primary_key=True, index=True)
    creator_name = Column(String, index=True)
    reason = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"))

# Crea las tablas si no existen en la base de datos (incluyendo la nueva de Requests)
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

# Configuración de CORS
origins = [
    "http://localhost:5173",
    "https://creators-frontend-lovat.vercel.app" # <-- ¡Pon tu URL real de Vercel aquí!
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Crear carpetas locales
os.makedirs("uploads/avatars", exist_ok=True)
os.makedirs("uploads/posts", exist_ok=True)
#app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# ==========================================
# SEGURIDAD Y AUTENTICACIÓN
# ==========================================
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, auth_utils.SECRET_KEY, algorithms=[auth_utils.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
    return user


# ==========================================
# ENDPOINTS DE USUARIOS
# ==========================================
@app.post("/auth/register", response_model=schemas.UserOut)
def register(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    
    hashed = auth_utils.hash_password(user.password)
    new_user = models.User(
        email=user.email, 
        hashed_password=hashed, 
        full_name=user.full_name,
        role=user.role 
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/auth/login")
def login(user_credentials: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.email == user_credentials.username).first()
    if not user or not auth_utils.verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

    access_token = auth_utils.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer", "user": user}

@app.get("/users/me", response_model=schemas.UserOut)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user

# ==========================================
# 🛑 TRUCO DE DESARROLLADOR (Borrar en Producción)
# ==========================================
@app.get("/api/dev/make-admin/{email}")
def make_me_admin(email: str, db: Session = Depends(database.get_db)):
    """ Convierte a cualquier usuario en Super Admin al instante """
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        return {"error": "Usuario no encontrado. Verifica bien tu correo."}
    
    user.role = "admin"
    db.commit()
    return {"message": f"¡Éxito! El usuario {email} ahora es ADMIN. Cierra sesión y vuelve a entrar en React."}


# ==========================================
# ENDPOINTS DE PÁGINAS (HUBS) - ACTUALIZADOS PARA SUPABASE
# ==========================================

# 🌟 ESTE ES EL ENDPOINT QUE TE FALTABA PARA EL ERROR 404
class HubCreateTemp(BaseModel):
    name: str
    description: str

@app.post("/api/hubs")
def create_hub(
    hub_data: HubCreateTemp, 
    db: Session = Depends(database.get_db), 
    current_user: models.User = Depends(get_current_user)
):
    # Verificamos que tenga permisos
    if current_user.role not in ["admin", "subadmin", "creator"]:
        raise HTTPException(status_code=403, detail="No tienes permisos para crear comunidades")

    # Creamos el registro en la base de datos
    new_hub = models.CreatorPage(
        name=hub_data.name,
        description=hub_data.description
    )
    
    db.add(new_hub)
    db.commit()
    db.refresh(new_hub)
    
    return new_hub

@app.post("/api/hubs/{hub_id}/avatar")
async def upload_hub_avatar(hub_id: int, file: UploadFile = File(...), db: Session = Depends(database.get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.role not in ["admin", "subadmin"]: raise HTTPException(status_code=403, detail="Permiso denegado")
    hub = db.query(models.CreatorPage).filter(models.CreatorPage.id == hub_id).first()
    
    # 🌟 SUBIDA A SUPABASE
    ext = file.filename.split(".")[-1]
    file_path_in_bucket = f"avatars/hub_{hub_id}_avatar_{uuid.uuid4().hex}.{ext}" # Le agregamos UUID para que no haya caché
    
    # Leemos el archivo en memoria y lo subimos
    file_contents = await file.read()
    supabase_client.storage.from_("creators_uploads").upload(file_path_in_bucket, file_contents)
    
    # Generamos la URL pública
    public_url = supabase_client.storage.from_("creators_uploads").get_public_url(file_path_in_bucket)
    
    hub.avatar_url = public_url
    db.commit()
    db.refresh(hub)
    return hub

@app.post("/api/hubs/{hub_id}/banner")
async def upload_hub_banner(hub_id: int, file: UploadFile = File(...), db: Session = Depends(database.get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.role not in ["admin", "subadmin"]: raise HTTPException(status_code=403, detail="Permiso denegado")
    hub = db.query(models.CreatorPage).filter(models.CreatorPage.id == hub_id).first()
    
    # 🌟 SUBIDA A SUPABASE
    ext = file.filename.split(".")[-1]
    file_path_in_bucket = f"banners/hub_{hub_id}_banner_{uuid.uuid4().hex}.{ext}"
    
    file_contents = await file.read()
    supabase_client.storage.from_("creators_uploads").upload(file_path_in_bucket, file_contents)
    
    public_url = supabase_client.storage.from_("creators_uploads").get_public_url(file_path_in_bucket)
    
    hub.banner_url = public_url
    db.commit()
    db.refresh(hub)
    return hub

# ==========================================
# ENDPOINTS DE LECTURA (GET) PARA REACT
# ==========================================

@app.get("/api/hubs")
def get_all_hubs(db: Session = Depends(database.get_db)):
    """ Devuelve todas las comunidades en formato JSON perfecto para React """
    hubs = db.query(models.CreatorPage).all()
    
    # Empacamos los datos a mano para que React los pueda leer sin errores
    resultado = []
    for h in hubs:
        resultado.append({
            "id": h.id,
            "name": h.name,
            "description": h.description,
            "avatar_url": getattr(h, "avatar_url", None),
            "banner_url": getattr(h, "banner_url", None)
        })
    return resultado

@app.get("/api/hubs/{hub_id}/posts")
def get_hub_posts(hub_id: int, db: Session = Depends(database.get_db)):
    """ Devuelve los posts de una comunidad específica (React lo usa para contar) """
    posts = db.query(models.Post).filter(models.Post.page_id == hub_id).all()
    
    resultado = []
    for p in posts:
        resultado.append({
            "id": p.id,
            "title": p.title,
            "content_url": getattr(p, "content_url", None)
        })
    return resultado

# ==========================================
# ENDPOINT PARA VER UNA SOLA COMUNIDAD
# ==========================================

@app.get("/api/hubs/{hub_id}")
def get_single_hub(hub_id: int, db: Session = Depends(database.get_db)):
    """ Devuelve la información de una sola comunidad """
    hub = db.query(models.CreatorPage).filter(models.CreatorPage.id == hub_id).first()
    
    if not hub:
        raise HTTPException(status_code=404, detail="Comunidad no encontrada")
    
    # Empacamos los datos en JSON para React
    return {
        "id": hub.id,
        "name": hub.name,
        "description": hub.description,
        "avatar_url": getattr(hub, "avatar_url", None),
        "banner_url": getattr(hub, "banner_url", None)
    }

# ==========================================
# ENDPOINTS DE POSTS - ACTUALIZADO PARA SUPABASE
# ==========================================

@app.post("/api/posts", response_model=schemas.PostOut)
async def create_post(
    title: str = Form(...), page_id: int = Form(...), file: UploadFile = File(...),
    db: Session = Depends(database.get_db), current_user: models.User = Depends(get_current_user)
):
    if current_user.role not in ["admin", "subadmin"]:
        raise HTTPException(status_code=403, detail="Solo los administradores pueden publicar")

    # 🌟 SUBIDA A SUPABASE
    ext = file.filename.split(".")[-1]
    file_path_in_bucket = f"posts/post_{uuid.uuid4().hex}.{ext}"
    
    file_contents = await file.read()
    supabase_client.storage.from_("creators_uploads").upload(file_path_in_bucket, file_contents)
    
    public_url = supabase_client.storage.from_("creators_uploads").get_public_url(file_path_in_bucket)
    
    new_post = models.Post(
        title=title, content_url=public_url, # Usamos la URL que nos da la nube
        uploader_id=current_user.id, page_id=page_id
    )
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return new_post


# ==========================================
# ENDPOINT DE SOLICITUDES (FANS)
# ==========================================
class RequestCreate(BaseModel):
    creator_name: str
    reason: str

@app.post("/api/requests")
def create_community_request(request_data: RequestCreate, db: Session = Depends(database.get_db), current_user: models.User = Depends(get_current_user)):
    new_request = Request(
        creator_name=request_data.creator_name,
        reason=request_data.reason,
        user_id=current_user.id
    )
    db.add(new_request)
    db.commit()
    return {"message": "Sugerencia enviada a los administradores"}

@app.get("/api/requests")
def get_all_requests(db: Session = Depends(database.get_db), current_user: models.User = Depends(get_current_user)):
    """ Devuelve todas las sugerencias (Solo Admins y Subadmins) """
    if current_user.role not in ["admin", "subadmin"]:
        raise HTTPException(status_code=403, detail="Acceso denegado al buzón")
    
    # Traemos todas las solicitudes de la base de datos
    requests = db.query(Request).all()
    return requests

# ==========================================
# ENDPOINTS DE MODERACIÓN (PANEL ADMIN)
# ==========================================
class RoleUpdate(schemas.BaseModel):
    role: str

@app.get("/api/admin/users")
def get_all_users(db: Session = Depends(database.get_db), current_user: models.User = Depends(get_current_user)):
    """ Devuelve todos los usuarios (Solo para Admins y Subadmins) """
    if current_user.role not in ["admin", "subadmin"]:
        raise HTTPException(status_code=403, detail="Acceso denegado")
    
    # Traemos información básica de todos
    users = db.query(models.User).all()
    return [{"id": u.id, "email": u.email, "full_name": u.full_name, "role": u.role, "is_banned": u.is_banned} for u in users]

@app.put("/api/admin/users/{target_id}/role")
def update_user_role(target_id: int, payload: RoleUpdate, db: Session = Depends(database.get_db), current_user: models.User = Depends(get_current_user)):
    """ Sube o baja de rango a un usuario (¡SOLO SUPER ADMIN!) """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Solo el Super Admin puede cambiar roles")
    
    user = db.query(models.User).filter(models.User.id == target_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
    user.role = payload.role
    db.commit()
    return {"message": f"Rol actualizado a {payload.role}"}

@app.put("/api/admin/users/{target_id}/ban")
def toggle_ban_user(target_id: int, db: Session = Depends(database.get_db), current_user: models.User = Depends(get_current_user)):
    """ Banea o desbanea a un usuario (Admins y Subadmins) """
    if current_user.role not in ["admin", "subadmin"]:
        raise HTTPException(status_code=403, detail="Acceso denegado")
        
    user = db.query(models.User).filter(models.User.id == target_id).first()
    
    # Un subadmin no puede banear a un admin
    if current_user.role == "subadmin" and user.role == "admin":
        raise HTTPException(status_code=403, detail="No puedes castigar a un superior")
        
    user.is_banned = not user.is_banned
    db.commit()
    return {"message": "Estado de baneo actualizado", "is_banned": user.is_banned}

# ==========================================
# ENDPOINTS DE CONTROL DE POSTS (EDITAR / ELIMINAR)
# ==========================================

@app.delete("/api/posts/{post_id}")
def delete_post(post_id: int, db: Session = Depends(database.get_db), current_user: models.User = Depends(get_current_user)):
    """ Elimina un post (Solo Admins y Subadmins) """
    if current_user.role not in ["admin", "subadmin"]:
        raise HTTPException(status_code=403, detail="No tienes permisos para eliminar publicaciones")
        
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post no encontrado")
        
    # Eliminamos el registro de la base de datos
    db.delete(post)
    db.commit()
    
    # Nota para la Fase 3: Aquí también deberíamos programar que la imagen se borre del Storage de Supabase para ahorrar espacio.
    return {"message": "Publicación eliminada correctamente"}


@app.put("/api/posts/{post_id}")
def update_post(
    post_id: int, 
    title: str = Form(...), 
    db: Session = Depends(database.get_db), 
    current_user: models.User = Depends(get_current_user)
):
    """ Edita el título de un post (Solo Admins y Subadmins) """
    if current_user.role not in ["admin", "subadmin"]:
        raise HTTPException(status_code=403, detail="No tienes permisos para editar publicaciones")
        
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post no encontrado")
        
    # Actualizamos los datos
    post.title = title
    db.commit()
    db.refresh(post)
    
    return post
