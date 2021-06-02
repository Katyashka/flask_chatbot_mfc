from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

ug_relations = db.Table('UG_relations',
                        db.Column('user_id', db.Integer, db.ForeignKey('users.id')),
                        db.Column('group_id', db.Integer, db.ForeignKey('groups.id'))
                        )

gs_relations = db.Table('GS_relations',
                        db.Column('group_id', db.Integer, db.ForeignKey('groups.id')),
                        db.Column('source_id', db.Integer, db.ForeignKey('sources.id'))
                        )


class Users(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    surname = db.Column(db.String(255))
    name = db.Column(db.String(255))
    patronymic = db.Column(db.String(255))
    chat_id = db.Column(db.Integer(), nullable=False)
    username = db.Column(db.String(12), nullable=False)
    active = db.Column(db.Boolean, default=True)
    groups = db.relationship('Groups', secondary=ug_relations,
                             backref=db.backref('users'), lazy='subquery')

    def __init__(self, surname, name, chat_id, username):
        self.surname = surname
        self.name = name
        self.chat_id = chat_id
        self.username = username
        pass

    def __repr__(self):
        s = ""
        if self.surname is not None:
            s+= f"{self.surname} "
        if self.name is not None:
            s+= f"{self.name} "
        if self.patronymic is not None:
            s+= f"{self.patronymic} "
            # s+=f"\r\n Имя пользователя в telegram: {self.username}\r\n

        if len(self.groups) != 0:
            s += "\r\n Роль: "
            for g in self.groups:
                s += g.name + ', '
            s=s[:-2:]
            s += "\r\n Сервисы: "
            for g in self.groups:
                for source in g.sources:
                    s += source.name + ', '
            s=s[:-2:]
        else:
            s += "\r\nРоль: - "
            s += "\r\nСервисы: - "
        return s

    def add_groups(self, groups):
        if type(groups) is Groups:
            self.groups.append(groups)
        else:
            for g in groups:
                self.groups.append(g)


class Groups(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    # users = db.relationship('Users', secondary=ug_relations, backref=db.backref('users', lazy='dynamic'))
    sources = db.relationship('Sources', secondary=gs_relations, lazy='subquery', backref=db.backref('groups'))

class Sources(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    # groups = db.relationship('Groups', secondary=gs_relations, backref=db.backref('groups', lazy='dynamic'))
