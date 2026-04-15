from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

# 👤 ENTIDAD ORIGINAL: Usuarios del sistema (Admins, Fans, etc.)
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    bio = Column(Text, nullable=True)
    
    # 🛡️ Sistema de Roles (fan, creator, admin, subadmin)
    role = Column(String, default="fan")
    
    # 🚫 Sistema de Baneos (active, banned)
    status = Column(String, default="active")
    
    # 📸 Foto de perfil personalizada
    avatar_url = Column(String, nullable=True)

    # Estado de la cuenta (active, banned)
    is_banned = Column(Boolean, default=False)


# 🌟 NUEVA ENTIDAD: La Página/Hub dedicada a un creador (ej. "MrBeast Archive")
class CreatorPage(Base):
    __tablename__ = "creator_pages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False) 
    description = Column(Text, nullable=True)
    avatar_url = Column(String, nullable=True)
    banner_url = Column(String, nullable=True)
    
    # Para saber cuánto dinero ha recaudado esta página específica
    total_raised = Column(Integer, default=0) 

    # Relación: Una página tiene muchos posts
    posts = relationship("Post", back_populates="page")


# 📸 NUEVA ENTIDAD: El contenido que los usuarios suben a las páginas
class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content_url = Column(String, nullable=False) # La ruta de la imagen/video local
    
    # Llaves foráneas: ¿Quién lo subió y a qué página pertenece?
    uploader_id = Column(Integer, ForeignKey("users.id"))
    page_id = Column(Integer, ForeignKey("creator_pages.id"))

    # Relaciones bidireccionales para que SQLAlchemy navegue los datos fácilmente
    page = relationship("CreatorPage", back_populates="posts")

class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(String, nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id"))
    user_id = Column(Integer, ForeignKey("users.id"))

class Reaction(Base):
    __tablename__ = "reactions"
    id = Column(Integer, primary_key=True, index=True)
    emoji = Column(String, nullable=False) # Aquí guardaremos "❤️", "🔥", etc.
    post_id = Column(Integer, ForeignKey("posts.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    uploader = relationship("User")

class PostMedia(Base):
    __tablename__ = "post_media"
    id = Column(Integer, primary_key=True, index=True)
    media_url = Column(String, nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id"))
