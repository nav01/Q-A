from pyramid.view import (
    view_config,
    view_defaults
)

#Used to test the database connection.  Will not go to final production.
@view_defaults(renderer = 'templates/index.pt')
class DatabaseViews:
    def __init__(self,request):
        self.request = request

    @view_config(route_name='hits')
    def hits(self):
        hits = 'hits'
        result = self.request.db.test.update_one({hits:{'$exists': True}}, {'$inc': {hits: 1}})
        if result.modified_count == 0:
            result = {hits:1}
            self.request.db.test.insert_one(result)
        else:
            result = self.request.db.test.find_one({hits:{'$exists': True}})
        return result
