from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Table, Boolean
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# Association table for topic hierarchy (many-to-many to support multiple parents)
topic_hierarchy = Table(
    'topic_hierarchy',
    Base.metadata,
    Column('parent_id', Integer, ForeignKey('topics.id'), primary_key=True),
    Column('child_id', Integer, ForeignKey('topics.id'), primary_key=True)
)

class Topic(Base):
    __tablename__ = 'topics'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    order_index = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    notes = relationship("Note", back_populates="topic", cascade="all, delete-orphan")
    
    # Children/Parents relationship
    children = relationship(
        "Topic",
        secondary=topic_hierarchy,
        primaryjoin=id==topic_hierarchy.c.parent_id,
        secondaryjoin=id==topic_hierarchy.c.child_id,
        order_by="Topic.order_index",
        backref="parents"
    )

    def __repr__(self):
        return f"<Topic(name='{self.name}')>"

class Note(Base):
    __tablename__ = 'notes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    topic_id = Column(Integer, ForeignKey('topics.id'), nullable=True) # None for Daily Notes unless linked
    title = Column(String(255), nullable=True)
    content = Column(Text, nullable=False, default="")
    section_type = Column(String(50), default="Notes") # e.g. Notes, Questions, Resources, Flashcards
    is_daily = Column(Boolean, default=False)
    daily_date = Column(String(50), nullable=True) # e.g., "2026-07-17"
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    topic = relationship("Topic", back_populates="notes")
    references = relationship("NoteReference", back_populates="note", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Note(id={self.id}, title='{self.title}')>"

class NoteReference(Base):
    """
    Represents a backlink. A note references a topic via [[Topic Name]]
    """
    __tablename__ = 'note_references'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    note_id = Column(Integer, ForeignKey('notes.id'), nullable=False)
    referenced_topic_id = Column(Integer, ForeignKey('topics.id'), nullable=False)
    
    note = relationship("Note", back_populates="references")
    referenced_topic = relationship("Topic")
