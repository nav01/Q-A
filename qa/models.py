from passlib.hash import pbkdf2_sha256
class User(object):
    COLLECTION = 'users'
    #database fields
    USERNAME = 'username'
    PASSWORD_HASH = 'password_hash'

    def create(values, db):
        if db[User.COLLECTION].find({User.USERNAME:values[User.USERNAME]}).limit(1).count() > 0:
            raise ValueError('Username already exists.')
        else:
            password_hash = pbkdf2_sha256.hash(values['password'])
            db[User.COLLECTION].insert({User.USERNAME:values[User.USERNAME],User.PASSWORD_HASH:password_hash})
