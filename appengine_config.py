from google.appengine.ext import vendor
vendor.add('lib')

appstats_CALC_RPC_COSTS = True

def webapp_add_wsgi_middleware(app):
    from google.appengine.ext.appstats import recording
    app = recording.appstats_wsgi_middleware(app)
    return app